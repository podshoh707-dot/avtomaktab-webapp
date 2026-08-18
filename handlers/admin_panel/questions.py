from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Question
from sqlalchemy import select, delete
from config import ADMIN_IDS

questions_router = Router()





class QuestionStates(StatesGroup):
    adding_text      = State()
    adding_option_a  = State()
    adding_option_b  = State()
    adding_option_c  = State()
    adding_option_d  = State()
    adding_correct   = State()
    adding_image     = State()
    adding_explain   = State()
    editing_field    = State()
    editing_value    = State()
    sending_channel  = State()


def back_kb(cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]
    ])


# ── Savollar ro'yxati ──────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("admin_tests"))
async def admin_questions_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    # admin_tests yoki admin_tests_1 kabi
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
        total_result = await session.execute(select(func.count()).select_from(Question))
        total = total_result.scalar()

        result = await session.execute(
            select(Question).order_by(Question.id.asc()).offset(offset).limit(per_page)
        )
        questions = result.scalars().all()

    buttons = []
    for q in questions:
        short_text = q.text[:40] + "..." if len(q.text) > 40 else q.text
        buttons.append([
            InlineKeyboardButton(text=f"#{q.id} {short_text}", callback_data=f"q_detail_{q.id}")
        ])

    # Sahifalash tugmalari
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_tests_{page-1}"))
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_tests_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi savol qo'shish", callback_data="q_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    start_num = offset + 1
    end_num = min(offset + per_page, total)
    
    await callback.message.edit_text(
        f"🗃 SAVOLLAR BAZASI\n\nJami: {total} ta savol\nKo'rsatilmoqda: {start_num}-{end_num}\n\nSavolni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


# ── Savol tafsiloti ────────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_detail_"))
async def admin_question_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()

    if not q:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga yuborish", callback_data=f"q_send_{qid}")],
        [InlineKeyboardButton(text="✏️ Savolni o'zgartir", callback_data=f"q_edit_{qid}_text")],
        [InlineKeyboardButton(text="✏️ A variantni o'zgartir", callback_data=f"q_edit_{qid}_a")],
        [InlineKeyboardButton(text="✏️ B variantni o'zgartir", callback_data=f"q_edit_{qid}_b")],
        [InlineKeyboardButton(text="✏️ C variantni o'zgartir", callback_data=f"q_edit_{qid}_c")],
        [InlineKeyboardButton(text="✏️ D variantni o'zgartir", callback_data=f"q_edit_{qid}_d")],
        [InlineKeyboardButton(text="✏️ To'g'ri javobni o'zgartir", callback_data=f"q_edit_{qid}_correct")],
        [InlineKeyboardButton(text="✏️ Rasm URLni o'zgartir", callback_data=f"q_edit_{qid}_image")],
        [InlineKeyboardButton(text="✏️ Izohni o'zgartir", callback_data=f"q_edit_{qid}_explain")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"q_del_{qid}")],
        [InlineKeyboardButton(text="🔙 Savollar ro'yxatiga", callback_data="admin_tests")]
    ])

    text = (
        f"📋 Savol #{q.id}\n\n"
        f"❓ {q.text}\n\n"
        f"A) {q.option_a}\n"
        f"B) {q.option_b}\n"
    )
    if q.option_c:
        text += f"C) {q.option_c}\n"
    if q.option_d:
        text += f"D) {q.option_d}\n"
    text += f"\n✅ To'g'ri javob: {q.correct_option}"
    if q.explanation:
        text += f"\n📖 Izoh: {q.explanation[:100]}"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@questions_router.callback_query(F.data.startswith("q_send_"))
async def q_send_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.fromuser.id if hasattr(callback, 'fromuser', "can_manage_content") else callback.from_user.id):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    qid = int(callback.data.split("_")[2])
    await state.update_data(send_qid=qid)
    await state.set_state(QuestionStates.sending_channel)
    await callback.message.edit_text(
        "📢 Qaysi kanalga yubormoqchisiz?\n\nKanal usernamesini @ bilan yozing (masalan: @avtomaktab_uz)\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"q_detail_{qid}")
    )
    await callback.answer()

@questions_router.message(QuestionStates.sending_channel)
async def q_send_do(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
        
    channel = message.text.strip()
    if not channel.startswith("@"):
        await message.answer("❌ Kanal usernamesi @ belgisi bilan boshlanishi kerak!")
        return
        
    data = await state.get_data()
    qid = data.get("send_qid")
    
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()
        
    if not q:
        await message.answer("Savol topilmadi.")
        await state.clear()
        return

    text = f"❓ {q.text}"
    
    buttons = []
    buttons.append([InlineKeyboardButton(text=f"A) {q.option_a}", callback_data=f"ch_ans_{qid}_A")])
    buttons.append([InlineKeyboardButton(text=f"B) {q.option_b}", callback_data=f"ch_ans_{qid}_B")])
    if q.option_c:
        buttons.append([InlineKeyboardButton(text=f"C) {q.option_c}", callback_data=f"ch_ans_{qid}_C")])
    if q.option_d:
        buttons.append([InlineKeyboardButton(text=f"D) {q.option_d}", callback_data=f"ch_ans_{qid}_D")])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        if q.image_url:
            from aiogram.types import FSInputFile
            import os
            from config import BASE_DIR
            
            photo_obj = q.image_url
            if not str(q.image_url).startswith("http"):
                img_path = os.path.join(BASE_DIR, str(q.image_url).replace('\\', '/'))
                if os.path.exists(img_path):
                    photo_obj = FSInputFile(img_path)
                else:
                    photo_obj = None

            if photo_obj:
                await message.bot.send_photo(
                    chat_id=channel,
                    photo=photo_obj,
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await message.bot.send_message(
                    chat_id=channel,
                    text=text,
                    reply_markup=keyboard
                )
        else:
            await message.bot.send_message(
                chat_id=channel,
                text=text,
                reply_markup=keyboard
            )
        await message.answer(f"✅ Savol {channel} kanaliga muvaffaqiyatli yuborildi!\n\n/admin - panelga qaytish")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi. Bot kanalda admin emasmi yoki kanal xatomi?\n\nXato: {str(e)}")
        
    await state.clear()


# ── Savol tahrirlash ───────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_edit_"))
async def admin_question_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    qid   = int(parts[2])
    field = parts[3]
    field_names = {
        "text": "Savol matni", "a": "A variant", "b": "B variant",
        "c": "C variant", "d": "D variant", "correct": "To'g'ri javob (A,B,C,D)",
        "image": "Rasm URL", "explain": "Izoh"
    }
    await state.update_data(qid=qid, field=field)
    await state.set_state(QuestionStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"q_detail_{qid}")
    )
    await callback.answer()


@questions_router.message(QuestionStates.editing_value)
async def admin_question_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data  = await state.get_data()
    qid   = data["qid"]
    field = data["field"]
    value = message.text.strip() if message.text else ""

    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()
        if q:
            if field == "text":
                q.text = value
            elif field == "a":
                q.option_a = value
            elif field == "b":
                q.option_b = value
            elif field == "c":
                q.option_c = None if value.lower() == "yoq" else value
            elif field == "d":
                q.option_d = None if value.lower() == "yoq" else value
            elif field == "correct":
                val_upper = value.upper()
                if val_upper in ("A", "B", "C", "D"):
                    q.correct_option = val_upper
                else:
                    await message.answer("❌ Faqat A, B, C yoki D harfini yozing!")
                    return
            elif field == "image":
                if message.photo:
                    q.image_url = message.photo[-1].file_id
                else:
                    q.image_url = value if value.startswith("http") else None
            elif field == "explain":
                q.explanation = None if value.lower() == "yoq" else value
            await session.commit()

    await state.clear()
    await message.answer(f"✅ Savol #{qid} yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")


# ── Savol o'chirish ────────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_del_"))
async def admin_question_delete_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"q_delok_{qid}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data=f"q_detail_{qid}")
    ]])
    await callback.message.edit_text(
        f"⚠️ Savol #{qid}ni o'chirishni tasdiqlaysizmi?",
        reply_markup=keyboard
    )
    await callback.answer()


@questions_router.callback_query(F.data.startswith("q_delok_"))
async def admin_question_delete_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(Question).where(Question.id == qid))
        await session.commit()

    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_questions_list(callback)


# ── Yangi savol qo'shish (FSM) ──────────────────────────────────────────────
@questions_router.callback_query(F.data == "q_add")
async def admin_question_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(QuestionStates.adding_text)
    await callback.message.edit_text(
        "➕ YANGI SAVOL QO'SHISH\n\n1️⃣ Savol matnini yozing:\n(Agar rasm qo'shmoqchi bo'lsangiz, rasmni biriktirib tagiga matnini yozib bittada yuboring. Rasm yo'q bo'lsa shunchaki matn yozing)\n\nBekor qilish: /cancel",
        reply_markup=back_kb("admin_tests")
    )
    await callback.answer()


@questions_router.message(QuestionStates.adding_text)
async def q_add_text(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
        
    if message.photo:
        text = message.caption.strip() if message.caption else ""
        image_id = message.photo[-1].file_id
    else:
        text = message.text.strip() if message.text else ""
        image_id = None
        
    if not text:
        await message.answer("❌ Matn kiritilmadi! Iltimos, savol matnini yozing.")
        return

    await state.update_data(text=text, image_url=image_id)
    await state.set_state(QuestionStates.adding_option_a)
    await message.answer("2️⃣ A variantini yozing:")


@questions_router.message(QuestionStates.adding_option_a)
async def q_add_a(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(option_a=message.text.strip())
    await state.set_state(QuestionStates.adding_option_b)
    await message.answer("3️⃣ B variantini yozing:")


@questions_router.message(QuestionStates.adding_option_b)
async def q_add_b(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(option_b=message.text.strip())
    await state.set_state(QuestionStates.adding_option_c)
    await message.answer("4️⃣ C variantini yozing:\n(yo'q bo'lsa 'yoq' deb yozing)")


@questions_router.message(QuestionStates.adding_option_c)
async def q_add_c(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    val = message.text.strip()
    await state.update_data(option_c=None if val.lower() == "yoq" else val)
    await state.set_state(QuestionStates.adding_option_d)
    await message.answer("5️⃣ D variantini yozing:\n(yo'q bo'lsa 'yoq' deb yozing)")


@questions_router.message(QuestionStates.adding_option_d)
async def q_add_d(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    val = message.text.strip()
    await state.update_data(option_d=None if val.lower() == "yoq" else val)
    await state.set_state(QuestionStates.adding_correct)
    await message.answer("6️⃣ To'g'ri javob harfini yozing (A, B, C yoki D):")


@questions_router.message(QuestionStates.adding_correct)
async def q_add_correct(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    ans = message.text.strip().upper()
    if ans not in ("A", "B", "C", "D"):
        await message.answer("❌ Faqat A, B, C yoki D harfini yozing!")
        return
    await state.update_data(correct_option=ans)
    await state.set_state(QuestionStates.adding_explain)
    await message.answer("7️⃣ Izoh (tushuntirish) yozing:\n(izoh yo'q bo'lsa 'yoq' deb yozing)")


@questions_router.message(QuestionStates.adding_explain)
async def q_add_explain(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    exp = message.text.strip()
    data = await state.get_data()

    async with async_session() as session:
        q = Question(
            text=data["text"],
            option_a=data["option_a"],
            option_b=data["option_b"],
            option_c=data.get("option_c"),
            option_d=data.get("option_d"),
            correct_option=data["correct_option"],
            image_url=data.get("image_url"),
            explanation=None if exp.lower() == "yoq" else exp
        )
        session.add(q)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Savol muvaffaqiyatli qo'shildi!\n\n"
        f"❓ {data['text']}\n"
        f"✅ To'g'ri javob: {data['correct_option']}\n\n"
        f"/admin orqali panelga qaytishingiz mumkin."
    )
