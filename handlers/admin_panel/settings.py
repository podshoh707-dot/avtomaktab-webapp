from aiogram import Router, types, F
from utils.permissions import check_permission, is_superadmin
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User, Setting
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from config import ADMIN_IDS

settings_router = Router()

class PremiumStates(StatesGroup):
    waiting_for_card = State()
    waiting_for_user_id = State()
    waiting_for_tariff_price = State()
    waiting_for_tariff_text = State()



@settings_router.callback_query(F.data == "admin_premium")
async def admin_premium(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
        setting = result.scalars().first()
        is_on = setting.value == "1" if setting else False
        status_text = "🟢 Yoqilgan" if is_on else "🔴 O'chirilgan"
        
        result_card = await session.execute(select(Setting).where(Setting.key == "admin_card"))
        card_setting = result_card.scalars().first()
        card_num = card_setting.value if card_setting else "O'rnatilmagan"
        
        result_price = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        price_setting = result_price.scalars().first()
        tariff_price = price_setting.value if price_setting else "O'rnatilmagan"
        
        result_text = await session.execute(select(Setting).where(Setting.key == "tariff_text"))
        text_setting = result_text.scalars().first()
        tariff_text = text_setting.value if text_setting else "O'rnatilmagan"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Premium reja: {status_text}", callback_data="admin_toggle_premium")],
        [
            InlineKeyboardButton(text="🎟 +5 ta Promokod Yaratish", callback_data="admin_gen_promos"),
            InlineKeyboardButton(text="📋 Barcha Promokodlar", callback_data="admin_list_promos")
        ],
        [
            InlineKeyboardButton(text="💳 Karta raqami", callback_data="admin_set_card"),
            InlineKeyboardButton(text="💵 Tarif narxi", callback_data="admin_set_price")
        ],
        [InlineKeyboardButton(text="🧾 Kutilayotgan To'lov Cheklari", callback_data="admin_pending_payments")],
        [InlineKeyboardButton(text="🎁 Foydalanuvchiga VIP berish", callback_data="admin_give_premium")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]
    ])
    
    await callback.message.edit_text(
        f"💰 <b>PREMIUM VA TO'LOVLAR BOSHQARUVI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>Karta raqami:</b> <code>{card_num}</code>\n"
        f"💵 <b>Tarif narxi:</b> <code>{tariff_price}</code>\n"
        f"📝 <b>Tarif tavsifi:</b>\n<i>{tariff_text}</i>\n\n"
        f"👇 <i>Kerakli amalni tanlang:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@settings_router.callback_query(F.data == "admin_toggle_premium")
async def toggle_premium(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
        setting = result.scalars().first()
        
        if not setting:
            setting = Setting(key="premium_mode", value="1")
            session.add(setting)
        else:
            setting.value = "0" if setting.value == "1" else "1"
        
        await session.commit()
    
    await admin_premium(callback)

@settings_router.callback_query(F.data == "admin_set_card")
async def set_card_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
        
    await callback.message.edit_text("Yangi karta raqamini yozib yuboring (Masalan: 8600 1234 5678 9012):")
    await state.set_state(PremiumStates.waiting_for_card)

@settings_router.message(PremiumStates.waiting_for_card)
async def set_card_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
        
    new_card = message.text
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "admin_card"))
        setting = result.scalars().first()
        
        if not setting:
            setting = Setting(key="admin_card", value=new_card)
            session.add(setting)
        else:
            setting.value = new_card
            
        await session.commit()
        
    await state.clear()
    await message.answer(f"✅ Karta raqami muvaffaqiyatli saqlandi: {new_card}\n/admin orqali panelga qaytishingiz mumkin.")

@settings_router.callback_query(F.data == "admin_give_premium")
async def give_premium_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("Premium berish kerak bo'lgan foydalanuvchining Telegram ID sini yozing:")
    await state.set_state(PremiumStates.waiting_for_user_id)

@settings_router.message(PremiumStates.waiting_for_user_id)
async def give_premium_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    try:
        target_id = int(message.text)
    except ValueError:
        await message.answer("Faqat raqam kiriting.")
        return
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == target_id))
        user = result.scalars().first()
        if not user:
            await message.answer("Bu ID ga ega foydalanuvchi topilmadi.")
            return
        user.is_premium = True
        user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ {target_id} ID egasiga 30 kunlik Premium taqdim etildi.\n/admin orqali panelga qaytishingiz mumkin.")

@settings_router.callback_query(F.data == "admin_set_price")
async def set_price_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("1 oylik Premium tarif narxini yozing (Masalan: 15 000 so'm):")
    await state.set_state(PremiumStates.waiting_for_tariff_price)

@settings_router.message(PremiumStates.waiting_for_tariff_price)
async def set_price_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    new_price = message.text
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="tariff_price", value=new_price)
            session.add(setting)
        else:
            setting.value = new_price
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Tarif narxi saqlandi: {new_price}\n/admin orqali panelga qaytishingiz mumkin.")

@settings_router.callback_query(F.data == "admin_set_text")
async def set_text_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("Tarif haqida to'liq matnni yozing (afzalliklari va shartlari):")
    await state.set_state(PremiumStates.waiting_for_tariff_text)

@settings_router.message(PremiumStates.waiting_for_tariff_text)
async def set_text_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    new_text = message.text
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "tariff_text"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="tariff_text", value=new_text)
            session.add(setting)
        else:
            setting.value = new_text
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Tarif matni saqlandi.\n/admin orqali panelga qaytishingiz mumkin.")

class OrgStates(StatesGroup):
    waiting_for_org_text = State()

@settings_router.callback_query(F.data == "admin_org_edit")
async def org_edit_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
        current_text = "Hali kiritilmagan."
        if setting:
            import json
            try:
                data = json.loads(setting.value)
                current_text = data.get("text", "")
            except:
                current_text = setting.value
        
    await callback.message.edit_text(
        f"🏢 Tashkilot haqida ma'lumot:\n\n{current_text[:800]}\n\nYangi ma'lumotni yuboring (Rasm va matnni birga yuborishingiz ham mumkin):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]])
    )
    await state.set_state(OrgStates.waiting_for_org_text)

@settings_router.message(OrgStates.waiting_for_org_text)
async def org_edit_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
        
    text = message.html_text or message.text or ""
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
        
    import json
    val = json.dumps({"text": text, "photo_id": photo_id}, ensure_ascii=False)
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="org_info", value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()
        
    await state.clear()
    await message.answer("✅ Tashkilot ma'lumotlari saqlandi.\n/admin orqali panelga qaytishingiz mumkin.")


# ──────────────── PROMO KOD GENERATORI ────────────────
@settings_router.callback_query(F.data == "admin_gen_promos")
async def generate_promocodes_handler(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    import secrets
    from database import PromoCode
    
    generated = []
    async with async_session() as session:
        for _ in range(5):
            code = f"VIP-{secrets.token_hex(3).upper()}"
            promo = PromoCode(code=code, days_granted=30, is_active=True)
            session.add(promo)
            generated.append(code)
        await session.commit()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yana +5 ta yaratish", callback_data="admin_gen_promos")],
        [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
    ])
    
    list_str = "\n".join([f"<code>{c}</code> (30 kunlik VIP)" for c in generated])
    msg_text = (
        "🎟 <b>5 TA YANGI VIP PROMOKOD YARATILDI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{list_str}\n\n"
        "<i>(Promokodni nusxalash uchun ustiga bosing va o'quvchilarga yoki kanalga ulashing)</i>"
    )
    await callback.message.edit_text(msg_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("✅ 5 ta yangi promokod yaratildi!")


# ──────────────── BARCHA PROMOKODLAR RO'YXATI ────────────────
@settings_router.callback_query(F.data == "admin_list_promos")
async def list_promocodes_handler(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    from database import PromoCode
    async with async_session() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.is_active == True).order_by(PromoCode.id.desc()).limit(20)
        )
        promos = result.scalars().all()
        
    if not promos:
        text = "📋 <b>Ayni damda faol promokodlar yo'q.</b>\n\nQuyidagi tugma orqali yangi promokodlar yaratishingiz mumkin:"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎟 +5 ta Promokod Yaratish", callback_data="admin_gen_promos")],
            [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
        ])
    else:
        promo_lines = []
        for i, p in enumerate(promos, 1):
            promo_lines.append(f"{i}. <code>{p.code}</code> — {p.days_granted} kunlik VIP")
            
        text = (
            f"📋 <b>FAOL PROMOKODLAR (Jami: {len(promos)} ta):</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(promo_lines)
            + "\n\n<i>(Nusxalash uchun promokod ustiga bosing)</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎟 +5 ta Yangi Yaratish", callback_data="admin_gen_promos")],
            [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
        ])
        
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ──────────────── KUTILAYOTGAN TO'LOV CHEKLARI ────────────────
@settings_router.callback_query(F.data == "admin_pending_payments")
async def pending_payments_handler(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    from database import Payment, User
    async with async_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.status == "pending").order_by(Payment.id.desc()).limit(10)
        )
        pending_list = result.scalars().all()
        
    if not pending_list:
        text = "🧾 <b>Ayni damda kutilayotgan to'lov cheklari yo'q.</b>\n\nBarcha to'lovlar ko'rib chiqilgan! ✅"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_pending_payments")],
            [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    text = f"🧾 <b>KUTILAYOTGAN TO'LOVLAR (Jami: {len(pending_list)} ta):</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for p in pending_list:
        dt_str = p.created_at.strftime("%d.%m %H:%M") if p.created_at else ""
        text += (
            f"📌 <b>ID: #{p.id}</b> | User ID: <code>{p.user_id}</code>\n"
            f"💵 Summa: <b>{p.amount}</b> | Sana: {dt_str}\n"
            f"───────────────────\n"
        )
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{p.id} Tasdiqlash", callback_data=f"pay_appr_{p.id}"),
            InlineKeyboardButton(text=f"❌ Rad etish", callback_data=f"pay_rejc_{p.id}")
        ])
        
    buttons.append([InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
