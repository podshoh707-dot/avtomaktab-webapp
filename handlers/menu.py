from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from database import async_session, User, Setting, Rule, VideoLesson, News, QAItem, UserStat
from sqlalchemy import select, func
from sqlalchemy.sql.expression import desc
from aiogram.fsm.context import FSMContext

menu_router = Router()


# ──────────────── HELP ────────────────
@menu_router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "ℹ️ <b>AVTOVATANPARVAR BOT YORDAMI</b>\n"
        "───────────────────────────\n\n"
        "<b>Asosiy buyruqlar:</b>\n"
        "• /start — Botni qayta ishga tushirish\n"
        "• /test — Yangi YHQ testini boshlash\n"
        "• /stats — Shaxsiy natijalar statistikasi\n"
        "• /help — Ushbu yordam ko'rsatmasi\n\n"
        "📞 <b>Qo'shimcha savol va murojaatlar uchun:</b>\n"
        "Menyudagi <b>☎️ Adminga murojaat</b> tugmasidan foydalaning."
    )
    await message.answer(text, parse_mode="HTML")


# ──────────────── YO'L HARAKATI QOIDALARI ────────────────
RULES_PER_PAGE = 8

async def get_rules_keyboard_and_text(page: int = 1):
    async with async_session() as session:
        result = await session.execute(select(Rule).order_by(Rule.id))
        rules = result.scalars().all()

    if not rules:
        return None, "❌ Hozircha qoidalar kiritilmagan. Admin tez orada qo'shadi."

    total_rules = len(rules)
    total_pages = (total_rules + RULES_PER_PAGE - 1) // RULES_PER_PAGE
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * RULES_PER_PAGE
    end_idx = start_idx + RULES_PER_PAGE
    page_rules = rules[start_idx:end_idx]

    buttons = []
    for rule in page_rules:
        buttons.append([InlineKeyboardButton(
            text=f"📖 {rule.title[:55]}",
            callback_data=f"rule_{rule.id}_{page}"
        )])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"rules_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="rules_nop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingisi ➡️", callback_data=f"rules_page_{page + 1}"))

    buttons.append(nav_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        f"📚 <b>YO'L HARAKATI QOIDALARI KITOBI</b>\n"
        f"───────────────────────────\n\n"
        f"📋 Jami boblar: <b>{total_rules} ta</b> (Sahifa {page}/{total_pages})\n\n"
        f"👇 <i>O'qimoqchi bo'lgan bobni tanlang:</i>"
    )
    return keyboard, text


@menu_router.message(F.text.in_([
    "📚 YHQ Qoidalari", "📚 YHQ Qoidalari & Video Darslar", "📚 Yo'l harakati qoidalari",
    "📖 YHQ Kitobi", "📚 YHQ Kitobi", "📖 YHQ kitobi",
    "📚 Йўл ҳаракати қоидалари", "📚 Правила дорожного движения"
]))
async def rules_hub_menu(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 YHQ Qoidalari Kitobi (30 ta bob)", callback_data="rules_page_1")],
        [InlineKeyboardButton(text="🎥 133 ta Rasmiy Video Darslar", callback_data="vsec_all")],
        [InlineKeyboardButton(text="📱 Mini Ilovada O'rganish", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_main_menu")]
    ])
    text = (
        "📚 <b>YHQ QOIDALARI VA VIDEO DARSLAR BAZASI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Quyidagi o'quv bo'limlaridan birini tanlang:\n\n"
        "📖 <b>YHQ Qoidalari:</b> O'zbekiston Respublikasi rasmiy yo'l harakati qoidalari matnlari.\n"
        "🎥 <b>Video Darslar:</b> e-avtomaktab va Vatanparvar ning 133 ta rasmiy videodarsliklari.\n"
        "📱 <b>Mini Ilova:</b> Interaktiv animatsiyalar va qulay testlar."
    )
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await message.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@menu_router.callback_query(F.data == "rules_hub")
async def cb_rules_hub(callback: types.CallbackQuery, state: FSMContext = None):
    await rules_hub_menu(callback, state)


@menu_router.callback_query(F.data.regexp(r'^rules_page_\d+$'))
async def rules_page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    keyboard, text = await get_rules_keyboard_and_text(page)
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@menu_router.callback_query(F.data == "rules_nop")
async def rules_nop(callback: types.CallbackQuery):
    await callback.answer()


@menu_router.callback_query(F.data == "rules_back")
async def rules_back(callback: types.CallbackQuery):
    await rules_hub_menu(callback)


@menu_router.callback_query(F.data.regexp(r'^rule_\d+(?:_\d+)?$'))
async def show_rule(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    rule_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    async with async_session() as session:
        result = await session.execute(select(Rule).where(Rule.id == rule_id))
        rule = result.scalars().first()

    if not rule:
        await callback.answer("Qoida topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Boblar ro'yxatiga", callback_data=f"rules_page_{page}")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")]
    ])

    text = f"📖 <b>{rule.title}</b>\n\n{rule.text or 'Matn kiritilmagan.'}"
    if len(text) > 4000:
        text = text[:4000] + "..."

    if rule.image_url:
        await callback.message.answer_photo(photo=rule.image_url, caption=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ──────────────── 133 TA VIDEO DARSLAR ────────────────
@menu_router.message(F.text.in_([
    "🎥 Video darslar", "🎬 Video Darsliklar (VIP)", "🎬 Video Darsliklar", "🎥 Video Darsliklar",
    "🎥 Видео дарслар", "🎥 Видеоуроки", "🎥 Video darsliklar"
]))
async def video_menu(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
    await show_video_sections(message)


@menu_router.callback_query(F.data.in_(["vsec_all", "vback"]))
async def video_menu_callback(callback: types.CallbackQuery):
    await show_video_sections(callback.message, is_callback=True)
    await callback.answer()


async def show_video_sections(target, is_callback=False):
    async with async_session() as session:
        result = await session.execute(select(VideoLesson).order_by(VideoLesson.id))
        videos = result.scalars().all()

    if not videos:
        msg = "❌ Hozircha video darslar kiritilmagan."
        if is_callback: await target.edit_text(msg)
        else: await target.answer(msg)
        return

    sections = {}
    for v in videos:
        sec = v.section or "Umumiy ta'lim darslari"
        if sec not in sections:
            sections[sec] = 0
        sections[sec] += 1

    buttons = []
    for sec_name, count in sections.items():
        buttons.append([InlineKeyboardButton(
            text=f"📁 {sec_name} ({count} ta dars)",
            callback_data=f"vsec_{sec_name[:20]}_1"
        )])

    buttons.append([
        InlineKeyboardButton(text="🔙 YHQ Markaziga", callback_data="rules_hub"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        f"🎥 <b>133 TA RASMIY VIDEO DARSLAR BAZASI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📹 Jami darslar: <b>{len(videos)} ta</b> (e-avtomaktab.uz rasmiy darslari)\n\n"
        f"👇 <i>Ko'rmoqchi bo'lgan mavzuli bo'limni tanlang:</i>"
    )
    if is_callback:
        await target.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")


@menu_router.callback_query(F.data.regexp(r'^vsec_(.+)_(\d+)$'))
async def video_section(callback: types.CallbackQuery):
    match = re.match(r'^vsec_(.+)_(\d+)$', callback.data)
    sec_prefix = match.group(1)
    page = int(match.group(2))
    
    async with async_session() as session:
        result = await session.execute(select(VideoLesson).order_by(VideoLesson.id))
        all_vids = result.scalars().all()

    # Bo'lim bo'yicha filter
    matched_vids = [v for v in all_vids if (v.section or "Umumiy ta'lim darslari").startswith(sec_prefix)]
    if not matched_vids:
        matched_vids = all_vids

    per_page = 8
    total_pages = max(1, (len(matched_vids) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_vids = matched_vids[start_idx:end_idx]

    buttons = []
    for v in page_vids:
        topic_title = v.topic if len(v.topic) <= 45 else v.topic[:42] + "..."
        buttons.append([InlineKeyboardButton(
            text=f"▶️ {v.id}-Dars: {topic_title}",
            callback_data=f"vid_{v.id}"
        )])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"vsec_{sec_prefix}_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="rules_nop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"vsec_{sec_prefix}_{page+1}"))

    if nav_row:
        buttons.append(nav_row)
    buttons.append([
        InlineKeyboardButton(text="🔙 Bo'limlarga qaytish", callback_data="vback"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    sec_title = matched_vids[0].section if matched_vids else "Darslar"
    await callback.message.edit_text(
        f"📁 <b>Bo'lim: {sec_title}</b> (Jami: {len(matched_vids)} ta dars)\n\n"
        f"👇 <i>Ko'rmoqchi bo'lgan darsingizni tanlang:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@menu_router.callback_query(F.data.regexp(r'^vid_\d+$'))
async def show_video(callback: types.CallbackQuery):
    vid_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(VideoLesson).where(VideoLesson.id == vid_id))
        video = result.scalars().first()

    if not video:
        await callback.answer("Video topilmadi.", show_alert=True)
        return

    sec_prefix = (video.section or "Umumiy")[:20]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Videoni Onlayn Ko'rish (HD)", url=video.video_url or video.youtube_url or "https://e-avtomaktab.uz")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data=f"vsec_{sec_prefix}_1")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")]
    ])

    text = (
        f"🎥 <b>{video.id}-DARS: {video.topic}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 <b>Bo'lim:</b> {video.section or 'Umumiy ta\'lim darslari'}\n"
        f"🌐 <b>Manba:</b> e-avtomaktab.uz rasmiy darsi\n\n"
        f"👇 <i>Darsni to'liq HD sifatda tomosha qilish uchun pastdagi tugmani bosing:</i>"
    )

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@menu_router.callback_query(F.data == "vback")
async def video_back(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(VideoLesson))
        videos = result.scalars().all()

    sections = {}
    for v in videos:
        sec = v.section or "Umumiy"
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(v)

    buttons = []
    for sec_name, vids in sections.items():
        buttons.append([InlineKeyboardButton(
            text=f"📁 {sec_name} ({len(vids)} ta dars)",
            callback_data=f"vsec_{sec_name}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        f"🎥 <b>MAVZULASHGAN VIDEO DARSLAR</b>\n"
        f"───────────────────────────\n\n"
        f"📹 Jami darslar: <b>{len(videos)} ta</b>\n\n"
        f"👇 <i>Ko'rmoqchi bo'lgan bo'limni tanlang:</i>"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ──────────────── STATISTIKA ────────────────
@menu_router.message(Command("stats"))
@menu_router.message(F.text.in_(["📈 Mening Natijalarim", "📊 Statistika", "📊 Статистика"]))
async def show_stats(message: types.Message):
    async with async_session() as session:
        result_user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result_user.scalars().first()

        if not user:
            await message.answer("❌ Siz hali ro'yxatdan o'tmagansiz. /start ni bosing.")
            return

        result_stat = await session.execute(select(UserStat).where(UserStat.user_id == user.id))
        stat = result_stat.scalars().first()

    name = user.full_name or "Noma'lum"
    premium_status = "💎 VIP Premium" if user.is_premium else "⭐️ Standart"

    if not stat or (stat.tests_taken == 0):
        text = (
            f"📊 <b>SHAXSIY STATISTIKA VA NATIJALAR</b>\n"
            f"───────────────────────────\n\n"
            f"👤 <b>Foydalanuvchi:</b> {name}\n"
            f"👑 <b>Maqom:</b> {premium_status}\n"
            f"🏆 <b>Jami ballar:</b> <code>{user.points}</code> ball\n\n"
            f"⚠️ <i>Siz hali birorta ham test yechmadingiz!</i>\n"
            f"🚀 Pastdagi <b>🚗 Ishlash testi</b> tugmasi orqali bilimingizni sinashni boshlang!"
        )
        await message.answer(text, parse_mode="HTML")
        return

    percent = 0
    total_answers = stat.correct_answers + stat.wrong_answers
    if total_answers > 0:
        percent = round(stat.correct_answers / total_answers * 100)

    filled_bars = round(percent / 10)
    progress_bar = "🟩" * filled_bars + "⬜️" * (10 - filled_bars)

    text = (
        f"📊 <b>SHAXSIY STATISTIKA VA NATIJALAR</b>\n"
        f"───────────────────────────\n\n"
        f"👤 <b>Foydalanuvchi:</b> {name}\n"
        f"👑 <b>Maqom:</b> {premium_status}\n"
        f"🏆 <b>Umumiy Ballar:</b> <code>{user.points}</code> ball\n\n"
        f"📝 <b>Yechilgan testlar:</b> {stat.tests_taken} ta\n"
        f"✅ <b>To'g'ri javoblar:</b> {stat.correct_answers} ta\n"
        f"❌ <b>Noto'g'ri javoblar:</b> {stat.wrong_answers} ta\n\n"
        f"🎯 <b>To'g'rilik Foizi:</b> {percent}%\n"
        f"   {progress_bar}"
    )
    await message.answer(text, parse_mode="HTML")



# ──────────────── SAVOL-JAVOB ────────────────
@menu_router.message(F.text.in_(["💬 Savol-javob", "💬 Савол-жавоб", "💬 Вопрос-ответ"]))
async def show_qa(message: types.Message):
    async with async_session() as session:
        result = await session.execute(select(QAItem).limit(20))
        qa_list = result.scalars().all()

    if not qa_list:
        await message.answer(
            "💬 <b>SAVOL-JAVOB BO'LIMI</b>\n───────────────────────────\n\nHozircha savollar yo'q.",
            parse_mode="HTML"
        )
        return

    buttons = []
    for qa in qa_list:
        buttons.append([InlineKeyboardButton(
            text=f"❓ {qa.question[:50]}",
            callback_data=f"qa_{qa.id}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"💬 <b>KO'P BERILADIGAN SAVOLLAR VA JAVOBLAR</b>\n───────────────────────────\n\n📋 Jami: {len(qa_list)} ta savol\n\n👇 <i>Savolni tanlang:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data.regexp(r'^qa_\d+$'))
async def show_qa_answer(callback: types.CallbackQuery):
    qa_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(QAItem).where(QAItem.id == qa_id))
        qa = result.scalars().first()

    if not qa:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="qa_back")]
    ])
    await callback.message.edit_text(
        f"❓ <b>Savol:</b>\n{qa.question}\n\n✅ <b>Javob:</b>\n{qa.answer}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@menu_router.callback_query(F.data == "qa_back")
async def qa_back(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(QAItem).limit(20))
        qa_list = result.scalars().all()

    buttons = []
    for qa in qa_list:
        buttons.append([InlineKeyboardButton(
            text=f"❓ {qa.question[:50]}",
            callback_data=f"qa_{qa.id}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"💬 <b>KO'P BERILADIGAN SAVOLLAR VA JAVOBLAR</b>\n───────────────────────────\n\n📋 Jami: {len(qa_list)} ta savol\n\n👇 <i>Savolni tanlang:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ──────────────── ADMIN BILAN BOG'LANISH ────────────────
@menu_router.message(F.text.in_([
    "☎️ Adminga murojaat", "🎧 Qo'llab-quvvatlash (Support)", "🎧 Qo'llab-quvvatlash",
    "☎️ Qo'llab-quvvatlash", "☎️ Админга мурожаат", "☎️ Связаться с админом"
]))
async def contact_admin(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "contact_link"))
        setting = result.scalars().first()

    admin_contact = setting.value if (setting and setting.value) else "@Avto_admin"
    url = admin_contact if admin_contact.startswith("http") else f"https://t.me/{admin_contact.replace('@', '')}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Adminga Yozish (Telegram)", url=url)]
    ])
    text = (
        f"☎️ <b>ADMINISTRATSIYA BILAN ALOQA</b>\n"
        f"───────────────────────────\n\n"
        f"Savol, taklif va texnik yordam uchun quyidagi havola orqali bog'lanishingiz mumkin:\n\n"
        f"👤 <b>Telegram:</b> {admin_contact}\n"
        f"📞 <b>Aloqa markazi:</b> +998 97 069 70 77\n\n"
        f"⏱ <i>Ish vaqti: 09:00 - 20:00</i>"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@menu_router.message(F.text.in_(["🏛 Biz Haqimizda", "🏛 Tashkilot haqida"]))
async def org_info_handler(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
    
    if not setting:
        default_text = (
            "🏛 <b>AVTOVATANPARVAR INNOVATSION AVTOMAKTABI</b>\n"
            "───────────────────────────\n\n"
            "<b>\"AVTOVATANPARVAR\"</b> – O'zbekistonda yoshlarni va barcha qiziquvchilarni "
            "haydovchilik sirlariga o'rgatish, yo'l harakati xavfsizligini oshirish maqsadida tashkil etilgan zamonaviy o'quv maskani.\n\n"
            "🎯 <b>Bizning maqsadimiz:</b> Yo'llarda xavfsizlikni ta'minlaydigan, yuqori malakali, "
            "qoidalarni puxta biladigan madaniyatli haydovchilarni yetishtirib chiqarish.\n\n"
            "🌟 <b>Afzalliklarimiz:</b>\n"
            "• Zamonaviy interaktiv o'quv texnologiyalari va onlayn tayyorgarlik\n"
            "• Katta tajribaga ega professional instruktor va ustozlar\n"
            "• Qulay jadval va individual yondashuv\n"
            "• Innovatsion test bot va Mini App platformasi\n\n"
            "📍 <b>Manzil:</b> Toshkent shahri\n"
            "📞 <b>Aloqa:</b> +998 97 069 70 77\n\n"
            "<i>Biz bilan professionallar safiga qo'shiling!</i>"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Adminga murojaat", url="https://t.me/Avto_admin")]
        ])
        await message.answer(default_text, reply_markup=keyboard, parse_mode="HTML")
        return
        
    import json
    try:
        data = json.loads(setting.value)
        text = data.get("text", "")
        photo_id = data.get("photo_id")
        
        if photo_id:
            if photo_id.endswith('.png') or photo_id.endswith('.jpg'):
                from aiogram.types import FSInputFile
                import os
                from config import BASE_DIR
                full_photo_id = os.path.join(BASE_DIR, photo_id)
                if os.path.exists(full_photo_id):
                    await message.answer_photo(photo=FSInputFile(full_photo_id), caption=text, parse_mode="HTML")
                else:
                    await message.answer(text, parse_mode="HTML")
            else:
                await message.answer_photo(photo=photo_id, caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    except:
        await message.answer(setting.value, parse_mode="HTML")


# ──────────────── REFERRAL (DO'STLARNI TAKLIF QILISH) ────────────────
@menu_router.message(F.text.in_([
    "🎁 Taklif Qilish & VIP", "🎁 Taklif Qilish", "🎁 Do'stlarni taklif qilish", "🎁 Реферал"
]))
async def referral_menu(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
        
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalars().first()
        ref_count = user.referrals_count if user and user.referrals_count else 0
        
    share_text = f"🚗 Haydovchilik guvohnomasiga tayyorlanyapsizmi? Ushbu bot orqali YHQ testlarini yeching va haqiqiy GAI imtihoniga tayyorlaning: {ref_link}"
    import urllib.parse
    encoded_share = urllib.parse.quote(share_text)
    share_url = f"https://t.me/share/url?url={ref_link}&text={urllib.parse.quote('🚗 Haydovchilik guvohnomasiga tayyorlanish uchun 1-raqamli bot!')}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Do'stlarga yuborish (Ulashish)", url=share_url)],
        [InlineKeyboardButton(text="💎 VIP Obuna xarid qilish", callback_data="premium_buy")]
    ])
    
    text = (
        f"🎁 <b>DO'STLARNI TAKLIF QILIB BEPUL VIP YUTIB OLING!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Do'stlaringizga o'z taklif havolangizni yuboring. Ular botga qo'shilishi bilan sizga va do'stingizga <b>VIP kunlari</b> sovg'a qilinadi!\n\n"
        f"🏆 <b>Sovrinlar shartlari:</b>\n"
        f" • <b>Har 3 ta taklif</b> uchun: <b>+3 kun VIP Premium</b>\n"
        f" • <b>10 ta taklif</b> uchun: <b>+15 kun VIP Premium</b>\n"
        f" • <b>20 ta taklif</b> uchun: <b>1 Oylik to'liq VIP</b>\n\n"
        f"📊 <b>Sizning ko'rsatkichingiz:</b>\n"
        f"👥 Taklif qilingan do'stlar: <b>{ref_count} nafar</b>\n\n"
        f"🔗 <b>Sizning shaxsiy havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"<i>(Havolani nusxalash uchun ustiga bosing yoki quyidagi tugma orqali ulashing)</i>"
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ──────────────── STATISTIKA VA TOP 10 REYTING ────────────────
@menu_router.message(F.text.in_([
    "📊 Statistika", "📊 Статистика", "📊 Reyting", "📊 Mening Natijalarim", "📊 Natijalarim"
]))
async def stats_menu(message: types.Message, state: FSMContext):
    if state:
        await state.clear()
        
    user_id = message.from_user.id
    async with async_session() as session:
        result_user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result_user.scalars().first()
        
        stat = None
        if user:
            result_stat = await session.execute(select(UserStat).where(UserStat.user_id == user.id))
            stat = result_stat.scalars().first()

        # TOP 10 Foydalanuvchilarni olish
        top_res = await session.execute(
            select(User.full_name, User.points, User.marathon_progress)
            .order_by(User.points.desc(), User.marathon_progress.desc())
            .limit(10)
        )
        top_users = top_res.all()

    tests_taken = stat.tests_taken if stat else 0
    correct_ans = stat.correct_answers if stat else 0
    wrong_ans = stat.wrong_answers if stat else 0
    total_answered = correct_ans + wrong_ans
    accuracy = round((correct_ans / max(1, total_answered)) * 100)
    marathon_prog = user.marathon_progress if user and user.marathon_progress else 0
    marathon_pct = round(min(1242, marathon_prog) / 1242 * 100)
    points = user.points if user and user.points else 0
    streak = user.streak_count if user and user.streak_count else 0
    rem_time = user.reminder_time if user and user.reminder_time else "20:00"

    # 🧠 AI Imtihon Ehtimolligi Hisoblash
    if total_answered < 15:
        ai_forecast_pct = 50
        ai_status = "⏳ <i>Aniqlash uchun kamida 15 ta test yeching</i>"
    else:
        ai_forecast_pct = int(min(98, max(25, (accuracy * 0.65) + (min(100, marathon_prog / 12.42) * 0.35))))
        if ai_forecast_pct >= 85:
            ai_status = f"🟢 <b>{ai_forecast_pct}% — Yuqori tayyorgarlik!</b> (Imtihondan o'tish ehtimoli juda katta)"
        elif ai_forecast_pct >= 70:
            ai_status = f"🟡 <b>{ai_forecast_pct}% — O'rtacha</b> (Yana biroz mashq qiling)"
        else:
            ai_status = f"🔴 <b>{ai_forecast_pct}% — Past</b> (Xatolar ustida ishlash tavsiya etiladi)"

    # Liderlar ro'yxatini shakllantirish
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    leaderboard_text = ""
    for idx, (u_name, u_pts, u_mar) in enumerate(top_users):
        name_clean = u_name or "O'quvchi"
        leaderboard_text += f"{medals[idx]} <b>{name_clean[:20]}</b> — <code>{u_pts or 0} ball</code> (Marafon: {u_mar or 0}/1242)\n"

    if not leaderboard_text:
        leaderboard_text = "<i>Hozircha reyting shakllanmoqda...</i>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Marafonni davom ettirish", callback_data="testcnt_marathon")],
        [InlineKeyboardButton(text="🎓 GAI Imtihonini topshirish", callback_data="testcnt_gai")],
        [InlineKeyboardButton(text=f"🔔 Kunlik Eslatma: {rem_time}", callback_data="menu_reminders")]
    ])

    text = (
        f"📊 <b>SIZNING SHAXSIY NATIJALARINGIZ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name}\n"
        f"🔥 <b>Kunlik Seriya (Streak):</b> <b>{streak} kun ketma-ket</b> 🔥\n"
        f"⭐️ <b>Umumiy ballar:</b> <code>{points} ball</code>\n"
        f"🎯 <b>1242 Marafon:</b> <b>{marathon_prog} / 1242 ta</b> ({marathon_pct}%)\n"
        f"📝 <b>Yechilgan testlar:</b> {tests_taken} ta\n"
        f"✅ <b>To'g'ri javoblar:</b> {correct_ans} ta | ❌ <b>Xatolar:</b> {wrong_ans} ta\n"
        f"📈 <b>Aniqlik darajasi:</b> <b>{accuracy}%</b>\n\n"
        f"🧠 <b>AI GAI IMTIHONIDAN O'TISH EHTIMOLI:</b>\n"
        f"{ai_status}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>TOP 10 ENG KUCHLI HAYDOVCHILAR:</b>\n\n"
        f"{leaderboard_text}\n"
        f"<i>Ko'proq test yeching va 1-o'ringa ko'tariling!</i>"
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ──────────────── KUNLIK ESLATMA SOATINI SOZLASH ────────────────
@menu_router.callback_query(F.data == "menu_reminders")
async def reminders_menu_callback(callback: types.CallbackQuery):
    async with async_session() as session:
        result_user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result_user.scalars().first()
        current_rem = user.reminder_time if user and user.reminder_time else "20:00"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌅 09:00", callback_data="setrem_09:00"),
            InlineKeyboardButton(text="☀️ 13:00", callback_data="setrem_13:00"),
            InlineKeyboardButton(text="🌆 18:00", callback_data="setrem_18:00")
        ],
        [
            InlineKeyboardButton(text="🌙 20:00 (Tavsiya)", callback_data="setrem_20:00"),
            InlineKeyboardButton(text="🌃 21:30", callback_data="setrem_21:30")
        ],
        [InlineKeyboardButton(text="🔕 Eslatmani o'chirish", callback_data="setrem_off")],
        [InlineKeyboardButton(text="🔙 Natijalarga qaytish", callback_data="close_profile")]
    ])

    status_str = "🔕 O'chirilgan" if current_rem == "off" else f"🔔 Har kuni <b>{current_rem}</b> da"
    text = (
        "🔔 <b>KUNLIK SHAXSIY ESLATMA SOATI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Darslarni kanda qilmaslik va kunlik olovli seriyangizni (Streak 🔥) saqlab qolish uchun o'zingizga qulay vaqtni tanlang.\n\n"
        f"📌 Hozirgi holat: {status_str}\n\n"
        "👇 <i>Qulay vaqtni belgilang:</i>"
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@menu_router.callback_query(F.data.startswith("setrem_"))
async def set_reminder_time_callback(callback: types.CallbackQuery):
    chosen_time = callback.data.split("_")[1]
    
    async with async_session() as session:
        result_user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result_user.scalars().first()
        if user:
            user.reminder_time = chosen_time
            await session.commit()

    if chosen_time == "off":
        await callback.answer("🔕 Kunlik eslatma o'chirildi.", show_alert=True)
    else:
        await callback.answer(f"✅ Eslatma soat {chosen_time} ga muvaffaqiyatli o'rnatildi!", show_alert=True)

    await reminders_menu_callback(callback)
