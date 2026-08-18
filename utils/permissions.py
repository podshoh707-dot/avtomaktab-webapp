import json
from config import ADMIN_IDS
from database import async_session, AdminUser
from sqlalchemy import select

def is_superadmin(user_id: int) -> bool:
    """Faqat .env (config) dagi asosiy adminmi shuni tekshiradi."""
    return user_id in ADMIN_IDS

async def check_permission(user_id: int, perm: str) -> bool:
    """
    Foydalanuvchi ma'lum huquqqa ega ekanligini tekshiradi.
    Agar Glovniya admin (superadmin) bo'lsa har doim True qaytaradi.
    Aks holda bazadagi huquqlariga qaraydi.
    """
    if is_superadmin(user_id):
        return True
        
    async with async_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == user_id, AdminUser.is_active == True)
        )
        admin = result.scalars().first()
        
    if not admin:
        return False
        
    if admin.role == "superadmin":
        return True
        
    if not admin.permissions:
        return False
        
    try:
        perms = json.loads(admin.permissions)
        return bool(perms.get(perm, False))
    except Exception:
        return False

async def is_any_admin(user_id: int) -> bool:
    """
    Kishi umuman adminmi yoki yo'qmi tekshiradi.
    (Istalgan bo'limga, masalan, admin panel tugmasini ko'rish uchun)
    """
    if is_superadmin(user_id):
        return True
        
    async with async_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.telegram_id == user_id, AdminUser.is_active == True)
        )
        admin = result.scalars().first()
        return admin is not None
