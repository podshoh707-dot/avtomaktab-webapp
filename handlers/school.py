from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Student, StudentPayment, Setting
from sqlalchemy import select, and_, or_
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
import logging
from datetime import datetime

school_router = Router()

class SchoolUserStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_receipt = State()

@school_router.message(F.text.in_([
    "⚙️ Avtomaktab moduli", "🏫 Avtomaktab moduli", "🏫 Avtomaktab Kabineti", "🎓 Avtomaktab moduli"
]))
async def school_menu(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
        
    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.telegram_id == message.from_user.id))
        student = result.scalars().first()

    if not student:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Profilimni Izlash & Bog'lash", callback_data="school_find_profile")]
        ])
        text = (
            f"🏫 <b>AVTOMAKTAB O'QUVCHILARI PORTALI</b>\n"
            f"───────────────────────────\n\n"
            f"⚠️ Sizning Telegram akkauntingiz hali o'quvchilar bazasiga bog'lanmagan.\n\n"
            f"📌 Profilingizni topish va bog'lash uchun pastdagi tugmani bosing va ism-familiyangizni kiriting."
        )
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Kontrakt To'lovini Amalga Oshirish", callback_data="school_pay")],
            [InlineKeyboardButton(text="🔓 Akkauntni Profildan Uzish", callback_data="school_unlink")]
        ])
        text = (
            f"🏫 <b>O'QUVCHI SHAXSIY KABINETI</b>\n"
            f"───────────────────────────\n\n"
            f"👤 <b>O'quvchi:</b> {student.full_name}\n"
            f"👥 <b>Guruh:</b> {student.group_name or 'Biriktirilmagan'}\n"
            f"📊 <b>Davomat bali:</b> <code>{student.attendance_score}</code>\n"
            f"🎓 <b>Imtihon bali:</b> <code>{student.exam_score}</code>\n\n"
            f"────────── TO'LOV HISOBLARI ──────────\n"
            f"💵 <b>Jami To'langan Summa:</b> <code>{student.paid_amount:,} so'm</code>"
        )
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@school_router.callback_query(F.data == "school_find_profile")
async def school_find_profile_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SchoolUserStates.waiting_for_name)
    await callback.message.edit_text(
        "🔍 **Profilni izlash**\n\n"
        "Iltimos, ism va familiyangizni to'liq kiriting (masalan: *Aliyev Vali*):\n\n"
        "Bekor qilish uchun: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()

@school_router.message(SchoolUserStates.waiting_for_name)
async def school_find_profile_process(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Amal bekor qilindi.")
        return

    query = message.text.strip().lower()
    async with async_session() as session:
        # FAQAT telegram_id ulanmagan profillarni qidiramiz
        result = await session.execute(
            select(Student).where(
                and_(
                    Student.full_name.ilike(f"%{query}%"),
                    Student.telegram_id.is_(None)
                )
            ).limit(10)
        )
        students = result.scalars().all()

    if not students:
        await message.answer(
            "❌ Kechirasiz, ko'rsatilgan ism bo'yicha bo'sh (ulanishga tayyor) profil topilmadi.\n\n"
            "Iltimos, ismingizni to'g'ri yozganingizni tekshiring yoki adminga murojaat qiling."
        )
        return

    buttons = []
    for s in students:
        buttons.append([InlineKeyboardButton(
            text=f"{s.full_name} ({s.group_name or 'Guruhsiz'})",
            callback_data=f"school_link_{s.id}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("✅ Sizning so'rovingiz bo'yicha topilgan profillar:\nO'zingizni tanlang:", reply_markup=keyboard)
    await state.clear()

@school_router.callback_query(F.data.startswith("school_link_"))
async def school_link_profile(callback: types.CallbackQuery):
    student_id = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        # Check if user already linked to another
        res_check = await session.execute(select(Student).where(Student.telegram_id == callback.from_user.id))
        if res_check.scalars().first():
            await callback.answer("Siz allaqachon profilga bog'langansiz!", show_alert=True)
            return

        result = await session.execute(select(Student).where(Student.id == student_id))
        student = result.scalars().first()
        
        if not student:
            await callback.answer("Profil topilmadi!", show_alert=True)
            return
            
        if student.telegram_id is not None:
            await callback.answer("Bu profil allaqachon boshqa raqamga bog'langan!", show_alert=True)
            return
            
        student.telegram_id = callback.from_user.id
        await session.commit()
        
    await callback.message.edit_text("✅ Profilingiz muvaffaqiyatli bog'landi! Endi '⚙️ Avtomaktab moduli' ga kirsangiz, ma'lumotlaringiz chiqadi.")
    await callback.answer()

@school_router.callback_query(F.data == "school_unlink")
async def school_unlink_profile(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.telegram_id == callback.from_user.id))
        student = result.scalars().first()
        if student:
            student.telegram_id = None
            await session.commit()
    await callback.message.edit_text("✅ Profildan muvaffaqiyatli chiqdingiz.")
    await callback.answer()

@school_router.callback_query(F.data == "school_pay")
async def school_pay_start(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result_card = await session.execute(select(Setting).where(Setting.key == "admin_card"))
        card_setting = result_card.scalars().first()
        card_num = card_setting.value if card_setting else "Hozircha karta raqami kiritilmagan. Admin bilan bog'laning."
        
    await state.set_state(SchoolUserStates.waiting_for_amount)
    await callback.message.edit_text(
        f"💳 **To'lov qilish**\n\n"
        f"Iltimos, to'lagan summangizni faqat raqamlarda kiriting (masalan: *500000* yoki *1000000*):\n\n"
        f"Karta raqami: `{card_num}`\n\n"
        f"Bekor qilish: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()

@school_router.message(SchoolUserStates.waiting_for_amount)
async def school_pay_amount(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Amal bekor qilindi.")
        return

    amount_str = message.text.strip().replace(" ", "").replace(",", "").replace(".", "")
    if not amount_str.isdigit():
        await message.answer("❌ Iltimos, summani faqat raqamlarda kiriting (masalan: 500000):")
        return
        
    amount = int(amount_str)
    if amount < 1000:
        await message.answer("❌ Kiritilgan summa juda kam. Qaytadan kiriting:")
        return

    await state.update_data(amount=amount)
    await state.set_state(SchoolUserStates.waiting_for_receipt)
    
    await message.answer(
        f"✅ Kiritilgan summa: **{amount:,} so'm**\n\n"
        f"Endi to'lov muvaffaqiyatli bo'lganligi haqidagi **chekni (skrinshotni)** shu yerga yuboring.",
        parse_mode="Markdown"
    )

@school_router.message(SchoolUserStates.waiting_for_receipt, F.photo)
async def process_school_receipt(message: types.Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    
    data = await state.get_data()
    amount = data.get("amount", 0)
    
    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.telegram_id == user_id))
        student = result.scalars().first()
        
        if not student:
            await message.answer("Sizning profilingiz topilmadi!")
            await state.clear()
            return
            
        payment = StudentPayment(
            student_id=student.id,
            amount=amount,
            status='pending'
        )
        session.add(payment)
        await session.commit()
        payment_id = payment.id
        student_name = student.full_name
        group_name = student.group_name or "Guruhsiz"

    # Adminga yuborish
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_spay_{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_spay_{payment_id}")
        ]
    ])
    
    admin_msg = (
        f"💸 **O'quvchidan Kontrakt To'lovi!**\n\n"
        f"👨‍🎓 **O'quvchi:** {student_name}\n"
        f"👥 **Guruh:** {group_name}\n"
        f"💰 **Yuborilgan summa:** `{amount:,} so'm`\n\n"
        "To'lovni tasdiqlaysizmi?"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=admin_msg, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Adminga to'lovni yuborishda xatolik: {e}")
            
    await message.answer("✅ To'lov chekingiz adminga yuborildi. Tasdiqlanishi bilan sizga darhol xabar beramiz va balansingizga qo'shiladi!")
    await state.clear()

@school_router.message(SchoolUserStates.waiting_for_receipt)
async def process_school_receipt_error(message: types.Message):
    await message.answer("Iltimos, to'lov chekini rasm (skrinshot) ko'rinishida yuboring.")
