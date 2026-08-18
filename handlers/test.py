from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User, Setting, Question, UserStat, UserMistake, TestSession
from sqlalchemy import select
from sqlalchemy.sql.expression import func
from datetime import datetime
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import json

test_router = Router()

# ─── Test sessiyasini bazaga saqlash ───
async def save_test_session(telegram_id: int, data: dict):
    async with async_session() as session:
        result = await session.execute(select(TestSession).where(TestSession.telegram_id == telegram_id))
        ts = result.scalars().first()
        q_ids = data.get('questions', [])
        if not q_ids:
            return
        if not ts:
            ts = TestSession(
                telegram_id=telegram_id,
                question_ids=json.dumps(q_ids),
                current_idx=data.get('current_idx', 0),
                correct_answers=data.get('correct_answers', 0),
                is_mistake_mode=data.get('is_mistake_mode', False),
                category=data.get('selected_category', None)
            )
            session.add(ts)
        else:
            ts.question_ids = json.dumps(q_ids)
            ts.current_idx = data.get('current_idx', 0)
            ts.correct_answers = data.get('correct_answers', 0)
            ts.is_mistake_mode = data.get('is_mistake_mode', False)
            ts.category = data.get('selected_category', None)
            ts.updated_at = datetime.utcnow()
        await session.commit()

async def delete_test_session(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(TestSession).where(TestSession.telegram_id == telegram_id))
        ts = result.scalars().first()
        if ts:
            await session.delete(ts)
            await session.commit()

async def load_test_session(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(TestSession).where(TestSession.telegram_id == telegram_id))
        ts = result.scalars().first()
        if ts:
            return {
                'questions': json.loads(ts.question_ids),
                'current_idx': ts.current_idx,
                'correct_answers': ts.correct_answers,
                'is_mistake_mode': ts.is_mistake_mode,
                'selected_category': ts.category
            }
    return None

class TestStates(StatesGroup):
    taking_test = State()

@test_router.message(Command("test"), F.chat.type == "private")
@test_router.message(F.text.in_([
    "🎯 Test Ishlash (1242 ta YHQ)", "🎯 Test Ishlash", "🎓 GAI Imtihoni (Sertifikatli)", "🎓 GAI Imtihoni",
    "🚗 Ishlash testi", "🚀 Test Boshlash (Pro)", "🚀 Test Boshlash", "🚗 Test ishlash",
    "🚗 Ишлаш тести", "🚗 Тестирование"
]), F.chat.type == "private")
async def cmd_test(message: types.Message, state: FSMContext):
    await state.clear()
    if message.text in ["🎓 GAI Imtihoni (Sertifikatli)", "🎓 GAI Imtihoni"]:
        # Darhol GAI imtihonini boshlash
        # Mock callback query
        class FakeCallback:
            def __init__(self, msg):
                self.message = msg
                self.from_user = msg.from_user
                self.data = "testcnt_gai"
                self.bot = msg.bot
            async def answer(self, *args, **kwargs): pass
        await start_test(FakeCallback(message), state)
        return
    await test_menu(message, state)

async def test_menu(message: types.Message, state: FSMContext):
    # Eski sessiya bor-yo'qligini tekshir
    existing = await load_test_session(message.from_user.id)
    if existing:
        left = len(existing['questions']) - existing['current_idx']
        resume_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Davom ettirish", callback_data="test_resume"),
             InlineKeyboardButton(text="🔄 Yangi test", callback_data="test_new")]
        ])
        await message.answer(
            f"⏸ <b>Sizda tugallanmagan test bor!</b>\n\n"
            f"📊 Savol: {existing['current_idx']}/{len(existing['questions'])}\n"
            f"✅ To'g'ri: {existing['correct_answers']}\n"
            f"🔢 Qolgan: {left} ta\n\n"
            f"Davom ettirasizmi yoki yangi test boshlaysizmi?",
            reply_markup=resume_kb,
            parse_mode="HTML"
        )
        return
    await state.clear()
    
    keyboard = [
        [InlineKeyboardButton(text="🎓 GAI Imtihoni (20 ta, Sertifikatli)", callback_data="testcnt_gai")],
        [InlineKeyboardButton(text="🎯 Marafon 1242 (To'xtagan joydan)", callback_data="testcnt_marathon")],
        [InlineKeyboardButton(text="🎬 Video-Testlar (207 ta 3D Vaziyat)", callback_data="testcnt_videos")],
        [InlineKeyboardButton(text="⚡️ Ekspress Blits (10 ta tezkor)", callback_data="testcnt_10"),
         InlineKeyboardButton(text="🧠 Zaif tomonlarim (Xatolar)", callback_data="test_mistakes")],
        [InlineKeyboardButton(text="📂 Barcha 70 ta Biletlar Katalogi", callback_data="biletpage_1")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_main_menu")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    bot_obj = message.bot if hasattr(message, 'bot') else message.message.bot if hasattr(message, 'message') else None
    bot_username = ""
    if bot_obj:
        bot_info = await bot_obj.get_me()
        bot_username = f"@{bot_info.username}"
    
    text = (
        "🏆 <b>AVTOMAKTAB — INNOVATSION AVTOTEST TIZIMI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚦 <i>O'zbekiston YHQ Davlat Standartidagi eng mukammal test bazasi!</i>\n\n"
        "🏎 <b>1242 ta Rasmiy Savollar</b> (826 ta rasm va 207 ta 3D video animatsiyalar)\n"
        "🎓 <b>GAI Imtihon Simulyatori:</b> 20 ta savol + Rasmiy Sertifikat\n"
        "🎯 <b>1242 Marafon:</b> Har bir savolni to'xtagan joyingizdan yechib boring\n"
        "🎬 <b>Video-Testlar:</b> Haqiqiy chorraha va harakat animatsiyalari\n\n"
        "👇 <b>Quyidagi test rejimlaridan birini tanlang:</b>"
    )
    
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

# 70 ta bilet sahifalash (1-10, 11-20, ...)
@test_router.callback_query(F.data.startswith("biletpage_"))
async def bilet_page_handler(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    per_page = 10
    total_bilets = 70
    start_bilet = (page - 1) * per_page + 1
    end_bilet = min(start_bilet + per_page - 1, total_bilets)
    
    keyboard = []
    row = []
    for b in range(start_bilet, end_bilet + 1):
        row.append(InlineKeyboardButton(text=f"📄 {b}-bilet", callback_data=f"testbilet_{b}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"biletpage_{page-1}"))
    if end_bilet < total_bilets:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"biletpage_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy test menyusi", callback_data="test_back_to_cats")])
    
    text = (
        f"📂 <b>YHQ BILETLAR KATALOGI ({start_bilet}-{end_bilet} / 70)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Har bir biletda 10 tadan rasmiy YHQ savollari mavjud.\n"
        f"👇 <i>Ishlamoqchi bo'lgan biletingizni tanlang:</i>"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@test_router.callback_query(F.data == "test_back_to_cats")
async def test_back_to_cats(callback: types.CallbackQuery, state: FSMContext):
    await test_menu(callback, state)

@test_router.callback_query(F.data == "test_resume")
async def test_resume(callback: types.CallbackQuery, state: FSMContext):
    existing = await load_test_session(callback.from_user.id)
    if not existing:
        await callback.answer("Sessiya topilmadi.", show_alert=True)
        return
    await state.set_state(TestStates.taking_test)
    await state.set_data(existing)
    await callback.message.delete()
    await send_question(callback, state)

@test_router.callback_query(F.data == "test_new")
async def test_new(callback: types.CallbackQuery, state: FSMContext):
    await delete_test_session(callback.from_user.id)
    await state.clear()
    await callback.message.delete()
    await test_menu(callback, state)

@test_router.callback_query(F.data.startswith("testcat_"))
async def test_count_menu(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data.split("_", 1)[1]
    await state.update_data(selected_category=cat)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 10 ta savol (Tezkor)", callback_data="testcnt_10"),
         InlineKeyboardButton(text="🔸 20 ta savol (O'rta)", callback_data="testcnt_20")],
        [InlineKeyboardButton(text="🔥 50 ta savol (Qiyin)", callback_data="testcnt_50"),
         InlineKeyboardButton(text="💎 100 ta savol (Pro Rejim)", callback_data="testcnt_100")],
        [InlineKeyboardButton(text="🎓 Haqiqiy Imtihon (70 ta savol, VIP)", callback_data="testcnt_70")],
        [InlineKeyboardButton(text="🔙 Orqaga Qaytish", callback_data="test_back_to_cats")]
    ])
    
    bot_info = await callback.bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    text = (
        f"📂 <b>Tanlangan bo'lim:</b> <i>{cat}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 <b>Maqsad:</b> Maksimal to'g'ri javob!\n"
        "⏳ <b>Vaqt:</b> Cheklanmagan (erkin rejim)\n\n"
        "<i>Imtihon rejimi faqat qiyin savollardan tashkil topadi va Premium talab qilinishi mumkin.</i>\n\n"
        "👇 <b>Nechta savol ishlashni xohlaysiz?</b>\n\n"
        f"👉 <i>Bizning bot orqali imtihonga tayyorlaning:</i> <b>{bot_username}</b>"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

async def send_question(message_or_callback, state: FSMContext):
    data = await state.get_data()
    q_ids = data.get("questions", [])
    current_idx = data.get("current_idx", 0)
    
    if current_idx >= len(q_ids):
        # End of test
        correct_count = data.get("correct_answers", 0)
        total_count = len(q_ids)
        
        # Save to UserStat
        async with async_session() as session:
            # We need user_id (the primary key in users table, not telegram_id)
            user_id_tg = message_or_callback.from_user.id
            result_user = await session.execute(select(User).where(User.telegram_id == user_id_tg))
            user = result_user.scalars().first()
            if user:
                result_stat = await session.execute(select(UserStat).where(UserStat.user_id == user.id))
                stat = result_stat.scalars().first()
                if not stat:
                    stat = UserStat(user_id=user.id, tests_taken=1, correct_answers=correct_count, wrong_answers=total_count - correct_count)
                    session.add(stat)
                else:
                    stat.tests_taken += 1
                    stat.correct_answers += correct_count
                    stat.wrong_answers += (total_count - correct_count)
                    stat.last_active = datetime.utcnow()

                # 🔥 Kunlik Seriya (Daily Streak) hisoblash
                from datetime import timedelta
                today_str = datetime.utcnow().strftime("%Y-%m-%d")
                yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                streak_bonus_text = ""
                if user.last_streak_date != today_str:
                    if user.last_streak_date == yesterday_str:
                        user.streak_count = (user.streak_count or 0) + 1
                    else:
                        user.streak_count = 1
                    user.last_streak_date = today_str
                    
                    # Har 7 kunlik uzluksiz seriya uchun +3 kun VIP sovg'a
                    if user.streak_count > 0 and user.streak_count % 7 == 0:
                        user.is_premium = True
                        base_exp = user.premium_expires_at if (user.premium_expires_at and user.premium_expires_at > datetime.utcnow()) else datetime.utcnow()
                        user.premium_expires_at = base_exp + timedelta(days=3)
                        streak_bonus_text = f"\n\n🎁 <b>QOYIL! {user.streak_count} KUNLIK UZLUKSIZ SERIYA UCHUN SIZGA +3 KUNLIK VIP OBUNA SOVG'A QILINDI!</b> 💎🔥"

                await session.commit()
                
        await state.clear()
        await delete_test_session(message_or_callback.from_user.id)
        
        # Reply based on object type
        percent = round(correct_count / max(total_count, 1) * 100)
        is_gai = data.get("is_gai_mode", False)
        
        # Foydalanuvchi ma'lumotlarini olish
        user_name = "Hurmatli Haydovchi"
        if user and user.full_name:
            user_name = user.full_name
            
        bot_obj = message_or_callback.bot if hasattr(message_or_callback, 'bot') else message_or_callback.message.bot if hasattr(message_or_callback, 'message') else None
        bot_uname = "Avtomaktab_bot"
        if bot_obj:
            binfo = await bot_obj.get_me()
            bot_uname = binfo.username
            
        import urllib.parse
        share_msg = f"🏆 Men Avtomaktab botida YHQ testini {percent}% natija bilan ishladim! Siz ham bilimingizni sinab ko'ring:"
        share_url = f"https://t.me/share/url?url=https://t.me/{bot_uname}?start=ref_{message_or_callback.from_user.id}&text={urllib.parse.quote(share_msg)}"

        cert_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Sertifikatni Ulashish (Do'stlarga)", url=share_url)],
            [InlineKeyboardButton(text="🔄 Yangi test boshlash", callback_data="test_back_to_cats")],
            [InlineKeyboardButton(text="👑 Xatolar tahlili", callback_data="test_mistakes")],
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")]
        ])

        finish_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Natijani Do'stlarga Ulashish", url=share_url)],
            [InlineKeyboardButton(text="🔄 Yangi test boshlash", callback_data="test_back_to_cats")],
            [InlineKeyboardButton(text="🎓 GAI Imtihonini topshirish", callback_data="testcnt_gai")],
            [InlineKeyboardButton(text="👑 Xatolar tahlili", callback_data="test_mistakes")],
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")]
        ])

        if is_gai and correct_count >= 18:
            # GAI IMTIHONIDAN O'TDI - SERTIFIKAT GENERATSIYA QILISH
            try:
                from utils.certificate_generator import generate_certificate
                from aiogram.types import FSInputFile
                cert_path = generate_certificate(user_name, correct_count, total_count)
                
                cert_caption = (
                    f"🎉 <b>TABRIKLAYMIZ, {user_name.upper()}!</b>\n\n"
                    f"🏆 <b>SIZ YHQ DAVLAT IMTIHONIDAN MUVAFFAQIYATLI O'TDINGIZ!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📊 <b>Natija:</b> {correct_count}/{total_count} ta to'g'ri ({percent}%)\n"
                    f"❌ <b>Xatolar soni:</b> {total_count - correct_count} ta (Ruxsat: 2 ta)\n\n"
                    f"📄 Sizning nomingizga rasmiy <b>Sertifikat</b> rasmiylashtirildi!\n"
                    f"<i>Ushbu sertifikatni saqlab oling va do'stlaringiz bilan ulashing!</i>"
                )
                
                if isinstance(message_or_callback, types.CallbackQuery):
                    await message_or_callback.message.answer_photo(
                        photo=FSInputFile(cert_path),
                        caption=cert_caption,
                        reply_markup=cert_kb,
                        parse_mode="HTML"
                    )
                    await message_or_callback.answer()
                else:
                    await message_or_callback.answer_photo(
                        photo=FSInputFile(cert_path),
                        caption=cert_caption,
                        reply_markup=cert_kb,
                        parse_mode="HTML"
                    )
                return
            except Exception as e:
                print(f"Error generating certificate: {e}")

        status_emoji = "🏆" if percent >= 90 else "👍" if percent >= 70 else "⚠️"
        is_marathon = data.get("is_marathon_mode", False)
        is_videos = data.get("is_video_mode", False)

        streak_info = f"🔥 <b>Kunlik Seriyangiz:</b> {user.streak_count or 1}-kun ketma-ket!\n" if user else ""

        if is_marathon:
            marathon_prog = user.marathon_progress if user else correct_count
            m_pct = round(min(1242, marathon_prog) / 1242 * 100)
            text = (
                f"🎯 <b>1242 MARAFON BOSQICHI YAKUNLANDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{streak_info}"
                f"📊 <b>Umumiy Marafon Natijangiz:</b> {marathon_prog} / 1242 ta ({m_pct}%)\n"
                f"✅ <b>Ushbu bosqichda to'g'ri:</b> {correct_count} ta\n\n"
                f"<i>Sizning ko'rsatkichingiz bazada saqlandi. Xohlagan vaqtingizda to'xtagan joyingizdan davom ettirishingiz mumkin!</i>"
                f"{streak_bonus_text}"
            )
        elif is_videos:
            text = (
                f"🎬 <b>VIDEO-TESTLAR BOSQICHI YAKUNLANDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{streak_info}"
                f"📊 <b>Jami savollar:</b> {total_count} ta\n"
                f"✅ <b>To'g'ri javoblar:</b> {correct_count} ta\n"
                f"❌ <b>Noto'g'ri javoblar:</b> {total_count - correct_count} ta\n"
                f"🎯 <b>Natija:</b> {percent}%\n\n"
                f"<i>Harakat xavfsizligini oshirish uchun video-vaziyatlarni muntazam mashq qilib boring!</i>"
                f"{streak_bonus_text}"
            )
        else:
            text = (
                f"🏁 <b>TEST YAKUNLANDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{streak_info}"
                f"📊 <b>Jami savollar:</b> {total_count} ta\n"
                f"✅ <b>To'g'ri javoblar:</b> {correct_count} ta\n"
                f"❌ <b>Noto'g'ri javoblar:</b> {total_count - correct_count} ta\n"
                f"{status_emoji} <b>Natija:</b> {percent}%\n\n"
                f"<i>Bilimingizni mustahkamlash uchun yana test ishlang yoki xatolaringiz ustida ishlang!</i>"
                f"{streak_bonus_text}"
            )
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.message.answer(text, reply_markup=finish_kb, parse_mode="HTML")
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(text, reply_markup=finish_kb, parse_mode="HTML")
        return

    # Fetch question and setting
    q_id = q_ids[current_idx]
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == q_id))
        q = result.scalars().first()
        
        result_set = await session.execute(select(Setting).where(Setting.key == "protect_content"))
        protect_setting = result_set.scalars().first()
        # Default is False (Forward allowed), if setting is "1" -> protect=True
        protect = True if (protect_setting and protect_setting.value == "1") else False
        
    if not q:
        # Failsafe
        await state.update_data(current_idx=current_idx + 1)
        await send_question(message_or_callback, state)
        return
        
    # Tugmalar qatori
    btns = []
    btns.append(InlineKeyboardButton(text="A", callback_data="ans_A"))
    if q.option_b: btns.append(InlineKeyboardButton(text="B", callback_data="ans_B"))
    if q.option_c: btns.append(InlineKeyboardButton(text="C", callback_data="ans_C"))
    if q.option_d: btns.append(InlineKeyboardButton(text="D", callback_data="ans_D"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        btns,
        [InlineKeyboardButton(text="Tugatish", callback_data="ans_quit")]
    ])
    
    # Filter empty rows
    keyboard.inline_keyboard = [row for row in keyboard.inline_keyboard if row]

    if isinstance(message_or_callback, types.CallbackQuery):
        msg = message_or_callback.message
        bot_obj = msg.bot
    else:
        msg = message_or_callback
        bot_obj = msg.bot

    # Savol matni va variantlar caption sifatida
    caption = (
        f"<b>Savol {current_idx + 1} / {len(q_ids)}</b>\n\n"
        f"❓ {q.text}\n\n"
        f"1️⃣ A) {q.option_a}\n"
    )
    if q.option_b: caption += f"2️⃣ B) {q.option_b}\n"
    if q.option_c: caption += f"3️⃣ C) {q.option_c}\n"
    if q.option_d: caption += f"4️⃣ D) {q.option_d}\n"

    bot_info = await bot_obj.get_me()
    caption += f"\n👉 @{bot_info.username}"

    # Media fayllarni aniqlash
    from aiogram.types import FSInputFile
    import os, json
    from config import BASE_DIR

    media_obj = None
    is_vid = False

    # Agar savolda asosiy video bo'lsa
    if q.media_urls:
        try:
            m_dict = json.loads(q.media_urls) if isinstance(q.media_urls, str) else q.media_urls
            if isinstance(m_dict, dict) and m_dict.get("main"):
                main_vid_path = os.path.join(BASE_DIR, m_dict["main"].replace('\\', '/'))
                if os.path.exists(main_vid_path):
                    media_obj = FSInputFile(main_vid_path)
                    is_vid = True
        except Exception:
            pass

    # Agar video topilmagan bo'lsa, rasmni olamiz
    if not media_obj and q.image_url:
        if not str(q.image_url).startswith("http"):
            cand1 = os.path.join(BASE_DIR, "webapp", str(q.image_url).replace('\\', '/'))
            cand2 = os.path.join(BASE_DIR, str(q.image_url).replace('\\', '/'))
            if os.path.exists(cand1):
                media_obj = FSInputFile(cand1)
            elif os.path.exists(cand2):
                media_obj = FSInputFile(cand2)
        else:
            media_obj = q.image_url

    try:
        if media_obj:
            if is_vid:
                await msg.answer_video(
                    video=media_obj,
                    caption=caption,
                    reply_markup=keyboard,
                    protect_content=protect,
                    parse_mode="HTML"
                )
            else:
                await msg.answer_photo(
                    photo=media_obj,
                    caption=caption,
                    reply_markup=keyboard,
                    protect_content=protect,
                    parse_mode="HTML"
                )
        else:
            await msg.answer(caption, reply_markup=keyboard, protect_content=protect, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending question media: {e}")
        await msg.answer(caption, reply_markup=keyboard, protect_content=protect, parse_mode="HTML")

@test_router.callback_query(F.data.startswith("testcnt_") | F.data.startswith("testbilet_") | F.data.in_(["test_mistakes"]))
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    if callback.data.startswith("testbilet_"):
        bilet_num = callback.data.split("_")[1]
        mode = f"bilet_{bilet_num}"
    elif callback.data.startswith("testcnt_"):
        mode = callback.data.split("_")[1]
    else:
        mode = "mistakes"
    
    # Premium check for locked modes
    if mode in ["70", "mistakes"]:
        async with async_session() as session:
            result_user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
            user = result_user.scalars().first()
            is_expired = True
            if user and user.is_premium and user.premium_expires_at:
                if user.premium_expires_at > datetime.utcnow():
                    is_expired = False
            
            if not user or not user.is_premium or is_expired:
                await callback.answer("👑 Kechirasiz, bu bo'lim faqat VIP (Premium) foydalanuvchilar uchun ochiq!", show_alert=True)
                return

    if mode == "mistakes":
        async with async_session() as session:
            user_id_tg = callback.from_user.id
            result_user = await session.execute(select(User).where(User.telegram_id == user_id_tg))
            user = result_user.scalars().first()
            if not user:
                await callback.message.edit_text("Foydalanuvchi topilmadi.")
                return
                
            result_mistakes = await session.execute(
                select(UserMistake.question_id).where(UserMistake.user_id == user.id).order_by(func.random()).limit(50)
            )
            q_ids = result_mistakes.scalars().all()
            
            if not q_ids:
                await callback.message.edit_text("🎉 Sizda hozircha xato ishlangan testlar yo'q. Ofarin!")
                return
                
            await state.set_state(TestStates.taking_test)
            await state.update_data(questions=q_ids, current_idx=0, correct_answers=0, is_mistake_mode=True)
            await callback.message.delete()
            await send_question(callback, state)
        return
        
    is_gai = mode == "gai"
    is_marathon = mode == "marathon"
    is_videos = mode == "videos"
    is_bilet = mode.startswith("bilet_")
    
    data = await state.get_data()
    category = data.get("selected_category", "Barchasi")
    
    # Premium check for ALL tests if premium_mode is ON
    async with async_session() as session:
        result_mode = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
        mode_setting = result_mode.scalars().first()
        is_premium_mode_on = mode_setting.value == "1" if mode_setting else False
        
        result_user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result_user.scalars().first()

        if is_premium_mode_on:
            is_expired = True
            if user and user.is_premium and user.premium_expires_at:
                if user.premium_expires_at > datetime.utcnow():
                    is_expired = False
            
            if not user or not user.is_premium or is_expired:
                await callback.message.edit_text(
                    "🔒 Hozirda bot faqat **Premium** tarifda ishlamoqda.\n"
                    "Sizda faol obuna yo'q yoki uning muddati tugagan.\n\n"
                    "Iltimos, Asosiy menyudan **⭐ Premium** bo'limiga o'tib, bot tarifini xarid qiling."
                )
                return
                
        # 1. Marafon Rejimi (1242 savol)
        if is_marathon:
            marathon_prog = user.marathon_progress if user and user.marathon_progress else 0
            if marathon_prog >= 1242:
                marathon_prog = 0 # Qayta boshlash
            stmt = select(Question.id).order_by(Question.id).offset(marathon_prog).limit(50)
            result_q = await session.execute(stmt)
            q_ids = result_q.scalars().all()
            
        # 2. Faqat Video-testlar rejimi
        elif is_videos:
            stmt = select(Question.id).where(Question.media_urls != None).order_by(func.random()).limit(20)
            result_q = await session.execute(stmt)
            q_ids = result_q.scalars().all()
            
        # 3. Aniq Bilet tanlanganda
        elif is_bilet:
            b_num = mode.split("_")[1]
            stmt = select(Question.id).where(Question.category == f"{b_num}-Bilet").order_by(Question.id)
            result_q = await session.execute(stmt)
            q_ids = result_q.scalars().all()
            
        # 4. GAI Imtihoni yoki Oddiy sonli test
        else:
            count = 20 if is_gai else int(mode)
            stmt = select(Question.id)
            if not is_gai and category and category != "Barchasi":
                stmt = stmt.where(Question.category.startswith(category))
                
            result_q = await session.execute(stmt.order_by(func.random()).limit(count))
            q_ids = result_q.scalars().all()
        
    if not q_ids:
        await callback.message.edit_text("Hozircha bazada savollar yo'q.")
        return
        
    await state.set_state(TestStates.taking_test)
    await state.update_data(
        questions=q_ids, current_idx=0, correct_answers=0, wrong_count=0,
        is_gai_mode=is_gai, is_marathon_mode=is_marathon, is_video_mode=is_videos
    )
    # Sessiyani bazaga saqlash
    await save_test_session(callback.from_user.id, {
        'questions': q_ids, 'current_idx': 0, 'correct_answers': 0,
        'is_gai_mode': is_gai, 'is_marathon_mode': is_marathon, 'selected_category': category
    })
    await callback.message.delete()
    await send_question(callback, state)

@test_router.callback_query(TestStates.taking_test, F.data.startswith("ans_"))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    ans = callback.data.split("_")[1]
    
    if ans == "quit":
        await callback.message.delete()
        data = await state.get_data()
        answered = data.get("current_idx", 0)  # Hozircha nechta savol o'tilgan
        q_ids = data.get("questions", [])
        # Savollar ro'yxatini faqat javob berilganlarga qisqartir
        await state.update_data(questions=q_ids[:answered], current_idx=answered)
        await send_question(callback, state)
        return
        
    data = await state.get_data()
    q_ids = data.get("questions", [])
    current_idx = data.get("current_idx", 0)
    correct_count = data.get("correct_answers", 0)
    
    if current_idx >= len(q_ids):
        await callback.answer("Test tugagan.", show_alert=True)
        return
        
    q_id = q_ids[current_idx]
    
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == q_id))
        q = result.scalars().first()
        
        result_set = await session.execute(select(Setting).where(Setting.key == "protect_content"))
        protect_setting = result_set.scalars().first()
        protect = True if (protect_setting and protect_setting.value == "1") else False
        
    if not q:
        await state.update_data(current_idx=current_idx + 1)
        await callback.message.delete()
        await send_question(callback, state)
        return
    
    options_map = {
        "A": q.option_a,
        "B": q.option_b,
        "C": q.option_c,
        "D": q.option_d
    }
    correct_text = options_map.get(q.correct_option, "")
    explanation = (q.explanation or "").strip()
    
    emoji_map = {
        "A": "1️⃣ A",
        "B": "2️⃣ B",
        "C": "3️⃣ C",
        "D": "4️⃣ D"
    }
    
    is_correct = ans == q.correct_option
    bot_info = await callback.bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    result_msg = f"🚸 <b>DIQQAT, TEST SAVOLI!</b>\n\n{q.text} 🤔\n\n"
    
    if is_correct:
        correct_count += 1
        result_msg += f"✅ <b>Sizning javobingiz to'g'ri:</b> {emoji_map.get(q.correct_option, q.correct_option)} — {correct_text}"
        
        if data.get("is_marathon_mode"):
            user_id_tg = callback.from_user.id
            async with async_session() as session_m:
                result_u = await session_m.execute(select(User).where(User.telegram_id == user_id_tg))
                u_obj = result_u.scalars().first()
                if u_obj:
                    u_obj.marathon_progress = (u_obj.marathon_progress or 0) + 1
                    await session_m.commit()

        if data.get("is_mistake_mode"):
            from sqlalchemy import delete
            user_id_tg = callback.from_user.id
            async with async_session() as session2:
                result_user = await session2.execute(select(User).where(User.telegram_id == user_id_tg))
                user = result_user.scalars().first()
                if user:
                    # Xatoni o'chirish (to'g'ri topildi)
                    await session2.execute(
                        delete(UserMistake).where(
                            (UserMistake.user_id == user.id) & (UserMistake.question_id == q_id)
                        )
                    )
                    await session2.commit()
    else:
        chosen_text = options_map.get(ans, "")
        result_msg += (
            f"❌ <b>Siz tanladingiz:</b> {emoji_map.get(ans, ans)} — {chosen_text}\n"
            f"✅ <b>To'g'ri javob:</b> {emoji_map.get(q.correct_option, q.correct_option)} — {correct_text}"
        )
        
        user_id_tg = callback.from_user.id
        async with async_session() as session2:
            result_user = await session2.execute(select(User).where(User.telegram_id == user_id_tg))
            user = result_user.scalars().first()
            if user:
                result_mistake = await session2.execute(
                    select(UserMistake).where((UserMistake.user_id == user.id) & (UserMistake.question_id == q_id))
                )
                mistake = result_mistake.scalars().first()
                if mistake:
                    mistake.mistake_count += 1
                    mistake.last_mistake_at = datetime.utcnow()
                else:
                    mistake = UserMistake(user_id=user.id, question_id=q_id)
                    session2.add(mistake)
                await session2.commit()
    
    if explanation:
        result_msg += f"\n\n📖 <b>Izoh:</b>\n<i>{explanation}</i>"
        
    result_msg += f"\n\n🚘 <b>Avtotest savollari va foydali ma'lumotlar:</b>\n👉 {bot_username}"
    
    new_idx = current_idx + 1
    wrong_count = data.get("wrong_count", 0)
    if not is_correct:
        wrong_count += 1
        
    await state.update_data(current_idx=new_idx, correct_answers=correct_count, wrong_count=wrong_count)
    # Sessiyani yangilash
    await save_test_session(callback.from_user.id, {'questions': q_ids, 'current_idx': new_idx, 'correct_answers': correct_count, 'wrong_count': wrong_count, 'is_mistake_mode': data.get('is_mistake_mode', False), 'is_gai_mode': data.get('is_gai_mode', False), 'selected_category': data.get('selected_category')})
    
    if is_correct:
        await callback.answer("🎉 Qoyil! Javobingiz to'g'ri!", show_alert=True)
    else:
        await callback.answer("❌ Noto'g'ri javob!", show_alert=True)
    await callback.message.delete()

    # GAI Imtihonida 3 ta xato bo'lsa darhol to'xtatish
    if data.get("is_gai_mode") and wrong_count >= 3:
        await state.clear()
        await delete_test_session(callback.from_user.id)
        
        fail_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Qayta topshirish", callback_data="testcnt_gai")],
            [InlineKeyboardButton(text="🔙 Bo'limlar menyusi", callback_data="test_back_to_cats")]
        ])
        
        fail_text = (
            f"❌ <b>GAI IMTIHONI TOPSHIRILMADI (YIQILDI)!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚠️ <b>Qilingan xatolar:</b> 3 ta\n"
            f"📊 <b>Ko'rilgan savollar:</b> {new_idx}/20 ta\n\n"
            f"<i>YHQ Davlat Standartiga ko'ra 20 ta savoldan maksimal 2 tagacha xatoga ruxsat beriladi. 3-xatoda imtihon to'xtatiladi.</i>\n\n"
            f"💡 <i>Mavzularni qayta takrorlab, yana bir bor sinab ko'ring!</i>"
        )
        await callback.message.answer(result_msg + "\n\n" + fail_text, reply_markup=fail_kb, protect_content=protect, parse_mode="HTML")
        return
    
    # Izohni alohida xabar sifatida yuborish — keyingi savol va AI Ustoz tugmasi bilan
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data="next_question")],
        [InlineKeyboardButton(text="🤖 AI Ustoz tushuntirishi", callback_data=f"ai_explain_{q_id}")]
    ])

    # Variant videosini (3D animatsiyani) tekshirish
    anim_vid_file = None
    if q.media_urls:
        try:
            m_dict = json.loads(q.media_urls) if isinstance(q.media_urls, str) else q.media_urls
            if isinstance(m_dict, dict):
                # O'quvchi tanlagan variant yoki to'g'ri variant videosi
                v_target = m_dict.get(ans) or m_dict.get(q.correct_option)
                if v_target:
                    v_full = os.path.join(BASE_DIR, v_target.replace('\\', '/'))
                    if os.path.exists(v_full):
                        anim_vid_file = FSInputFile(v_full)
        except Exception:
            pass

    if anim_vid_file:
        try:
            await callback.message.answer_video(
                video=anim_vid_file,
                caption=result_msg,
                reply_markup=keyboard,
                protect_content=protect,
                parse_mode="HTML"
            )
            return
        except Exception as e:
            print(f"Error sending anim video: {e}")

    await callback.message.answer(result_msg, reply_markup=keyboard, protect_content=protect, parse_mode="HTML")

@test_router.callback_query(TestStates.taking_test, F.data == "next_question")
async def next_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await send_question(callback, state)
