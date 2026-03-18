import asyncio
import sqlite3
import logging
import os
from datetime import datetime
from typing import Union, List, Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    ContentType,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

# ─── КОНФИГУРАЦИЯ И НАСТРОЙКИ ────────────────────────────────
API_TOKEN = "8649187707:AAHRB0xnugFsg0Itnlecy7-wqCGPivltz6M"
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"
LOG_FILE = "bot_system.log"

# Настройка логирования (в консоль и в файл)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── СОСТОЯНИЯ (FSM) ──────────────────────────────────────────
class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    confirm_broadcast = State()

class UserStates(StatesGroup):
    viewing_content = State()

# ─── КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ──────────────────────────
class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_table()

    def _execute(self, query: str, params: tuple = (), fetch: bool = False):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()

    def _create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            referrer_id INTEGER,
            reg_date TEXT,
            is_active INTEGER DEFAULT 1
        )
        """
        self._execute(query)

    def add_user(self, uid: int, name: str, username: str, ref_id: int = None):
        check = self._execute("SELECT user_id FROM users WHERE user_id = ?", (uid,), fetch=True)
        if not check:
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query = "INSERT INTO users (user_id, full_name, username, referrer_id, reg_date) VALUES (?, ?, ?, ?, ?)"
            self._execute(query, (uid, name, username, ref_id, date))
            return True
        return False

    def get_stats(self):
        total = self._execute("SELECT COUNT(*) FROM users", fetch=True)[0][0]
        refs = self._execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL", fetch=True)[0][0]
        return total, refs

    def get_all_users(self):
        return self._execute("SELECT user_id FROM users", fetch=True)

db = Database(DB_NAME)

# ─── ИНИЦИАЛИЗАЦИЯ БОТА ───────────────────────────────────────
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────
def main_menu_kb(user_id: int):
    kb = [
        [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🔗 Реферальная ссылка")]
    ]
    if user_id in ADMIN_IDS:
        kb.append([KeyboardButton(text="⚙️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="📈 Детальная статистика")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

# ─── ОБРАБОТЧИКИ ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(m: Message):
    uid = m.from_user.id
    ref_id = None
    args = m.text.split()
    
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1]) if int(args[1]) != uid else None

    is_new = db.add_user(uid, m.from_user.full_name, m.from_user.username, ref_id)
    
    if is_new and ref_id:
        try:
            await bot.send_message(ref_id, f"🔔 По вашей ссылке зарегистрировался новый пользователь: {m.from_user.full_name}")
        except: pass

    welcome_msg = (
        f"Рады видеть тебя, {m.from_user.first_name}! 🚀\n\n"
        "Это пространство для твоего роста. Если ты хочешь в команду, "
        "просто **отправь «+»** в этот чат, и мы начнем."
    )
    await m.answer(welcome_msg, reply_markup=main_menu_kb(uid), parse_mode="Markdown")

@router.message(F.text == "+")
async def process_plus(m: Message):
    uid = m.from_user.id
    name = m.from_user.first_name
    
    # Уведомление админам
    for adm in ADMIN_IDS:
        try:
            admin_btn = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 Профиль", url=f"tg://user?id={uid}")]
            ])
            await bot.send_message(adm, f"🚨 **Новая заявка!**\nОт: {m.from_user.full_name}\nID: `{uid}`", reply_markup=admin_btn, parse_mode="Markdown")
        except: pass

    msg_1 = (
        f"Спасибо, {name}! ❤️\n\n"
        "Ты готова сделать первый шаг. Давай начнём с простого: я расскажу о возможностях.\n\n"
        "Хочешь получить наш чек-лист для старта сейчас?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, присылай ✅", callback_data="get_checklist")],
        [InlineKeyboardButton(text="Уже есть чек-лист 📁", callback_data="already_have_checklist")]
    ])
    await m.answer(msg_1, reply_markup=kb)

@router.callback_query(F.data == "get_checklist")
async def send_checklist(cb: CallbackQuery):
    text = (
        "Супер! ✨ Вот твой первый шаг.\n\n"
        "Чек-лист поможет тебе сориентироваться. Хочешь, чтобы я помогла выбрать направление?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, давай! 🚀", callback_data="choose_direction")]
    ])
    await cb.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.in_({"choose_direction", "already_have_checklist"}))
async def final_step(cb: CallbackQuery):
    url = "https://docs.google.com/document/d/1lfw0xlnBjAOqMpo6utmjQ2w1QzFs7APON9WnJc_qI1w/edit?usp=sharing"
    text = (
        f"Отлично! 💎\n\n[Скачать чек-лист]({url})\n\n"
        "Теперь выбери, что тебе интереснее:\n"
        "• **Бизнес** — построение дохода.\n"
        "• **Покупки** — бонусы и продукты."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="result_biz")],
        [InlineKeyboardButton(text="🛍 Покупки", callback_data="result_shop")]
    ])
    await cb.message.answer(text, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)

@router.callback_query(F.data.startswith("result_"))
async def process_result(cb: CallbackQuery):
    choice = "бизнесе" if "biz" in cb.data else "покупках"
    await cb.message.answer(f"Прекрасно! Мы начнем твой путь в {choice}. Скоро я напишу тебе лично! 📩")
    await cb.answer()

# ─── АДМИНСКАЯ ЛОГИКА (РАССЫЛКА) ──────────────────────────────

@router.message(F.text == "⚙️ Админ панель")
async def cmd_admin(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    total, refs = db.get_stats()
    await m.answer(f"🔐 **Админ-панель**\n\nВсего юзеров: {total}\nРефералов: {refs}", reply_markup=admin_kb(), parse_mode="Markdown")

@router.message(F.text == "📢 Рассылка")
async def start_broadcast(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS: return
    await m.answer("Отправьте сообщение для рассылки (текст, фото или видео):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AdminStates.waiting_for_broadcast_text)

@router.message(AdminStates.waiting_for_broadcast_text)
async def broadcast_content(m: Message, state: FSMContext):
    if m.text == "❌ Отмена":
        await state.clear()
        return await m.answer("Рассылка отменена.", reply_markup=admin_kb())
    
    users = db.get_all_users()
    await m.answer(f"Начинаю рассылку на {len(users)} пользователей...")
    
    count = 0
    for user in users:
        try:
            await m.copy_to(chat_id=user[0])
            count += 1
            await asyncio.sleep(0.05) # Защита от Flood
        except TelegramForbiddenError:
            logger.info(f"Пользователь {user[0]} заблокировал бота.")
        except Exception as e:
            logger.error(f"Ошибка при рассылке {user[0]}: {e}")

    await m.answer(f"✅ Рассылка завершена! Доставлено: {count}", reply_markup=admin_kb())
    await state.clear()

# ─── ПРОЧИЕ КОМАНДЫ ──────────────────────────────────────────

@router.message(F.text == "📊 Моя статистика")
async def my_stats(m: Message):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT full_name, username FROM users WHERE referrer_id = ?", (m.from_user.id,))
    rows = cur.fetchall()
    
    if not rows:
        return await m.answer("У вас пока нет приглашенных партнеров. Поделитесь ссылкой!")
    
    res = f"📊 **Ваша статистика**\nПриглашено: {len(rows)}\n\n"
    for i, r in enumerate(rows[:20], 1):
        name = r[0] if r[0] else "Без имени"
        res += f"{i}. {name}\n"
    await m.answer(res, parse_mode="Markdown")

@router.message(F.text == "🔗 Реферальная ссылка")
async def my_ref(m: Message):
    bot_user = await bot.get_me()
    link = f"https://t.me/{bot_user.username}?start={m.from_user.id}"
    await m.answer(f"Твоя личная ссылка для приглашений:\n`{link}`", parse_mode="Markdown")

@router.message(F.text == "🔙 Назад")
async def back_to_main(m: Message):
    await m.answer("Возвращаемся в главное меню", reply_markup=main_menu_kb(m.from_user.id))

# ─── ЗАПУСК ───────────────────────────────────────────────────
async def main():
    logger.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Уведомление админов о запуске
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 Бот успешно перезапущен!")
        except: pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Бот был остановлен пользователем.")
