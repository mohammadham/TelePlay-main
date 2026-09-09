"""
Telegram Multi-Client Pool Manager.

Manages separate pools of Bot Clients and User (MTProto) Accounts.
Handles round-robin selection, pressure-based selection, random selection,
and error-based selection. Tracks account health and errors.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import deque

from pyrogram import Client

from .config import get_settings
from .telegram import clients as bot_clients, tg_client

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Strategy for account selection in uploads."""
    ROUND_ROBIN = "round_robin"
    PRESSURE = "pressure"
    RANDOM = "random"
    ERROR_BASED = "error_based"


class PoolHealth:
    """Health status for a single client."""
    def __init__(self, name: str, is_connected: bool = False, flood_wait_until: Optional[float] = None):
        self.name = name
        self.is_connected = is_connected
        self.flood_wait_until = flood_wait_until


class TelegramPoolManager:
    """Manages bot and user client pools with flexible selection strategies."""

    def __init__(self, strategy: SelectionStrategy = SelectionStrategy.ROUND_ROBIN):
        self.bot_pool: Dict[int, Client] = {}  # index -> Client
        self.user_pool: Dict[int, Client] = {}  # index -> Client (lazy loaded)
        self.bot_pool_order: List[int] = []  # used order for round-robin
        self.user_pool_order: List[int] = []
        self.bot_index = 0
        self.user_index = 0
        self.strategy = strategy

        # Error tracking for error_based strategy
        self.user_errors: Dict[int, int] = {}  # index -> error count
        self.user_last_error: Dict[int, float] = {}  # index -> timestamp of last error
        self.user_last_success: Dict[int, float] = {}  # index -> timestamp of last success

        # Pressure tracking for pressure strategy
        self.user_pressure: Dict[int, int] = {}  # index -> concurrent upload count
        self.user_queue: Dict[int, deque] = {}  # index -> pending upload queue

    def set_strategy(self, strategy: SelectionStrategy):
        """Update the selection strategy."""
        self.strategy = strategy
        logger.info(f"Upload strategy changed to: {strategy.value}")

    def add_bot(self, client: Client, index: int) -> None:
        """Add a bot client to the pool."""
        self.bot_pool[index] = client
        if index not in self.bot_pool_order:
            self.bot_pool_order.append(index)
        logger.info("Bot client %d added to pool", index)

    def remove_bot(self, index: int) -> None:
        """Remove a bot client from the pool."""
        self.bot_pool.pop(index, None)
        self.bot_pool_order = [i for i in self.bot_pool_order if i != index]
        logger.info("Bot client %d removed from pool", index)

    def add_user(self, client: Client, index: int) -> None:
        """Add a user (MTProto) client to the pool."""
        self.user_pool[index] = client
        if index not in self.user_pool_order:
            self.user_pool_order.append(index)
        self.user_errors[index] = 0
        self.user_last_error[index] = 0
        self.user_last_success[index] = 0
        self.user_pressure[index] = 0
        self.user_queue[index] = deque()
        logger.info("User client %d added to pool", index)

    def remove_user(self, index: int) -> None:
        """Remove a user client from the pool."""
        self.user_pool.pop(index, None)
        self.user_pool_order = [i for i in self.user_pool_order if i != index]
        self.user_errors.pop(index, None)
        self.user_last_error.pop(index, None)
        self.user_last_success.pop(index, None)
        self.user_pressure.pop(index, None)
        self.user_queue.pop(index, None)
        logger.info("User client %d removed from pool", index)

    def increment_pressure(self, user_index: int):
        """Increment pressure counter for a user account."""
        if user_index in self.user_pressure:
            self.user_pressure[user_index] += 1

    def decrement_pressure(self, user_index: int):
        """Decrement pressure counter for a user account."""
        if user_index in self.user_pressure:
            self.user_pressure[user_index] = max(0, self.user_pressure[user_index] - 1)

    def record_error(self, user_index: int):
        """Record a failed upload for a user account."""
        self.user_errors[user_index] = self.user_errors.get(user_index, 0) + 1
        self.user_last_error[user_index] = asyncio.get_event_loop().time()

    def record_success(self, user_index: int):
        """Record a successful upload for a user account."""
        self.user_errors[user_index] = 0  # Reset on success
        self.user_last_success[user_index] = asyncio.get_event_loop().time()

    def get_bot(self, purpose: str = "MAIN") -> Optional[Client]:
        """Get a bot client using current selection strategy."""
        if not self.bot_pool:
            return None

        if self.strategy == SelectionStrategy.RANDOM:
            available = [i for i in self.bot_pool_order if self.bot_pool.get(i) is not None]
            if not available:
                return None
            import random
            return self.bot_pool[random.choice(available)]
        else:
            return self._get_bot_cycle()

    def _get_bot_cycle(self) -> Optional[Client]:
        """Get a bot client using round-robin selection."""
        pool_size = len(self.bot_pool_order)
        if pool_size == 0:
            return None

        # Advance index, skip inactive clients
        for _ in range(pool_size):
            idx = self.bot_pool_order[self.bot_index % pool_size]
            client = self.bot_pool.get(idx)
            if client is not None:
                self.bot_index = (self.bot_index + 1) % pool_size
                return client
            self.bot_index = (self.bot_index + 1) % pool_size

        return None

    def get_user(self, purpose: str = "STORAGE") -> Optional[Client]:
        """Get a user (MTProto) client using current selection strategy."""
        if not self.user_pool:
            return None

        if self.strategy == SelectionStrategy.RANDOM:
            import random
            available = [i for i in self.user_pool_order if self.user_pool.get(i) is not None]
            if not available:
                return None
            return self.user_pool[random.choice(available)]
        elif self.strategy == SelectionStrategy.PRESSURE:
            return self._get_user_pressure()
        elif self.strategy == SelectionStrategy.ERROR_BASED:
            return self._get_user_error_based()
        else:  # ROUND_ROBIN
            return self._get_user_cycle()

    def _get_user_pressure(self) -> Optional[Client]:
        """Select user with lowest pressure (queue length)."""
        pool_size = len(self.user_pool_order)
        if pool_size == 0:
            return None

        # Find user with minimum pressure
        min_pressure = float('inf')
        selected_idx = None
        for i in range(pool_size):
            idx = self.user_pool_order[i % pool_size]
            client = self.user_pool.get(idx)
            if client is not None:
                pressure = self.user_pressure.get(idx, 0)
                if pressure < min_pressure:
                    min_pressure = pressure
                    selected_idx = idx

        if selected_idx is not None:
            self.bot_index = (self.user_pool_order.index(selected_idx) + 1) % pool_size
            return self.user_pool[selected_idx]
        return None

    def _get_user_error_based(self) -> Optional[Client]:
        """Select user with least errors (error_based strategy)."""
        pool_size = len(self.user_pool_order)
        if pool_size == 0:
            return None

        # Find user with minimum errors
        min_errors = float('inf')
        selected_idx = None
        for i in range(pool_size):
            idx = self.user_pool_order[i % pool_size]
            client = self.user_pool.get(idx)
            if client is not None:
                error_count = self.user_errors.get(idx, 0)
                if error_count < min_errors:
                    min_errors = error_count
                    selected_idx = idx

        if selected_idx is not None:
            self.bot_index = (self.user_pool_order.index(selected_idx) + 1) % pool_size
            return self.user_pool[selected_idx]
        return None

    def _get_user_cycle(self) -> Optional[Client]:
        """Get a user client using round-robin selection."""
        pool_size = len(self.user_pool_order)
        if pool_size == 0:
            return None

        for _ in range(pool_size):
            idx = self.user_pool_order[self.user_index % pool_size]
            client = self.user_pool.get(idx)
            if client is not None:
                self.user_index = (self.user_index + 1) % pool_size
                return client
            self.user_index = (self.user_index + 1) % pool_size

        return None

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all clients in the pool."""
        health: Dict[str, Any] = {
            "bot_clients": {},
            "user_clients": {},
            "strategy": self.strategy.value,
            "total_bots": len(self.bot_pool),
            "total_users": len(self.user_pool),
        }

        # Check bot clients
        pool_size = len(self.bot_pool_order)
        for i in range(pool_size if pool_size > 0 else 1):
            idx = self.bot_pool_order[i % pool_size] if pool_size > 0 else 0
            client = self.bot_pool.get(idx)
            if client:
                try:
                    me = await client.get_me()
                    health["bot_clients"][idx] = {
                        "name": client.name,
                        "username": me.username,
                        "is_connected": client.is_connected,
                    }
                except Exception as e:
                    health["bot_clients"][idx] = {
                        "name": client.name,
                        "error": str(e),
                        "is_connected": False,
                    }
            else:
                health["bot_clients"][idx] = {"name": str(idx), "is_connected": False}

        # Check user clients
        user_pool_size = len(self.user_pool_order)
        for i in range(user_pool_size if user_pool_size > 0 else 1):
            idx = self.user_pool_order[i % user_pool_size] if user_pool_size > 0 else 0
            client = self.user_pool.get(idx)
            if client:
                try:
                    me = await client.get_me()
                    health["user_clients"][idx] = {
                        "name": client.name,
                        "username": me.username,
                        "is_connected": client.is_connected,
                        "errors": self.user_errors.get(idx, 0),
                        "last_error": self.user_last_error.get(idx),
                        "last_success": self.user_last_success.get(idx),
                        "pressure": self.user_pressure.get(idx, 0),
                    }
                except Exception as e:
                    health["user_clients"][idx] = {
                        "name": client.name,
                        "error": str(e),
                        "is_connected": False,
                    }
            else:
                health["user_clients"][idx] = {"name": str(idx), "is_connected": False}

        return health


# Global pool manager instance
pool_manager = TelegramPoolManager()


async def init_pool_manager():
    """Initialize pool manager from existing bot clients and user accounts."""
    from .telegram import clients as bot_clients_list
    for i, client in enumerate(bot_clients_list):
        pool_manager.add_bot(client, i)
    logger.info("Pool manager initialized with %d bot clients", len(bot_clients_list))

    # Load active user accounts from database
    await load_user_accounts()


async def load_user_accounts():
    """Load active MTProto user accounts from database into pool."""
    try:
        from .database import get_sessionmaker
        from .models import UserAccount
        from .encryption import decrypt
        from .config import get_settings

        session_maker = get_sessionmaker()
        async with session_maker() as db:
            from sqlalchemy import select
            result = await db.execute(select(UserAccount).where(UserAccount.is_active == True))
            accounts = result.scalars().all()

            settings = get_settings()
            for account in accounts:
                try:
                    session_str = decrypt(account.session_string_encrypted)
                    api_hash = decrypt(account.api_hash_encrypted)

                    client = Client(
                        name=f"user_{account.id}",
                        api_id=account.api_id,
                        api_hash=api_hash,
                        session_string=session_str,
                        ipv6=False,
                    )
                    await client.start()
                    pool_manager.add_user(client, len(pool_manager.user_pool))
                    logger.info("User account %s (%s) added to pool", account.name, account.purpose)
                except Exception as e:
                    logger.error("Failed to load user account %s: %s", account.name, e)
    except Exception as e:
        logger.warning("Could not load user accounts from database: %s", e)
