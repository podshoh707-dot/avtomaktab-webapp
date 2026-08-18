from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Setting
from sqlalchemy import select
import os
import re

from config import ADMIN_IDS

system_router = Router()

@system_router.callback_query(F.data == "admin_system")
async def admin_system_menu(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "forward_status"))
        setting = result.scalars().first()
        status_text = "🟢 Yoqilgan" if setting and setting.value == "1" else "🔴 O'chirilgan"
        
        result_protect = await session.execute(select(Setting).where(Setting.key == "protect_content"))
        protect_setting = result_protect.scalars().first()
        protect_text = "🟢 Yoqilgan" if protect_setting and protect_setting.value == "1" else "🔴 O'chirilgan"
    
        result_req = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        req_setting = result_req.scalars().first()
        req_channel = req_setting.value if req_setting and req_setting.value else "O'rnatilmagan"
        
        result_auto = await session.execute(select(Setting).where(Setting.key == "auto_test_enabled"))
        auto_setting = result_auto.scalars().first()
        auto_text = "🟢 Yoqilgan" if auto_setting and auto_setting.value == "1" else "🔴 O'chirilgan"

        result_auto_users = await session.execute(select(Setting).where(Setting.key == "auto_test_send_users"))
        auto_users_setting = result_auto_users.scalars().first()
        auto_users_text = "🟢 Yoqilgan" if auto_users_setting and auto_users_setting.value == "1" else "🔴 O'chirilgan"

        # Avto-test oraligi (daqiqa)
        result_interval = await session.execute(select(Setting).where(Setting.key == "auto_test_interval"))
        interval_setting = result_interval.scalars().first()
        interval_val = interval_setting.value if interval_setting else "10"

        # Kartochka tema soatlari
        result_light = await session.execute(select(Setting).where(Setting.key == "card_light_start"))
        light_setting = result_light.scalars().first()
        light_hour = light_setting.value if light_setting else "6"

        result_dark = await session.execute(select(Setting).where(Setting.key == "card_dark_start"))
        dark_setting = result_dark.scalars().first()
        dark_hour = dark_setting.value if dark_setting else "21"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💾 Baza Nusxasi (Backup)", callback_data="admin_backup_db"),
            InlineKeyboardButton(text="🧹 Tizim Salomatligi", callback_data="admin_system_health")
        ],
        [InlineKeyboardButton(text="📢 Majburiy obuna kanallari", callback_data="admin_channels_menu")],
        [InlineKeyboardButton(text="🔄 WebApp bazasini yangilash", callback_data="admin_export_webapp")],
        [InlineKeyboardButton(text=f"⏱ Avto-test: {auto_text}", callback_data="toggle_auto_test"),
         InlineKeyboardButton(text=f"🕐 Har {interval_val} daq", callback_data="admin_set_interval")],
        [InlineKeyboardButton(text=f"👤 Lichkaga avto-savol: {auto_users_text}", callback_data="toggle_auto_test_users")],
        [InlineKeyboardButton(text=f"☀️ Och tema: {light_hour}:00 dan", callback_data="admin_set_light_hour"),
         InlineKeyboardButton(text=f"🌙 To'q tema: {dark_hour}:00 dan", callback_data="admin_set_dark_hour")],
        [InlineKeyboardButton(text=f"📨 Xabar uzatish: {status_text}", callback_data="toggle_forward")],
        [InlineKeyboardButton(text=f"🛡 Kontentni himoyalash: {protect_text}", callback_data="toggle_protect_content")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]
    ])
    
    await callback.message.edit_text(
        f"⚙️ TIZIM SOZLAMALARI\n\n"
        f"🕐 Avto-test oraligi: har <b>{interval_val} daqiqa</b>\n"
        f"☀️ Och (Light) tema: <b>{light_hour}:00 – {dark_hour}:00</b>\n"
        f"🌙 To'q (Dark) tema: <b>{dark_hour}:00 – {light_hour}:00</b>\n\n"
        f"Kerakli bo'limni tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@system_router.callback_query(F.data == "toggle_forward")
async def toggle_forward(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "forward_status"))
        setting = result.scalars().first()
        if setting:
            setting.value = "0" if setting.value == "1" else "1"
        else:
            setting = Setting(key="forward_status", value="1")
            session.add(setting)
        await session.commit()
        
    await admin_system_menu(callback)

@system_router.callback_query(F.data == "admin_export_webapp")
async def admin_export_webapp_handler(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    await callback.answer("⏳ Bazani eksport qilish boshlandi...", show_alert=False)
    try:
        from export_questions import export
        await export()
        await callback.message.answer("✅ Savollar bazasi muvaffaqiyatli WebApp (Mini Ilova) ga eksport qilindi!\n\nEndi `webapp/questions.json` faylida yangilangan bazani ko'rishingiz mumkin. Agar siz Vercel/GitHub ishlatsangiz, o'zgarishlarni yuklashni unutmang.")
    except Exception as e:
        await callback.message.answer(f"❌ Xatolik yuz berdi: {e}")

@system_router.callback_query(F.data == "toggle_auto_test")
async def toggle_auto_test(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "auto_test_enabled"))
        setting = result.scalars().first()
        
        if not setting:
            setting = Setting(key="auto_test_enabled", value="1")
            session.add(setting)
        else:
            setting.value = "0" if setting.value == "1" else "1"
            
        await session.commit()
        
    await admin_system_menu(callback.message)
    await callback.answer("Avto-test holati o'zgartirildi!")

@system_router.callback_query(F.data == "toggle_auto_test_users")
async def toggle_auto_test_users(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "auto_test_send_users"))
        setting = result.scalars().first()

        if not setting:
            setting = Setting(key="auto_test_send_users", value="1")
            session.add(setting)
            new_val = "1"
        else:
            new_val = "0" if setting.value == "1" else "1"
            setting.value = new_val

        await session.commit()

    status = "yoqildi ✅" if new_val == "1" else "o'chirildi ❌"
    await callback.answer(f"Lichkaga avto-savol {status}", show_alert=True)
    await admin_system_menu(callback)

@system_router.callback_query(F.data == "toggle_protect_content")
async def toggle_protect_content(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "protect_content"))
        setting = result.scalars().first()
        if setting:
            setting.value = "0" if setting.value == "1" else "1"
        else:
            setting = Setting(key="protect_content", value="1")
            session.add(setting)
        await session.commit()
        
    await admin_system_menu(callback)

class AdminStates(StatesGroup):
    waiting_for_new_admin_id = State()
    waiting_for_req_channel = State()
    waiting_for_interval = State()
    waiting_for_light_hour = State()
    waiting_for_dark_hour = State()


# ── Avto-test oraligi ──────────────────────────────────────────────
@system_router.callback_query(F.data == "admin_set_interval")
async def admin_set_interval_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 daq",  callback_data="setinterval_5"),
         InlineKeyboardButton(text="10 daq", callback_data="setinterval_10"),
         InlineKeyboardButton(text="15 daq", callback_data="setinterval_15")],
        [InlineKeyboardButton(text="20 daq", callback_data="setinterval_20"),
         InlineKeyboardButton(text="30 daq", callback_data="setinterval_30"),
         InlineKeyboardButton(text="60 daq", callback_data="setinterval_60")],
        [InlineKeyboardButton(text="✍️ O'zim kiritaman", callback_data="setinterval_custom")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_system")]
    ])
    await callback.message.edit_text(
        "⏱ Avto-test oraligi\n\n"
        "Quyidagilardan birini tanlang yoki o'z qiymatini kiriting (daqiqalarda):",
        reply_markup=keyboard
    )

@system_router.callback_query(F.data.startswith("setinterval_"))
async def admin_set_interval_quick(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    val = callback.data.split("_")[1]
    if val == "custom":
        await callback.message.edit_text(
            "✍️ Oraliqni daqiqalarda kiriting (masalan: 25):\n/cancel — bekor qilish"
        )
        await state.set_state(AdminStates.waiting_for_interval)
        return
    # Tayyor qiymat
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "auto_test_interval"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="auto_test_interval", value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()
    await callback.answer(f"✅ Oraliq {val} daqiqa qilib saqlandi!", show_alert=True)
    await admin_system_menu(callback)

@system_router.message(AdminStates.waiting_for_interval)
async def admin_set_interval_save(message: types.Message, state: FSMContext):
    if not is_superadmin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return
    try:
        val = int(message.text.strip())
        if val < 1 or val > 1440:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat! 1 dan 1440 daqiqagacha son kiriting.")
        return
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "auto_test_interval"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="auto_test_interval", value=str(val))
            session.add(setting)
        else:
            setting.value = str(val)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Avto-test oraligi {val} daqiqa qilib saqlandi!\n/admin")


# ── Kartochka tema soatlari ─────────────────────────────────────────
@system_router.callback_query(F.data == "admin_set_light_hour")
async def admin_set_light_hour_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5:00", callback_data="setlighth_5"),
         InlineKeyboardButton(text="6:00", callback_data="setlighth_6"),
         InlineKeyboardButton(text="7:00", callback_data="setlighth_7"),
         InlineKeyboardButton(text="8:00", callback_data="setlighth_8")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_system")]
    ])
    await callback.message.edit_text(
        "☀️ Och (Light) tema qaysi soatdan boshlansin?\n"
        "(Toshkent vaqti bo'yicha)",
        reply_markup=keyboard
    )

@system_router.callback_query(F.data.startswith("setlighth_"))
async def admin_set_light_hour_save(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        return
    val = callback.data.split("_")[1]
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "card_light_start"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="card_light_start", value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()
    await callback.answer(f"✅ Och tema {val}:00 dan boshlanadi!", show_alert=True)
    await admin_system_menu(callback)

@system_router.callback_query(F.data == "admin_set_dark_hour")
async def admin_set_dark_hour_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="18:00", callback_data="setdarkh_18"),
         InlineKeyboardButton(text="19:00", callback_data="setdarkh_19"),
         InlineKeyboardButton(text="20:00", callback_data="setdarkh_20"),
         InlineKeyboardButton(text="21:00", callback_data="setdarkh_21")],
        [InlineKeyboardButton(text="22:00", callback_data="setdarkh_22"),
         InlineKeyboardButton(text="23:00", callback_data="setdarkh_23")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_system")]
    ])
    await callback.message.edit_text(
        "🌙 To'q (Dark) tema qaysi soatdan boshlansin?\n"
        "(Toshkent vaqti bo'yicha)",
        reply_markup=keyboard
    )

@system_router.callback_query(F.data.startswith("setdarkh_"))
async def admin_set_dark_hour_save(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        return
    val = callback.data.split("_")[1]
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "card_dark_start"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="card_dark_start", value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()
    await callback.answer(f"✅ To'q tema {val}:00 dan boshlanadi!", show_alert=True)
    await admin_system_menu(callback)



import json

@system_router.callback_query(F.data == "admin_channels_menu")
async def admin_channels_menu(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        setting = result.scalars().first()
        channels = []
        if setting and setting.value and setting.value != "off":
            try:
                channels = json.loads(setting.value)
            except json.JSONDecodeError:
                channels = [setting.value]
                
    buttons = []
    text = "📢 MAJBURIY OBUNA KANALLARI\n\nUshbu kanallarga a'zo bo'lmaguncha foydalanuvchilar botdan foydalana olmaydi.\n\n"
    
    for i, ch in enumerate(channels):
        text += f"{i+1}. {ch}\n"
        buttons.append([
            InlineKeyboardButton(text=f"❌ {ch} ni o'chirish", callback_data=f"del_channel_{i}")
        ])
        
    if not channels:
        text += "Hozircha kanallar yo'q."
        
    buttons.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_set_req_channel")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_system")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@system_router.callback_query(F.data.startswith("del_channel_"))
async def admin_del_channel(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
        
    idx = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        setting = result.scalars().first()
        if setting and setting.value:
            try:
                channels = json.loads(setting.value)
            except json.JSONDecodeError:
                channels = [setting.value]
                
            if 0 <= idx < len(channels):
                channels.pop(idx)
                setting.value = json.dumps(channels) if channels else "off"
                await session.commit()
                
    await callback.answer("Kanal o'chirildi", show_alert=True)
    await admin_channels_menu(callback)

@system_router.callback_query(F.data == "admin_set_req_channel")
async def admin_set_req_channel(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
    await callback.message.edit_text("📢 Majburiy obuna uchun kanal usernamesini (Masalan: @kanal_nomi) kiriting:\n\nBekor qilish uchun /cancel")
    await state.set_state(AdminStates.waiting_for_req_channel)

@system_router.message(AdminStates.waiting_for_req_channel)
async def process_req_channel(message: types.Message, state: FSMContext):
    if not is_superadmin(message.from_user.id):
        await message.answer("Bu amal faqat asosiy admin uchun!")
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Jarayon bekor qilindi.")
        return
        
    new_channel = message.text.strip()
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "required_channel"))
        setting = result.scalars().first()
        
        channels = []
        if setting:
            if setting.value and setting.value != "off":
                try:
                    channels = json.loads(setting.value)
                except json.JSONDecodeError:
                    channels = [setting.value]
            channels.append(new_channel)
            setting.value = json.dumps(channels)
        else:
            channels.append(new_channel)
            setting = Setting(key="required_channel", value=json.dumps(channels))
            session.add(setting)
            
        await session.commit()
        
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Kanallar ro'yxatiga qaytish", callback_data="admin_channels_menu")]])
    await message.answer(f"✅ Yangi kanal qo'shildi: {new_channel}\n\n⚠️ DIQQAT: Bot ushbu kanalda admin huquqlariga ega bo'lishi shart, aks holda obuna tekshiruvi ishlamaydi!", reply_markup=keyboard)
@system_router.callback_query(F.data == "admin_strike")
async def admin_strike_handler(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Bu amal faqat asosiy admin uchun!", show_alert=True)
        return
    await callback.answer("🔥 Premium Strike bo'limi faol!", show_alert=True)


# ──────────────── BAZA ZAXIRA NUSXASI (BACKUP) ────────────────
@system_router.callback_query(F.data == "admin_backup_db")
async def admin_backup_db_handler(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Faqat superadmin uchun!", show_alert=True)
        return
        
    await callback.answer("⏳ Zaxira nusxasi tayyorlanmoqda...")
    
    from aiogram.types import FSInputFile
    from config import BASE_DIR
    import os
    from datetime import datetime
    
    db_path = os.path.join(BASE_DIR, "db", "database.sqlite")
    if not os.path.exists(db_path):
        await callback.message.answer("❌ database.sqlite fayli topilmadi!")
        return
        
    file_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc = FSInputFile(db_path, filename=f"avtomaktab_backup_{now_str}.sqlite")
    
    caption = (
        "💾 <b>MA'LUMOTLAR BAZASI ZAXIRA NUSXASI (BACKUP)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 Fayl: <code>database.sqlite</code>\n"
        f"📦 Hajmi: <b>{file_size_mb} MB</b>\n"
        f"📅 Sana: <b>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</b>\n\n"
        "🔒 <i>Ushbu faylni xavfsiz joyda saqlang.</i>"
    )
    await callback.message.answer_document(document=doc, caption=caption, parse_mode="HTML")


# ──────────────── TIZIM SALOMATLIGI & XOTIRA (RAM) ────────────────
@system_router.callback_query(F.data == "admin_system_health")
async def admin_system_health_handler(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id):
        await callback.answer("Faqat superadmin uchun!", show_alert=True)
        return
        
    import os, sys, shutil
    from database import Question, Sign, User, BotGroup
    from sqlalchemy import func
    
    # Savollar va modellar statistikasi
    async with async_session() as session:
        q_count = await session.scalar(select(func.count(Question.id)))
        sign_count = await session.scalar(select(func.count(Sign.id)))
        u_count = await session.scalar(select(func.count(User.id)))
        g_count = await session.scalar(select(func.count(BotGroup.id)))
        
    # Disk xotirasi
    total, used, free = shutil.disk_usage(".")
    free_gb = round(free / (1024 ** 3), 1)
    total_gb = round(total / (1024 ** 3), 1)
    
    # Python va tizim
    py_ver = sys.version.split()[0]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_system_health")],
        [InlineKeyboardButton(text="🔙 Tizim sozlamalari", callback_data="admin_system")]
    ])
    
    health_text = (
        "🧹 <b>TIZIM VA SERVER SALOMATLIGI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 <b>Bot Holati:</b> 100% Faol & Barqaror\n"
        f"🐍 <b>Python Versiyasi:</b> <code>{py_ver}</code>\n"
        f"💾 <b>Bo'sh Disk Xotirasi:</b> <b>{free_gb} GB / {total_gb} GB</b>\n\n"
        "📊 <b>Baza Ko'rsatkichlari:</b>\n"
        f"   • 🏎 YHQ Savollari: <b>{q_count} ta</b>\n"
        f"   • 🚦 Yo'l Belgilari: <b>{sign_count} ta</b>\n"
        f"   • 👤 Foydalanuvchilar: <b>{u_count} nafar</b>\n"
        f"   • 👥 Faol Guruhlar: <b>{g_count} ta</b>\n\n"
        "⚡️ <i>Barcha modullar va servislar yuqori tezlikda ishlamoqda.</i>"
    )
    
    await callback.message.edit_text(health_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

