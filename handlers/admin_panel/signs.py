from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Sign
from sqlalchemy import select, delete
from config import ADMIN_IDS

signs_router = Router()



class SignStates(StatesGroup):
    adding_category = State()
    adding_name = State()
    adding_image = State()
    adding_desc = State()
    adding_example = State()
    editing_field = State()
    editing_value = State()

def back_kb(cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]
    ])

@signs_router.callback_query(F.data.startswith("admin_signs"))
async def admin_signs_list(callback: types.CallbackQuery):
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
        total_result = await session.execute(select(func.count()).select_from(Sign))
        total = total_result.scalar()

        result = await session.execute(
            select(Sign).order_by(Sign.id.asc()).offset(offset).limit(per_page)
        )
        signs = result.scalars().all()

    buttons = []
    for s in signs:
        buttons.append([
            InlineKeyboardButton(text=f"🚦 #{s.id} {s.name[:35]}", callback_data=f"sign_detail_{s.id}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_signs_{page-1}"))
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_signs_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi belgi qo'shish", callback_data="sign_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    start_num = offset + 1
    end_num = min(offset + per_page, total)

    await callback.message.edit_text(
        f"🚦 YO'L BELGILARI ({total} ta)\nKo'rsatilmoqda: {start_num}-{end_num}\n\nBelgini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@signs_router.callback_query(F.data.startswith("sign_detail_"))
async def admin_sign_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    sid = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        result = await session.execute(select(Sign).where(Sign.id == sid))
        s = result.scalars().first()

    if not s:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Toifani o'zgartir", callback_data=f"sign_edit_{sid}_category")],
        [InlineKeyboardButton(text="✏️ Nomini o'zgartir", callback_data=f"sign_edit_{sid}_name")],
        [InlineKeyboardButton(text="✏️ Rasm URLni o'zgartir", callback_data=f"sign_edit_{sid}_image")],
        [InlineKeyboardButton(text="✏️ Tavsifni o'zgartir", callback_data=f"sign_edit_{sid}_desc")],
        [InlineKeyboardButton(text="✏️ Misolni o'zgartir", callback_data=f"sign_edit_{sid}_example")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"sign_del_{sid}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_signs")]
    ])

    text = (
        f"🚦 Yo'l belgisi #{s.id}\n\n"
        f"📂 Toifa: {s.category}\n"
        f"📌 Nomi: {s.name}\n"
        f"🖼 Rasm URL: {s.image_url or 'Yoq'}\n\n"
        f"📖 Tavsif: {s.description or 'Yoq'}\n\n"
        f"💡 Misol: {s.example or 'Yoq'}"
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@signs_router.callback_query(F.data.startswith("sign_edit_"))
async def admin_sign_edit(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    sid = int(parts[2])
    field = parts[3]
    field_names = {
        "category": "Toifa", "name": "Nomi", "image": "Rasm URL",
        "desc": "Tavsif", "example": "Misol"
    }
    await state.update_data(sid=sid, field=field)
    await state.set_state(SignStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"sign_detail_{sid}")
    )
    await callback.answer()

@signs_router.message(SignStates.editing_value)
async def admin_sign_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    sid = data["sid"]
    field = data["field"]
    value = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(Sign).where(Sign.id == sid))
        s = result.scalars().first()
        if s:
            if field == "category":
                s.category = value
            elif field == "name":
                s.name = value
            elif field == "image":
                s.image_url = value if value.startswith("http") else None
            elif field == "desc":
                s.description = None if value.lower() == "yoq" else value
            elif field == "example":
                s.example = None if value.lower() == "yoq" else value
            await session.commit()
    
    await state.clear()
    await message.answer(f"✅ Belgi #{sid} yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")

@signs_router.callback_query(F.data.startswith("sign_del_"))
async def admin_sign_del_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    sid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"sign_delok_{sid}"),
         InlineKeyboardButton(text="❌ Bekor", callback_data=f"sign_detail_{sid}")]
    ])
    await callback.message.edit_text(f"⚠️ #{sid} belgini o'chirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()

@signs_router.callback_query(F.data.startswith("sign_delok_"))
async def admin_sign_del_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    sid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(Sign).where(Sign.id == sid))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_signs_list(callback)

@signs_router.callback_query(F.data == "sign_add")
async def admin_sign_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(SignStates.adding_category)
    await callback.message.edit_text(
        "➕ YANGI BELGI QO'SHISH\n\n1️⃣ Toifani yozing (masalan: Taqiqlovchi belgilar):",
        reply_markup=back_kb("admin_signs")
    )
    await callback.answer()

@signs_router.message(SignStates.adding_category)
async def sign_add_cat(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(category=message.text.strip())
    await state.set_state(SignStates.adding_name)
    await message.answer("2️⃣ Belgi nomini yozing:")

@signs_router.message(SignStates.adding_name)
async def sign_add_name(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(SignStates.adding_image)
    await message.answer("3️⃣ Rasm URL manzilini yozing (yo'q bo'lsa 'yoq'):")

@signs_router.message(SignStates.adding_image)
async def sign_add_img(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    val = message.text.strip()
    await state.update_data(image_url=val if val.startswith("http") else None)
    await state.set_state(SignStates.adding_desc)
    await message.answer("4️⃣ Tavsifni yozing (yo'q bo'lsa 'yoq'):")

@signs_router.message(SignStates.adding_desc)
async def sign_add_desc(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    val = message.text.strip()
    await state.update_data(description=None if val.lower() == "yoq" else val)
    await state.set_state(SignStates.adding_example)
    await message.answer("5️⃣ Misol yozing (yo'q bo'lsa 'yoq'):")

@signs_router.message(SignStates.adding_example)
async def sign_add_example(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    val = message.text.strip()
    data = await state.get_data()
    
    async with async_session() as session:
        s = Sign(
            category=data["category"],
            name=data["name"],
            image_url=data.get("image_url"),
            description=data.get("description"),
            example=None if val.lower() == "yoq" else val
        )
        session.add(s)
        await session.commit()
    
    await state.clear()
    await message.answer("✅ Yangi belgi qo'shildi!\n\n/admin orqali panelga qaytishingiz mumkin.")
