import os
import sys
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Asosiy YHQ mavzulari bo'yicha qoidalar lug'ati (Offline AI Knowledge Base)
YHQ_KNOWLEDGE = {
    "tezlik": (
        "📌 <b>Tezlik me'yorlari bo'yicha YHQ qoidasi:</b>\n"
        "• Aholi yashash punktlarida barcha yengil transport vositalari uchun eng yuqori tezlik — <b>60 km/soat</b>.\n"
        "• Maktab, bog'cha va maxsus hududlar oldida — <b>30 km/soat</b>.\n"
        "• Turar joy dahalari (hovlilar)da — <b>20 km/soat</b>.\n"
        "• Shahardan tashqaridagi oddiy yo'llarda — <b>100 km/soat</b>.\n"
        "• Avtomagistral (avtostrada)larda — <b>110 km/soat</b>."
    ),
    "kamari": (
        "📌 <b>Xavfsizlik kamari qoidasi:</b>\n"
        "• Harakatlanayotgan avtomobilda haydovchi va barcha yo'lovchilar (shu jumladan orqa o'rindiqdagi) xavfsizlik kamarini taqishlari shart.\n"
        "• Faqat orqaga harakatlanayotgan haydovchilar yoki o'quv mashinasidagi instruktor mashg'ulot paytida taqmasligi mumkin."
    ),
    "svetofor": (
        "📌 <b>Svetofor signallari qoidasi:</b>\n"
        "• 🟢 Yashil — Harakatlanishga to'liq ruxsat beradi.\n"
        "• 🟡 Sariq — Harakatlanishni TAQIQLAYDI! (Faqat keskin tormoz bermaslik holatidagina o'tishga ruxsat etiladi).\n"
        "• 🔴 Qizil — Harakatlanish qat'iyan taqiqlanadi.\n"
        "• 🔴+🟡 Qizil va sariq birga yonsa — Harakat taqiqlanadi, tez orada yashil yonishidan ogohlantiradi."
    ),
    "chorraha": (
        "📌 <b>Chorrahalardan o'tish qoidasi:</b>\n"
        "• Teng ahamiyatli chorrahada 'O'ng qo'l qoidasi' amal qiladi: O'ng tomondan kelayotgan transportga yo'l beriladi.\n"
        "• Chapga burilayotgan transport qarama-qarshi tomondan to'g'riga yoki o'ngga ketayotgan transportga yo'l berishi shart.\n"
        "• Maxsus mayoqchasi (ko'k/qizil) va tovushi yoqilgan operativ transportlar har doim mutlaq ustunlikka ega!"
    ),
    "quvib": (
        "📌 <b>Quvib o'tish qoidalari:</b>\n"
        "• Quvib o'tish faqat qarama-qarshi yo'l bo'sh bo'lganda va 3.20 'Quvib o'tish taqiqlangan' belgisi bo'lmaganda ruxsat etiladi.\n"
        "• Chorrahalarda, piyodalar o'tish joylarida, temir yo'l kesishmalarida va tik burilishlarda quvib o'tish qat'iyan taqiqlanadi!"
    ),
    "tibbiy": (
        "📌 <b>Birinchi tibbiy yordam ko'rsatish asoslari:</b>\n"
        "• Kuchli qon ketishda birinchi navbatda turniket (jgut) jarohatdan yuqoriroqqa qo'yiladi va vaqti yozib qo'yiladi.\n"
        "• Jabrlanuvchini nafas yo'llarini ochish uchun boshi orqaga ohista egiladi.\n"
        "• Sun'iy nafas berish va yurak massaji nisbati: 30 ta bosish va 2 ta nafas berish (30:2)."
    )
}

def generate_ai_explanation(question_text: str, correct_answer_text: str, official_explanation: str = "") -> str:
    """
    Test savoli bo'yicha AI Ustozning interaktiv va qiziqarli tushuntirishini yaratadi.
    """
    q_lower = (question_text + " " + correct_answer_text).lower()
    
    # Mavzuga oid chuqur bilim topish
    matched_tip = ""
    for keyword, tip_text in YHQ_KNOWLEDGE.items():
        if keyword in q_lower:
            matched_tip = tip_text
            break

    response = (
        "🤖 <b>AI USTOZNING TAHLILI VA TUSHUNTIRISHI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ <b>Savol:</b> <i>{question_text}</i>\n\n"
        f"✅ <b>To'g'ri javob:</b> <b>{correct_answer_text}</b>\n\n"
    )

    if official_explanation:
        response += f"📖 <b>Rasmiy YHQ moddasi:</b>\n{official_explanation}\n\n"

    # Mnemonika / Esda saqlash kaliti
    mnemonic = "🧠 <b>Esda saqlash siri (Mnemonika):</b>\n"
    if "o'ng" in q_lower or "chorraha" in q_lower:
        mnemonic += "👉 <i>'O'ng tomondan xavf — to'xta va qara!'</i> qoidasini yodda tuting."
    elif "tezlik" in q_lower:
        mnemonic += "⚡️ <i>'Shahar ichida 60, maktab oldida 30, hovlida 20!'</i> formulasi bilan yodlang."
    elif "kamari" in q_lower:
        mnemonic += "🔒 <i>'Kamar — hayot sug'urtasi!'</i> Mashinaga o'tirganda 1-harakat bo'lsin."
    elif "svetofor" in q_lower:
        mnemonic += "🚦 <i>'Sariq — o'tish emas, to'xtash signali!'</i> Shoshilmaslik xavfsizlik garovidir."
    elif "tibbiy" in q_lower:
        mnemonic += "🩺 <i>'30 ta bosish : 2 ta nafas'</i> — 30:2 oltin qoidasi."
    else:
        mnemonic += "🎯 <i>'Avval qoida, keyin harakat!'</i> Savol kalit so'zlariga sinchkovlik bilan e'tibor bering."

    response += f"{mnemonic}\n\n"
    response += "━━━━━━━━━━━━━━━━━━━━\n🚘 <i>Xavfsiz va ehtiyotkor haydash tilaymiz!</i>"

    return response

def answer_user_free_question(user_query: str) -> str:
    """
    Foydalanuvchining erkin savollariga javob beradi.
    """
    query_lower = user_query.lower()
    
    for keyword, tip_text in YHQ_KNOWLEDGE.items():
        if keyword in query_lower:
            return (
                f"🤖 <b>AI USTOZ JAVOBI:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Savolingiz bo'yicha quyidagi rasmiy YHQ qoidasi belgilangan:\n\n"
                f"{tip_text}\n\n"
                f"❓ Yana savollaringiz bo'lsa, bemalol yozib qoldirishingiz mumkin!"
            )
            
    return (
        f"🤖 <b>AI USTOZ JAVOBI:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Sizning savolingiz: <i>«{user_query}»</i>\n\n"
        f"🚗 <b>Avto-Instruktor tavsiyasi:</b>\n"
        f"Yo'l harakati xavfsizligi qoidalariga muvofiq, har qanday yo'l harakati vaziyatida asosiy mezon — bu <b>yo'l belgilari, chiziqlar va svetofor signallari</b> talablariga qat'iy amal qilishdir.\n\n"
        f"Barcha murakkab vaziyatlarda tezlikni me'yorida saqlang, xavfsiz oraliq masofani (distansiya) ushlang va boshqa harakat ishtirokchilariga hurmat bilan munosabatda bo'ling.\n\n"
        f"📚 <i>Aniq mavzu bo'yicha (masalan: tezlik, svetofor, chorraha, quvib o'tish, tibbiy yordam) so'rasangiz, batafsil moddalar bilan tushuntirib beraman.</i>"
    )

# Alias for backward compatibility
explain_question_by_ai = generate_ai_explanation

if __name__ == "__main__":
    res = generate_ai_explanation("Aholi yashash punktlarida tezlik qancha?", "60 km/soat", "YHQ 10-bandiga asosan")
    print(res)
