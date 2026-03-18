import asyncio
import sqlite3
import logging
import sys
from datetime import datetime
from typing import List, Union

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
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
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # Новый импорт для фикса ошибки

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
API_TOKEN = "8649187707:AAHRB0xnugFsg0Itnlecy7-wqCGPivltz6M"
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class AdminProcess(StatesGroup):
    broadcast_message = State()

# ИСПРАВЛЕНО: Теперь настройки передаются через default=DefaultBotProperties
bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ─── БАЗА ДАННЫХ ──────────────────────────────────────────────
class DataManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    referrer_id INTEGER,
                    reg_date TEXT
                )
            """)
            conn.commit()

    def register_user(self, uid: int, name: str, username: str, ref: Union[int, None]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
            if not cursor.fetchone():
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO users (user_id, full_name, username, referrer_id, reg_date) VALUES (?, ?, ?, ?, ?)",
                    (uid, name, username, ref, date_str)
                )
                conn.commit()
                return True
            return False

    def fetch_all_ids(self) -> List[int]:
        with self._get_connection() as conn:
            return [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]

    def get_system_stats(self):
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            refs = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL").fetchone()[0]
            return total, refs

db_manager = DataManager(DB_NAME)

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────
def get_main_reply_kb(uid: int):
    struct = [[KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🔗 Реферальная ссылка")]]
    if uid in ADMIN_IDS:
        struct.append([KeyboardButton(text="⚙️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=struct, resize_keyboard=True)

def get_admin_reply_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📢 Рассылка")], [KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)

# ─── ОБРАБОТЧИКИ ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(m: Message):
    uid = m.from_user.id
    name = m.from_user.full_name 
    
    ref_param = None
    args = m.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_param = int(args[1])

    db_manager.register_user(uid, name, m.from_user.username, ref_param)

    text = (
        f"<b>{name}</b>, добро пожаловать в чат!\n\n"
        "Рады видеть тебя. Это пространство для тех, кто хочет развиваться, расти и выстраивать доход в комфортном темпе.\n\n"
        "Здесь: поддержка, честно про деньги и возможности — без давления и спешки, с уважением к каждому.\n\n"
        "Если ты хочешь в команду, напиши в чат «+» — подскажем, с чего лучше начать.\n\n"
        "Рады, что ты с нами."
    )
    await m.answer(text, reply_markup=get_main_reply_kb(uid))

@router.message(F.text == "+")
async def process_plus(m: Message):
    uid = m.from_user.id
    name = m.from_user.first_name

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"🚨 НОВЫЙ ОТКЛИК (+)\n👤 {m.from_user.full_name}\nID: {uid}")
        except: pass

    text = (
        f"Спасибо, <b>{name}</b>!✨ \n\n"
        "Отлично, ты готова сделать первый шаг.😊 \n"
        "Давай начнём с простого: я расскажу, какие возможности у нас есть и как комфортно подключиться к команде.\n\n"
        "Сначала небольшая рекомендация:\n"
        " 1. Ознакомься с нашим чек-листом для старта — он поможет понять, с чего начать.\n"
        " 2. Потом мы вместе выберем направление, которое тебе ближе: развитие бизнеса или покупка для себя.\n\n"
        "Если готова, могу сразу прислать чек-лист и пошаговое руководство, чтобы начать уже сегодня.\n\n"
        "Хочешь, чтобы я отправила его сейчас?✅"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="flow_yes")],
        [InlineKeyboardButton(text="Уже есть чек-лист", callback_data="flow_already")]
    ])
    await m.answer(text, reply_markup=kb)

@router.callback_query(F.data == "flow_yes")
async def flow_yes(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = (
        f"Супер, <b>{name}</b>! \n\n"
        "Вот твой чек-лист для старта — он поможет легко и уверенно сделать первый шаг:\n"
        " 1. Ознакомься с возможностями — что можно делать в команде и как получать доход.\n"
        " 2. Выбери свой путь — бизнес-партнёрство или покупки для себя.\n"
        " 3. Начни действовать — шаг за шагом, в комфортном темпе.\n\n"
        "Я буду рядом, чтобы поддерживать и отвечать на все вопросы. \n"
        "Если хочешь, можем прямо сейчас обсудить, с чего лучше начать твой первый шаг.\n\n"
        "Хочешь, чтобы я помогла выбрать стартовое направление?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Да", callback_data="flow_choice")]])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "flow_choice")
async def flow_choice(cb: CallbackQuery):
    name = cb.from_user.first_name
    checklist_url = "https://clipr.cc/RC4rz"
    
    text = (
        f"Замечательно, <b>{name}</b>! 🎉 \n\n"
        f"Вот твой <a href='{checklist_url}'>ЧЕК-ЛИСТ</a> для старта — он поможет сделать первые шаги легко и уверенно.\n\n"
        "Теперь давай определимся с первым действием, чтобы начать прямо сегодня:\n"
        " • Если хочешь попробовать себя в бизнесе, я покажу, с чего начать и как строить доход шаг за шагом.\n"
        " • Если хочешь начать с покупок для себя, расскажу, как использовать продукты и получать бонусы уже с первых заказов.\n\n"
        "Что тебе ближе на этом этапе: бизнес или покупки для себя?💛"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="res_biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="res_shop")]
    ])
    await cb.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await cb.answer()

@router.callback_query(F.data == "flow_already")
async def flow_already(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = (
        f"Прекрасно, <b>{name}</b>!✨ \n\n"
        "Раз чек-лист у тебя уже есть, давай определимся, с чего начать твой путь:\n"
        " • Развитие бизнеса — я покажу, как строить доход шаг за шагом и подключаться к команде.\n"
        " • Покупки для себя — расскажу, как выгодно использовать продукты и получать бонусы с первых заказов.\n\n"
        "Что тебе ближе на этом этапе: бизнес или покупки для себя?💛"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="res_biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="res_shop")]
    ])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "res_biz")
async def res_biz(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = (
        f"Супер, <b>{name}</b>!🚀 \n\n"
        "Тогда давай сосредоточимся на твоём старте в бизнесе.💼 \n"
        "Вот первый шаг:\n"
        " 1. Ознакомление с возможностями — я пришлю тебе простую инструкцию, как начать строить доход.\n"
        " 2. Выбор направления и плана действий — мы вместе определим, с чего лучше начать именно тебе.\n"
        " 3. Поддержка и сопровождение — я буду рядом на каждом шаге, чтобы помочь и ответить на вопросы.\n\n"
        "Скоро я напишу лично тебе сообщение и мы сможем встретиться в удобное для тебя время."
    )
    await cb.message.answer(text)
    await cb.answer()

@router.callback_query(F.data == "res_shop")
async def res_shop(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = (
        f"Прекрасно, <b>{name}</b>!🌸 \n\n"
        "Тогда начнём с твоих покупок и выгод:\n"
        " 1. Ознакомься с продуктами — я пришлю тебе список самых популярных товаров и бонусов.\n"
        " 2. Сделай первый заказ — легко и удобно, чтобы сразу получить выгоду и бонусы.\n"
        " 3. Поддержка и советы — я буду рядом, чтобы ответить на любые вопросы и подсказать, как максимально выгодно использовать покупки.\n\n"
        "Скоро я напишу тебе личное сообщение, где помогу оформить личный бесплатный кабинет. И буду твоим гидом и помощником."
    )
    await cb.message.answer(text)
    await cb.answer()

# ─── АДМИН ПАНЕЛЬ И СТАТИСТИКА ───────────────────────────────
@router.message(F.text == "⚙️ Админ панель")
async def admin_panel(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    total, refs = db_manager.get_system_stats()
    await m.answer(f"⚙️ Панель управления\n\nВсего юзеров: {total}\nРефералов: {refs}", reply_markup=get_admin_reply_kb())

@router.message(F.text == "📢 Рассылка")
async def broadcast_start(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS: return
    await m.answer("Введите сообщение для рассылки:")
    await state.set_state(AdminProcess.broadcast_message)

@router.message(AdminProcess.broadcast_message)
async def broadcast_send(m: Message, state: FSMContext):
    ids = db_manager.fetch_all_ids()
    count = 0
    for uid in ids:
        try:
            await m.copy_to(uid)
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await m.answer(f"✅ Рассылка завершена. Получили: {count} чел.", reply_markup=get_admin_reply_kb())
    await state.clear()

@router.message(F.text == "📊 Моя статистика")
async def stats(m: Message):
    with sqlite3.connect(DB_NAME) as conn:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (m.from_user.id,)).fetchone()[0]
    await m.answer(f"📊 Вы пригласили: {count} чел.")

@router.message(F.text == "🔗 Реферальная ссылка")
async def ref(m: Message):
    me = await bot.get_me()
    await m.answer(f"Твоя ссылка:\nhttps://t.me/{me.username}?start={m.from_user.id}")

@router.message(F.text == "🔙 Назад")
async def back(m: Message):
    await m.answer("Главное меню", reply_markup=get_main_reply_kb(m.from_user.id))

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
