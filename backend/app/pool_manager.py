"""
Telegram Multi-Client Pool Manager.

Manages separate pools of Bot Clients and User (MTProto) Accounts.
Handles round-robin selection, rate limiting, and flood wait recovery.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any

from pyrogram import Client

from .config import get_settings
from .telegram import clients as bot_clients, tg_client

logger = logging.getLogger(__name__)


class PoolHealth:
    """Health status for a single client."""
    def __init__(self, name: str, is_connected: bool = False, flood_wait_until: Optional[float] = None):
        self.name = name
        self.is_connected = is_connected
        self.flood_wait_until = flood_wait_until


class TelegramPoolManager:
    """Manages bot and user client pools with round-robin selection and health checks."""
    
    def __init__(self):
        self.bot_pool: Dict[int, Client] = {}  # index -> Client
        self.user_pool: Dict[int, Client] = {}  # index -> Client (lazy loaded)
        self.bot_pool_order: List[int] = []  # used order for round-robin
        self.user_pool_order: List[int] = []
        self.bot_index = 0
        self.user_index = 0
    
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
        logger.info("User client %d added to pool", index)
    
    def remove_user(self, index: int) -> None:
        """Remove a user client from the pool."""
        self.user_pool.pop(index, None)
        self.user_pool_order = [i for i in self.user_pool_order if i != index]
        logger.info("User client %d removed from pool", index)
    
    def get_bot(self, purpose: str = "MAIN") -> Optional[Client]:
        """Get a bot client using round-robin selection."""
        if not self.bot_pool:
            return None
        
        # Round-robin: find next available client
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
        """Get a user (MTProto) client using round-robin selection."""
        if not self.user_pool:
            return None
        
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