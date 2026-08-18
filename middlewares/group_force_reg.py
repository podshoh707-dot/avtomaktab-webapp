import asyncio
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from database import async_session, User, BotGroup
from sqlalchemy import select
from utils.subscription import check_user_subscription

# Guruh va user ogohlantirishlari uchun kesh (spamni oldini olish)
# {user_id: timestamp}
USER_WARNING_COOLDOWN = {}
# {chat_id: timestamp}
CHAT_WARNING_COOLDOWN = {}

USER_WARNING_TIME = 300 # 5 minut
CHAT_WARNING_TIME = 60  # 1 minut

class GroupForceRegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Faqat message eventlar va guruhlar uchun ishlaydi
        if not isinstance(event, Message) or not event.chat or event.chat.type not in ["group", "supergroup"]:
            return await handler(event, data)
            
        # /bot kabi buyruqlarni o'tkazib yuborish kerakmi?
        if event.text and event.text.startswith("/"):
            return await handler(event, data)
            
        # Adminlar yoki botlarga tegmaymiz, yoki anonim adminlarga
        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)
            
        if getattr(event, "sender_chat", None) and event.sender_chat.id == event.chat.id:
            return await handler(event, data)

        # Admin ekanligini tekshiramiz
        try:
            chat_member = await event.chat.get_member(event.from_user.id)
            if chat_member.status in ["administrator", "creator"]:
                return await handler(event, data)
        except Exception:
            pass

        # Guruhda subscription_guard yoqilganmi?
        async with async_session() as session:
            group_result = await session.execute(select(BotGroup).where(BotGroup.chat_id == event.chat.id))
            group = group_result.scalars().first()
            if not group or not group.subscription_guard:
                return await handler(event, data)

        # Botga ro'yxatdan o'tganligini va kanallarga obuna bo'lganligini tekshiramiz
        async with async_session() as session:
            result = await session.execute(select(User).where(User.telegram_id == event.from_user.id))
            user = result.scalars().first()
            
        has_started = bool(user and user.language and user.full_name and user.phone)
        is_subscribed = False
        
        if has_started:
            bot = data.get("bot") or event.bot
            is_subscribed = await check_user_subscription(bot, event.from_user.id)
            
        # Agar hamma narsa joyida bo'lsa
        if has_started and is_subscribed:
            return await handler(event, data)
            
        # Agar ro'yxatdan o'tmagan yoki obuna bo'lmagan bo'lsa
        try:
            # Guruhda yozishni taqiqlaymiz (agar xohlasangiz buni o'chirib qo'yishingiz mumkin, shunchaki xabarni o'chirish ham yetarli bo'ladi. Lekin oldingi versiyada bor edi)
            # await event.chat.restrict(
            #     event.from_user.id,
            #     permissions=ChatPermissions(can_send_messages=False)
            # )
            pass
        except Exception:
            pass
            
        try:
            await event.delete()
        except Exception:
            pass
            
        now = time.time()
        last_user_warn = USER_WARNING_COOLDOWN.get(event.from_user.id, 0)
        last_chat_warn = CHAT_WARNING_COOLDOWN.get(event.chat.id, 0)
        
        # Spam bo'lmasligi uchun cooldown tekshiramiz
        if (now - last_user_warn) < USER_WARNING_TIME or (now - last_chat_warn) < CHAT_WARNING_TIME:
            return
            
        bot_info = await event.bot.get_me()
        bot_username = bot_info.username
        
        if not has_started:
            text = (
                f"🚫 <b>Hurmatli {event.from_user.first_name}!</b>\n\n"
                f"Guruhda xabar yozish uchun avvalo bizning rasmiy botimizdan ro'yxatdan o'tishingiz kerak!\n\n"
                f"👇 <b>Iltimos, quyidagi tugma orqali botga o'ting va ro'yxatdan o'ting:</b>"
            )
            payload = f"unmute_{event.chat.id}"
            url = f"https://t.me/{bot_username}?start={payload}"
        else:
            text = (
                f"🚫 <b>Hurmatli {event.from_user.first_name}!</b>\n\n"
                f"Guruhda xabar yozish uchun rasmiy kanallarimizga obuna bo'lishingiz kerak!\n\n"
                f"👇 <b>Iltimos, botga o'tib, obunani yakunlang:</b>"
            )
            url = f"https://t.me/{bot_username}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Botga o'tish", url=url)]
        ])
        
        try:
            photo = FSInputFile("welcome.png")
            warning = await event.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception:
            # Agar rasm topilmasa yoki yuborishda xato bo'lsa, matnli xabar
            warning = await event.answer(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
        USER_WARNING_COOLDOWN[event.from_user.id] = now
        CHAT_WARNING_COOLDOWN[event.chat.id] = now
        
        async def delete_later(msg, delay):
            await asyncio.sleep(delay)
            try:
                await msg.delete()
            except:
                pass
                
        asyncio.create_task(delete_later(warning, 60))
        # Handlerga o'tishni to'xtatamiz
        return
