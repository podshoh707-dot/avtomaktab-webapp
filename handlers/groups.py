from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from database import async_session, Question, User, BotGroup, GroupQuizSession, Sign
from sqlalchemy import select, func
import asyncio
import random
import json
import time
import os
import re
from datetime import datetime
from config import BASE_DIR, ADMIN_IDS

groups_router = Router()

from middlewares.group_force_reg import GroupForceRegistrationMiddleware
groups_router.message.middleware(GroupForceRegistrationMiddleware())

# Guruhdagi faol viktorinalarni saqlash xotirasi:
# {chat_id: {"is_active": bool, "poll_ids": {}, "participants": {}, "current_poll_start": float, "total_questions": int, "chat_title": str}}
active_quizzes = {}

async def delete_later(message: types.Message, delay: int = 5):
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass

# ─── Guruh viktorinasi DB yordamchilari ───
async def save_group_quiz_to_db(chat_id: int, chat_title: str, q_ids: list, idx: int, total: int, participants: dict, poll_ids: dict):
    try:
        async with async_session() as session:
            result = await session.execute(select(GroupQuizSession).where(GroupQuizSession.chat_id == chat_id))
            gs = result.scalars().first()
            p_json = json.dumps(participants, ensure_ascii=False)
            poll_json = json.dumps(poll_ids, ensure_ascii=False)
            if not gs:
                gs = GroupQuizSession(
                    chat_id=chat_id, chat_title=chat_title,
                    question_ids=json.dumps(q_ids), current_idx=idx,
                    total_questions=total, participants=p_json,
                    poll_ids=poll_json, is_active=True
                )
                session.add(gs)
            else:
                gs.current_idx = idx
                gs.participants = p_json
                gs.poll_ids = poll_json
                gs.is_active = True
                gs.updated_at = datetime.utcnow()
            await session.commit()
    except Exception as e:
        print(f"Error saving group quiz to db: {e}")

async def delete_group_quiz_from_db(chat_id: int):
    try:
        async with async_session() as session:
            result = await session.execute(select(GroupQuizSession).where(GroupQuizSession.chat_id == chat_id))
            gs = result.scalars().first()
            if gs:
                await session.delete(gs)
                await session.commit()
    except Exception:
        pass

# Guruhga qo'shilganda botni tanishtirish
@groups_router.my_chat_member()
async def on_bot_added_to_group(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"] and event.new_chat_member.user.id == event.bot.id:
        try:
            bot_info = await event.bot.get_me()
            await event.bot.send_message(
                event.chat.id,
                f"👋 <b>Assalomu alaykum, {event.chat.title} a'zolari!</b>\n\n"
                f"Men <b>Avtovatanparvar</b> — YHQ bo'yicha aqlli va innovatsion viktorina botiman! 🚗💨\n\n"
                f"🏆 <b>Guruhdagi asosiy imkoniyatlar:</b>\n"
                f"• <code>/test</code> yoki <code>/viktorina</code> — Qiziqarli YHQ viktorinasini boshlash\n"
                f"• <code>/statistika</code> — Guruhning eng bilimdon TOP haydovchilari\n"
                f"• <code>/toxta</code> — Viktorinani to'xtatish (adminlar uchun)\n"
                f"• <code>/bot</code> — Obuna va bot sozlamalari\n\n"
                f"⚠️ <b>Maslahat:</b> Bot guruhda to'liq va tezkor ishlashi uchun uni guruhga <b>ADMIN</b> qilib tayinlashingizni tavsiya qilamiz!",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending welcome message to chat {event.chat.id}: {e}")


# ─── PREMIUM VIKTORINA BOSHLASH MENYUSI ────────────────────────────
@groups_router.channel_post(Command(commands=["test", "quiz", "viktorina", "boshla", "testlar"]))
@groups_router.message(Command(commands=["test", "quiz", "viktorina", "boshla", "testlar"]), F.chat.type.in_(["group", "supergroup"]))
async def group_test_launcher(message: types.Message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    
    # Guruhda adminlikni tekshirish
    if chat_type in ["group", "supergroup"]:
        is_admin = False
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            is_admin = True
        elif message.from_user:
            try:
                chat_member = await message.chat.get_member(message.from_user.id)
                if chat_member.status in ["administrator", "creator"]:
                    is_admin = True
            except Exception:
                pass
        
        # Agar admin bo'lmasa, faoliyatni tekshirish yoki xabar berish
        if not is_admin:
            msg = await message.answer("ℹ️ <i>Guruhda viktorinani faqat guruh adminlari boshlashi mumkin.</i>", parse_mode="HTML")
            asyncio.create_task(delete_later(msg, 6))
            return

    if chat_id in active_quizzes and active_quizzes[chat_id].get("is_active"):
        msg = await message.answer("⏳ <b>Hozir guruhda faol viktorina davom etmoqda!</b>\nIltimos, avvalgi viktorina yakunlanishini kuting yoki <code>/toxta</code> buyrug'ini bering.", parse_mode="HTML")
        asyncio.create_task(delete_later(msg, 6))
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Aralash (10 ta / 20s)", callback_data="startgq_mix_10_20"),
            InlineKeyboardButton(text="🎲 Aralash (20 ta / 20s)", callback_data="startgq_mix_20_20")
        ],
        [
            InlineKeyboardButton(text="🎬 3D Video-Viktorina (10 ta)", callback_data="startgq_video_10_25"),
            InlineKeyboardButton(text="⚡️ Blits (10 ta / 15s)", callback_data="startgq_blitz_10_15")
        ],
        [
            InlineKeyboardButton(text="🚦 Yo'l Belgilari (15 ta / 20s)", callback_data="startgq_signs_15_20"),
            InlineKeyboardButton(text="🏆 Marafon (30 ta / 30s)", callback_data="startgq_mix_30_30")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="close_profile")
        ]
    ])

    text = (
        "👑 <b>AVTOMAKTAB PREMIUM VIKTORINA</b> 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚗 <b>Guruh a'zolari uchun YHQ bo'yicha intellektual jang!</b>\n"
        "To'g'ri va tezkor javob bergan ishtirokchilarga ballar taqsimlanadi.\n\n"
        "👇 <b>Quyidagi rejimlardan birini tanlang:</b>"
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ─── VIKTORINANI ISHGA TUSHIRISH CALLBACKI ─────────────────────────
@groups_router.callback_query(F.data.startswith("startgq_"))
async def start_group_quiz_callback(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    chat_type = callback.message.chat.type
    
    if chat_type in ["group", "supergroup"]:
        try:
            chat_member = await callback.message.chat.get_member(callback.from_user.id)
            if chat_member.status not in ["administrator", "creator"]:
                await callback.answer("❌ Faqat adminlar boshlay oladi!", show_alert=True)
                return
        except Exception:
            pass
            
    try:
        await callback.message.delete()
    except Exception:
        pass

    parts = callback.data.split("_")
    # Format: startgq_{mode}_{count}_{duration}
    if len(parts) != 4:
        return
        
    mode = parts[1]
    limit = int(parts[2])
    duration = int(parts[3])

    if chat_id in active_quizzes and active_quizzes[chat_id].get("is_active"):
        msg = await callback.message.answer("⏳ <b>Hozir guruhda viktorina ketmoqda.</b>", parse_mode="HTML")
        asyncio.create_task(delete_later(msg, 5))
        return

    # Savollarni tanlangan rejim bo'yicha olish
    async with async_session() as session:
        if mode == "video":
            result = await session.execute(
                select(Question).where(Question.media_urls != None, Question.option_b != None)
            )
            raw_questions = result.scalars().all()
        elif mode == "signs":
            result = await session.execute(
                select(Question).where(Question.category.like("%belgi%"), Question.option_b != None)
            )
            raw_questions = result.scalars().all()
            if len(raw_questions) < limit:
                result_all = await session.execute(select(Question).where(Question.option_b != None))
                raw_questions = result_all.scalars().all()
        else: # mix or blitz
            result = await session.execute(
                select(Question).where(Question.option_b != None)
            )
            raw_questions = result.scalars().all()

    if not raw_questions:
        await callback.message.answer("❌ Hozircha bazada savollar topilmadi.")
        return

    quiz_questions = random.sample(raw_questions, min(limit, len(raw_questions)))
    q_ids = [q.id for q in quiz_questions]

    mode_titles = {
        "mix": "🎲 Aralash YHQ Viktorinasi",
        "video": "🎬 3D Video-Viktorina",
        "blitz": "⚡️ Tezkor Ekspress Blits",
        "signs": "🚦 Yo'l Belgilari Viktorinasi"
    }
    mode_title = mode_titles.get(mode, "🏆 YHQ Viktorinasi")

    active_quizzes[chat_id] = {
        "is_active": True,
        "poll_ids": {},
        "participants": {},
        "current_poll_start": 0.0,
        "total_questions": len(quiz_questions),
        "chat_title": callback.message.chat.title or "Guruh",
        "mode": mode
    }

    await save_group_quiz_to_db(chat_id, callback.message.chat.title or "", q_ids, 0, len(quiz_questions), {}, {})

    intro_text = (
        f"👑 <b>{mode_title.upper()}</b> 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 <b>Diqqat, ishtirokchilar!</b>\n"
        f"📚 <b>Savollar soni:</b> {len(quiz_questions)} ta\n"
        f"⏱ <b>Har bir savolga vaqt:</b> {duration} soniya\n"
        f"🏆 <b>Mukofot:</b> Har bir to'g'ri javob uchun <b>+5 ball</b>!\n\n"
        "💡 <i>Variantni tez va to'g'ri bosib, peshqadam bo'ling!</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    msg = await callback.message.answer(intro_text + "⏳ <b>Tayyorgarlik ko'ring...</b>", parse_mode="HTML")

    countdowns = [
        "🔴 <b>3️⃣ - Dvigatellarni o't oldiring!</b>", 
        "🟡 <b>2️⃣ - Xavfsizlik kamarini taqing!</b>", 
        "🟢 <b>1️⃣ - Gazni bosing!</b>", 
        "🚀 <b>BOSHLADIK! OQ YO'L!</b> 🏁"
    ]
    for count in countdowns:
        await asyncio.sleep(1)
        try:
            await msg.edit_text(intro_text + f"🎯 <b>{count}</b>", parse_mode="HTML")
        except Exception:
            pass

    # Savollarni ketma-ket chiqarish
    for i, q in enumerate(quiz_questions):
        if not active_quizzes.get(chat_id, {}).get("is_active"):
            break

        # 1. Variantlarni tartib bilan yig'ish va to'g'ri javob indeksini aniqlash
        raw_options = [
            ("A", q.option_a),
            ("B", q.option_b),
            ("C", q.option_c),
            ("D", q.option_d)
        ]
        
        options = []
        correct_idx = 0
        corr_letter = (q.correct_option or "A").strip().upper()

        for letter, opt_text in raw_options:
            if opt_text and str(opt_text).strip():
                clean_opt = str(opt_text).strip()[:95]
                if letter == corr_letter:
                    correct_idx = len(options)
                options.append(clean_opt)

        if len(options) < 2:
            options = [q.option_a or "To'g'ri", q.option_b or "Noto'g'ri"]
            correct_idx = 0 if corr_letter == "A" else 1

        # Savol matni (Telegram poll uchun max 295 belgi)
        poll_question = f"[{i+1}/{len(quiz_questions)}] {q.text}".strip()
        if len(poll_question) > 295:
            poll_question = poll_question[:292] + "..."

        # 2. Rasm yoki Video mavjudligini tekshirish va yuborish
        media_sent = False
        
        # Agar savolda asosiy video yoki video-animatsiya bo'lsa
        if q.media_urls:
            try:
                m_dict = json.loads(q.media_urls) if isinstance(q.media_urls, str) else q.media_urls
                if isinstance(m_dict, dict):
                    v_rel = m_dict.get("main") or list(m_dict.values())[0] if m_dict else None
                    if v_rel:
                        v_full = os.path.join(BASE_DIR, str(v_rel).replace('\\', '/'))
                        if os.path.exists(v_full):
                            v_file = FSInputFile(v_full)
                            await callback.message.bot.send_video(
                                chat_id=chat_id,
                                video=v_file,
                                caption=f"🎬 <b>[{i+1}/{len(quiz_questions)}] - savol videosi</b>",
                                parse_mode="HTML"
                            )
                            media_sent = True
                            await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Group video send error: {e}")

        # Agar video bo'lmasa, rasmni tekshirish
        if not media_sent and q.image_url:
            try:
                photo_file = None
                if not str(q.image_url).startswith("http"):
                    cand1 = os.path.join(BASE_DIR, "webapp", str(q.image_url).replace('\\', '/'))
                    cand2 = os.path.join(BASE_DIR, str(q.image_url).replace('\\', '/'))
                    if os.path.exists(cand1):
                        photo_file = FSInputFile(cand1)
                    elif os.path.exists(cand2):
                        photo_file = FSInputFile(cand2)
                else:
                    photo_file = q.image_url

                if photo_file:
                    await callback.message.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_file,
                        caption=f"📸 <b>[{i+1}/{len(quiz_questions)}] - savol rasmi</b>",
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Group photo send error: {e}")

        # 3. Telegram Quiz (Poll) yuborish
        raw_exp = re.sub(r'<[^>]+>', '', (q.explanation or "").strip())
        explanation_text = raw_exp[:190] if raw_exp else None

        try:
            poll_msg = await callback.message.bot.send_poll(
                chat_id=chat_id,
                question=poll_question,
                options=options,
                correct_option_id=correct_idx,
                type="quiz",
                is_anonymous=False,
                explanation=explanation_text,
                open_period=max(10, min(60, int(duration)))
            )

            poll_id = poll_msg.poll.id
            active_quizzes[chat_id]["poll_ids"][poll_id] = correct_idx
            active_quizzes[chat_id]["current_poll_start"] = time.time()

        except Exception as e:
            print(f"Poll send error in group {chat_id}: {e}")
            await callback.message.answer(f"⚠️ [{i+1}-savol yuklanmadi, keyingisiga o'tilmoqda...]")

        # Savol tugashini kutish
        await asyncio.sleep(duration + 2)

    # Viktorinani yakunlash
    if chat_id in active_quizzes:
        await finish_group_quiz(chat_id, callback.message.chat.title or "Guruh", callback.message.bot)


# ─── VIKTORINANI YAKUNLASH VA G'OLIBLARNI TAQDIRLASH ───────────────
async def finish_group_quiz(chat_id: int, chat_title: str, bot):
    quiz_data = active_quizzes.get(chat_id)
    if not quiz_data or not quiz_data.get("is_active"):
        return
        
    quiz_data["is_active"] = False
    
    participants = quiz_data.get("participants", {})
    total_questions = quiz_data.get("total_questions", 10)
    mode = quiz_data.get("mode", "mix")
    
    if not participants:
        await bot.send_message(
            chat_id,
            "🏁 <b>VIKTORINA YAKUNLANDI!</b>\n\n"
            "Afsuski, hech kim javob berishga ulgurmadi. Keyingi safar faolroq bo'ling! 🚗💨",
            parse_mode="HTML"
        )
        await delete_group_quiz_from_db(chat_id)
        if chat_id in active_quizzes:
            del active_quizzes[chat_id]
        return

    # Ishtirokchilarni saralash (eng ko'p to'g'ri javob → eng kam vaqt sarflagan)
    sorted_users = sorted(
        [(uid, data) for uid, data in participants.items()],
        key=lambda x: (x[1]["score"], -x[1]["time_taken"]),
        reverse=True
    )

    # Ballarni DB ga saqlash
    async with async_session() as session:
        for uid, p_data in sorted_users:
            if p_data["score"] > 0:
                res_u = await session.execute(select(User).where(User.telegram_id == uid))
                db_u = res_u.scalars().first()
                if db_u:
                    db_u.points = (db_u.points or 0) + (p_data["score"] * 5)
        await session.commit()

    text = (
        "🎆 💥 🎆 <b>MUSHAKBOZLIK & G'OLIBLAR TANTANASI!</b> 🎆 💥 🎆\n"
        "🥳 <b>PREMIUM VIKTORINA MUVAFFAQIYATLI YAKUNLANDI!</b> 🥳\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Jami savollar:</b> {total_questions} ta\n"
        f"👥 <b>Ishtirokchilar soni:</b> {len(sorted_users)} nafar\n\n"
        "🏆 <b>LIDERLAR DOSKASI (TOP-10):</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    medals = ["🥇 <b>Oltin Kubok</b> 🎆", "🥈 <b>Kumush Kubok</b> ✨", "🥉 <b>Bronza Kubok</b> 🌟"]
    
    for i, (user_id, p_data) in enumerate(sorted_users[:10]):
        medal = medals[i] if i < 3 else f"🎖 <b>{i+1}-o'rin</b>"
        score = p_data["score"]
        wrong = p_data.get("wrong", 0)
        total_time = round(p_data["time_taken"], 1)
        name = p_data["name"]
        pct = round(score / total_questions * 100) if total_questions > 0 else 0
        points_earned = score * 5

        status = "🌟 A'lo" if pct >= 80 else ("⚡ Yaxshi" if pct >= 50 else "📚 Qoniqarli")

        text += (
            f"{medal} — <a href=\"tg://user?id={user_id}\">{name}</a>\n"
            f"   ├ ✅ <b>To'g'ri:</b> {score}/{total_questions} ({pct}%)\n"
            f"   ├ ⚡️ <b>Olingan ball:</b> +{points_earned} ball\n"
            f"   └ ⏱ <b>Vaqt:</b> {total_time}s | {status}\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎉 <i>Barcha qatnashchilarga minnatdorchilik bildiramiz!</i>\n"
        "🚀 <i>Yana viktorina o'tkazish uchun <code>/test</code> buyrug'ini yuboring!</i>"
    )

    await bot.send_message(chat_id, text, parse_mode="HTML")
    await delete_group_quiz_from_db(chat_id)
    if chat_id in active_quizzes:
        del active_quizzes[chat_id]


# ─── POLL JAVOBLARINI TUTIB QOLISH ────────────────────────────────
@groups_router.poll_answer()
async def on_group_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    name = poll_answer.user.full_name or "Haydovchi"
    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else None
    
    for chat_id, q_data in active_quizzes.items():
        if q_data.get("is_active") and poll_answer.poll_id in q_data.get("poll_ids", {}):
            correct_option = q_data["poll_ids"][poll_answer.poll_id]
            time_taken = time.time() - q_data.get("current_poll_start", time.time())
            
            if user_id not in q_data["participants"]:
                q_data["participants"][user_id] = {
                    "name": name,
                    "score": 0,
                    "wrong": 0,
                    "answered": 0,
                    "time_taken": 0.0
                }
                
            q_data["participants"][user_id]["time_taken"] += time_taken
            q_data["participants"][user_id]["answered"] += 1
            
            if selected_option == correct_option:
                q_data["participants"][user_id]["score"] += 1
            else:
                q_data["participants"][user_id]["wrong"] += 1
                
            break


# ─── VIKTORINANI TO'XTATISH BUYRUG'I ──────────────────────────────
@groups_router.message(Command(commands=["toxta", "stop"]), F.chat.type.in_(["group", "supergroup"]))
async def stop_group_test(message: types.Message):
    chat_id = message.chat.id
    
    # Anonim admin yoki guruh adminini tekshirish
    is_admin = False
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        is_admin = True
    elif message.from_user:
        try:
            chat_member = await message.chat.get_member(message.from_user.id)
            is_admin = chat_member.status in ["administrator", "creator"]
        except Exception:
            is_admin = False
            
    if not is_admin:
        msg = await message.answer("❌ Viktorinani faqat guruh adminlari to'xtata oladi.")
        asyncio.create_task(delete_later(msg, 5))
        return
        
    if chat_id in active_quizzes and active_quizzes[chat_id].get("is_active"):
        active_quizzes[chat_id]["is_active"] = False
        await message.answer("🛑 <b>Viktorina admin tomonidan to'xtatildi!</b>", parse_mode="HTML")
        await delete_group_quiz_from_db(chat_id)
        del active_quizzes[chat_id]
    else:
        msg = await message.answer("ℹ️ Guruhda ayni paytda faol viktorina yo'q.")
        asyncio.create_task(delete_later(msg, 5))


# ─── GURUH STATISTIKASI VA LIDERLARI ───────────────────────────────
@groups_router.message(Command(commands=["statistika", "stats", "liderlar"]), F.chat.type.in_(["group", "supergroup"]))
async def group_stats_handler(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.points.desc()).limit(10)
        )
        top_users = result.scalars().all()
        
    if not top_users:
        await message.answer("🏆 Guruhda hozircha statistikalar va ballar mavjud emas.")
        return

    now = datetime.now()
    month_name = now.strftime("%B %Y")

    text = (
        f"🎆 💥 <b>GURUH REYTINGI VA LIDERLARI</b> 💥 🎆\n"
        f"📅 <b>Davr: {month_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🥇 <b>OYNING ENG KUCHLI BILIMDONI:</b>\n"
        f"👑 <b>{top_users[0].full_name or 'Noma\'lum'}</b> — <code>{top_users[0].points}</code> ball 🔥\n\n"
        f"🏆 <b>TOP-10 ENG FAOL HAYDOVCHILAR:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, u in enumerate(top_users):
        m = medals[i] if i < len(medals) else f"{i+1}."
        name = u.full_name or "Noma'lum"
        text += f"{m} <a href=\"tg://user?id={u.telegram_id}\">{name}</a> — <b>{u.points} ball</b>\n"

    text += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 <i>Guruhda <code>/test</code> buyrug'ini yuborib viktorinalarda qatnashing va ballar to'plang!</i> 💥 🎆"
    )
    await message.answer(text, parse_mode="HTML")


# ─── GURUH START VA BOT BUYRUQLARI ─────────────────────────────────
@groups_router.message(Command("start"), F.chat.type.in_(["group", "supergroup"]))
async def group_start_handler(message: types.Message):
    bot_info = await message.bot.get_me()
    text = (
        "👑 <b>AVTOVATANPARVAR GURUH BOTI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 Ushbu guruhda bot quyidagi vazifalarni bajaradi:\n\n"
        "🎯 <b>YHQ Viktorinalari:</b> 1242 ta rasmiy savol va 3D video-testlar.\n"
        "🛡 <b>Obuna nazorati:</b> Faqat kanal a'zolari yozishini ta'minlaydi.\n\n"
        "📌 <b>Guruh buyruqlari:</b>\n"
        "• <code>/test</code> yoki <code>/viktorina</code> — Viktorina boshlash\n"
        "• <code>/toxta</code> — Viktorinani to'xtatish\n"
        "• <code>/statistika</code> — TOP 10 liderlar reytingi\n"
        "• <code>/bot</code> — Obuna sozlamalari (adminlar uchun)\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Shaxsiy imtihon topshirish uchun botga o'ting!</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Botda Imtihon Topshirish", url=f"https://t.me/{bot_info.username}?start=group")]
    ])
    try:
        photo = FSInputFile("welcome.png")
        await message.answer_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@groups_router.message(Command("bot"), F.chat.type.in_(["group", "supergroup"]))
async def group_cmd_bot(message: types.Message):
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()

    is_bot_admin = (user_id in ADMIN_IDS)
    try:
        member = await message.bot.get_chat_member(message.chat.id, user_id)
        is_group_admin = member.status in ["administrator", "creator"]
    except Exception:
        is_group_admin = False
        
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        is_group_admin = True

    if not (is_bot_admin or is_group_admin):
        try:
            await message.delete()
        except Exception:
            pass
        warn = await message.answer("⛔ Bu buyruq faqat guruh adminlari uchun!")
        asyncio.create_task(delete_later(warn, 10))
        return

    args = message.text.split()
    async with async_session() as session:
        group_result = await session.execute(select(BotGroup).where(BotGroup.chat_id == message.chat.id))
        group = group_result.scalars().first()
        if not group:
            group = BotGroup(chat_id=message.chat.id, title=message.chat.title)
            session.add(group)
            await session.commit()
            
        if len(args) > 1 and args[1].lower() in ["on", "off"]:
            if args[1].lower() == "off":
                group.subscription_guard = False
                await session.commit()
                await message.answer("🛑 <b>Obuna nazorati o'chirildi.</b>\nEndi barcha a'zolar yoza oladi.", parse_mode="HTML")
            else:
                group.subscription_guard = True
                await session.commit()
                await message.answer(f"✅ <b>Obuna nazorati yoqildi!</b>\n\nEndi faqat @{bot_info.username} botimizga obuna bo'lganlar guruhda yoza oladi.", parse_mode="HTML")
            return

        guard_on = group.subscription_guard

    status_icon = "✅ Yoqilgan" if guard_on else "❌ O'chirilgan"
    action_text = "O'chirish" if guard_on else "Yoqish"

    text = (
        f"🤖 <b>BOT VA GURUH SOZLAMALARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Guruh: <b>{message.chat.title}</b>\n"
        f"🛡 Obuna nazorati: <b>{status_icon}</b>\n\n"
        f"Quyidagi tugmalar orqali sozlang, yoki:\n"
        f"<code>/bot on</code> - Yoqish\n"
        f"<code>/bot off</code> - O'chirish"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🛡 Obuna nazoratini {action_text}",
            callback_data=f"toggle_guard_{message.chat.id}"
        )],
        [InlineKeyboardButton(text="📊 Guruh a'zolari soni", callback_data=f"group_stats_{message.chat.id}")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="close_profile")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@groups_router.callback_query(F.data.startswith("toggle_guard_"))
async def toggle_guard_callback(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    is_bot_admin = (user_id in ADMIN_IDS)
    try:
        member = await callback.bot.get_chat_member(chat_id, user_id)
        is_group_admin = member.status in ["administrator", "creator"]
    except Exception:
        is_group_admin = False

    if not (is_bot_admin or is_group_admin):
        return await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)

    async with async_session() as session:
        group_result = await session.execute(select(BotGroup).where(BotGroup.chat_id == chat_id))
        group = group_result.scalars().first()
        if not group:
            return await callback.answer("Guruh bazada topilmadi", show_alert=True)
            
        group.subscription_guard = not group.subscription_guard
        new_state = group.subscription_guard
        await session.commit()
        
    status = "✅ Yoqildi" if new_state else "❌ O'chirildi"
    await callback.answer(f"Obuna nazorati: {status}", show_alert=True)
    
    guard_on = new_state
    status_icon = "✅ Yoqilgan" if guard_on else "❌ O'chirilgan"
    action_text = "O'chirish" if guard_on else "Yoqish"
    
    title = callback.message.chat.title if callback.message.chat else "Guruh"
    text = (
        f"🤖 <b>BOT VA GURUH SOZLAMALARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Guruh: <b>{title}</b>\n"
        f"🛡 Obuna nazorati: <b>{status_icon}</b>\n\n"
        f"Quyidagi tugmalar orqali sozlang, yoki:\n"
        f"<code>/bot on</code> - Yoqish\n"
        f"<code>/bot off</code> - O'chirish"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🛡 Obuna nazoratini {action_text}",
            callback_data=f"toggle_guard_{chat_id}"
        )],
        [InlineKeyboardButton(text="📊 Guruh a'zolari soni", callback_data=f"group_stats_{chat_id}")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="close_profile")]
    ])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@groups_router.callback_query(F.data.startswith("group_stats_"))
async def group_stats_callback(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    try:
        count = (await callback.bot.get_chat_member_count(chat_id))
        await callback.answer(f"👥 A'zolar soni: {count} ta", show_alert=True)
    except Exception:
        await callback.answer("❌ Ma'lumot olishda xatolik.", show_alert=True)
        
@groups_router.callback_query(F.data == "close_profile")
async def close_profile_callback(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

# Guruhda Anti-spam (Ssilkalarni filtrlash)
@groups_router.message(F.chat.type.in_(["group", "supergroup"]))
async def antispam_filter(message: types.Message):
    if not message.text:
        return
    
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        return
        
    if not message.from_user:
        return
    
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[a-zA-Z0-9_]+')
    if url_pattern.search(message.text):
        try:
            chat_member = await message.chat.get_member(message.from_user.id)
            if chat_member.status in ["administrator", "creator"]:
                return
        except Exception:
            return
            
        await message.delete()
        warning = await message.answer(f"🚫 {message.from_user.first_name}, guruhda reklama va ssilkalar tashlash taqiqlangan!")
        asyncio.create_task(delete_later(warning, 5))
