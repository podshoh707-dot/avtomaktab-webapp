from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User, Question, Setting
from sqlalchemy import select
from sqlalchemy.sql.expression import func
import asyncio
import uuid
import time
import os
from aiogram.types import FSInputFile
from config import BASE_DIR

duel_router = Router()

WAITING_PLAYER = None
ACTIVE_DUELS = {}

@duel_router.message(F.text == "⚔️ Battle (Duel Rejimi)")
async def duel_menu(message: types.Message):
    global WAITING_PLAYER
    user_id = message.from_user.id

    if WAITING_PLAYER and WAITING_PLAYER['id'] != user_id:
        # Raqib topildi — zudlik bilan jang boshlash
        opponent = WAITING_PLAYER
        WAITING_PLAYER = None
        await _start_duel_between(message.bot, user_id, message.from_user.full_name,
                                  opponent['id'], opponent['name'])
    else:
        WAITING_PLAYER = {'id': user_id, 'name': message.from_user.full_name}

        bot_info = await message.bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start=duel_{user_id}"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔗 Do'stga Chaqiruv Yuborish",
                url=f"https://t.me/share/url?url={invite_link}&text=⚔️%20Meni%20Avtotest%20Duelida%20yengib%20ko'r!%20Avtomaktab%20botda%20jangga%20chaq"
            )],
            [InlineKeyboardButton(text="🔄 Raqib kutilmoqda...", callback_data="duel_cancel")]
        ])

        await message.answer(
            f"⚔️ <b>DUEL JANG REJIMI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Siz endi navbatda turibsiz.\n"
            f"Boshqa o'yinchi \"⚔️ Battle\" tugmasini bosishi bilan <b>avtomatik</b> jang boshlanadi.\n\n"
            f"📨 <b>Yoki do'stingizni to'g'ridan-to'g'ri chaqirish uchun:</b>\n"
            f"Quyidagi tugmani bosib chaqiruv yuboring:\n\n"
            f"<code>{invite_link}</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )


@duel_router.callback_query(F.data == "duel_cancel")
async def duel_cancel(callback: types.CallbackQuery):
    global WAITING_PLAYER
    if WAITING_PLAYER and WAITING_PLAYER['id'] == callback.from_user.id:
        WAITING_PLAYER = None
    await callback.message.edit_text("🚫 Jang bekor qilindi. Qaytadan urinish uchun «⚔️ Battle» tugmasini bosing.")
    await callback.answer()


async def handle_duel_invite(bot, inviter_id: int, challenger_id: int, challenger_name: str):
    """Deep link orqali kelgan o'yinchini tayyor bo'lgan inviter bilan jangga qo'shadi."""
    global WAITING_PLAYER

    # Inviter hali kutayotganmi?
    if WAITING_PLAYER and WAITING_PLAYER['id'] == inviter_id:
        opponent = WAITING_PLAYER
        WAITING_PLAYER = None
        await _start_duel_between(bot, challenger_id, challenger_name, opponent['id'], opponent['name'])
    else:
        # Inviter bo'sh — challengers navbatga qo'shiladi yoki xabar yuboriladi
        await bot.send_message(
            challenger_id,
            f"⚔️ Chaqiruv qabul qilindi!\n"
            f"Raqibingiz hali duel oynasida emas.\n\n"
            f"Siz endi navbatda turibsiz — "
            f"raqibingiz «⚔️ Battle» tugmasini bosganda jang boshlanadi.",
            parse_mode="HTML"
        )
        WAITING_PLAYER = {'id': challenger_id, 'name': challenger_name}
        try:
            await bot.send_message(
                inviter_id,
                f"📬 <b>{challenger_name}</b> sizning duel chaqiruvingizni qabul qildi!\n"
                f"Jangni boshlash uchun «⚔️ Battle» tugmasini bosing.",
                parse_mode="HTML"
            )
        except Exception:
            pass


async def _start_duel_between(bot, p1_id, p1_name, p2_id, p2_name):
    """Ikki o'yinchi o'rtasida duel boshlash."""
    duel_id = str(uuid.uuid4())

    async with async_session() as session:
        result = await session.execute(
            select(Question)
            .where(Question.option_b != None, Question.option_b != "")
            .order_by(func.random())
            .limit(10)
        )
        questions = result.scalars().all()

        result_set = await session.execute(select(Setting).where(Setting.key == "protect_content"))
        protect_setting = result_set.scalars().first()
        protect = protect_setting and protect_setting.value == "1"

    if len(questions) < 10:
        for uid in [p1_id, p2_id]:
            try:
                await bot.send_message(uid, "❌ Bazada yetarli savollar yo'q.")
            except Exception:
                pass
        return

    ACTIVE_DUELS[duel_id] = {
        "start_time": time.time(),
        "questions": questions,
        "protect": protect,
        "bot": bot,
        "p1": {"id": p1_id, "name": p1_name, "score": 0, "idx": 0, "finished": False, "finish_time": 150.0},
        "p2": {"id": p2_id, "name": p2_name, "score": 0, "idx": 0, "finished": False, "finish_time": 150.0},
    }

    for pid, oname in [(p1_id, p2_name), (p2_id, p1_name)]:
        try:
            await bot.send_message(
                pid,
                f"🔥 Raqib topildi! Siz <b>{oname}</b> bilan jang qilasiz!\n\n"
                f"🚀 Jang boshlandi! Har kim o'z tezligida yechadi (150 soniya max).",
                parse_mode="HTML"
            )
        except Exception:
            await bot.send_message(p1_id, "❌ Raqib botni bloklagan. Jang bekor qilindi.")
            del ACTIVE_DUELS[duel_id]
            return

    asyncio.create_task(send_question(duel_id, "p1"))
    asyncio.create_task(send_question(duel_id, "p2"))
    asyncio.create_task(duel_timeout(duel_id, bot))



async def send_question(duel_id: str, player_key: str):
    duel = ACTIVE_DUELS.get(duel_id)
    if not duel: return
    
    player = duel[player_key]
    idx = player["idx"]
    q = duel["questions"][idx]
    
    btns = []
    btns.append(InlineKeyboardButton(text="A", callback_data=f"duelans_{duel_id}_{player_key}_{idx}_A"))
    if q.option_b: btns.append(InlineKeyboardButton(text="B", callback_data=f"duelans_{duel_id}_{player_key}_{idx}_B"))
    if q.option_c: btns.append(InlineKeyboardButton(text="C", callback_data=f"duelans_{duel_id}_{player_key}_{idx}_C"))
    if q.option_d: btns.append(InlineKeyboardButton(text="D", callback_data=f"duelans_{duel_id}_{player_key}_{idx}_D"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[btns])
    
    caption = (
        f"🥊 <b>JANG | {idx+1}/10-savol</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ {q.text}\n\n"
        f"1️⃣ A) {q.option_a}\n"
    )
    if q.option_b: caption += f"2️⃣ B) {q.option_b}\n"
    if q.option_c: caption += f"3️⃣ C) {q.option_c}\n"
    if q.option_d: caption += f"4️⃣ D) {q.option_d}\n"
    
    caption += f"\n📊 <b>Sizning hisobingiz:</b> {player['score']} to'g'ri"
    
    try:
        if q.image_url:
            photo_obj = None
            if not str(q.image_url).startswith("http"):
                media_path = os.path.join(BASE_DIR, str(q.image_url).replace('\\', '/'))
                if os.path.exists(media_path):
                    photo_obj = FSInputFile(media_path)
            else:
                photo_obj = q.image_url
                
            if photo_obj:
                await duel["bot"].send_photo(player['id'], photo=photo_obj, caption=caption, reply_markup=keyboard, protect_content=duel['protect'], parse_mode="HTML")
                return
        
        await duel["bot"].send_message(player['id'], caption, reply_markup=keyboard, protect_content=duel['protect'], parse_mode="HTML")
    except Exception as e:
        print(f"Duel send error: {e}")


@duel_router.callback_query(F.data.startswith("duelans_"))
async def process_duel_answer(callback: types.CallbackQuery):
    data = callback.data.split("_")
    duel_id = data[1]
    player_key = data[2]
    q_idx = int(data[3])
    ans = data[4]
    
    duel = ACTIVE_DUELS.get(duel_id)
    if not duel:
        await callback.answer("⏳ Bu jang tugagan yoki bekor qilingan.", show_alert=True)
        return
        
    player = duel[player_key]
    
    if player["idx"] != q_idx or player["finished"]:
        await callback.answer("⏳ Vaqt o'tgan yoki boshqa savoldasiz.", show_alert=True)
        return
        
    q = duel["questions"][q_idx]
    is_correct = (ans == q.correct_option)
    
    if is_correct:
        player["score"] += 1
        await callback.answer("🎉 Qoyil! Javobingiz to'g'ri!", show_alert=True)
    else:
        await callback.answer("❌ Noto'g'ri javob!", show_alert=True)
        
    try:
        await callback.message.delete()
    except: pass
    
    player["idx"] += 1
    
    if player["idx"] >= 10:
        player["finished"] = True
        player["finish_time"] = time.time() - duel["start_time"]
        
        op_key = "p2" if player_key == "p1" else "p1"
        op_finished = duel[op_key]["finished"]
        
        if op_finished:
            await finish_duel(duel_id)
        else:
            await duel["bot"].send_message(player['id'], "⏳ <b>Siz barcha savollarni yechib bo'ldingiz!</b>\nRaqibingiz tugatishi kutilmoqda...", parse_mode="HTML")
    else:
        await send_question(duel_id, player_key)


async def duel_timeout(duel_id: str, bot):
    await asyncio.sleep(150.0)
    duel = ACTIVE_DUELS.get(duel_id)
    if duel:
        # Time's up! Force finish
        duel["p1"]["finished"] = True
        duel["p2"]["finished"] = True
        await finish_duel(duel_id)


async def finish_duel(duel_id: str):
    duel = ACTIVE_DUELS.get(duel_id)
    if not duel: return
    
    # Remove from active to prevent double firing
    del ACTIVE_DUELS[duel_id]
    
    p1 = duel['p1']
    p2 = duel['p2']
    
    # Check who won
    winner = None
    if p1['score'] > p2['score']: 
        winner = p1
    elif p2['score'] > p1['score']: 
        winner = p2
    else:
        # Tie in score, check time
        if p1['finish_time'] < p2['finish_time']:
            winner = p1
        elif p2['finish_time'] < p1['finish_time']:
            winner = p2
        else:
            winner = None # True tie
            
    async with async_session() as session:
        if winner:
            result = await session.execute(select(User).where(User.telegram_id == winner['id']))
            user = result.scalars().first()
            if user:
                user.points = (user.points or 0) + 5
                await session.commit()
                
    async def send_final(player, op):
        text = "🏁 <b>JANG YAKUNLANDI!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"👤 <b>Sizning to'g'ri javoblaringiz:</b> {player['score']}/10\n"
        text += f"⏱ <b>Sizning vaqtingiz:</b> {round(player['finish_time'], 1)} s\n\n"
        
        text += f"👤 <b>Raqib ({op['name']}):</b> {op['score']}/10\n"
        text += f"⏱ <b>Raqib vaqti:</b> {round(op['finish_time'], 1)} s\n\n"
        
        if winner and winner['id'] == player['id']:
            text += "🏆 <b>TABRIKLAYMIZ! SIZ G'OLIB BO'LDINGIZ!</b> 🎉\nTezlik va aniqlik evaziga sizga +5 ball qo'shildi!"
        elif winner and winner['id'] == op['id']:
            text += "💔 <b>Afsuski, yutqazdingiz!</b>\nRaqibingiz aniqroq yoki tezroq harakat qildi. Keyingi safar omad yor bo'lsin!"
        else:
            text += "🤝 <b>DURANG!</b> Ikkala tomon ham bir xil natija ko'rsatdi!"
            
        text += "\n\n<i>Reytingingizni ko'rish uchun menyudan '🏆 Reyting' tugmasini bosing!</i>"
        try:
            await duel["bot"].send_message(player['id'], text, parse_mode="HTML")
        except: pass
        
    await send_final(p1, p2)
    await send_final(p2, p1)
