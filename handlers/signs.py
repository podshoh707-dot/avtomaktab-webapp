from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import async_session, Sign
from sqlalchemy import select

signs_router = Router()

class SignStates(StatesGroup):
    searching = State()

# ─── ASOSIY MENYU ──────────────────────────────────────────────────
@signs_router.message(F.text.in_([
    "🚦 Yo'l belgilari", "⚠️ Yo'l Belgilari", "🚦 Yo'l Belgilari", "⚠️ Yo'l belgilari",
    "🚦 Йўл белгилари", "🚦 Дорожные знаки"
]))
async def signs_menu(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Taqiqlovchi", callback_data="signs_cat_taqiqlovchi"),
         InlineKeyboardButton(text="⚠️ Ogohlantiruvchi", callback_data="signs_cat_ogohlantiruvchi")],
        [InlineKeyboardButton(text="ℹ️ Axborot", callback_data="signs_cat_axborot"),
         InlineKeyboardButton(text="➡️ Buyuruvchi", callback_data="signs_cat_buyuruvchi")],
        [InlineKeyboardButton(text="🔑 Imtiyoz", callback_data="signs_cat_imtiyoz"),
         InlineKeyboardButton(text="🛠 Servis", callback_data="signs_cat_servis")],
        [InlineKeyboardButton(text="🔍 Belgini qidirish", callback_data="signs_search")],
        [InlineKeyboardButton(text="📝 Belgilar bo'yicha test", callback_data="signs_test")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_main_menu")]
    ])
    await message.answer("🚦 YO'L BELGILARI\n\nKatalogdan bo'lim tanlang yoki belgini qidiring:", reply_markup=keyboard)

# ─── KATEGORIYA ──────────────────────────────────────────────────
@signs_router.callback_query(F.data.startswith("signs_cat_"))
async def show_signs_category(callback: types.CallbackQuery):
    category = callback.data.replace("signs_cat_", "")
    
    cat_labels = {
        "taqiqlovchi": "🛑 Taqiqlovchi belgilar",
        "ogohlantiruvchi": "⚠️ Ogohlantiruvchi belgilar",
        "axborot": "ℹ️ Axborot belgilari",
        "buyuruvchi": "➡️ Buyuruvchi belgilar",
        "imtiyoz": "🔑 Imtiyoz belgilari",
        "servis": "🛠 Servis belgilari",
    }
    
    async with async_session() as session:
        result = await session.execute(select(Sign).where(Sign.category == category))
        signs = result.scalars().all()
    
    if not signs:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="signs_back")]
        ])
        text_content = f"{cat_labels.get(category, category)}\n\nHozircha bu kategoriyada belgilar yo'q."
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text_content, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text_content, reply_markup=keyboard)
        await callback.answer()
        return
    
    buttons = []
    for sign in signs:
        buttons.append([InlineKeyboardButton(
            text=sign.name[:55],
            callback_data=f"sign_{sign.id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="signs_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.answer()
    
    text_content = f"<b>{cat_labels.get(category, category)}</b>\n\nJami: {len(signs)} ta belgi\n\nBelgini tanlang:"
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text_content, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="HTML")

# ─── BELGI TAFSILOTI ───────────────────────────────────────────────
@signs_router.callback_query(F.data.regexp(r'^sign_\d+$'))
async def show_sign_detail(callback: types.CallbackQuery):
    sign_id = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        result = await session.execute(select(Sign).where(Sign.id == sign_id))
        sign = result.scalars().first()
    
    if not sign:
        await callback.answer("Belgi topilmadi.", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Kategoriyaga qaytish", callback_data=f"signs_cat_{sign.category}")]
    ])
    
    no_desc = "Ta'rif kiritilmagan."
    text = (
        f"🚦 <b>{sign.name}</b>\n\n"
        f"📂 Kategoriya: {sign.category.capitalize()}\n\n"
        f"📖 Ta'rifi:\n{sign.description or no_desc}"
    )
    if sign.example:
        text += f"\n\n💡 Misol:\n{sign.example}"
    
    await callback.answer()
    
    if sign.image_url:
        sent = False
        # Local file
        if not sign.image_url.startswith("http"):
            import os
            from aiogram.types import FSInputFile
            from config import BASE_DIR
            
            # Check if it's in webapp/ or root
            path1 = os.path.join(BASE_DIR, 'webapp', sign.image_url)
            path2 = os.path.join(BASE_DIR, sign.image_url)
            
            local_path = path1 if os.path.exists(path1) else path2
            
            if os.path.exists(local_path):
                try:
                    photo = FSInputFile(local_path)
                    await callback.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard, parse_mode="HTML")
                    await callback.message.delete()
                    sent = True
                except Exception as e:
                    print(f"Local photo send error: {e}")
        # Remote URL
        elif sign.image_url.startswith("http"):
            try:
                await callback.message.answer_photo(photo=sign.image_url, caption=text, reply_markup=keyboard, parse_mode="HTML")
                await callback.message.delete()
                sent = True
            except Exception as e:
                print(f"Remote photo send error: {e}")
        
        if not sent:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# ─── QIDIRISH (FSM) ────────────────────────────────────────────────
@signs_router.callback_query(F.data == "signs_search")
async def signs_search_prompt(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="signs_back")]
    ])
    text_content = (
        "🔍 BELGI QIDIRISH\n\n"
        "Qidirmoqchi bo'lgan belgining nomi yoki raqamini yozing:\n\n"
        "Misol: «3.24» yoki «taqiqlangan» yoki «chorraha»"
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text_content, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text_content, reply_markup=keyboard)
    await state.set_state(SignStates.searching)
    await callback.answer()

@signs_router.message(SignStates.searching)
async def signs_search_result(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    await state.clear()
    
    async with async_session() as session:
        result = await session.execute(select(Sign))
        all_signs = result.scalars().all()
    
    # Qidiruv: nom yoki ta'rifda topamiz
    found = [s for s in all_signs if query in s.name.lower() or (s.description and query in s.description.lower())]
    
    if not found:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Belgilar bo'limiga qaytish", callback_data="signs_back")]
        ])
        await message.answer(
            f"❌ «{message.text}» bo'yicha hech narsa topilmadi.\n\n"
            f"Belgining raqami yoki nomi bilan qayta qidirib ko'ring.",
            reply_markup=keyboard
        )
        return
    
    buttons = []
    for sign in found[:20]:
        buttons.append([InlineKeyboardButton(
            text=f"[{sign.category}] {sign.name[:45]}",
            callback_data=f"sign_{sign.id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="signs_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"🔍 «{message.text}» bo'yicha qidiruv natijalari:\n"
        f"Topildi: {len(found)} ta belgi",
        reply_markup=keyboard
    )

# ─── ORQAGA ──────────────────────────────────────────────────────
@signs_router.callback_query(F.data == "signs_back")
async def signs_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Taqiqlovchi", callback_data="signs_cat_taqiqlovchi"),
         InlineKeyboardButton(text="⚠️ Ogohlantiruvchi", callback_data="signs_cat_ogohlantiruvchi")],
        [InlineKeyboardButton(text="ℹ️ Axborot", callback_data="signs_cat_axborot"),
         InlineKeyboardButton(text="➡️ Buyuruvchi", callback_data="signs_cat_buyuruvchi")],
        [InlineKeyboardButton(text="🔑 Imtiyoz", callback_data="signs_cat_imtiyoz"),
         InlineKeyboardButton(text="🛠 Servis", callback_data="signs_cat_servis")],
        [InlineKeyboardButton(text="🔍 Belgini qidirish", callback_data="signs_search")],
        [InlineKeyboardButton(text="📝 Belgilar bo'yicha test", callback_data="signs_test")]
    ])
    text_content = "🚦 YO'L BELGILARI\n\nKatalogdan bo'lim tanlang yoki belgini qidiring:"
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text_content, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text_content, reply_markup=keyboard)
    await callback.answer()

# ─── BELGILAR BO'YICHA TEST ─────────────────────────────────────
@signs_router.callback_query(F.data == "signs_test")
async def signs_test(callback: types.CallbackQuery, state: FSMContext):
    from database import Question
    from sqlalchemy.sql.expression import func
    from handlers.test import TestStates, send_question
    
    async with async_session() as session:
        result = await session.execute(
            select(Question).where(
                Question.category == "Yo'l belgilari va chiziqlari"
            ).order_by(func.random()).limit(10)
        )
        questions = result.scalars().all()
    
    if not questions:
        await callback.answer("Hozircha belgilar bo'yicha savollar yo'q.", show_alert=True)
        return
    
    q_ids = [q.id for q in questions]
    await state.set_state(TestStates.taking_test)
    await state.update_data(questions=q_ids, current_idx=0, correct_answers=0, selected_category="Yo'l belgilari va chiziqlari")
    await callback.message.delete()
    
    await send_question(callback, state)

