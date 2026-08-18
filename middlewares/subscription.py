from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from utils.subscription import check_user_subscription, get_subscription_keyboard

class SubscriptionCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        
        # ── 1. "check_sub" callback'ini DOIM o'tkazib yuboramiz ──
        if isinstance(event, CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)

        # ── 2. Guruh/supergroup xabar va callback'larini o'tkazib yuboramiz ──
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat
        
        if chat and chat.type not in ("private",):
            return await handler(event, data)

        bot = data.get("bot")
        user = event.from_user
        
        if not user or not bot:
            return await handler(event, data)
            
        # Obunani check_user_subscription funksiyamiz orqali xavfsiz tekshiramiz
        is_subscribed = await check_user_subscription(bot, user.id)
        
        if not is_subscribed:
            try:
                keyboard = await get_subscription_keyboard(bot)
                text = (
                    "Botdan foydalanish uchun quyidagi rasmiy kanallarimizga a'zo bo'lishingiz kerak!\n\n"
                    "Iltimos, pastdagi tugmalar orqali kanallarga a'zo bo'ling va 'Obunani tekshirish' tugmasini bosing."
                )
                if isinstance(event, Message):
                    await event.answer(text, reply_markup=keyboard)
                elif isinstance(event, CallbackQuery):
                    await bot.send_message(chat_id=user.id, text=text, reply_markup=keyboard)
            except Exception as e:
                print(f"Send sub message err: {e}")

            if isinstance(event, CallbackQuery):
                await event.answer("Siz barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
            return

        return await handler(event, data)
