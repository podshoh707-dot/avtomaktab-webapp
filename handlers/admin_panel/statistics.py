from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User, UserStat, Question, BotGroup, AdminUser, Setting, Payment
from sqlalchemy import select, func, and_
from sqlalchemy.sql import text as sql_text
from utils.permissions import check_permission
from datetime import datetime, timedelta
import json

statistics_router = Router()


@statistics_router.callback_query(F.data == "admin_stats")
async def show_statistics(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_view_stats"):
        await callback.answer("Sizda ushbu bo'limni ko'rish ruxsati yo'q!", show_alert=True)
        return

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    async with async_session() as session:
        # ─── Obunachilar ───
        total_users = (await session.execute(select(func.count()).select_from(User))).scalar()
        
        active_users = (await session.execute(
            select(func.count()).select_from(User).where(
                User.language.isnot(None),
                User.full_name.isnot(None),
                User.phone.isnot(None)
            )
        )).scalar()
        
        blocked_users = (await session.execute(
            select(func.count()).select_from(User).where(User.is_premium == False)
        )).scalar()
        # Actually blocked count — hard to track without a field, use 0 as placeholder
        blocked_count = 0  # Bot tomonidan bloklanganlar (real tracking kerak)
        
        premium_users = (await session.execute(
            select(func.count()).select_from(User).where(
                User.is_premium == True,
                User.premium_expires_at > now
            )
        )).scalar()

        # ─── O'sish ───
        today_count = (await session.execute(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        )).scalar()

        week_count = (await session.execute(
            select(func.count()).select_from(User).where(User.created_at >= week_start)
        )).scalar()

        month_count = (await session.execute(
            select(func.count()).select_from(User).where(User.created_at >= month_start)
        )).scalar()

        # ─── Faollik (UserStat orqali) ───
        yesterday_start = today_start - timedelta(days=1)
        active_today = (await session.execute(
            select(func.count()).select_from(UserStat).where(UserStat.last_active >= today_start)
        )).scalar()
        
        active_week = (await session.execute(
            select(func.count()).select_from(UserStat).where(UserStat.last_active >= week_start)
        )).scalar()

        # ─── Guruhlar ───
        total_groups = (await session.execute(
            select(func.count()).select_from(BotGroup)
        )).scalar()
        
        active_groups = (await session.execute(
            select(func.count()).select_from(BotGroup).where(BotGroup.is_active == True)
        )).scalar()

        admin_count = (await session.execute(
            select(func.count()).select_from(AdminUser).where(AdminUser.is_active == True)
        )).scalar()

        # ─── Majburiy obuna kanallari ───
        result_ch = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        ch_setting = result_ch.scalars().first()
        channels = []
        if ch_setting and ch_setting.value and ch_setting.value != "off":
            try:
                channels = json.loads(ch_setting.value)
            except Exception:
                channels = [ch_setting.value]

    # Majburiy obuna check (kanallar soni)
    total_channels = len(channels)

    # ─── To'lovlar (Payments) ───
    async with async_session() as session:
        payments_query = await session.execute(
            select(Payment).where(Payment.status == 'approved')
        )
        approved_payments = payments_query.scalars().all()
        
    total_earnings = 0
    today_earnings = 0
    week_earnings = 0
    month_earnings = 0
    
    import re
    for p in approved_payments:
        # Raqamlarni ajratib olish (masalan "50 000 so'm" -> 50000)
        amount_str = re.sub(r'\D', '', str(p.amount))
        amount = int(amount_str) if amount_str else 0
        
        total_earnings += amount
        
        if p.resolved_at:
            if p.resolved_at >= today_start:
                today_earnings += amount
            if p.resolved_at >= week_start:
                week_earnings += amount
            if p.resolved_at >= month_start:
                month_earnings += amount

    # Reklama statistikasi placeholder
    ad_total = 0
    ad_success = 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Foydalanuvchilar (CSV)", callback_data="admin_export_users"),
            InlineKeyboardButton(text="💳 To'lovlar Tarixi (CSV)", callback_data="admin_export_payments")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_stats"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="admin_back_main")
        ]
    ])

    msg_text = (
        "📊 <b>BOTNING TO'LIQ STATISTIKASI</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"

        "👤 <b>Foydalanuvchilar</b>\n"
        f"   📋 Jami: <b>{total_users}</b> nafar\n"
        f"   ✅ Ro'yxatdan o'tgan: <b>{active_users}</b> nafar\n"
        f"   💎 VIP Obunachilar: <b>{premium_users}</b> nafar\n\n"

        "📈 <b>O'sish Ko'rsatkichi</b>\n"
        f"   🆕 Bugun: <b>+{today_count}</b>\n"
        f"   📅 So'nggi 7 kun: <b>+{week_count}</b>\n"
        f"   📅 So'nggi 30 kun: <b>+{month_count}</b>\n\n"

        "⚡️ <b>Faollik</b>\n"
        f"   👥 Bugungi faol: <b>{active_today}</b>\n"
        f"   👥 Haftalik faol: <b>{active_week}</b>\n\n"

        "👥 <b>Guruhlar & Kanallar</b>\n"
        f"   👥 Faol guruhlar: <b>{active_groups} / {total_groups}</b>\n"
        f"   📢 Majburiy kanallar: <b>{total_channels} ta</b>\n"
        f"   👮 Adminlar: <b>{admin_count} nafar</b>\n\n"

        "💰 <b>Moliya & Tushumlar</b>\n"
        f"   💳 Jami tushum: <b>{total_earnings:,} so'm</b>\n"
        f"   💵 Bugun: <b>{today_earnings:,} so'm</b>\n"
        f"   💵 7 kun: <b>{week_earnings:,} so'm</b>\n"
        f"   💵 30 kun: <b>{month_earnings:,} so'm</b>"
    )

    from aiogram.exceptions import TelegramBadRequest
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(msg_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.message.edit_text(msg_text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

    await callback.answer()


@statistics_router.callback_query(F.data == "admin_export_users")
async def export_users_csv(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_view_stats"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    await callback.answer("⏳ Baza shakllanmoqda, kuting...")
    
    import csv
    import os
    from aiogram.types import FSInputFile
    from config import BASE_DIR
    
    export_path = os.path.join(BASE_DIR, "db", "users_export.csv")
    
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.id))
        users = result.scalars().all()
        
    with open(export_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Telegram ID", "F.I.Sh", "Telefon", "Til", "VIP Status", "Ballar", "Referallar", "Marafon Progress", "Sana"])
        for u in users:
            is_vip = "VIP" if (u.is_premium and u.premium_expires_at and u.premium_expires_at > datetime.utcnow()) else "Oddiy"
            dt_str = u.created_at.strftime("%d.%m.%Y %H:%M") if u.created_at else ""
            writer.writerow([
                u.id, u.telegram_id, u.full_name or "", u.phone or "",
                u.language or "", is_vip, u.points or 0, u.referrals_count or 0,
                u.marathon_progress or 0, dt_str
            ])
            
    doc = FSInputFile(export_path, filename=f"avtomaktab_users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    await callback.message.answer_document(
        document=doc,
        caption=f"📊 <b>Avtomaktab foydalanuvchilar bazasi</b>\n\nJami yozuvlar: <b>{len(users)} ta</b>",
        parse_mode="HTML"
    )


@statistics_router.callback_query(F.data == "admin_export_payments")
async def export_payments_csv(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_view_stats"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    await callback.answer("⏳ To'lovlar hisoboti tayyorlanmoqda...")
    
    import csv, os
    from aiogram.types import FSInputFile
    from config import BASE_DIR
    
    export_path = os.path.join(BASE_DIR, "db", "payments_export.csv")
    
    from database import Payment
    async with async_session() as session:
        result = await session.execute(select(Payment).order_by(Payment.id.desc()))
        payments = result.scalars().all()
        
    with open(export_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Foydalanuvchi ID", "Summa", "To'lov Usuli", "Status", "Tasdiqlagan Admin", "Yaratilgan Sana", "Tasdiqlangan Sana"])
        for p in payments:
            c_str = p.created_at.strftime("%d.%m.%Y %H:%M") if p.created_at else ""
            r_str = p.resolved_at.strftime("%d.%m.%Y %H:%M") if p.resolved_at else ""
            writer.writerow([
                p.id, p.user_id, p.amount, p.payment_method or "Karta",
                p.status, p.approved_by or "", c_str, r_str
            ])
            
    doc = FSInputFile(export_path, filename=f"avtomaktab_payments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    await callback.message.answer_document(
        document=doc,
        caption=f"💳 <b>Avtomaktab to'lovlar hisoboti</b>\n\nJami to'lovlar: <b>{len(payments)} ta</b>",
        parse_mode="HTML"
    )
