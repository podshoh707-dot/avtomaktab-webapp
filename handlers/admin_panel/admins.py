import json
from datetime import datetime
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from database import async_session, AdminUser, User
from config import ADMIN_IDS
from utils.permissions import is_superadmin

admins_router = Router()

PERM_NAMES = {
    "can_broadcast": "Xabar tarqatish",
    "can_manage_users": "Foydalanuvchilar",
    "can_manage_content": "Kontent (savol/video)",
    "can_manage_premium": "Premium tasdiqlash",
    "can_view_stats": "Statistika",
    "can_manage_groups": "Guruhlar",
}

class AdminMgmtStates(StatesGroup):
    waiting_for_admin_id = State()
    choosing_permissions = State()

async def get_admin_mgmt_menu_content():
    async with async_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.is_active == True)
        )
        db_admins = result.scalars().all()
    
    # We also have ADMIN_IDS which are superadmins
    text = "<b>👑 Adminlar boshqaruvi</b>\n━━━━━━━━━━━━━━\n"
    kb = []
    
    # Add superadmins from config
    for uid in ADMIN_IDS:
        text += f"• <code>{uid}</code> [🔴 Glavniy]\n"
    
    # Add db admins
    for adm in db_admins:
        uid = adm.telegram_id
        if uid in ADMIN_IDS:
            continue # already shown
            
        role = adm.role
        role_tag = "🔴 Glavniy" if role == 'superadmin' else "🔵 Yordamchi"
        text += f"• <code>{uid}</code> [{role_tag}]\n"
        
        if role != 'superadmin':
            perms = {}
            if adm.permissions:
                try:
                    perms = json.loads(adm.permissions)
                except Exception:
                    pass
                    
            active_perms = [PERM_NAMES.get(k, k) for k, v in perms.items() if v]
            if not active_perms:
                text += f"   └ 🔑 <i>Ruxsat yo'q</i>\n"
            else:
                translated_perms = ", ".join(active_perms)
                text += f"   └ 🔑 <i>{translated_perms}</i>\n"
                
            kb.append([
                InlineKeyboardButton(text=f"⚙️ Ruxsatlar", callback_data=f"adm_perms_{uid}"),
                InlineKeyboardButton(text=f"❌ O'chirish", callback_data=f"adm_remove_{uid}")
            ])
            
    kb.append([InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="adm_add_start")])
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_back_main")])
    
    return text, InlineKeyboardMarkup(inline_keyboard=kb)

@admins_router.callback_query(F.data == "adm_mgmt")
async def admin_mgmt_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_superadmin(callback.from_user.id):
        return await callback.answer("❌ Bu bo'limga faqat Glavniy admin kirishi mumkin!", show_alert=True)
    
    await callback.answer()
    text, markup = await get_admin_mgmt_menu_content()
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

def get_perms_kb(uid, current_perms_json):
    perms = {}
    if current_perms_json:
        try:
            perms = json.loads(current_perms_json)
        except Exception:
            pass
            
    kb = []
    row = []
    
    for k, name in PERM_NAMES.items():
        icon = "✅" if perms.get(k, False) else "❌"
        row.append(InlineKeyboardButton(text=f"{icon} {name}", callback_data=f"toggle_p_{uid}_{k}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    
    kb.append([InlineKeyboardButton(text="💾 Saqlash", callback_data=f"adm_perms_save_{uid}")])
    kb.append([InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="adm_mgmt")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@admins_router.callback_query(F.data.startswith("adm_perms_"))
async def adm_perms_edit(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id): return
    
    parts = callback.data.split("_")
    if parts[2] == 'save':
        await callback.answer("✅ Ruxsatlar saqlandi")
        return await admin_mgmt_menu(callback, state)
        
    uid = int(parts[2])
    
    async with async_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == uid)
        )
        adm = result.scalars().first()
        
    if not adm:
        return await callback.answer("Admin topilmadi")
        
    await callback.message.edit_text(f"🔑 <b>Admin ruxsatlarini sozlash:</b> <code>{uid}</code>", 
                                   reply_markup=get_perms_kb(uid, adm.permissions), parse_mode="HTML")

@admins_router.callback_query(F.data.startswith("toggle_p_"))
async def adm_perms_toggle(callback: types.CallbackQuery):
    if not is_superadmin(callback.from_user.id): return
    
    parts = callback.data.split("_")
    uid = int(parts[2])
    key = "_".join(parts[3:])
    
    async with async_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == uid)
        )
        adm = result.scalars().first()
        
        if adm:
            perms = {}
            if adm.permissions:
                try:
                    perms = json.loads(adm.permissions)
                except Exception:
                    pass
                    
            # Toggle boolean
            perms[key] = not perms.get(key, False)
            adm.permissions = json.dumps(perms)
            await session.commit()
            
            await callback.message.edit_reply_markup(reply_markup=get_perms_kb(uid, adm.permissions))

@admins_router.callback_query(F.data == "adm_add_start")
async def adm_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id): return
    await callback.answer()
    await state.set_state(AdminMgmtStates.waiting_for_admin_id)
    await callback.message.edit_text(
        "➕ <b>Yangi yordamchi admin qo'shish</b>\n\nFoydalanuvchining ID raqamini kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_mgmt")]])
    )

@admins_router.message(AdminMgmtStates.waiting_for_admin_id)
async def process_adm_add(message: types.Message, state: FSMContext):
    if not is_superadmin(message.from_user.id): return
    
    if not message.text.isdigit():
        return await message.answer("❌ Iltimos, faqat ID (raqam) kiriting!")
    
    new_uid = int(message.text)
    
    if new_uid in ADMIN_IDS:
        return await message.answer("❌ Bu asosiy admin (Glavniy)!")
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == new_uid)
        )
        user = result.scalars().first()
        
        if not user:
            return await message.answer("❌ Bu ID dagi foydalanuvchi bot bazasida topilmadi. Avval u botni boshlashi kerak.")
            
        # Check if already admin
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == new_uid)
        )
        adm = result.scalars().first()
        
        if adm:
            adm.is_active = True
            adm.role = 'moderator'
            adm.permissions = json.dumps({}) # Clear permissions
        else:
            new_admin = AdminUser(
                telegram_id=new_uid,
                full_name=user.full_name,
                role='moderator',
                permissions=json.dumps({}),
                added_by=message.from_user.id,
                is_active=True
            )
            session.add(new_admin)
            
        await session.commit()
    
    await message.answer(f"✅ Foydalanuvchi <code>{new_uid}</code> yordamchi admin qilib qo'shildi! Endi '⚙️ Ruxsatlar' tugmasi orqali huquqlarni belgilang.", parse_mode="HTML")
    await state.clear()
    
    # Show the menu again
    text, markup = await get_admin_mgmt_menu_content()
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

@admins_router.callback_query(F.data.startswith("adm_remove_"))
async def process_adm_remove(callback: types.CallbackQuery, state: FSMContext):
    if not is_superadmin(callback.from_user.id): return
    
    uid = int(callback.data.replace("adm_remove_", ""))
    
    async with async_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == uid)
        )
        adm = result.scalars().first()
        
        if adm:
            adm.is_active = False
            await session.commit()
            
    await callback.answer("✅ Admin olib tashlandi")
    await admin_mgmt_menu(callback, state)
