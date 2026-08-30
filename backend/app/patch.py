import asyncio
import functools
from typing import Dict, Optional, Union
from pyrogram import handlers, types
from pyrogram import Client as PyroClient
from pyrogram import errors, raw, session, types
from pyrogram.filters import Filter


class ListenerCanceled(Exception):
    pass


class PatchedClient(PyroClient):
    def __init__(self, *args, **kwargs):
        self.listeners: Dict[str, Dict[str, Union[asyncio.Future, Filter, None]]] = {}
        super().__init__(*args, **kwargs)

    async def start(self):
        await super().start()

    async def stop(self, *args):
        await super().stop()

    """Custom methods for conversation support from pyromod && pyropatch"""

    async def check_cbd(self, buttons: types.InlineKeyboardMarkup):
        if not buttons:
            return False
        for button_row in buttons.inline_keyboard:
            for button in button_row:
                if button.callback_data:
                    return True
        return False

    async def wait_for_callback_query(
        self,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        timeout: Optional[int] = None,
        filters: Optional[Filter] = None,
    ) -> types.CallbackQuery:
        if chat_id:
            if not message_id:
                raise TypeError("message_id is required")
            msg = await self.get_messages(chat_id=chat_id, message_ids=message_id)
            if msg.empty:  # type: ignore
                raise ValueError("message id is invalid")
            if not msg.from_user.is_self:  # type: ignore
                raise ValueError("cannot use self message")
            # if not await self.check_cbd(msg.reply_markup):  # type: ignore
            #     raise TypeError("message type invalid [no callback button]")
            key = f"{chat_id}:{message_id}"
        elif inline_message_id:
            key = inline_message_id
        else:
            raise TypeError("chat_id or inline_message_id is required")
        future = self.loop.create_future()
        future.add_done_callback(functools.partial(self.remove_listener, key))
        self.listeners.update({key: {"future": future, "filters": filters}})
        return await asyncio.wait_for(future, timeout)

    async def wait_for_message(
        self,
        chat_id: Union[str, int],
        filters: Optional[Filter] = None,
        timeout: Optional[int] = None,
    ) -> types.Message:
        if not isinstance(chat_id, int):
            chat = await self.get_chat(chat_id)
            chat_id = chat.id  # type: ignore
        future = self.loop.create_future()
        future.add_done_callback(functools.partial(self.remove_listener, str(chat_id)))
        self.listeners.update({str(chat_id): {"future": future, "filters": filters}})
        return await asyncio.wait_for(future, timeout)

    async def wait_for_inline_query(
        self, user_id: int, filters: Optional[Filter] = None, timeout: Optional[int] = None
    ):
        future = self.loop.create_future()
        future.add_done_callback(functools.partial(self.remove_listener, str(user_id)))
        self.listeners.update({str(user_id): {"future": future, "filters": filters}})
        return await asyncio.wait_for(future, timeout)

    async def wait_for_inline_result(
        self, user_id: int, filters: Optional[Filter] = None, timeout: Optional[int] = None
    ):
        future = self.loop.create_future()
        future.add_done_callback(functools.partial(self.remove_listener, str(user_id)))
        self.listeners.update({str(user_id): {"future": future, "filters": filters}})
        return await asyncio.wait_for(future, timeout)

    def remove_listener(self, key: str, future=None):
        if key in self.listeners and future == self.listeners[key]["future"]:
            self.listeners.pop(key)

    def cancel_listener(self, key: str):

        listener = self.listeners.get(key)
        if not listener or listener["future"].done():  # type: ignore
            return
        listener["future"].set_exception(ListenerCanceled())  # type: ignore
        self.remove_listener(key, listener["future"])

    async def invoke(
        self,
        query: raw.core.TLObject,
        retries: int = session.Session.MAX_RETRIES,
        timeout: float = session.Session.WAIT_TIMEOUT,
        sleep_threshold: float = None,  # type: ignore
    ):
        while True:
            try:
                res = await super().invoke(
                    query=query,
                    retries=retries,
                    timeout=timeout,
                    sleep_threshold=sleep_threshold,
                )
                return res
            except (errors.FloodWait) as e:
                await asyncio.sleep(e.value + 2)  # type: ignore
                    
async def resolve_listener(
    client: PatchedClient,
    update: Union[types.CallbackQuery, types.Message, types.InlineQuery, types.ChosenInlineResult],
):
    if isinstance(update, types.CallbackQuery):
        if update.message:
            key = f"{update.message.chat.id}:{update.message.id}"
        elif update.inline_message_id:
            key = update.inline_message_id
        else:
            return
    elif isinstance(update, (types.ChosenInlineResult, types.InlineQuery)):
        key = str(update.from_user.id)
    else:
        key = str(update.chat.id)  # type: ignore

    listener = client.listeners.get(key)

    if listener and not listener["future"].done():  # type: ignore
        if callable(listener["filters"]):
            if not await listener["filters"](client, update):
                update.continue_propagation()
        listener["future"].set_result(update)  # type: ignore
        update.stop_propagation()
    else:
        if listener and listener["future"].done():  # type: ignore
            client.remove_listener(key, listener["future"])


class Client(PatchedClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def start(self, *args, **kwargs):
        self.add_handler(handlers.CallbackQueryHandler(resolve_listener), group=-1)
        self.add_handler(handlers.InlineQueryHandler(resolve_listener), group=-1)
        self.add_handler(handlers.ChosenInlineResultHandler(resolve_listener), group=-1)
        self.add_handler(handlers.MessageHandler(resolve_listener), group=-1)
        await super().start(*args, **kwargs)