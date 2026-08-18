from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from database import async_session, User, Setting
from sqlalchemy import select
from locales import get_text
import re
from datetime import datetime, timedelta

WEBAPP_URL = "https://avtomaktab-webapp.vercel.app/"

registration_router = Router()

class RegistrationStates(StatesGroup):
    language = State()
    full_name = State()
    phone = State()

@registration_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    payload = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else None
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        
        # Agar foydalanuvchi allaqachon ro'yxatdan to'liq o'tgan bo'lsa
        if user and user.language and user.full_name and user.phone:
            if payload and payload.startswith("unmute_"):
                chat_id_str = payload.replace("unmute_", "")
                try:
                    from aiogram.types import ChatPermissions
                    await bot.restrict_chat_member(
                        int(chat_id_str), 
                        message.from_user.id, 
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_audios=True,
                            can_send_documents=True,
                            can_send_photos=True,
                            can_send_videos=True,
                            can_send_video_notes=True,
                            can_send_voice_notes=True,
                            can_send_polls=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True,
                            can_change_info=False,
                            can_invite_users=True,
                            can_pin_messages=False
                        )
                    )
                    await message.answer("✅ Guruhda yozish uchun ruxsat berildi! Endi bemalol guruhga qaytib yozishingiz mumkin.")
                except Exception as e:
                    print(f"Error unmuting: {e}")

            # ⚔️ Duel chaqiruvi
            if payload and payload.startswith("duel_"):
                inviter_id_str = payload.replace("duel_", "")
                if inviter_id_str.isdigit():
                    inviter_id = int(inviter_id_str)
                    if inviter_id != message.from_user.id:
                        from handlers.duel import handle_duel_invite
                        await handle_duel_invite(
                            bot, inviter_id,
                            message.from_user.id, message.from_user.full_name
                        )
                        return

            # Asosiy menyuni chiqarish
            await send_main_menu(message, user.language, user.full_name)
            return
            
        if payload and payload.startswith("unmute_"):
            await state.update_data(unmute_chat_id=payload.replace("unmute_", ""))
            
        # Agar yangi bo'lsa, bazaga qo'shamiz
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name, # vaqtinchalik
                language=None,
                is_premium=True,
                premium_expires_at=datetime.utcnow() + timedelta(days=5)
            )
            session.add(user)
            await session.commit()
            
            # Referal check
            if payload and payload.startswith("ref_"):
                inviter_id_str = payload.replace("ref_", "")
                if inviter_id_str.isdigit():
                    inviter_id = int(inviter_id_str)
                    if inviter_id != message.from_user.id:
                        user.referred_by = inviter_id
                        result_inviter = await session.execute(select(User).where(User.telegram_id == inviter_id))
                        inviter = result_inviter.scalars().first()
                        if inviter:
                            inviter.referrals_count = (inviter.referrals_count or 0) + 1
                            if inviter.is_premium and inviter.premium_expires_at and inviter.premium_expires_at > datetime.utcnow():
                                inviter.premium_expires_at += timedelta(days=1)
                            else:
                                inviter.is_premium = True
                                inviter.premium_expires_at = datetime.utcnow() + timedelta(days=1)
                            await session.commit()
                            try:
                                await bot.send_message(
                                    inviter_id,
                                    f"🎁 <b>TABRIKLAYMIZ!</b>\n\nSizning taklif havolangiz orqali <b>{message.from_user.full_name}</b> botga qo'shildi!\n\n"
                                    f"⭐️ Sizga <b>+1 KUN VIP PREMIUM</b> sovg'a qilindi!\n"
                                    f"👥 Jami taklif qilgan do'stlaringiz: <b>{inviter.referrals_count} nafar</b>",
                                    parse_mode="HTML"
                                )
                            except:
                                pass
    
    # Til tanlash menyusi
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇺🇿 Ўзбекча")],
            [KeyboardButton(text="🇷🇺 Русский")]
        ],
        resize_keyboard=True
    )
    await message.answer("Iltimos, tilni tanlang:\nИлтимос, тилни танланг:\nПожалуйста, выберите язык:", reply_markup=kb)
    await state.set_state(RegistrationStates.language)


@registration_router.message(RegistrationStates.language)
async def process_language(message: types.Message, state: FSMContext):
    lang_map = {
        "🇺🇿 O'zbekcha": "uz",
        "🇺🇿 Ўзбекча": "uz_cyr",
        "🇷🇺 Русский": "ru"
    }
    
    chosen_lang = lang_map.get(message.text)
    if not chosen_lang:
        await message.answer("Iltimos, pastdagi tugmalardan birini tanlang.")
        return
        
    await state.update_data(language=chosen_lang)
    
    # Check if user already exists
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        
    if user and user.full_name and user.phone:
        # User is already registered, just update their language
        async with async_session() as session:
            result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            db_user = result.scalars().first()
            if db_user:
                db_user.language = chosen_lang
                await session.commit()
        await state.clear()
        
        await message.answer(get_text(chosen_lang, "lang_changed"), reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message, chosen_lang, user.full_name)
    else:
        # F.I.SH so'rash (Registration flow)
        text = get_text(chosen_lang, "enter_fullname")
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await state.set_state(RegistrationStates.full_name)


@registration_router.message(RegistrationStates.full_name)
async def process_fullname(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 3:
        # Tilni state dan olamiz
        data = await state.get_data()
        lang = data.get("language", "uz")
        await message.answer(get_text(lang, "enter_fullname"))
        return
        
    await state.update_data(full_name=full_name)
    
    # Raqam so'rash
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    btn_text = get_text(lang, "btn_send_phone")
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn_text, request_contact=True)]],
        resize_keyboard=True
    )
    
    await message.answer(get_text(lang, "send_phone"), reply_markup=kb)
    await state.set_state(RegistrationStates.phone)


@registration_router.message(RegistrationStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    phone = None
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        # Oddiy text bo'lsa, telefon formatini tekshiramiz
        text_phone = message.text.strip().replace(" ", "")
        if re.match(r'^\+?998\d{9}$', text_phone):
            phone = text_phone
            
    if not phone:
        await message.answer(get_text(lang, "invalid_phone"))
        return
        
    # Bazaga saqlash
    full_name = data.get("full_name")
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()
        if user:
            user.language = lang
            user.full_name = full_name
            user.phone = phone
            await session.commit()
            
    unmute_chat_id = data.get("unmute_chat_id")
    if unmute_chat_id:
        try:
            from aiogram.types import ChatPermissions
            await message.bot.restrict_chat_member(
                int(unmute_chat_id), 
                message.from_user.id, 
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=False,
                    can_invite_users=True,
                    can_pin_messages=False
                )
            )
            await message.answer("✅ Guruhda yozish uchun ruxsat berildi! Endi bemalol guruhga qaytib yozishingiz mumkin.")
        except Exception as e:
            print(f"Error unmuting after registration: {e}")

    await state.clear()
    
    await message.answer(get_text(lang, "reg_success"))
    await send_main_menu(message, lang, full_name)


async def send_main_menu(message: types.Message, lang: str, name: str):
    """Asosiy menyuni yuborish uchun yordamchi funksiya"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Test Ishlash (1242 ta YHQ)")],
            [KeyboardButton(text="🎓 GAI Imtihoni (Sertifikatli)"), KeyboardButton(text="🤖 AI Ustoz (Savol berish)")],
            [KeyboardButton(text="🚦 Yo'l Belgilari"), KeyboardButton(text="📚 YHQ Qoidalari")],
            [KeyboardButton(text="🎁 Taklif Qilish & VIP"), KeyboardButton(text="📊 Statistika & Reyting")],
            [KeyboardButton(text="📱 Avtomaktab (Mini App)", web_app=WebAppInfo(url=WEBAPP_URL)), KeyboardButton(text="💎 VIP (Premium)")]
        ],
        resize_keyboard=True
    )

    caption = (
        f"✨ <b>XUSH KELIBSIZ, {name.upper()}!</b> ✨\n\n"
        f"🏆 <b>AVTOVATANPARVAR PREMIUM PLATFORMA</b>\n"
        f"⚡️ <i>O'zbekistonning 1-raqamli innovatsion YHQ va GAI tizimi</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚀 <b>Bu bot nima qila oladi?</b>\n"
        f"🏎 <b>1 242 ta Rasmiy YHQ Savollari:</b> Barcha testlar va 62 ta rasmiy biletlar\n"
        f"🎬 <b>207 ta 3D Harakatlanish Videolari:</b> Murakkab chorrahalar animatsiyasi\n"
        f"🎓 <b>GAI Davlat Imtihoni (20/20):</b> Jonli taymer va Oltin Sertifikat\n"
        f"🤖 <b>AI Aqlli Ustoz:</b> Har bir savolga tushuntirish va esda saqlash sirlari\n"
        f"🥊 <b>1vs1 Duel Janglari:</b> Do'stlar yoki AI botga qarshi onlayn bellashuv\n"
        f"🚦 <b>130 ta HD Yo'l Belgilari:</b> Barcha rasmiy belgilar va jarimalar\n"
        f"🎥 <b>133 ta Rasmiy Video Darslar:</b> e-avtomaktab to'liq video kursi\n"
        f"🧠 <b>Spaced Repetition:</b> Xatolaringiz ustida aqlli ishlash tizimi\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b>Sizga 5 kunlik VIP Premium sovg'a qilindi!</b>\n\n"
        f"👇 <i>Boshlash uchun pastdagi menyudan bo'limni tanlang:</i>"
    )

    import os
    welcome_img = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "welcome.png")

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Mini Ilovani Ochish 📱", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    if os.path.exists(welcome_img):
        from aiogram.types import FSInputFile
        photo = FSInputFile(welcome_img)
        try:
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML"
            )
            await message.answer(
                "📱 <b>Interaktiv Mini App orqali ham test yechishingiz mumkin:</b>",
                reply_markup=inline_kb,
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await message.answer(caption, reply_markup=kb, parse_mode="HTML")
    await message.answer(
        "📱 <b>Interaktiv Mini App orqali ham test yechishingiz mumkin:</b>",
        reply_markup=inline_kb,
        parse_mode="HTML"
    )

@registration_router.message(F.text.in_(["⚙️ Tilni o'zgartirish", "⚙️ Тилни ўзгартириш", "⚙️ Изменить язык"]))
async def change_language(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇺🇿 Ўзбекча")],
            [KeyboardButton(text="🇷🇺 Русский")]
        ],
        resize_keyboard=True
    )
    await message.answer("Iltimos, tilni tanlang:\nИлтимос, тилни танланг:\nПожалуйста, выберите язык:", reply_markup=kb)
    await state.set_state(RegistrationStates.language)

@registration_router.message(F.text == "🎁 Taklif Qilish & VIP")
async def invite_friends(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    
    text = (
        "🎁 **DO'STLARNI TAKLIF QILING VA VIP OLING!**\n\n"
        "Quyidagi shaxsiy havolangizni do'stlaringizga yuboring. Ular botga kirishi bilan sizga avtomatik ravishda **+1 KUN VIP (PREMIUM)** taqdim etiladi!\n\n"
        f"🔗 Sizning havolangiz:\n`{ref_link}`"
    )
    await message.answer(text, parse_mode="Markdown")

@registration_router.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery, bot: Bot):
    """Obunani tekshirish tugmasi bosilganda."""
    from utils.subscription import check_user_subscription, get_subscription_keyboard
    
    is_sub = await check_user_subscription(bot, callback.from_user.id, bypass_cache=True)
    
    if not is_sub:
        await callback.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz! Iltimos, avval obuna bo'ling.",
            show_alert=True
        )
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        keyboard = await get_subscription_keyboard(bot)
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="Botdan foydalanish uchun quyidagi rasmiy kanallarimizga a'zo bo'lishingiz kerak!\n\n"
                 "Iltimos, pastdagi tugmalar orqali kanallarga a'zo bo'ling va 'Obunani tekshirish' tugmasini bosing.",
            reply_markup=keyboard
        )
        return

    # ✅ Barcha kanallarga obuna bo'lgan — muvaffaqiyat!
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("✅ Obunangiz tasdiqlandi. Rahmat!", show_alert=True)
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalars().first()
    
    if user and user.language and user.full_name:
        await send_main_menu(callback.message, user.language, user.full_name)
    else:
        await callback.message.answer("Iltimos, botdan foydalanish uchun /start buyrug'ini yuboring.")


@registration_router.callback_query(F.data.in_(["back_to_main_menu", "back_to_main", "nav_main_menu", "main_menu"]))
async def cb_back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Har qanday bo'limdan to'g'ridan-to'g'ri Bosh menyuga qaytarish"""
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalars().first()
        lang = user.language if user and user.language else "uz"
        name = user.full_name if user and user.full_name else callback.from_user.full_name
    await send_main_menu(callback.message, lang, name)
    await callback.answer()


