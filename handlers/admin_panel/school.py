from aiogram import Router, types, F, Bot
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Student, StudentPayment, BotGroup, Setting
from sqlalchemy import select, delete
from datetime import datetime
from config import ADMIN_IDS

school_router = Router()



class SchoolStates(StatesGroup):
    adding_name = State()
    adding_group = State()
    editing_field = State()
    editing_value = State()

def back_kb(cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]
    ])

@school_router.callback_query(F.data.startswith("admin_school"))
async def admin_school_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    data_parts = callback.data.split("_")
    page = 1
    if len(data_parts) > 2:
        try:
            page = int(data_parts[2])
        except ValueError:
            page = 1

    per_page = 20
    offset = (page - 1) * per_page

    async with async_session() as session:
        from sqlalchemy import func
        total_result = await session.execute(select(func.count()).select_from(Student))
        total = total_result.scalar()

        result = await session.execute(
            select(Student).order_by(Student.id.asc()).offset(offset).limit(per_page)
        )
        students = result.scalars().all()

    buttons = []
    for s in students:
        buttons.append([
            InlineKeyboardButton(text=f"👨‍🎓 #{s.id} {s.full_name[:30]}", callback_data=f"student_detail_{s.id}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_school_{page-1}"))
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_school_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi o'quvchi qo'shish", callback_data="student_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    start_num = offset + 1
    end_num = min(offset + per_page, total)

    await callback.message.edit_text(
        f"🏫 AVTOMAKTAB O'QUVCHILARI ({total} ta)\nKo'rsatilmoqda: {start_num}-{end_num}\n\nO'quvchini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@school_router.callback_query(F.data.startswith("student_detail_"))
async def admin_student_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    sid = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.id == sid))
        s = result.scalars().first()

    if not s:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ismni o'zgartir", callback_data=f"student_edit_{sid}_name")],
        [InlineKeyboardButton(text="✏️ Guruhni o'zgartir", callback_data=f"student_edit_{sid}_group")],
        [InlineKeyboardButton(text="✏️ Davomat balini o'zgartir", callback_data=f"student_edit_{sid}_att")],
        [InlineKeyboardButton(text="✏️ Imtihon balini o'zgartir", callback_data=f"student_edit_{sid}_exam")],
        [InlineKeyboardButton(text="💰 To'langan summani o'zgartir", callback_data=f"student_edit_{sid}_paid")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"student_del_{sid}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_school")]
    ])

    text = (
        f"👨‍🎓 O'quvchi #{s.id}\n\n"
        f"👤 Ism-familiya: {s.full_name}\n"
        f"👥 Guruh: {s.group_name or 'Biriktirilmagan'}\n"
        f"📊 Davomat bali: {s.attendance_score}\n"
        f"🎓 Imtihon bali: {s.exam_score}\n"
        f"💵 Jami to'langan summa: {s.paid_amount:,} so'm"
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@school_router.callback_query(F.data.startswith("student_edit_"))
async def admin_student_edit(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    sid = int(parts[2])
    field = parts[3]
    field_names = {
        "name": "Ism-familiya", "group": "Guruh nomi", 
        "att": "Davomat bali (raqam)", "exam": "Imtihon bali (raqam)",
        "paid": "To'langan summa (raqam, so'm)"
    }
    await state.update_data(sid=sid, field=field)
    await state.set_state(SchoolStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"student_detail_{sid}")
    )
    await callback.answer()

@school_router.message(SchoolStates.editing_value)
async def admin_student_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    sid = data["sid"]
    field = data["field"]
    value = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(Student).where(Student.id == sid))
        s = result.scalars().first()
        if s:
            if field == "name":
                s.full_name = value
            elif field == "group":
                s.group_name = None if value.lower() == "yoq" else value
            elif field == "att":
                if value.isdigit(): s.attendance_score = int(value)
                else: return await message.answer("❌ Faqat raqam kiriting!")
            elif field == "exam":
                if value.isdigit(): s.exam_score = int(value)
                else: return await message.answer("❌ Faqat raqam kiriting!")
            elif field == "paid":
                if value.isdigit(): s.paid_amount = int(value)
                else: return await message.answer("❌ Faqat raqam kiriting!")
            await session.commit()
    
    await state.clear()
    await message.answer(f"✅ O'quvchi #{sid} yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")

@school_router.callback_query(F.data.startswith("student_del_"))
async def admin_student_del_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    sid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"student_delok_{sid}"),
         InlineKeyboardButton(text="❌ Bekor", callback_data=f"student_detail_{sid}")]
    ])
    await callback.message.edit_text(f"⚠️ O'quvchini o'chirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()

@school_router.callback_query(F.data.startswith("student_delok_"))
async def admin_student_del_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    sid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(Student).where(Student.id == sid))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_school_list(callback)

@school_router.callback_query(F.data == "student_add")
async def admin_student_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(SchoolStates.adding_name)
    await callback.message.edit_text(
        "➕ YANGI O'QUVCHI QO'SHISH\n\n1️⃣ To'liq ismini yozing:",
        reply_markup=back_kb("admin_school")
    )
    await callback.answer()

@school_router.message(SchoolStates.adding_name)
async def student_add_name(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(full_name=message.text.strip())
    await state.set_state(SchoolStates.adding_group)
    await message.answer("2️⃣ Guruh nomini yozing (yo'q bo'lsa 'yoq' deb yozing):")

@school_router.message(SchoolStates.adding_group)
async def student_add_group(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    val = message.text.strip()
    data = await state.get_data()
    
    async with async_session() as session:
        s = Student(
            full_name=data["full_name"],
            group_name=None if val.lower() == "yoq" else val,
            attendance_score=0,
            exam_score=0
        )
        session.add(s)
        await session.commit()
    
    await state.clear()
    await message.answer("✅ Yangi o'quvchi qo'shildi!\n\n/admin orqali panelga qaytishingiz mumkin.")

@school_router.callback_query(F.data.startswith("approve_spay_") | F.data.startswith("reject_spay_"))
async def admin_student_payment_action(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return
        
    action_parts = callback.data.split("_")
    action = action_parts[0]
    payment_id = int(action_parts[2])
    
    async with async_session() as session:
        result_pay = await session.execute(select(StudentPayment).where(StudentPayment.id == payment_id))
        payment = result_pay.scalars().first()
        
        if not payment:
            await callback.answer("To'lov ma'lumotlari topilmadi!", show_alert=True)
            return
            
        if payment.status != 'pending':
            await callback.answer(f"Bu to'lov allaqachon {payment.status} qilingan!", show_alert=True)
            return
            
        result_student = await session.execute(select(Student).where(Student.id == payment.student_id))
        student = result_student.scalars().first()
        
        if not student:
            await callback.answer("O'quvchi topilmadi!", show_alert=True)
            return
            
        if action == "approve":
            student.paid_amount += payment.amount
            payment.status = 'approved'
            payment.approved_by = callback.from_user.id
            payment.resolved_at = datetime.utcnow()
            await session.commit()
            
            if student.telegram_id:
                try:
                    await bot.send_message(
                        student.telegram_id, 
                        f"🎉 **To'lovingiz tasdiqlandi!**\n\n"
                        f"Sizning balansingizga **{payment.amount:,} so'm** qo'shildi.\n"
                        f"💵 **Jami to'langan:** {student.paid_amount:,} so'm",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **QABUL QILINDI**")
        else:
            payment.status = 'rejected'
            payment.approved_by = callback.from_user.id
            payment.resolved_at = datetime.utcnow()
            await session.commit()
            
            if student.telegram_id:
                try:
                    await bot.send_message(
                        student.telegram_id, 
                        "❌ Kechirasiz, siz yuborgan kontrakt to'lovi cheki tasdiqlanmadi. Muammo bo'yicha admin bilan bog'laning."
                    )
                except Exception:
                    pass
            await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **RAD ETILDI**")
        
    await callback.answer("Mijozga xabar yuborildi!")
