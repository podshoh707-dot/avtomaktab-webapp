"""
Avtomaktab YHQ Nazariy Imtihon Sertifikati Generatori (Pillow)
Yuqori aniqlikdagi (High Quality) nomli sertifikat tasvirlarini generatsiya qiladi.
"""
import os
import uuid
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTS_DIR = os.path.join(BASE_DIR, "db", "certificates")
os.makedirs(CERTS_DIR, exist_ok=True)

def get_font(size, bold=False):
    """Tizimda mavjud standart shriftni tanlaydi (Windows yoki fallback)."""
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "tahomabd.ttf" if bold else "tahoma.ttf",
        "seguiemj.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]
    for fn in font_names:
        try:
            # Windows font directory
            win_font = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", fn)
            if os.path.exists(win_font):
                return ImageFont.truetype(win_font, size)
            return ImageFont.truetype(fn, size)
        except Exception:
            continue
    return ImageFont.load_default()

def generate_certificate(full_name: str, score: int, total: int = 20) -> str:
    """
    Foydalanuvchi nomiga YHQ Imtihon Sertifikatini generatsiya qiladi.
    Qaytaradi: yaratilgan rasm faylining mutlaq yo'li (str).
    """
    width = 1200
    height = 850
    
    # 1. Asosiy fon (Oq-krem rangli gradient effekti)
    img = Image.new("RGB", (width, height), color=(252, 252, 254))
    draw = ImageDraw.Draw(img)
    
    # 2. Hashamatli oltin-ko'k ramkalar
    # Tashqi to'q ko'k hoshiya
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(15, 34, 64), width=8)
    # Ichki oltin hoshiya
    draw.rectangle([(32, 32), (width - 32, height - 32)], outline=(212, 160, 23), width=3)
    # Yupqa nozik hoshiya
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(200, 210, 225), width=1)
    
    # Burchak bezaklari (Gold Corner Accents)
    corner_size = 45
    corners = [
        (40, 40, 40 + corner_size, 40),
        (40, 40, 40, 40 + corner_size),
        (width - 40, 40, width - 40 - corner_size, 40),
        (width - 40, 40, width - 40, 40 + corner_size),
        (40, height - 40, 40 + corner_size, height - 40),
        (40, height - 40, 40, height - 40 - corner_size),
        (width - 40, height - 40, width - 40 - corner_size, height - 40),
        (width - 40, height - 40, width - 40, height - 40 - corner_size),
    ]
    for x1, y1, x2, y2 in corners:
        draw.line([(x1, y1), (x2, y2)], fill=(212, 160, 23), width=4)

    # 3. Yuqori sarlavha va Emblem
    font_badge = get_font(18, bold=True)
    draw.text((width // 2, 75), "O'ZBEKISTON RESPUBLIKASI YO'L HARAKATI XAVFSIZLIGI", fill=(70, 90, 120), font=font_badge, anchor="mm")
    
    font_title = get_font(42, bold=True)
    draw.text((width // 2, 130), "SERTIFIKAT", fill=(15, 34, 64), font=font_title, anchor="mm")
    
    # Oltin ajratuvchi chiziq
    draw.line([(width // 2 - 180, 160), (width // 2 + 180, 160)], fill=(212, 160, 23), width=3)
    draw.ellipse([(width // 2 - 6, 157), (width // 2 + 6, 163)], fill=(212, 160, 23))

    font_sub = get_font(20, bold=False)
    draw.text((width // 2, 195), "USHBU HUJJAT BILAN TASDIQLANADI", fill=(100, 115, 135), font=font_sub, anchor="mm")

    # 4. Foydalanuvchi ismi (Katta va qalin shriftda)
    name_display = full_name.upper() if full_name else "FOTIX FOYDALANUVCHI"
    font_name = get_font(38, bold=True)
    draw.text((width // 2, 265), name_display, fill=(18, 52, 102), font=font_name, anchor="mm")
    
    # Ism ostidagi chiziq
    draw.line([(width // 2 - 250, 295), (width // 2 + 250, 295)], fill=(180, 195, 215), width=1)

    # 5. Matn va Natija
    percent = round(score / max(total, 1) * 100)
    font_body = get_font(21, bold=False)
    body_text_1 = "Avtomaktab YHQ Davlat Standarti bo'yicha Nazariy Imtihon sinovidan"
    body_text_2 = f"muvaffaqiyatli o'tib, {total} ta savoldan {score} tasiga to'g'ri javob berdi ({percent}%)."
    
    draw.text((width // 2, 350), body_text_1, fill=(40, 50, 70), font=font_body, anchor="mm")
    draw.text((width // 2, 385), body_text_2, fill=(40, 50, 70), font=font_body, anchor="mm")

    font_grade = get_font(24, bold=True)
    status_text = "STATUS: IMTIHONDAN O'TDI (HAYDOVCHILIKKA TAYYOR)"
    draw.text((width // 2, 440), status_text, fill=(34, 139, 34), font=font_grade, anchor="mm")

    # 6. Markaziy Natija Qutisi (Badge)
    box_x1, box_y1, box_x2, box_y2 = width // 2 - 130, 480, width // 2 + 130, 560
    draw.rectangle([(box_x1, box_y1), (box_x2, box_y2)], fill=(245, 248, 255), outline=(212, 160, 23), width=2)
    
    font_score_label = get_font(16, bold=False)
    draw.text((width // 2, 500), "UMUMIY NATIJA", fill=(100, 115, 135), font=font_score_label, anchor="mm")
    font_score_val = get_font(32, bold=True)
    draw.text((width // 2, 535), f"{score} / {total} BALL", fill=(15, 34, 64), font=font_score_val, anchor="mm")

    # 7. Pastki ma'lumotlar (Sana, Sertifikat ID, Muhr)
    cert_id = f"AVTO-{uuid.uuid4().hex[:8].upper()}"
    date_str = datetime.now().strftime("%d.%m.%Y")

    # Chap tomon: Sana va ID
    font_footer = get_font(16, bold=False)
    font_footer_val = get_font(17, bold=True)
    
    draw.text((100, 680), "Berilgan sana:", fill=(100, 115, 135), font=font_footer)
    draw.text((100, 705), date_str, fill=(20, 35, 60), font=font_footer_val)
    
    draw.text((100, 740), "Sertifikat raqami:", fill=(100, 115, 135), font=font_footer)
    draw.text((100, 765), cert_id, fill=(20, 35, 60), font=font_footer_val)

    # O'ng tomon: Tasdiqlovchi organ va Muhr (Seal)
    seal_cx, seal_cy = width - 180, 720
    draw.ellipse([(seal_cx - 55, seal_cy - 55), (seal_cx + 55, seal_cy + 55)], outline=(190, 40, 40), width=3)
    draw.ellipse([(seal_cx - 48, seal_cy - 48), (seal_cx + 48, seal_cy + 48)], outline=(190, 40, 40), width=1)
    
    font_seal = get_font(12, bold=True)
    draw.text((seal_cx, seal_cy - 20), "AVTOMAKTAB", fill=(190, 40, 40), font=font_seal, anchor="mm")
    draw.text((seal_cx, seal_cy), "★ RASMIY ★", fill=(190, 40, 40), font=font_seal, anchor="mm")
    draw.text((seal_cx, seal_cy + 20), "TASDIQLANDI", fill=(190, 40, 40), font=font_seal, anchor="mm")

    # Faylni saqlash
    file_name = f"cert_{cert_id}.png"
    file_path = os.path.join(CERTS_DIR, file_name)
    img.save(file_path, "PNG", quality=95)
    return file_path

if __name__ == "__main__":
    test_path = generate_certificate("Aliyev Vali Karimboyevich", 19, 20)
    print("Sertifikat yaratildi:", test_path)
