import asyncio
import os
import sys
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Set up logging to show all bot activity in the terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, MenuButtonWebApp, WebAppInfo
from handlers import router
from config import BOT_TOKEN

WEBAPP_URL = "https://avtomaktab-webapp.vercel.app/"

LOCK_FILE = os.path.join(os.path.dirname(__file__), "bot.lock")

lock_file_handle = None

def acquire_lock():
    global lock_file_handle
    try:
        lock_file_handle = open(LOCK_FILE, "w")
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
    except Exception:
        print("Bot allaqachon ishlayapti yoki lock fayl band. Chiqilmoqda.")
        sys.exit(1)

def release_lock():
    global lock_file_handle
    if lock_file_handle:
        try:
            if os.name == 'nt':
                import msvcrt
                lock_file_handle.seek(0)
                msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
            lock_file_handle.close()
        except Exception:
            pass
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

import atexit
atexit.register(release_lock)


async def set_default_commands(bot: Bot):
    private_commands = [
        BotCommand(command="start",  description="Botni ishga tushirish"),
        BotCommand(command="test",   description="Yangi test boshlash"),
        BotCommand(command="stats",  description="Natijalar statistikasi"),
        BotCommand(command="help",   description="Yordam"),
    ]
    group_commands = [
        BotCommand(command="test",   description="Guruh viktorinasini boshlash"),
        BotCommand(command="stats",  description="Natijalar statistikasi"),
        BotCommand(command="help",   description="Yordam"),
    ]
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands,   scope=BotCommandScopeAllGroupChats())


async def set_bot_profile_and_description(bot: Bot):
    """Botning Description (What can this bot do?) va Short Description (Bio) larini o'rnatish"""
    # 1. To'liq tavsif (What can this bot do? ekrani)
    desc_uz = (
        "🏆 AVTOVATANPARVAR — O'zbekistonning 1-raqamli YHQ va GAI Imtihon platformasi! 🚘✨\n\n"
        "Bot nima qila oladi? 👇\n"
        "🏎 1 242 ta Rasmiy YHQ Imtihon Savollari\n"
        "🎬 207 ta 3D Harakatlanish Videolari\n"
        "🎓 GAI Davlat Imtihoni Simulyatori (20/20) & Oltin Sertifikat\n"
        "🤖 AI Ustoz — Aqlli Avto-Instruktor (Tushuntirish va sirlar)\n"
        "🥊 1vs1 Real-Time Duel Janglari\n"
        "🚦 130 ta Yo'l Belgilari & Jarimalar Jadvali\n"
        "🎥 133 ta Rasmiy Video Darsliklar\n"
        "📱 Telegram Mini App (WebApp)\n\n"
        "🎁 /start bosing va 5 kunlik VIP Premium obunaga ega bo'ling! 🚀"
    )
    
    desc_ru = (
        "🏆 АВТОВАТАНПАРВАР — №1 Платформа ПДД и экзаменов ГАИ в Узбекистане! 🚘✨\n\n"
        "Возможности бота: 👇\n"
        "🏎 1 242 официальных вопроса ПДД\n"
        "🎬 207 3D видео-анимаций перекрестков\n"
        "🎓 Симулятор госэкзамена ГАИ и Золотой Сертификат\n"
        "🤖 ИИ Авто-Инструктор (разбор правил)\n"
        "🥊 Онлайн дуэли 1 на 1\n"
        "🚦 130 дорожных знаков и штрафы\n"
        "🎥 133 видеоурока\n"
        "📱 Telegram Mini App\n\n"
        "🎁 Нажмите /start и получите 5 дней VIP бесплатно! 🚀"
    )

    # 2. Qisqa tavsif (Bio / About) — max 120 belgi
    short_uz = "🚘 1242 ta YHQ testi, 3D videolar, GAI imtihoni simulyatori, AI Ustoz va 1vs1 Duel! 🏆 Bepul sinab ko'ring!"
    short_ru = "🚘 1242 вопроса ПДД, 3D видео, симулятор ГАИ, ИИ-инструктор и дуэли 1 на 1! 🏆 Попробуйте бесплатно!"

    try:
        await bot.set_my_description(description=desc_uz)
        await bot.set_my_description(description=desc_uz, language_code="uz")
        await bot.set_my_description(description=desc_ru, language_code="ru")
        
        await bot.set_my_short_description(short_description=short_uz)
        await bot.set_my_short_description(short_description=short_uz, language_code="uz")
        await bot.set_my_short_description(short_description=short_ru, language_code="ru")
        print("Bot Description va Bio muvaffaqiyatli yangilandi!")
    except Exception as e:
        print(f"Bot Description/Bio o'rnatishda xatolik: {e}")


async def set_menu_button(bot: Bot):
    """Botning chap pastki burchagidagi Menu tugmasini Mini App ga ulaymiz"""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📱 Mini Ilova",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        print("Menu Button (WebApp) ulandi!")
    except Exception as e:
        print(f"Menu Button o'rnatishda xatolik: {e}")


async def resume_interrupted_quizzes(bot: Bot):
    """Bot qayta yonganda tugamagan viktorinalarni topib, natijalarini guruhga yuboradi."""
    import json
    from database import async_session, GroupQuizSession
    from sqlalchemy import select

    try:
        async with async_session() as session:
            result = await session.execute(
                select(GroupQuizSession).where(GroupQuizSession.is_active == True)
            )
            interrupted = result.scalars().all()

        for gs in interrupted:
            try:
                participants = json.loads(gs.participants or '{}')
                total = gs.total_questions
                chat_id = gs.chat_id
                chat_title = gs.chat_title or "Guruh"

                if not participants:
                    # Hech kim ishtirok etmagan — shunchaki xabar yuboramiz
                    await bot.send_message(
                        chat_id,
                        "⚠️ <b>Bot qayta ishga tushdi.</b>\n\n"
                        "Oldingi viktorina to'xtatib qo'yildi. "
                        "Yangi viktorina boshlash uchun /test yuboring.",
                        parse_mode="HTML"
                    )
                else:
                    # Natijalarni ko'rsatamiz
                    sorted_users = sorted(
                        participants.items(),
                        key=lambda x: (x[1].get("score", 0), -x[1].get("time_taken", 0)),
                        reverse=True
                    )
                    answered = gs.current_idx

                    text = (
                        f"⚠️ <b>Bot qayta ishga tushdi — viktorina to'xtatildi!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📊 <b>O'tilgan savollar:</b> {answered}/{total} ta\n"
                        f"👥 <b>Ishtirokchilar:</b> {len(sorted_users)} ta\n\n"
                        "🏆 <b>ORALIQ NATIJALAR:</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    )
                    medals = ["🥇", "🥈", "🥉"]
                    for i, (uid, udata) in enumerate(sorted_users[:10]):
                        medal = medals[i] if i < 3 else f"🎖 {i+1}."
                        name = udata.get("name", "Noma'lum")
                        score = udata.get("score", 0)
                        pct = round(score / max(answered, 1) * 100)
                        text += f"{medal} <a href=\"tg://user?id={uid}\">{name}</a> — {score} ball ({pct}%)\n"

                    text += (
                        "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "🔄 Yangi viktorina boshlash uchun /test yuboring."
                    )
                    await bot.send_message(chat_id, text, parse_mode="HTML")

                # DB dan o'chiramiz
                async with async_session() as session2:
                    r2 = await session2.execute(
                        select(GroupQuizSession).where(GroupQuizSession.chat_id == chat_id)
                    )
                    gs2 = r2.scalars().first()
                    if gs2:
                        await session2.delete(gs2)
                        await session2.commit()

            except Exception as e:
                print(f"Interrupted quiz recovery error (chat {gs.chat_id}): {e}")

    except Exception as e:
        print(f"resume_interrupted_quizzes error: {e}")


async def main():
    acquire_lock()
    
    # Initialize DB
    from database import init_db
    await init_db()

    # FSM Storage (Persistent JSON Storage - qayta ishga tushganda davom etishi uchun)
    from utils.json_storage import JSONStorage
    storage = JSONStorage(file_path="fsm_data.json")

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=storage)
    dp.include_router(router)

    await set_default_commands(bot)
    await set_bot_profile_and_description(bot)
    await set_menu_button(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    # Start APScheduler
    from scheduler import setup_scheduler
    app_scheduler = await setup_scheduler(bot)

    # PvP Duel API serverni ishga tushirish (Mini App uchun)
    from api_server import start_api_server
    from database import async_session, Question
    from sqlalchemy import select as sa_select
    async with async_session() as _sess:
        _res = await _sess.execute(
            sa_select(Question).where(Question.option_b != None, Question.option_b != "")
        )
        _questions = [
            {
                "id": q.id, "text": q.text, "image_url": q.image_url or "",
                "option_a": q.option_a, "option_b": q.option_b or "",
                "option_c": q.option_c or "", "option_d": q.option_d or "",
                "correct_option": q.correct_option,
            }
            for q in _res.scalars().all()
        ]
    api_runner = await start_api_server(_questions, port=3001)

    print("Bot ishga tushdi...")
    # Bot qayta yonganda tugamagan guruh viktorinalarini tekshiramiz
    await resume_interrupted_quizzes(bot)
    try:
        await dp.start_polling(bot, skip_updates=True)
    except asyncio.CancelledError:
        print("Polling to'xtatildi.")
    finally:
        await api_runner.cleanup()
        await bot.session.close()
        release_lock()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Foydalanuvchi tomonidan to'xtatildi.")
    finally:
        release_lock()
