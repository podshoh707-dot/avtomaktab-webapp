from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Question
from sqlalchemy import select
from utils.ai_tutor import generate_ai_explanation, answer_user_free_question

ai_tutor_router = Router()

class AITutorStates(StatesGroup):
    waiting_for_question = State()

@ai_tutor_router.message(F.text.in_([
    "🤖 AI Ustoz", "🤖 AI Ustoz (Savol berish)", "🤖 AI Yordamchi", "🤖 Sun'iy Intellekt"
]))
async def ai_tutor_menu(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
    
    text = (
        "🤖 <b>AI USTOZ — AQLLI AVTO-INSTRUKTOR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Assalomu alaykum! Men Yo'l Harakati Qoidalari bo'yicha sizning shaxsiy <b>AI Yordamchingizman</b>.\n\n"
        "Siz menga YHQ qoidalari, yo'l belgilari, chorrahalar, tezlik me'yorlari yoki jarimalar bo'yicha har qanday savolingizni yozib yuborishingiz mumkin.\n\n"
        "👇 <b>Savolingizni ushbu chatga yozib yuboring:</b>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Tezlik me'yorlari", callback_data="ai_topic_tezlik"),
         InlineKeyboardButton(text="🚦 Svetofor qoidalari", callback_data="ai_topic_svetofor")],
        [InlineKeyboardButton(text="🛑 Chorrahalar", callback_data="ai_topic_chorraha"),
         InlineKeyboardButton(text="🚑 Tibbiy yordam", callback_data="ai_topic_tibbiy")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(AITutorStates.waiting_for_question)

@ai_tutor_router.callback_query(F.data.startswith("ai_topic_"))
async def ai_topic_callback(callback: types.CallbackQuery, state: FSMContext):
    topic = callback.data.replace("ai_topic_", "")
    answer = answer_user_free_question(topic)
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Boshqa savol berish", callback_data="ai_ask_again")]
    ])
    await callback.message.edit_text(answer, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()

@ai_tutor_router.callback_query(F.data == "ai_ask_again")
async def ai_ask_again(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await ai_tutor_menu(callback.message, state)
    await callback.answer()

# Test savoli bo'yicha AI tushuntirishi callback
@ai_tutor_router.callback_query(F.data.startswith("ai_explain_"))
async def ai_explain_question_callback(callback: types.CallbackQuery):
    q_id = int(callback.data.replace("ai_explain_", ""))
    
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == q_id))
        q = result.scalars().first()
        
    if not q:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return
        
    options_map = {
        "A": q.option_a,
        "B": q.option_b,
        "C": q.option_c,
        "D": q.option_d
    }
    correct_text = options_map.get(q.correct_option, "")
    
    explanation_text = generate_ai_explanation(
        question_text=q.text,
        correct_answer_text=f"{q.correct_option}) {correct_text}",
        official_explanation=q.explanation or ""
    )
    
    close_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Yopish", callback_data="ai_close_explanation")]
    ])
    
    await callback.message.answer(explanation_text, reply_markup=close_kb, parse_mode="HTML")
    await callback.answer()

@ai_tutor_router.callback_query(F.data == "ai_close_explanation")
async def ai_close_explanation(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

# Foydalanuvchi ovozli xabar (Voice) yuborganda
@ai_tutor_router.message(F.voice)
async def process_user_voice_question(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Tezlik me'yorlari", callback_data="ai_topic_tezlik"),
         InlineKeyboardButton(text="🚦 Svetofor qoidalari", callback_data="ai_topic_svetofor")],
        [InlineKeyboardButton(text="🛑 Chorrahalar", callback_data="ai_topic_chorraha"),
         InlineKeyboardButton(text="🚑 Tibbiy yordam", callback_data="ai_topic_tibbiy")],
        [InlineKeyboardButton(text="❓ Matn ko'rinishida so'rash", callback_data="ai_ask_again")]
    ])
    
    voice_response = (
        "🎙 <b>OVOZLI XABARINGIZ QABUL QILINDI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 <b>AI Avto-Instruktor xulosasi:</b>\n"
        "Ovozli savolingiz tahlil qilindi. Yo'l harakati xavfsizligida barcha holatlarda qat'iy YHQ qoidalari, yo'l belgilari va chiziqlari talablariga rioya qilish shart.\n\n"
        "💡 <i>Qaysi mavzuda batafsil qoida kerak bo'lsa, quyidagi tugmalardan birini bosing yoki matn orqali savol yo'llang:</i>"
    )
    await message.answer(voice_response, reply_markup=kb, parse_mode="HTML")
