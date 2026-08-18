from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User
from sqlalchemy import select, update
from config import ADMIN_IDS

rating_router = Router()



@rating_router.callback_query(F.data == "admin_rating")
async def admin_rating_menu(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_users"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.points.desc()).limit(10))
        top_users = result.scalars().all()

    text = "🏆 REYTING TIZIMI (Top 10)\n\n"
    if not top_users:
        text += "Hozircha hech kim yo'q."
    else:
        for i, u in enumerate(top_users, 1):
            name = u.full_name or "Nomsiz"
            text += f"{i}. {name} - {u.points} ball\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Barcha ballarni tozalash", callback_data="admin_rating_reset")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@rating_router.callback_query(F.data == "admin_rating_reset")
async def admin_rating_reset_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_users"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, tozalash", callback_data="admin_rating_reset_ok")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_rating")]
    ])
    await callback.message.edit_text("⚠️ Barcha foydalanuvchilarning ballarini (reytingini) 0 ga tushirishni tasdiqlaysizmi?", reply_markup=keyboard)
    await callback.answer()

@rating_router.callback_query(F.data == "admin_rating_reset_ok")
async def admin_rating_reset_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_users"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    async with async_session() as session:
        await session.execute(update(User).values(points=0))
        await session.commit()

    await callback.answer("✅ Barcha ballar tozalandi!", show_alert=True)
    await admin_rating_menu(callback)
