from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, delete
from database import async_session, VideoLesson, Rule, News, QAItem
from config import ADMIN_IDS

content_router = Router()



# ──────────────────────────────────────────────────────────
# FSM States
# ──────────────────────────────────────────────────────────
class VideoStates(StatesGroup):
    adding_topic   = State()
    adding_section = State()
    adding_url     = State()
    editing_field  = State()
    editing_value  = State()

class RuleStates(StatesGroup):
    adding_title  = State()
    adding_text   = State()
    adding_image  = State()
    editing_field = State()
    editing_value = State()

class NewsStates(StatesGroup):
    adding_title   = State()
    adding_content = State()
    adding_image   = State()
    adding_btn_txt = State()
    adding_btn_url = State()
    editing_field  = State()
    editing_value  = State()

class QAStates(StatesGroup):
    adding_question = State()
    adding_answer   = State()
    editing_field   = State()
    editing_value   = State()


# ──────────────────────────────────────────────────────────
# Helper: back keyboard
# ──────────────────────────────────────────────────────────
def back_kb(cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]
    ])


# ══════════════════════════════════════════════════════════
# 🎥 VIDEO DARSLAR — Admin
# ══════════════════════════════════════════════════════════
@content_router.callback_query(F.data.startswith("admin_videos"))
async def admin_videos_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    data_parts = callback.data.split("_")
    page = 1
    if len(data_parts) > 2:
        try:
            page = int(data_parts[2])
        except ValueError:
            page = 1

    per_page = 15
    offset = (page - 1) * per_page

    async with async_session() as session:
        from sqlalchemy import func
        total_result = await session.execute(select(func.count()).select_from(VideoLesson))
        total = total_result.scalar() or 0

        result = await session.execute(
            select(VideoLesson).order_by(VideoLesson.id.asc()).offset(offset).limit(per_page)
        )
        videos = result.scalars().all()

    buttons = []
    for v in videos:
        buttons.append([
            InlineKeyboardButton(text=f"🎥 #{v.id} {v.topic[:35]}", callback_data=f"vid_admin_{v.id}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_videos_{page-1}"))
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_videos_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi video qo'shish", callback_data="vid_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    start_num = offset + 1
    end_num = min(offset + per_page, total)

    await callback.message.edit_text(
        f"🎥 <b>VIDEO DARSLAR RO'YXATI</b> ({total} ta)\n"
        f"Ko'rsatilmoqda: <b>{start_num}-{end_num}</b>\n\n"
        f"Videoni tanlang yoki yangi qo'shing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("vid_admin_"))
async def admin_video_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    vid_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(VideoLesson).where(VideoLesson.id == vid_id))
        v = result.scalars().first()

    if not v:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Mavzuni o'zgartir", callback_data=f"vid_edit_{vid_id}_topic")],
        [InlineKeyboardButton(text="✏️ Bo'limni o'zgartir", callback_data=f"vid_edit_{vid_id}_section")],
        [InlineKeyboardButton(text="✏️ YouTube URLni o'zgartir", callback_data=f"vid_edit_{vid_id}_url")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"vid_del_{vid_id}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_videos")]
    ])
    await callback.message.edit_text(
        f"🎥 Video #{v.id}\n\n"
        f"📌 Mavzu: {v.topic}\n"
        f"📂 Bo'lim: {v.section or 'Yo\'q'}\n"
        f"🔗 URL: {v.youtube_url or 'Yo\'q'}\n"
        f"📱 Telegram: {v.telegram_video_id or 'Yo\'q'}",
        reply_markup=keyboard
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("vid_edit_"))
async def admin_video_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    vid_id = int(parts[2])
    field  = parts[3]

    field_names = {"topic": "Mavzu", "section": "Bo'lim", "url": "YouTube URL"}
    await state.update_data(vid_id=vid_id, field=field)
    await state.set_state(VideoStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\n"
        f"Bekor qilish uchun /cancel",
        reply_markup=back_kb(f"vid_admin_{vid_id}")
    )
    await callback.answer()


@content_router.message(VideoStates.editing_value)
async def admin_video_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    vid_id = data["vid_id"]
    field  = data["field"]
    value  = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(VideoLesson).where(VideoLesson.id == vid_id))
        v = result.scalars().first()
        if v:
            if field == "topic":
                v.topic = value
            elif field == "section":
                v.section = value
            elif field == "url":
                v.youtube_url = value
            await session.commit()

    await state.clear()
    await message.answer(f"✅ Video #{vid_id} muvaffaqiyatli yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")


@content_router.callback_query(F.data.startswith("vid_del_"))
async def admin_video_delete_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    vid_id = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"vid_delok_{vid_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"vid_admin_{vid_id}")
        ]
    ])
    await callback.message.edit_text(
        f"⚠️ Video #{vid_id}ni o'chirishni tasdiqlaysizmi?",
        reply_markup=keyboard
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("vid_delok_"))
async def admin_video_delete_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    vid_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(VideoLesson).where(VideoLesson.id == vid_id))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_videos_list(callback)


# Add new video
@content_router.callback_query(F.data == "vid_add")
async def admin_video_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(VideoStates.adding_topic)
    await callback.message.edit_text(
        "🎥 Yangi video qo'shish\n\n1️⃣ Mavzu nomini yozing (masalan: 1-dars: Yo'l belgilari):",
        reply_markup=back_kb("admin_videos")
    )
    await callback.answer()


@content_router.message(VideoStates.adding_topic)
async def admin_video_add_topic(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(topic=message.text.strip())
    await state.set_state(VideoStates.adding_section)
    await message.answer("2️⃣ Bo'lim nomini yozing (masalan: Yo'l belgilari):\n(Bo'lim yo'q bo'lsa 'Umumiy' yozing)")


@content_router.message(VideoStates.adding_section)
async def admin_video_add_section(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(section=message.text.strip())
    await state.set_state(VideoStates.adding_url)
    await message.answer("3️⃣ YouTube URL manzilini yozing:\n(YouTube yo'q bo'lsa 'yoq' deb yozing)")


@content_router.message(VideoStates.adding_url)
async def admin_video_add_url(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    url  = message.text.strip()
    if url.lower() == "yoq":
        url = None

    async with async_session() as session:
        v = VideoLesson(
            topic=data["topic"],
            section=data["section"],
            youtube_url=url
        )
        session.add(v)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Video muvaffaqiyatli qo'shildi!\n\n"
        f"📌 Mavzu: {data['topic']}\n"
        f"📂 Bo'lim: {data['section']}\n"
        f"🔗 URL: {url or 'Yo\'q'}\n\n"
        f"/admin orqali panelga qaytishingiz mumkin."
    )


# ══════════════════════════════════════════════════════════
# 📚 QOIDALAR — Admin
# ══════════════════════════════════════════════════════════
@content_router.callback_query(F.data.startswith("admin_rules"))
async def admin_rules_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    data_parts = callback.data.split("_")
    page = 1
    if len(data_parts) > 2:
        try:
            page = int(data_parts[2])
        except ValueError:
            page = 1

    per_page = 15
    offset = (page - 1) * per_page

    async with async_session() as session:
        from sqlalchemy import func
        total_result = await session.execute(select(func.count()).select_from(Rule))
        total = total_result.scalar() or 0

        result = await session.execute(
            select(Rule).order_by(Rule.id.asc()).offset(offset).limit(per_page)
        )
        rules = result.scalars().all()

    buttons = []
    for r in rules:
        buttons.append([
            InlineKeyboardButton(text=f"📖 #{r.id} {r.title[:40]}", callback_data=f"rule_admin_{r.id}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_rules_{page-1}"))
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_rules_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi qoida qo'shish", callback_data="rule_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    start_num = offset + 1
    end_num = min(offset + per_page, total)

    await callback.message.edit_text(
        f"📚 <b>YHQ QOIDALARI RO'YXATI</b> ({total} ta)\n"
        f"Ko'rsatilmoqda: <b>{start_num}-{end_num}</b>\n\n"
        f"Qoidani tanlang yoki yangi qo'shing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("rule_admin_"))
async def admin_rule_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    rid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Rule).where(Rule.id == rid))
        r = result.scalars().first()

    if not r:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Sarlavhani o'zgartir", callback_data=f"rule_edit_{rid}_title")],
        [InlineKeyboardButton(text="✏️ Matnni o'zgartir",    callback_data=f"rule_edit_{rid}_text")],
        [InlineKeyboardButton(text="✏️ Rasm URLni o'zgartir", callback_data=f"rule_edit_{rid}_image")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"rule_del_{rid}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_rules")]
    ])
    text = r.text or "Matn yo'q"
    if len(text) > 200:
        text = text[:200] + "..."
    await callback.message.edit_text(
        f"📖 Qoida #{r.id}\n\n"
        f"📌 Sarlavha: {r.title}\n\n"
        f"📄 Matn: {text}\n\n"
        f"🖼 Rasm: {r.image_url or 'Yo\'q'}",
        reply_markup=keyboard
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("rule_edit_"))
async def admin_rule_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts  = callback.data.split("_")
    rid    = int(parts[2])
    field  = parts[3]
    field_names = {"title": "Sarlavha", "text": "Matn", "image": "Rasm URL"}
    await state.update_data(rid=rid, field=field)
    await state.set_state(RuleStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"rule_admin_{rid}")
    )
    await callback.answer()


@content_router.message(RuleStates.editing_value)
async def admin_rule_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data  = await state.get_data()
    rid   = data["rid"]
    field = data["field"]
    value = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(Rule).where(Rule.id == rid))
        r = result.scalars().first()
        if r:
            if field == "title":
                r.title = value
            elif field == "text":
                r.text = value
            elif field == "image":
                r.image_url = value if value.startswith("http") else None
            await session.commit()

    await state.clear()
    await message.answer(f"✅ Qoida #{rid} yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")


@content_router.callback_query(F.data.startswith("rule_del_"))
async def admin_rule_delete_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    rid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"rule_delok_{rid}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data=f"rule_admin_{rid}")
    ]])
    await callback.message.edit_text(f"⚠️ Qoida #{rid}ni o'chirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()


@content_router.callback_query(F.data.startswith("rule_delok_"))
async def admin_rule_delete_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    rid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(Rule).where(Rule.id == rid))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_rules_list(callback)


@content_router.callback_query(F.data == "rule_add")
async def admin_rule_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(RuleStates.adding_title)
    await callback.message.edit_text(
        "📚 Yangi qoida qo'shish\n\n1️⃣ Sarlavhani yozing:",
        reply_markup=back_kb("admin_rules")
    )
    await callback.answer()


@content_router.message(RuleStates.adding_title)
async def admin_rule_add_title(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(RuleStates.adding_text)
    await message.answer("2️⃣ Qoida matnini yozing:\n(Matn yo'q bo'lsa 'yoq' deb yozing)")


@content_router.message(RuleStates.adding_text)
async def admin_rule_add_text(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    txt = message.text.strip()
    await state.update_data(text=None if txt.lower() == "yoq" else txt)
    await state.set_state(RuleStates.adding_image)
    await message.answer("3️⃣ Rasm URL manzilini yozing:\n(Rasm yo'q bo'lsa 'yoq' deb yozing)")


@content_router.message(RuleStates.adding_image)
async def admin_rule_add_image(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    img  = message.text.strip()
    img  = img if img.startswith("http") else None

    async with async_session() as session:
        r = Rule(title=data["title"], text=data.get("text"), image_url=img)
        session.add(r)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Qoida qo'shildi!\n📌 {data['title']}\n\n/admin orqali panelga qaytishingiz mumkin.")


# ══════════════════════════════════════════════════════════
# 📰 YANGILIKLAR — Admin
# ══════════════════════════════════════════════════════════
@content_router.callback_query(F.data == "admin_news")
async def admin_news_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    async with async_session() as session:
        result = await session.execute(select(News).order_by(News.id.desc()))
        news_list = result.scalars().all()

    buttons = []
    for n in news_list:
        buttons.append([
            InlineKeyboardButton(text=f"📰 #{n.id} {n.title[:40]}", callback_data=f"news_admin_{n.id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Yangi yangili qo'shish", callback_data="news_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    await callback.message.edit_text(
        f"📰 YANGILIKLAR ({len(news_list)} ta)\n\nYangilikni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("news_admin_"))
async def admin_news_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    nid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(News).where(News.id == nid))
        n = result.scalars().first()

    if not n:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Sarlavhani o'zgartir", callback_data=f"news_edit_{nid}_title")],
        [InlineKeyboardButton(text="✏️ Matnni o'zgartir",    callback_data=f"news_edit_{nid}_content")],
        [InlineKeyboardButton(text="✏️ Rasm URLni o'zgartir", callback_data=f"news_edit_{nid}_image")],
        [InlineKeyboardButton(text="✏️ Tugma matnini o'zgartir", callback_data=f"news_edit_{nid}_btntxt")],
        [InlineKeyboardButton(text="✏️ Tugma URLni o'zgartir",  callback_data=f"news_edit_{nid}_btnurl")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"news_del_{nid}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_news")]
    ])
    content_short = (n.content[:150] + "...") if len(n.content) > 150 else n.content
    await callback.message.edit_text(
        f"📰 Yangili #{n.id}\n\n"
        f"📌 Sarlavha: {n.title}\n\n"
        f"📄 Matn: {content_short}\n\n"
        f"🖼 Rasm: {n.image_url or 'Yo\'q'}\n"
        f"🔗 Tugma: {n.button_text or 'Yo\'q'} → {n.button_url or 'Yo\'q'}",
        reply_markup=keyboard
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("news_edit_"))
async def admin_news_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    nid   = int(parts[2])
    field = parts[3]
    field_names = {
        "title": "Sarlavha", "content": "Matn", "image": "Rasm URL",
        "btntxt": "Tugma matni", "btnurl": "Tugma URL"
    }
    await state.update_data(nid=nid, field=field)
    await state.set_state(NewsStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"news_admin_{nid}")
    )
    await callback.answer()


@content_router.message(NewsStates.editing_value)
async def admin_news_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data  = await state.get_data()
    nid   = data["nid"]
    field = data["field"]
    value = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(News).where(News.id == nid))
        n = result.scalars().first()
        if n:
            if field == "title":
                n.title = value
            elif field == "content":
                n.content = value
            elif field == "image":
                n.image_url = value if value.startswith("http") else None
            elif field == "btntxt":
                n.button_text = value
            elif field == "btnurl":
                n.button_url = value if value.startswith("http") else None
            await session.commit()

    await state.clear()
    await message.answer(f"✅ Yangili #{nid} yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")


@content_router.callback_query(F.data.startswith("news_del_"))
async def admin_news_delete_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    nid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"news_delok_{nid}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data=f"news_admin_{nid}")
    ]])
    await callback.message.edit_text(f"⚠️ Yangili #{nid}ni o'chirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()


@content_router.callback_query(F.data.startswith("news_delok_"))
async def admin_news_delete_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    nid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(News).where(News.id == nid))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_news_list(callback)


@content_router.callback_query(F.data == "news_add")
async def admin_news_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(NewsStates.adding_title)
    await callback.message.edit_text(
        "📰 Yangi yangili qo'shish\n\n1️⃣ Sarlavhani yozing:",
        reply_markup=back_kb("admin_news")
    )
    await callback.answer()


@content_router.message(NewsStates.adding_title)
async def admin_news_add_title(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(NewsStates.adding_content)
    await message.answer("2️⃣ Yangili matnini yozing:")


@content_router.message(NewsStates.adding_content)
async def admin_news_add_content(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(content=message.text.strip())
    await state.set_state(NewsStates.adding_image)
    await message.answer("3️⃣ Rasm URL manzilini yozing:\n(Rasm yo'q bo'lsa 'yoq' deb yozing)")


@content_router.message(NewsStates.adding_image)
async def admin_news_add_image(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    img = message.text.strip()
    await state.update_data(image_url=img if img.startswith("http") else None)
    await state.set_state(NewsStates.adding_btn_txt)
    await message.answer("4️⃣ Tugma matnini yozing:\n(Tugma yo'q bo'lsa 'yoq' deb yozing)")


@content_router.message(NewsStates.adding_btn_txt)
async def admin_news_add_btn_txt(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    txt = message.text.strip()
    await state.update_data(button_text=None if txt.lower() == "yoq" else txt)
    await state.set_state(NewsStates.adding_btn_url)
    await message.answer("5️⃣ Tugma URL manzilini yozing:\n(Tugma yo'q bo'lsa 'yoq' deb yozing)")


@content_router.message(NewsStates.adding_btn_url)
async def admin_news_add_btn_url(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    url  = message.text.strip()

    async with async_session() as session:
        n = News(
            title=data["title"],
            content=data["content"],
            image_url=data.get("image_url"),
            button_text=data.get("button_text"),
            button_url=url if url.startswith("http") else None
        )
        session.add(n)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Yangili qo'shildi!\n📌 {data['title']}\n\n/admin orqali panelga qaytishingiz mumkin.")


# ══════════════════════════════════════════════════════════
# 💬 SAVOL-JAVOB — Admin
# ══════════════════════════════════════════════════════════
@content_router.callback_query(F.data == "admin_qa")
async def admin_qa_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    async with async_session() as session:
        result = await session.execute(select(QAItem).order_by(QAItem.id.desc()))
        qa_list = result.scalars().all()

    buttons = []
    for qa in qa_list:
        buttons.append([
            InlineKeyboardButton(text=f"❓ #{qa.id} {qa.question[:40]}", callback_data=f"qa_admin_{qa.id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Yangi savol qo'shish", callback_data="qa_add"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    await callback.message.edit_text(
        f"💬 SAVOL-JAVOB ({len(qa_list)} ta)\n\nSavolni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("qa_admin_"))
async def admin_qa_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(QAItem).where(QAItem.id == qid))
        qa = result.scalars().first()

    if not qa:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Savolni o'zgartir", callback_data=f"qa_edit_{qid}_question")],
        [InlineKeyboardButton(text="✏️ Javobni o'zgartir", callback_data=f"qa_edit_{qid}_answer")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"qa_del_{qid}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_qa")]
    ])
    ans_short = (qa.answer[:200] + "...") if len(qa.answer) > 200 else qa.answer
    await callback.message.edit_text(
        f"💬 Savol #{qa.id}\n\n"
        f"❓ Savol: {qa.question}\n\n"
        f"✅ Javob: {ans_short}",
        reply_markup=keyboard
    )
    await callback.answer()


@content_router.callback_query(F.data.startswith("qa_edit_"))
async def admin_qa_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    qid   = int(parts[2])
    field = parts[3]
    field_names = {"question": "Savol", "answer": "Javob"}
    await state.update_data(qid=qid, field=field)
    await state.set_state(QAStates.editing_value)
    await callback.message.edit_text(
        f"✏️ {field_names.get(field, field)} uchun yangi qiymatni yozing:\n\nBekor qilish: /cancel",
        reply_markup=back_kb(f"qa_admin_{qid}")
    )
    await callback.answer()


@content_router.message(QAStates.editing_value)
async def admin_qa_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data  = await state.get_data()
    qid   = data["qid"]
    field = data["field"]
    value = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(QAItem).where(QAItem.id == qid))
        qa = result.scalars().first()
        if qa:
            if field == "question":
                qa.question = value
            elif field == "answer":
                qa.answer = value
            await session.commit()

    await state.clear()
    await message.answer(f"✅ Savol #{qid} yangilandi!\n\n/admin orqali panelga qaytishingiz mumkin.")


@content_router.callback_query(F.data.startswith("qa_del_"))
async def admin_qa_delete_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    qid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"qa_delok_{qid}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data=f"qa_admin_{qid}")
    ]])
    await callback.message.edit_text(f"⚠️ Savol #{qid}ni o'chirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()


@content_router.callback_query(F.data.startswith("qa_delok_"))
async def admin_qa_delete_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(QAItem).where(QAItem.id == qid))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_qa_list(callback)


@content_router.callback_query(F.data == "qa_add")
async def admin_qa_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(QAStates.adding_question)
    await callback.message.edit_text(
        "💬 Yangi savol qo'shish\n\n1️⃣ Savolni yozing:",
        reply_markup=back_kb("admin_qa")
    )
    await callback.answer()


@content_router.message(QAStates.adding_question)
async def admin_qa_add_question(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    await state.update_data(question=message.text.strip())
    await state.set_state(QAStates.adding_answer)
    await message.answer("2️⃣ Javobni yozing:")


@content_router.message(QAStates.adding_answer)
async def admin_qa_add_answer(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    data = await state.get_data()
    async with async_session() as session:
        qa = QAItem(question=data["question"], answer=message.text.strip())
        session.add(qa)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Savol-javob qo'shildi!\n❓ {data['question']}\n\n/admin orqali panelga qaytishingiz mumkin.")


# ══════════════════════════════════════════════════════════
# /cancel — FSM ni tozalash
# ══════════════════════════════════════════════════════════
from aiogram.filters import Command

@content_router.message(Command("cancel"))
async def cancel_all(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await state.clear()
        await message.answer("❌ Jarayon bekor qilindi.\n\n/admin orqali panelga qaytishingiz mumkin.")

# ----------------------------------------------------------
# Tashkilot ma'lumotlari
# ----------------------------------------------------------

class OrgStates(StatesGroup):
    editing_text = State()
    editing_image = State()

@content_router.callback_query(F.data == "admin_org_edit")
async def org_edit_menu(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.fromuser.id if hasattr(callback, 'fromuser') else callback.from_user.id, "can_manage_content"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    await state.clear()
    
    from database import Setting
    async with async_session() as session:
        result_text = await session.execute(select(Setting).where(Setting.key == "org_text"))
        org_text = result_text.scalars().first()
        
        result_img = await session.execute(select(Setting).where(Setting.key == "org_image"))
        org_img = result_img.scalars().first()
        
    status_text = "Bor" if org_text else "Yo'q"
    status_img = "Bor" if org_img else "Yo'q"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"?? Matnni o'zgartirish ({status_text})", callback_data="admin_org_set_text")],
        [InlineKeyboardButton(text=f"?? Rasmni o'zgartirish ({status_img})", callback_data="admin_org_set_image")],
        [InlineKeyboardButton(text="?? Orqaga", callback_data="admin_back_main")]
    ])
    
    await callback.message.edit_text("?? <b>Tashkilot ma'lumotlarini boshqarish</b>", reply_markup=keyboard, parse_mode="HTML")


@content_router.callback_query(F.data == "admin_org_set_text")
async def ask_org_text(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("?? <b>Tashkilot haqida matnni yuboring (HTML format qo'llab-quvvatlanadi):</b>", parse_mode="HTML")
    await state.set_state(OrgStates.editing_text)

@content_router.message(OrgStates.editing_text)
async def save_org_text(message: types.Message, state: FSMContext):
    text_val = message.html_text if message.html_text else message.text
    from database import Setting
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_text"))
        setting = result.scalars().first()
        if setting:
            setting.value = text_val
        else:
            session.add(Setting(key="org_text", value=text_val))
        await session.commit()
        
    await message.answer("? Tashkilot matni saqlandi!")
    await state.clear()

@content_router.callback_query(F.data == "admin_org_set_image")
async def ask_org_image(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("?? <b>Tashkilot rasmini (Photo) yuboring:</b>", parse_mode="HTML")
    await state.set_state(OrgStates.editing_image)

@content_router.message(OrgStates.editing_image, F.photo)
async def save_org_image(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    from database import Setting
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_image"))
        setting = result.scalars().first()
        if setting:
            setting.value = photo_id
        else:
            session.add(Setting(key="org_image", value=photo_id))
        await session.commit()
        
    await message.answer("? Tashkilot rasmi saqlandi!")
    await state.clear()

