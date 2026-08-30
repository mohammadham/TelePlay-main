"""
Custom streaming utilities for Telegram media files.
Multi-client parallel streaming for maximum download speed.
"""
import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from pyrogram import Client

from .telegram import clients
from .config import get_settings

settings = get_settings()

logger = logging.getLogger("streamer")
logger.setLevel(logging.INFO)


# Global semaphores to limit concurrency per client across all streams
_client_semaphores = {}

def get_client_semaphore(client_index: int) -> asyncio.Semaphore:
    if client_index not in _client_semaphores:
        # Use the configured concurrency limit
        _client_semaphores[client_index] = asyncio.Semaphore(settings.telegram_client_concurrency)
    return _client_semaphores[client_index]


async def parallel_stream_generator(
    initial_message,
    offset: int,
    length: int,
    chunk_size: int = 1024 * 1024,
    concurrency: int = None,
):
    """
    Fetch file chunks in parallel using the client pool.
    Each worker uses its own client and fetches its own Message object
    to avoid cross-bot FILE_REFERENCE_INVALID errors.
    """
    pool_size = len(clients)
    if concurrency is None:
        concurrency = max(pool_size, 1)

    start_chunk = offset // chunk_size
    end_chunk = (offset + length - 1) // chunk_size
    total_chunks = end_chunk - start_chunk + 1

    chat_id = initial_message.chat.id
    message_id = initial_message.id

    # ── Pre-fetch messages for ALL clients in parallel (eliminates lag) ──
    async def fetch_msg(client, idx):
        try:
            msg = await client.get_messages(chat_id, message_id)
            if msg and (msg.document or msg.video or msg.audio):
                return (idx, msg)
            else:
                logger.warning("Bot %d: message %d has no media", idx, message_id)
                return (idx, None)
        except Exception as e:
            logger.error("Bot %d: failed to fetch message: %s", idx, e)
            return (idx, None)

    # Fetch all in parallel — fast!
    fetch_tasks = []
    for i in range(concurrency):
        c = clients[i % pool_size]
        c_idx = getattr(c, "pool_index", i % pool_size)
        fetch_tasks.append(fetch_msg(c, c_idx))

    fetch_results = await asyncio.gather(*fetch_tasks)
    client_messages = {idx: msg for idx, msg in fetch_results if msg is not None}

    if not client_messages:
        logger.error("No client could fetch the message")
        return

    # Task queue
    task_queue = asyncio.Queue()
    for i in range(total_chunks):
        task_queue.put_nowait(start_chunk + i)

    # Pre-create Futures for ordered yielding
    loop = asyncio.get_running_loop()
    results = {
        (start_chunk + i): loop.create_future()
        for i in range(total_chunks)
    }

    async def worker(worker_id: int):
        client = clients[worker_id % pool_size]
        c_idx = getattr(client, "pool_index", worker_id % pool_size)

        # Get semaphore for this client to ensure we don't exceed max_concurrent_transmissions
        # This prevents the "Request refused" or internal queue buildup in Pyrogram
        semaphore = get_client_semaphore(c_idx)

        msg = client_messages.get(c_idx)
        if msg is None:
            return  # This client couldn't access the file

        while not task_queue.empty():
            try:
                chunk_idx = task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                # Wait for slot before requesting chunk
                async with semaphore:
                    data = b""
                    async for part in client.stream_media(
                        msg, limit=1, offset=chunk_idx
                    ):
                        data += part

                if not results[chunk_idx].done():
                    results[chunk_idx].set_result(data)
            except Exception as e:
                logger.error("Bot %d failed chunk %d: %s", c_idx, chunk_idx, e)
                if not results[chunk_idx].done():
                    results[chunk_idx].set_exception(e)
            finally:
                task_queue.task_done()

    # Launch workers
    worker_tasks = [
        asyncio.create_task(worker(i)) for i in range(concurrency)
    ]

    # Yield results in order
    current_idx = start_chunk
    try:
        for _ in range(total_chunks):
            chunk_data = await results[current_idx]
            yield chunk_data
            del results[current_idx]
            current_idx += 1
    finally:
        for w in worker_tasks:
            w.cancel()


async def stream_file(
    client: Client,          # kept for API compat; pool is used instead
    message,
    from_bytes: int,
    until_bytes: int,
) -> AsyncGenerator[bytes, None]:
    """Stream a file range using the multi-client pool."""
    CHUNK_SIZE = 1024 * 1024

    total_bytes_needed = until_bytes - from_bytes + 1
    bytes_yielded = 0
    bytes_to_skip = from_bytes % CHUNK_SIZE

    logger.debug("Streaming %d-%d (%d bytes)", from_bytes, until_bytes, total_bytes_needed)

    async for chunk in parallel_stream_generator(
        message, from_bytes, total_bytes_needed
    ):
        if bytes_to_skip > 0:
            chunk = chunk[bytes_to_skip:]
            bytes_to_skip = 0

        remaining = total_bytes_needed - bytes_yielded
        if len(chunk) > remaining:
            chunk = chunk[:remaining]

        yield chunk
        bytes_yielded += len(chunk)
        if bytes_yielded >= total_bytes_needed:
            break
