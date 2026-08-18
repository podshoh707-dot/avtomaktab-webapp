import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy import select
import random
from database import async_session, Question, BotGroup, Setting, User
from datetime import datetime
import uuid

async def broadcast_auto_test(bot: Bot):
    async with async_session() as session:
        # Check if auto_test is enabled
        result_enabled = await session.execute(select(Setting).where(Setting.key == "auto_test_enabled"))
        enabled_setting = result_enabled.scalars().first()
        if not enabled_setting or enabled_setting.value != "1":
            return
            
        # Get all active groups
        result_groups = await session.execute(select(BotGroup).where(BotGroup.is_active == True))
        active_groups = result_groups.scalars().all()
        
        # Get required channel if any
        result_req = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        req_setting = result_req.scalars().first()
        req_channel = req_setting.value if req_setting and req_setting.value and req_setting.value != "off" else None
        
        chat_ids = [str(g.chat_id) for g in active_groups]
        if req_channel:
            chat_ids.append(req_channel)

        # Foydalanuvchilarning shaxsiy chatlariga yuborish (yoqilgan bo'lsa)
        result_users_setting = await session.execute(select(Setting).where(Setting.key == "auto_test_send_users"))
        users_setting = result_users_setting.scalars().first()
        send_to_users = users_setting and users_setting.value == "1"

        user_ids = []
        if send_to_users:
            result_users = await session.execute(select(User.telegram_id).where(User.phone != None))
            user_ids = [row[0] for row in result_users.all()]

        if not chat_ids and not user_ids:
            return
            
        # Get a random question
        result_q = await session.execute(select(Question))
        questions = result_q.scalars().all()
        if not questions:
            return
            
        q = random.choice(questions)
        
        # Broadcast to chats
        from aiogram.types import FSInputFile
        import os
        from config import BASE_DIR
        
        # Savol variantlari va to'g'ri javob indeksi
        letters = ['A', 'B', 'C', 'D']
        try:
            correct_idx = letters.index(q.correct_option)
        except ValueError:
            correct_idx = 0
            
        poll_options = [q.option_a[:100]]
        if q.option_b: poll_options.append(q.option_b[:100])
        if q.option_c: poll_options.append(q.option_c[:100])
        if q.option_d: poll_options.append(q.option_d[:100])
        
        # Telegram poll explanation max 200 belgi
        raw_exp = (q.explanation or "").strip()
        poll_explanation = raw_exp[:200] if raw_exp else None
        
        caption = f"🏁 <b>DIQQAT, TEST SAVOLI!</b>\n\n❓ {q.text}"
        
        media_obj = None
        if q.image_url:
            if not str(q.image_url).startswith("http"):
                local_path = os.path.join(BASE_DIR, str(q.image_url).replace('\\', '/'))
                if os.path.exists(local_path):
                    media_obj = FSInputFile(local_path)
            else:
                media_obj = q.image_url

        for chat_id in set(chat_ids):
            # 1. Rasm yuborish (agar bo'lsa)
            if media_obj:
                try:
                    await bot.send_photo(chat_id, media_obj, caption=caption, parse_mode="HTML")
                except Exception as e:
                    print(f"[AutoTest] Rasm yuborishda xato ({chat_id}): {e}")
            
            # 2. Poll (quiz) yuborish
            chat_id_str = str(chat_id)
            is_anonymous = chat_id_str.startswith("@") or chat_id_str.startswith("-")
            
            try:
                poll_q = q.text[:300] if not media_obj else "Qaysi javob to'g'ri?"
                await bot.send_poll(
                    chat_id=chat_id,
                    question=poll_q,
                    options=poll_options,
                    correct_option_id=correct_idx,
                    type="quiz",
                    is_anonymous=is_anonymous,
                    explanation=poll_explanation
                )
            except Exception as e:
                print(f"[AutoTest] Poll yuborishda xato ({chat_id}): {e}")

        # Foydalanuvchilarning lichkasiga yuborish
        if user_ids:
            for uid in user_ids:
                if media_obj:
                    try:
                        await bot.send_photo(uid, media_obj, caption=caption, parse_mode="HTML")
                    except Exception:
                        pass
                
                try:
                    poll_q = q.text[:300] if not media_obj else "Qaysi javob to'g'ri?"
                    await bot.send_poll(
                        chat_id=uid,
                        question=poll_q,
                        options=poll_options,
                        correct_option_id=correct_idx,
                        type="quiz",
                        is_anonymous=False,
                        explanation=poll_explanation
                    )
                except Exception:
                    pass
                await asyncio.sleep(0.05)  # Flood limit


async def broadcast_auto_ad(bot: Bot):
    async with async_session() as session:
        # Check if auto_ad is enabled
        res_enabled = await session.execute(select(Setting).where(Setting.key == "auto_ad_enabled"))
        setting_enabled = res_enabled.scalars().first()
        if not setting_enabled or setting_enabled.value != "1":
            return

        # Check msg chat & msg id
        res_from_chat = await session.execute(select(Setting).where(Setting.key == "auto_ad_from_chat_id"))
        from_chat_setting = res_from_chat.scalars().first()
        res_msg_id = await session.execute(select(Setting).where(Setting.key == "auto_ad_message_id"))
        msg_id_setting = res_msg_id.scalars().first()

        if not from_chat_setting or not msg_id_setting:
            return

        try:
            from_chat_id = int(from_chat_setting.value)
            message_id = int(msg_id_setting.value)
        except Exception:
            return

        # Target groups check
        res_groups_flag = await session.execute(select(Setting).where(Setting.key == "auto_ad_groups"))
        g_setting = res_groups_flag.scalars().first()
        send_groups = (not g_setting) or (g_setting.value == "1")

        # Target users check
        res_users_flag = await session.execute(select(Setting).where(Setting.key == "auto_ad_users"))
        u_setting = res_users_flag.scalars().first()
        send_users = u_setting and (u_setting.value == "1")

        target_chat_ids = []

        if send_groups:
            res_groups = await session.execute(select(BotGroup).where(BotGroup.is_active == True))
            active_groups = res_groups.scalars().all()
            for g in active_groups:
                target_chat_ids.append(g.chat_id)

        if send_users:
            res_users = await session.execute(select(User.telegram_id))
            all_users = res_users.scalars().all()
            for u_id in all_users:
                target_chat_ids.append(u_id)

        if not target_chat_ids:
            return

        sent = 0
        failed = 0
        for cid in set(target_chat_ids):
            try:
                await bot.copy_to(
                    chat_id=cid,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    allow_sending_without_reply=True
                )
                sent += 1
            except Exception as e:
                failed += 1
                err_str = str(e).lower()
                if "forbidden" not in err_str and "blocked" not in err_str and "deactivated" not in err_str:
                    print(f"[AutoAd] Xatolik ({cid}): {e}")
            await asyncio.sleep(0.05)

        print(f"[AutoAd] Avto-reklama tarqatildi: {sent} ta muvaffaqiyatli, {failed} ta xatolik")


async def check_expired_premiums(bot: Bot):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_premium == True))
        users = result.scalars().all()
        now = datetime.utcnow()
        
        for user in users:
            if user.premium_expires_at and user.premium_expires_at < now:
                user.is_premium = False
                await session.commit()
                try:
                    await bot.send_message(
                        user.telegram_id,
                        "⚠️ **Diqqat!** Bepul 5 kunlik Premium (VIP) muddati o'z nihoyasiga yetdi. \n\nVIP testlarni va Imtihon simulyatorini davom ettirish uchun asosiy menyudan **⭐ Premium** bo'limiga o'tib obuna xarid qiling!",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"Error sending expiration notice to {user.telegram_id}: {e}")

async def send_daily_smart_reminder(bot: Bot):
    """Foydalanuvchilarga kunlik xatolarni takrorlash eslatmasi (Spaced Repetition)"""
    from database import UserMistake
    async with async_session() as session:
        result_users = await session.execute(
            select(User.telegram_id, User.id).where(User.phone != None)
        )
        users = result_users.all()
        for tg_id, u_id in users:
            res_m = await session.execute(select(UserMistake).where(UserMistake.user_id == u_id))
            mistakes = res_m.scalars().all()
            if mistakes:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎯 Xatolarim Ustida Ishlash", callback_data="test_mistakes")]
                ])
                try:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=(
                            f"🧠 <b>KUNLIK AQLLI ESLATMA!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"Sizda <b>{len(mistakes)} ta</b> takrorlash kerak bo'lgan xato ishlangan savol mavjud.\n\n"
                            f"<i>Ebbinghaus unutish egri chizig'iga ko'ra, xatolarni 24 soat ichida takrorlash ularni umrbod xotiraga muhrlaydi!</i>\n\n"
                            f"👇 Quyidagi tugmani bosib xatolaringizni yeching:"
                        ),
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                await asyncio.sleep(0.05)


async def send_personalized_hourly_reminders(bot: Bot):
    """Foydalanuvchilarning o'zlari tanlagan soat bo'yicha shaxsiy dars va streak eslatmasi"""
    from datetime import datetime, timedelta
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # O'zbekiston vaqti (UTC+5)
    uz_now = datetime.utcnow() + timedelta(hours=5)
    current_hh = uz_now.strftime("%H")
    
    async with async_session() as session:
        result_users = await session.execute(
            select(User).where(User.phone != None, User.reminder_time != None, User.reminder_time != "off")
        )
        users = result_users.scalars().all()
        
    for user in users:
        rem_hh = user.reminder_time.split(":")[0] if ":" in user.reminder_time else "20"
        if rem_hh == current_hh:
            streak = user.streak_count or 0
            name = user.full_name or "Haydovchi"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 10 ta Test Yechish (Seriya 🔥)", callback_data="testcnt_10")],
                [InlineKeyboardButton(text="🎓 GAI Imtihoni", callback_data="testcnt_gai")]
            ])
            
            msg = (
                f"🚗 <b>Assalomu alaykum, {name}!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⏰ Siz belgilagan dars vaqti bo'ldi!\n"
                f"🔥 <b>Kunlik Seriyangiz:</b> {streak} kun\n\n"
                f"<i>Kunlik atigi 3 daqiqa vaqt ajratib 10 ta savol ishlang va seriyangizni davom ettiring!</i>"
            )
            try:
                await bot.send_message(user.telegram_id, msg, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            await asyncio.sleep(0.05)


_global_scheduler: AsyncIOScheduler = None

def get_scheduler() -> AsyncIOScheduler:
    global _global_scheduler
    return _global_scheduler

async def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _global_scheduler
    scheduler = AsyncIOScheduler()
    _global_scheduler = scheduler

    # Retrieve auto-test interval from Setting table (default 10 minutes)
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "auto_test_interval"))
        setting = result.scalars().first()
        interval = int(setting.value) if setting and setting.value and setting.value.isdigit() else 10

        result_ad = await session.execute(select(Setting).where(Setting.key == "auto_ad_interval_hours"))
        setting_ad = result_ad.scalars().first()
        ad_interval = int(setting_ad.value) if setting_ad and setting_ad.value and setting_ad.value.isdigit() else 2

    scheduler.add_job(broadcast_auto_test, "interval", minutes=interval, args=[bot], id="auto_test_job", replace_existing=True)
    scheduler.add_job(broadcast_auto_ad, "interval", hours=ad_interval, args=[bot], id="auto_ad_job", replace_existing=True)
    scheduler.add_job(check_expired_premiums, "interval", hours=1, args=[bot], id="expired_premium_job", replace_existing=True)
    scheduler.add_job(send_daily_smart_reminder, "cron", hour=18, minute=0, args=[bot], id="daily_reminder_job", replace_existing=True)
    scheduler.add_job(send_personalized_hourly_reminders, "cron", minute=0, args=[bot], id="personalized_reminders_job", replace_existing=True)
    scheduler.start()
    return scheduler

