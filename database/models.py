from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, DateTime, Text
import os
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    language = Column(String, default="uz")
    points = Column(Integer, default=0)
    is_premium = Column(Boolean, default=False)
    premium_expires_at = Column(DateTime, nullable=True)
    referred_by = Column(BigInteger, nullable=True)
    referrals_count = Column(Integer, default=0)
    marathon_progress = Column(Integer, default=0)
    streak_count = Column(Integer, default=0)
    last_streak_date = Column(String, nullable=True) # "YYYY-MM-DD"
    reminder_time = Column(String, default="20:00") # "20:00" yoki "off"
    region = Column(String, default="Toshkent")
    created_at = Column(DateTime, default=datetime.utcnow)

class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    media_type = Column(String, default="image") # image, video, multi_video
    media_urls = Column(Text, nullable=True) # JSON array for multiple videos
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=True)
    option_d = Column(String, nullable=True)
    correct_option = Column(String, nullable=False) # 'A', 'B', 'C', or 'D'
    explanation = Column(Text, nullable=True)
    difficulty = Column(String, default="o'rta") # oson, o'rta, qiyin
    category = Column(String, default="Umumiy")

class Sign(Base):
    __tablename__ = 'signs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False) # taqiqlovchi, ogohlantiruvchi, etc.
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    example = Column(Text, nullable=True)

class UserStat(Base):
    __tablename__ = 'user_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tests_taken = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    wrong_answers = Column(Integer, default=0)
    daily_streak = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = 'settings'
    
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)

class Rule(Base):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    text = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    pdf_url = Column(String, nullable=True)

class VideoLesson(Base):
    __tablename__ = 'video_lessons'
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String, nullable=False)
    section = Column(String, nullable=True)
    telegram_video_id = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)

class News(Base):
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    button_text = Column(String, nullable=True)
    button_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class QAItem(Base):
    __tablename__ = 'qa_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

class BotGroup(Base):
    __tablename__ = 'bot_groups'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    subscription_guard = Column(Boolean, default=False)
    antispam_enabled = Column(Boolean, default=False)
    block_links = Column(Boolean, default=False)
    block_flood = Column(Boolean, default=False)
    block_curse = Column(Boolean, default=False)

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True) # Telegram akk bog'lansa yoziladi
    full_name = Column(String, nullable=False)
    group_name = Column(String, nullable=True)
    attendance_score = Column(Integer, default=0)
    exam_score = Column(Integer, default=0)
    paid_amount = Column(Integer, default=0) # Jami to'lagan kontrakti

class StudentPayment(Base):
    """
    Avtomaktab o'quvchisi (Student) to'lovlari tarixi (kontrakt).
    """
    __tablename__ = 'student_payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Integer, nullable=False)           # To'lov summasi (raqam)
    status = Column(String, default='pending')         # pending | approved | rejected
    approved_by = Column(BigInteger, nullable=True)    # Tasdiqlagan admin telegram_id
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    days_granted = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)

class UserMistake(Base):
    __tablename__ = 'user_mistakes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    mistake_count = Column(Integer, default=1)
    last_mistake_at = Column(DateTime, default=datetime.utcnow)


class AdminUser(Base):
    """
    Bot adminlari jadvali.
    Rollar: superadmin | moderator | content_manager
    Huquqlar (permissions) JSON formatida saqlanadi:
      {
        "can_broadcast": true/false,
        "can_manage_users": true/false,
        "can_manage_content": true/false,
        "can_manage_premium": true/false,
        "can_view_stats": true/false,
        "can_manage_groups": true/false
      }
    """
    __tablename__ = 'admin_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    role = Column(String, default='moderator')  # superadmin | moderator | content_manager
    permissions = Column(Text, nullable=True)    # JSON string
    added_by = Column(BigInteger, nullable=True)  # Kim qo'shgani (telegram_id)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class TestSession(Base):
    """
    Foydalanuvchining joriy test sessiyasini saqlaydi.
    Bot o'chib yonsa, test davom ettirilishi mumkin.
    """
    __tablename__ = 'test_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    question_ids = Column(Text, nullable=False)    # JSON array of question IDs
    current_idx = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    is_mistake_mode = Column(Boolean, default=False)
    category = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GroupQuizSession(Base):
    """
    Guruh viktorinasi sessiyasini saqlaydi.
    Bot o'chib yonsa, natijalar qayta yuboriladi.
    """
    __tablename__ = 'group_quiz_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_title = Column(String, nullable=True)
    question_ids = Column(Text, nullable=False)       # JSON array of question IDs
    current_idx = Column(Integer, default=0)
    total_questions = Column(Integer, default=30)
    participants = Column(Text, nullable=True)         # JSON: {user_id: {name, score, time_taken}}
    poll_ids = Column(Text, nullable=True)             # JSON: {poll_id: correct_option_id}
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Payment(Base):
    """
    Premium to'lovlar tarixi.
    Har bir to'lov so'rovi (chek yuborilganda) bazaga yoziladi.
    Admin tasdiqlasa yoki rad etsa, status yangilanadi.
    """
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, nullable=False, index=True)
    user_full_name = Column(String, nullable=True)
    username = Column(String, nullable=True)           # @username (bo'lsa)
    amount = Column(String, nullable=True)             # To'lov summasi (matn, masalan "50 000 so'm")
    status = Column(String, default='pending')         # pending | approved | rejected
    days_granted = Column(Integer, default=30)         # Berilgan kunlar soni
    approved_by = Column(BigInteger, nullable=True)    # Tasdiqlagan admin telegram_id
    created_at = Column(DateTime, default=datetime.utcnow)   # Chek yuborilgan vaqt
    resolved_at = Column(DateTime, nullable=True)             # Tasdiqlangan/rad etilgan vaqt
