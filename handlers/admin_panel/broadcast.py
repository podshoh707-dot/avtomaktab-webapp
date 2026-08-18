from aiogram import Router, types, F, Bot
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User, Setting
from sqlalchemy import select
from config import ADMIN_IDS
import asyncio

broadcast_router = Router()


class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_autoad_post = State()


@broadcast_router.callback_query(F.data == "admin_broadcast")
async def broadcast_main_menu(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_broadcast"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Bir marta xabar tarqatish", callback_data="admin_broadcast_manual")],
        [InlineKeyboardButton(text="🤖 Avto-Reklama (Jadval soati)", callback_data="admin_autoad_menu")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]
    ])
    await callback.message.edit_text(
        "📢 <b>XABARLAR VA REKLAMA BO'LIMI</b>\n\n"
        "Kerakli bo'limni tanlang:\n"
        "• <b>Bir marta xabar tarqatish:</b> barcha foydalanuvchilarga darhol yuborish.\n"
        "• <b>Avto-Reklama:</b> guruh va lichkalarga belgilangan soat oralig'ida avtomatik reklama posti yuborish.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ══════════════════════════════════════════
#  QO'LDA BIR MARTA XABAR TARQATISH
# ══════════════════════════════════════════

@broadcast_router.callback_query(F.data == "admin_broadcast_manual")
async def broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_broadcast"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_broadcast")]
    ])
    await callback.message.edit_text(
        "📢 <b>BIR MARTALIK XABAR TARQATISH</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring.\n\n"
        "✅ Qo'llab-quvvatlanadigan xabar turlari:\n"
        "• Matn (bold, italic, emoji va h.k.)\n"
        "• Rasm (photo)\n"
        "• Video / Audio / Ovozli xabar\n"
        "• Fayl / Sticker / GIF / Video Note\n"
        "• Tugmali postlar\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.answer()


@broadcast_router.message(BroadcastStates.waiting_for_message)
async def broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    if not await check_permission(message.from_user.id, "can_broadcast"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return

    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Xabar tarqatish bekor qilindi.\n\n/admin orqali panelga qaytishingiz mumkin.")
        return

    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        user_ids = result.scalars().all()

    total = len(user_ids)
    sent = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Xabar yuborilmoqda... 0 / {total}")

    for i, uid in enumerate(user_ids):
        try:
            await message.copy_to(chat_id=uid, allow_sending_without_reply=True)
            sent += 1
        except Exception as e:
            failed += 1
            err_str = str(e).lower()
            if "forbidden" not in err_str and "blocked" not in err_str and "deactivated" not in err_str:
                print(f"Broadcast error to {uid}: {e}")

        if (i + 1) % 30 == 0:
            try:
                await status_msg.edit_text(
                    f"⏳ Xabar yuborilmoqda...\n\n"
                    f"📊 {i + 1} / {total}\n"
                    f"✅ Muvaffaqiyatli: {sent}\n"
                    f"❌ Xatolik: {failed}"
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await state.clear()
    try:
        await status_msg.edit_text(
            f"✅ <b>XABAR TARQATISH YAKUNLANDI</b>\n\n"
            f"👥 Jami foydalanuvchilar: {total}\n"
            f"✅ Muvaffaqiyatli: {sent}\n"
            f"❌ Xatolik: {failed}\n\n"
            f"/admin orqali panelga qaytishingiz mumkin.",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(f"✅ XABAR TARQATISH YAKUNLANDI\n\nJami: {total} | ✅ {sent} | ❌ {failed}")


# ══════════════════════════════════════════
#  🤖 AVTO-REKLAMA SOZLAMALARI (SCHEDULED ADS)
# ══════════════════════════════════════════

@broadcast_router.callback_query(F.data == "admin_autoad_menu")
async def admin_autoad_menu(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_broadcast"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    await state.clear()

    async with async_session() as session:
        r_en = await session.execute(select(Setting).where(Setting.key == "auto_ad_enabled"))
        s_en = r_en.scalars().first()
        status_text = "🟢 Yoqilgan" if s_en and s_en.value == "1" else "🔴 O'chirilgan"

        r_gr = await session.execute(select(Setting).where(Setting.key == "auto_ad_groups"))
        s_gr = r_gr.scalars().first()
        groups_text = "🟢 Yoqilgan" if (not s_gr) or (s_gr.value == "1") else "🔴 O'chirilgan"

        r_us = await session.execute(select(Setting).where(Setting.key == "auto_ad_users"))
        s_us = r_us.scalars().first()
        users_text = "🟢 Yoqilgan" if s_us and s_us.value == "1" else "🔴 O'chirilgan"

        r_int = await session.execute(select(Setting).where(Setting.key == "auto_ad_interval_hours"))
        s_int = r_int.scalars().first()
        interval_hrs = s_int.value if s_int and s_int.value else "2"

        r_msg = await session.execute(select(Setting).where(Setting.key == "auto_ad_message_id"))
        s_msg = r_msg.scalars().first()
        post_status = "✅ Post o'rnatilgan" if s_msg and s_msg.value else "❌ Post o'rnatilmagan"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔄 Holat: {status_text}", callback_data="toggle_autoad_status")],
        [InlineKeyboardButton(text=f"👥 Guruhlarga: {groups_text}", callback_data="toggle_autoad_groups"),
         InlineKeyboardButton(text=f"👤 Lichkalarga: {users_text}", callback_data="toggle_autoad_users")],
        [InlineKeyboardButton(text=f"⏱ Har {interval_hrs} soatda tarqatish", callback_data="autoad_select_interval")],
        [InlineKeyboardButton(text="📝 Reklama postini o'rnatish", callback_data="set_autoad_post"),
         InlineKeyboardButton(text="👁 Postni ko'rish", callback_data="test_autoad_post")],
        [InlineKeyboardButton(text="🗑 Postni o'chirish", callback_data="delete_autoad_post")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_broadcast")]
    ])

    await callback.message.edit_text(
        f"🤖 <b>AVTO-REKLAMA SOZLAMALARI</b>\n\n"
        f"Guruhlarga va foydalanuvchilar lichkasiga belgilangan vaqt soatida avtomatik reklama posti tarqatiladi.\n\n"
        f"📌 <b>Umumiy holat:</b> {status_text}\n"
        f"👥 <b>Guruhlarga yuborish:</b> {groups_text}\n"
        f"👤 <b>Lichkalarga yuborish:</b> {users_text}\n"
        f"⏱ <b>Takrorlanish vaqti:</b> Har <b>{interval_hrs} soatda</b>\n"
        f"📝 <b>Reklama posti:</b> {post_status}\n\n"
        f"👇 Kerakli tugmani bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@broadcast_router.callback_query(F.data == "toggle_autoad_status")
async def toggle_autoad_status(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        res = await session.execute(select(Setting).where(Setting.key == "auto_ad_enabled"))
        st = res.scalars().first()
        if st:
            st.value = "0" if st.value == "1" else "1"
        else:
            st = Setting(key="auto_ad_enabled", value="1")
            session.add(st)
        await session.commit()
    await admin_autoad_menu(callback, state)


@broadcast_router.callback_query(F.data == "toggle_autoad_groups")
async def toggle_autoad_groups(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        res = await session.execute(select(Setting).where(Setting.key == "auto_ad_groups"))
        st = res.scalars().first()
        if st:
            st.value = "0" if st.value == "1" else "1"
        else:
            st = Setting(key="auto_ad_groups", value="0")
            session.add(st)
        await session.commit()
    await admin_autoad_menu(callback, state)


@broadcast_router.callback_query(F.data == "toggle_autoad_users")
async def toggle_autoad_users(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        res = await session.execute(select(Setting).where(Setting.key == "auto_ad_users"))
        st = res.scalars().first()
        if st:
            st.value = "0" if st.value == "1" else "1"
        else:
            st = Setting(key="auto_ad_users", value="1")
            session.add(st)
        await session.commit()
    await admin_autoad_menu(callback, state)


@broadcast_router.callback_query(F.data == "autoad_select_interval")
async def autoad_select_interval(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱ 1 soatda", callback_data="set_autoad_hrs_1"),
         InlineKeyboardButton(text="⏱ 2 soatda", callback_data="set_autoad_hrs_2")],
        [InlineKeyboardButton(text="⏱ 4 soatda", callback_data="set_autoad_hrs_4"),
         InlineKeyboardButton(text="⏱ 6 soatda", callback_data="set_autoad_hrs_6")],
        [InlineKeyboardButton(text="⏱ 12 soatda", callback_data="set_autoad_hrs_12"),
         InlineKeyboardButton(text="⏱ 24 soatda (1 kunda)", callback_data="set_autoad_hrs_24")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_autoad_menu")]
    ])
    await callback.message.edit_text(
        "⏱ <b>AVTO-REKLAMA TAKRORLANISH VAQTINI TANLANG</b>\n\n"
        "Reklama posti qancha vaqt oralig'ida qayta yuborilsin?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@broadcast_router.callback_query(F.data.startswith("set_autoad_hrs_"))
async def set_autoad_hrs_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    hrs = callback.data.split("_")[-1]
    async with async_session() as session:
        res = await session.execute(select(Setting).where(Setting.key == "auto_ad_interval_hours"))
        st = res.scalars().first()
        if st:
            st.value = str(hrs)
        else:
            st = Setting(key="auto_ad_interval_hours", value=str(hrs))
            session.add(st)
        await session.commit()

    # Dynamic scheduler job update
    from scheduler import get_scheduler, broadcast_auto_ad
    sched = get_scheduler()
    if sched:
        try:
            sched.add_job(
                broadcast_auto_ad,
                "interval",
                hours=int(hrs),
                args=[bot],
                id="auto_ad_job",
                replace_existing=True
            )
        except Exception as e:
            print(f"Error updating scheduler auto_ad interval: {e}")

    await callback.answer(f"✅ Avto-reklama intervali {hrs} soatga o'rnatildi!", show_alert=True)
    await admin_autoad_menu(callback, state)


@broadcast_router.callback_query(F.data == "set_autoad_post")
async def set_autoad_post_prompt(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_autoad_menu")]
    ])
    await callback.message.edit_text(
        "📝 <b>AVTO-REKLAMA POSTINI YUBORING</b>\n\n"
        "Guruh va lichkalarga avtomatik yuboriladigan reklama xabarini shu yerga yuboring.\n\n"
        "✅ Istalgan turdagi matn, rasm, video, tugmali va formatlangan xabarlar saqlanadi!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_autoad_post)
    await callback.answer()


@broadcast_router.message(BroadcastStates.waiting_for_autoad_post)
async def save_autoad_post(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    chat_id_str = str(message.chat.id)
    msg_id_str = str(message.message_id)

    async with async_session() as session:
        # Save from_chat_id
        res_c = await session.execute(select(Setting).where(Setting.key == "auto_ad_from_chat_id"))
        st_c = res_c.scalars().first()
        if st_c: st_c.value = chat_id_str
        else: session.add(Setting(key="auto_ad_from_chat_id", value=chat_id_str))

        # Save message_id
        res_m = await session.execute(select(Setting).where(Setting.key == "auto_ad_message_id"))
        st_m = res_m.scalars().first()
        if st_m: st_m.value = msg_id_str
        else: session.add(Setting(key="auto_ad_message_id", value=msg_id_str))

        await session.commit()

    await state.clear()
    await message.answer("✅ <b>Avto-reklama posti muvaffaqiyatli saqlandi!</b>\n\nEndi belgilangan vaqt oralig'ida avtomatik yuboriladi.", parse_mode="HTML")


@broadcast_router.callback_query(F.data == "test_autoad_post")
async def test_autoad_post(callback: types.CallbackQuery, bot: Bot):
    async with async_session() as session:
        res_c = await session.execute(select(Setting).where(Setting.key == "auto_ad_from_chat_id"))
        st_c = res_c.scalars().first()
        res_m = await session.execute(select(Setting).where(Setting.key == "auto_ad_message_id"))
        st_m = res_m.scalars().first()

    if not st_c or not st_m:
        await callback.answer("❌ Avto-reklama posti hali o'rnatilmagan!", show_alert=True)
        return

    try:
        await bot.copy_to(
            chat_id=callback.from_user.id,
            from_chat_id=int(st_c.value),
            message_id=int(st_m.value)
        )
        await callback.answer("✅ Test reklama posti sizga yuborildi!")
    except Exception as e:
        await callback.answer(f"❌ Postni ko'rsatishda xatolik: {e}", show_alert=True)


@broadcast_router.callback_query(F.data == "delete_autoad_post")
async def delete_autoad_post(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        res_c = await session.execute(select(Setting).where(Setting.key == "auto_ad_from_chat_id"))
        st_c = res_c.scalars().first()
        if st_c: await session.delete(st_c)

        res_m = await session.execute(select(Setting).where(Setting.key == "auto_ad_message_id"))
        st_m = res_m.scalars().first()
        if st_m: await session.delete(st_m)

        await session.commit()

    await callback.answer("🗑 Avto-reklama posti o'chirildi!", show_alert=True)
    await admin_autoad_menu(callback, state)
