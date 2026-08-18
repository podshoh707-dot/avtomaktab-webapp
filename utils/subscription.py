import time
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Setting
from sqlalchemy import select
import json

# Subscription check cache
# {user_id: (timestamp, is_subscribed)}
SUB_CACHE = {}

def parse_channel_info(ch: str) -> dict:
    """
    Kanal havolasi yoki username'ini tahlil qiladi.
    Tashqi havolalar (Instagram, Youtube va h.k.) Telegram API orqali tekshirilmaydi.
    """
    ch = ch.strip()
    if ch.startswith("http://") or ch.startswith("https://"):
        if "t.me/" in ch:
            part = ch.split("t.me/")[-1].strip("/")
            if part.startswith("+") or "joinchat" in part:
                return {
                    "is_external": False,
                    "chat_id": ch,
                    "url": ch,
                    "title": "📢 Telegram Kanal"
                }
            else:
                username = part.split("?")[0].split("/")[0]
                return {
                    "is_external": False,
                    "chat_id": f"@{username}",
                    "url": f"https://t.me/{username}",
                    "title": f"📢 @{username}"
                }
        else:
            # Tashqi sotsial tarmoq (masalan Instagram, Youtube, Veb-sayt)
            title = "📸 Instagram" if "instagram" in ch.lower() else ("▶️ YouTube" if "youtube" in ch.lower() else "🔗 Rasmiy Havola")
            return {
                "is_external": True,
                "chat_id": None,
                "url": ch,
                "title": title
            }
    else:
        clean_ch = ch if ch.startswith("@") or ch.startswith("-100") else f"@{ch}"
        url_name = clean_ch.replace("@", "")
        url = f"https://t.me/{url_name}" if not clean_ch.startswith("-100") else "https://t.me"
        return {
            "is_external": False,
            "chat_id": clean_ch,
            "url": url,
            "title": f"📢 {clean_ch}"
        }

async def check_user_subscription(bot: Bot, user_id: int, bypass_cache: bool = False) -> bool:
    """
    Foydalanuvchining barcha majburiy Telegram kanallarga obuna bo'lganligini tekshiradi.
    Kesh (cache) dan foydalanadi (obuna bo'lsa 1 soat, bo'lmasa 10 soniya saqlaydi).
    """
    now = time.time()
    if not bypass_cache and user_id in SUB_CACHE:
        cached = SUB_CACHE[user_id]
        if isinstance(cached, tuple) and len(cached) >= 2:
            ts, is_sub = cached[0], cached[1]
            cache_limit = 3600 if is_sub else 10 # 1 hour if subbed, 10 seconds if not
            if (now - ts) < cache_limit:
                return is_sub

    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        setting = result.scalars().first()
        channels = []
        if setting and setting.value and setting.value != "off":
            try:
                channels = json.loads(setting.value)
            except json.JSONDecodeError:
                channels = [setting.value]

    if not channels:
        return True
        
    is_subscribed = True
    for ch in channels:
        info = parse_channel_info(ch)
        # Tashqi havolalarni (Instagram va hokazo) Telegram bot tekshira olmaydi, ularni o'tkazib yuboramiz
        if info["is_external"] or not info["chat_id"]:
            continue
            
        try:
            member = await bot.get_chat_member(chat_id=info["chat_id"], user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                is_subscribed = False
                break
        except Exception as e:
            print(f"Sub check err ({info['chat_id']}): {e}")
            pass
            
    SUB_CACHE[user_id] = (now, is_subscribed)
    return is_subscribed

async def get_subscription_keyboard(bot: Bot):
    """Obuna bo'lish uchun kanallar ro'yxati bilan keyboard qaytaradi"""
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        setting = result.scalars().first()
        channels = []
        if setting and setting.value and setting.value != "off":
            try:
                channels = json.loads(setting.value)
            except json.JSONDecodeError:
                channels = [setting.value]
                
    inline_keyboard = []
    for ch in channels:
        info = parse_channel_info(ch)
        chat_title = info["title"]
        channel_url = info["url"]
        
        if not info["is_external"] and info["chat_id"]:
            try:
                chat = await bot.get_chat(chat_id=info["chat_id"])
                if chat.title:
                    chat_title = f"📢 {chat.title}"
                if chat.invite_link:
                    channel_url = chat.invite_link
                elif chat.username:
                    channel_url = f"https://t.me/{chat.username}"
            except Exception as e:
                pass
        
        inline_keyboard.append([InlineKeyboardButton(text=chat_title, url=channel_url)])
        
    inline_keyboard.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
