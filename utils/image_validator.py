"""Rasm faylining haqiqiy rasm ekanligini tekshiruvchi yordamchi modul"""

VALID_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',     # JPEG
    b'\x89PNG': 'png',           # PNG
    b'GIF8': 'gif',              # GIF
    b'RIFF': 'webp',             # WebP (RIFF....WEBP)
    b'BM': 'bmp',                # BMP
}

def is_valid_image_file(path: str) -> bool:
    """Fayl haqiqiy rasm faylimi yoki yo'qligini tekshiradi."""
    try:
        with open(path, 'rb') as f:
            header = f.read(12)
        for magic, fmt in VALID_MAGIC_BYTES.items():
            if header[:len(magic)] == magic:
                # WebP uchun qo'shimcha tekshiruv
                if fmt == 'webp' and header[8:12] != b'WEBP':
                    continue
                return True
        return False
    except Exception:
        return False
