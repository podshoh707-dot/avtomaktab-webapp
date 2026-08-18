from aiogram import Router, types, Bot
from config import ADMIN_IDS
from database import async_session, Setting
from sqlalchemy import select
import logging

catchall_router = Router()

import json
from aiogram import F

@catchall_router.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    data_str = message.web_app_data.data
    try:
        data = json.loads(data_str)
        if data.get('action') == 'test_completed':
            correct = data.get('correct', 0)
            total = data.get('total', 10)
            
            async with async_session() as session:
                # User topish
                from database.models import User, UserStat
                result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
                user = result.scalars().first()
                
                if user:
                    # Ballarni yangilash (har bir to'g'ri javob uchun 5 ball masalan)
                    added_points = correct * 5
                    user.points += added_points
                    
                    # Statistikani yangilash
                    stat_result = await session.execute(select(UserStat).where(UserStat.user_id == user.id))
                    user_stat = stat_result.scalars().first()
                    
                    if user_stat:
                        user_stat.tests_taken += 1
                        user_stat.correct_answers += correct
                        user_stat.wrong_answers += (total - correct)
                    
                    await session.commit()
                    await message.answer(
                        f"🎉 **Test muvaffaqiyatli yakunlandi!**\n\n"
                        f"✅ To'g'ri javoblar: {correct}/{total}\n"
                        f"🏆 Sizga {added_points} ball berildi!"
                    )
    except Exception as e:
        logging.error(f"WebApp data error: {e}")

from aiogram.fsm.context import FSMContext

@catchall_router.message()
async def forward_user_messages(message: types.Message, state: FSMContext):
    # Agar xabar admindan bo'lsa yoki guruhda bo'lsa, forward qilmaymiz
    if message.from_user.id in ADMIN_IDS or message.chat.type != "private":
        return
        
    # Noto'g'ri tugma yoki yozuv kelsa, holatni tozalaymiz
    await state.clear()
    
    # Asosiy menyuni chaqirish uchun start bosishni eslatamiz
    await message.answer("Tushunarsiz buyruq yoki xabar. Iltimos, pastdagi menyudan kerakli bo'limni tanlang yoki /start ni bosing.")
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "forward_status"))
        setting = result.scalars().first()
        
    if setting and setting.value == "1":
        try:
            # Xabarni barcha adminlarga yuborish
            for admin_id in ADMIN_IDS:
                try:
                    await message.forward(chat_id=admin_id)
                except Exception as e:
                    logging.error(f"Adminga ({admin_id}) xabar uzatishda xatolik: {e}")
        except Exception as e:
            logging.error(f"Xabarni uzatishda umumiy xatolik: {e}")
