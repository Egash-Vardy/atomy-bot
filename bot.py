import asyncio
import sqlite3
import logging
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
API_TOKEN = "8649187707:AAHRB0xnugFsg0Itnlecy7-wqCGPivltz6M"
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Состояния для админки
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ─── БАЗА ДАННЫХ ──────────────────────────────────────────────
class Database:
    def __init__(self, path):
        self.path = path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users(
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    referrer_id INTEGER,
                    reg_date TEXT
                )
            """)
            conn.commit()

    def add_user(self, uid, name, username, ref):
        with sqlite3.connect(self.path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users (user_id, name, username, referrer_id, reg_date) VALUES (?, ?, ?, ?, ?)",
                    (uid, name, username, ref, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
                conn.commit()
                return True
            return False

    def get_all_users(self):
        with sqlite3.connect(self.path) as conn:
            return [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]

    def get_stats(self):
        with sqlite3.connect(self.path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            refs = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL").fetchone()[0]
            return total, refs

db = Database(DB_NAME)

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────
def get_main_kb(uid):
    buttons = [
        [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🔗 Реферальная ссылка")],
    ]
    if uid in ADMIN_IDS:
        buttons.append([KeyboardButton(text="⚙️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

# ─── ОБРАБОТЧИКИ ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(m: Message):
    uid = m.from_user.id
    name = m.from_user.full_name
    username = m.from_user.username
    
    ref = None
    if len(m.text.split()) > 1:
        try: ref = int(m.text.split()[1])
        except: pass

    db.add_user(uid, name, username, ref)

    text = (
        "Егор Морозов, добро пожаловать в чат!\n\n"
        "Рады видеть тебя. Это пространство для тех, кто хочет развиваться, расти и выстраивать доход в комфортном темпе.\n\n"
        "Здесь: поддержка, честно про деньги и возможности — без давления и спешки, с уважением к каждому.\n\n"
        "Если ты хочешь в команду, напиши в чат «+» — подскажем, с чего лучше начать.\n\n"
        "Рады, что ты с нами."
    )
    await m.answer(text, reply_markup=get_main_kb(uid))

@router.message(F.text == "+")
async def process_plus(m: Message):
    uid = m.from_user.id
    name = m.from_user.first_name or "Участник"

    # Уведомление админам
    for adm in ADMIN_IDS:
        try:
            kb_admin = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать сразу", url=f"tg://user?id={uid}")]
            ])
            await bot.send_message(adm, f"🚨 НОВЫЙ + ОТКЛИК\n👤 {m.from_user.full_name}\nID: {uid}", reply_markup=kb_admin)
        except: pass

    text = (
        f"Спасибо, {name}! \n\n"
        "Отлично, ты готова сделать первый шаг. \n"
        "Давай начнём с простого: я расскажу, какие возможности у нас есть и как комфортно подключиться к команде.\n\n"
        "Сначала небольшая рекомендация:\n"
        " 1. Ознакомься с нашим чек-листом для старта — он поможет понять, с чего начать.\n"
        " 2. Потом мы вместе выберем направление, которое тебе ближе: развитие бизнеса или покупка для себя.\n\n"
        "Если готова, могу сразу прислать чек-лист и пошаговое руководство, чтобы начать уже сегодня.\n\n"
        "Хочешь, чтобы я отправила его сейчас?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="yes_checklist")],
        [InlineKeyboardButton(text="Уже есть чек-лист", callback_data="already_have")]
    ])
    await m.answer(text, reply_markup=kb)

@router.callback_query(F.data == "yes_checklist")
async def cb_yes_checklist(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    text = (
        f"Супер, {name}! \n\n"
        "Вот твой чек-лист для старта — он поможет легко и уверенно сделать первый шаг:\n"
        " 1. Ознакомься с возможностями — что можно делать в команде и как получать доход.\n"
        " 2. Выбери свой путь — бизнес-партнёрство или покупки для себя.\n"
        " 3. Начни действовать — шаг за шагом, в комфортном темпе.\n\n"
        "Я буду рядом, чтобы поддерживать и отвечать на все вопросы. \n"
        "Если хочешь, можем прямо сейчас обсудить, с чего лучше начать твой первый шаг.\n\n"
        "Хочешь, чтобы я помогла выбрать стартовое направление?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Да", callback_data="help_direction")]])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "help_direction")
async def cb_help_direction(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    link = "https://docs.google.com/document/d/1lfw0xlnBjAOqMpo6utmjQ2w1QzFs7APON9WnJc_qI1w/edit?usp=sharing"
    text = (
        f"Замечательно, {name}! \n\n"
        f"Вот твой чек-лист для старта — он поможет сделать первые шаги легко и уверенно:\n"
        f"[{link}]\n\n"
        "Теперь давай определимся с первым действием, чтобы начать прямо сегодня:\n"
        " • Если хочешь попробовать себя в бизнесе, я покажу, с чего начать и как строить доход шаг за шагом.\n"
        " • Если хочешь начать с покупок для себя, расскажу, как использовать продукты и получать бонусы уже с первых заказов.\n\n"
        "Что тебе ближе на этом этапе: бизнес или покупки для себя?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="path_biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="path_shop")]
    ])
    await cb.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await cb.answer()

@router.callback_query(F.data == "already_have")
async def cb_already_have(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    text = (
        f"Прекрасно, {name}! \n\n"
        "Раз чек-лист у тебя уже есть, давай определимся, с чего начать твой путь:\n"
        " • Развитие бизнеса — я покажу, как строить доход шаг за шагом и подключаться к команде.\n"
        " • Покупки для себя — расскажу, как выгодно использовать продукты и получать бонусы с первых заказов.\n\n"
        "Что тебе ближе на этом этапе: бизнес или покупки для себя?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="path_biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="path_shop")]
    ])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "path_biz")
async def cb_biz(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    text = (
        f"Супер, {name}! \n\n"
        "Тогда давай сосредоточимся на твоём старте в бизнесе. \n"
        "Вот первый шаг:\n"
        " 1. Ознакомление с возможностями — я пришлю тебе простую инструкцию, как начать строить доход.\n"
        " 2. Выбор направления и плана действий — мы вместе определим, с чего лучше начать именно тебе.\n"
        " 3. Поддержка и сопровождение — я буду рядом на каждом шаге, чтобы помочь и ответить на вопросы.\n\n"
        "Скоро я напишу лично тебе сообщение и мы сможем встретиться в удобное для тебя время."
    )
    await cb.message.answer(text)
    await cb.answer()

@router.callback_query(F.data == "path_shop")
async def cb_shop(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    text = (
        f"Прекрасно, {name}! \n\n"
        "Тогда начнём с твоих покупок и выгод:\n"
        " 1. Ознакомься с продуктами — я пришлю тебе список самых популярных товаров и бонусов.\n"
        " 2. Сделай первый заказ — легко и удобно, чтобы сразу получить выгоду и бонусы.\n"
        " 3. Поддержка и советы — я буду рядом, чтобы ответить на любые вопросы и подсказать, как максимально выгодно использовать покупки.\n\n"
        "Скоро я напишу тебе личное сообщение, где помогу оформить личный бесплатный кабинет. И буду твоим гидом и помощником."
    )
    await cb.message.answer(text)
    await cb.answer()

# ─── АДМИНКА И ПРОЧЕЕ ─────────────────────────────────────────

@router.message(F.text == "⚙️ Админ панель")
async def admin_main(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    total, refs = db.get_stats()
    await m.answer(f"⚙️ Панель управления\n\nВсего юзеров: {total}\nРефералов: {refs}", reply_markup=get_admin_kb())

@router.message(F.text == "📢 Рассылка")
async def start_broadcast(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS: return
    await m.answer("Введите текст рассылки (или отправьте фото):")
    await state.set_state(AdminStates.waiting_for_broadcast)

@router.message(AdminStates.waiting_for_broadcast)
async def perform_broadcast(m: Message, state: FSMContext):
    users = db.get_all_users()
    count = 0
    for user_id in users:
        try:
            await m.copy_to(user_id)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await m.answer(f"✅ Рассылка завершена. Получили: {count} чел.")
    await state.clear()

@router.message(F.text == "📊 Моя статистика")
async def my_stats(m: Message):
    with sqlite3.connect(DB_NAME) as conn:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (m.from_user.id,)).fetchone()[0]
    await m.answer(f"📊 Вы пригласили: {count} чел.")

@router.message(F.text == "🔗 Реферальная ссылка")
async def ref_link(m: Message):
    me = await bot.get_me()
    await m.answer(f"Твоя ссылка:\nhttps://t.me/{me.username}?start={m.from_user.id}")

@router.message(F.text == "🔙 Назад")
async def back(m: Message):
    await m.answer("Главное меню", reply_markup=get_main_kb(m.from_user.id))

# ─── ЗАПУСК ───────────────────────────────────────────────────
async def main():
    logger.info("Бот запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
