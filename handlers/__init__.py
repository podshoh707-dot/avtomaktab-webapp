from aiogram import Router
from .menu import menu_router
from .test import test_router
from .signs import signs_router
from .groups import groups_router
from .admin_panel import admin_router
from .school import school_router
from .premium import premium_router
from .registration import registration_router
from .channel_quiz import channel_quiz_router
from .duel import duel_router
from .ai_tutor_handler import ai_tutor_router
from .business import business_router
from .catchall import catchall_router
from middlewares.subscription import SubscriptionCheckMiddleware

router = Router()

# Obuna tekshirish middleware'ini router'ga ulaymiz
router.message.middleware(SubscriptionCheckMiddleware())
router.callback_query.middleware(SubscriptionCheckMiddleware())

# Routers order matters: catchall should be the last one
router.include_router(registration_router)
router.include_router(admin_router)
router.include_router(menu_router)
router.include_router(test_router)
router.include_router(ai_tutor_router)
router.include_router(signs_router)
router.include_router(groups_router)
router.include_router(school_router)
router.include_router(premium_router)
router.include_router(channel_quiz_router)
router.include_router(duel_router)
router.include_router(business_router)
router.include_router(catchall_router)
