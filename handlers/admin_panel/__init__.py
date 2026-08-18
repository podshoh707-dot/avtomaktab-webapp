from aiogram import Router
from .main_menu import main_menu_router
from .statistics import statistics_router
from .settings import settings_router
from .content import content_router
from .broadcast import broadcast_router
from .rating import rating_router
from .groups_admin import groups_admin_router
from .system import system_router
from .school import school_router
from .questions import questions_router
from .signs import signs_router
from .admins import admins_router

admin_router = Router()

admin_router.include_router(main_menu_router)
admin_router.include_router(admins_router)
admin_router.include_router(statistics_router)
admin_router.include_router(settings_router)
admin_router.include_router(content_router)
admin_router.include_router(broadcast_router)
admin_router.include_router(rating_router)
admin_router.include_router(groups_admin_router)
admin_router.include_router(system_router)
admin_router.include_router(school_router)
admin_router.include_router(questions_router)
admin_router.include_router(signs_router)

