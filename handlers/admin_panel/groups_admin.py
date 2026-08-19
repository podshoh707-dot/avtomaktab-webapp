from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, BotGroup
from sqlalchemy import select, delete
from config import ADMIN_IDS

groups_admin_router = Router()



def back_kb(cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]
    ])

@groups_admin_router.callback_query(F.data.startswith("admin_groups"))
async def admin_groups_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_groups"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    data_parts = callback.data.split("_")
    page = 1
    if len(data_parts) > 2:
        try:
            page = int(data_parts[2])
        except ValueError:
            page = 1

    per_page = 20
    offset = (page - 1) * per_page

    async with async_session() as session:
        from sqlalchemy import func
        total_result = await session.execute(select(func.count()).select_from(BotGroup))
        total = total_result.scalar()

        result = await session.execute(
            select(BotGroup).order_by(BotGroup.id.asc()).offset(offset).limit(per_page)
        )
        groups = result.scalars().all()

    buttons = []
    for g in groups:
        title = g.title or str(g.chat_id)
        status = "✅" if g.is_active else "❌"
        buttons.append([
            InlineKeyboardButton(text=f"{status} {title[:35]}", callback_data=f"group_detail_{g.id}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_groups_{page-1}"))
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_groups_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="📢 Majburiy Obuna Kanallari", callback_data="admin_channels_menu"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")
    ])

    start_num = offset + 1
    end_num = min(offset + per_page, total)

    await callback.message.edit_text(
        f"👥 GURUHLAR ({total} ta)\nKo'rsatilmoqda: {start_num}-{end_num}\n\nGuruhni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@groups_admin_router.callback_query(F.data.startswith("group_detail_"))
async def admin_group_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_groups"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    gid = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        result = await session.execute(select(BotGroup).where(BotGroup.id == gid))
        g = result.scalars().first()

    if not g:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    def b(val): return "✅ Yoqilgan" if val else "❌ O'chirilgan"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Faollik: {b(g.is_active)}", callback_data=f"g_toggle_{gid}_active")],
        [InlineKeyboardButton(text=f"Antispam: {b(g.antispam_enabled)}", callback_data=f"g_toggle_{gid}_antispam")],
        [InlineKeyboardButton(text=f"Linklarni taqiqlash: {b(g.block_links)}", callback_data=f"g_toggle_{gid}_links")],
        [InlineKeyboardButton(text=f"Floodni taqiqlash: {b(g.block_flood)}", callback_data=f"g_toggle_{gid}_flood")],
        [InlineKeyboardButton(text=f"So'kinishni taqiqlash: {b(g.block_curse)}", callback_data=f"g_toggle_{gid}_curse")],
        [InlineKeyboardButton(text="🗑 O'chirish (bazadan)", callback_data=f"g_del_{gid}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_groups")]
    ])

    text = (
        f"👥 Guruh: {g.title or 'Nomsiz'}\n"
        f"🆔 Chat ID: {g.chat_id}\n\n"
        f"Quyidagi sozlamalarni o'zgartirish uchun tugmalarni bosing:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@groups_admin_router.callback_query(F.data.startswith("g_toggle_"))
async def admin_group_toggle(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_groups"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    gid = int(parts[2])
    setting = parts[3]

    async with async_session() as session:
        result = await session.execute(select(BotGroup).where(BotGroup.id == gid))
        g = result.scalars().first()
        if g:
            if setting == "active":
                g.is_active = not g.is_active
            elif setting == "antispam":
                g.antispam_enabled = not g.antispam_enabled
            elif setting == "links":
                g.block_links = not g.block_links
            elif setting == "flood":
                g.block_flood = not g.block_flood
            elif setting == "curse":
                g.block_curse = not g.block_curse
            await session.commit()
    
    await admin_group_detail(callback)

@groups_admin_router.callback_query(F.data.startswith("g_del_"))
async def admin_group_del_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_groups"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    gid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"g_delok_{gid}"),
         InlineKeyboardButton(text="❌ Bekor", callback_data=f"group_detail_{gid}")]
    ])
    await callback.message.edit_text("⚠️ Ushbu guruhni bazadan o'chirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()

@groups_admin_router.callback_query(F.data.startswith("g_delok_"))
async def admin_group_del_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_groups"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    gid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(BotGroup).where(BotGroup.id == gid))
        await session.commit()
    await callback.answer("🗑 O'chirildi!", show_alert=True)
    await admin_groups_list(callback)
