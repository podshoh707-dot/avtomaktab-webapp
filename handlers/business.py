from aiogram import Router, F
from aiogram.types import Message

business_router = Router()

@business_router.business_message(F.text)
async def handle_business_message(message: Message):
    """
    Biznes akkaunt orqali kelgan xabarlarga javob qaytarish.
    Bu bot egasining yoki ulangan foydalanuvchining shaxsiy akkauntiga boshqalar yozganda ishlaydi.
    """
    bot_info = await message.bot.get_me()
    user_name = message.from_user.first_name if message.from_user else "Hurmatli foydalanuvchi"
    
    text = (
        "👑 <b>AVTOMAKTAB PREMIUM XIZMATI</b> 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Assalomu alaykum, <b>{user_name}</b>! 👋\n\n"
        "Siz ayni damda <b>band bo'lgan ofitsial akkauntga</b> xabar yo'lladingiz. "
        "Xabaringiz xavfsiz saqlandi va akkaunt egasi onlayn bo'lishi bilan albatta javob beradi.\n\n"
        "🚦 <i>Kutish vaqtini unumli o'tkazishni xohlaysizmi?</i>\n"
        "Bizning maxsus botimiz orqali haydovchilik guvohnomasi uchun imtihonlarga tayyorlanishingiz mumkin!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>Bot xizmatlaridan bepul foydalanish uchun bosing:</b>"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Avtomaktab Botiga o'tish", url=f"https://t.me/{bot_info.username}")]
    ])
    
    await message.reply(text, reply_markup=markup, parse_mode="HTML")
