import asyncio
import sqlite3
import logging
import sys
from datetime import datetime
from typing import List, Union

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
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

# ─── КОНФИГУРАЦИЯ ─────────────────────────────────────────────
API_TOKEN = "8649187707:AAHRB0xnugFsg0Itnlecy7-wqCGPivltz6M"
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"

# Настройка логирования в файл и консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot_debug.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Состояния для административных функций
class AdminProcess(StatesGroup):
    broadcast_message = State()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ─── КЛАСС РАБОТЫ С ДАННЫМИ (SQLITE3) ─────────────────────────
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
                    reg_date TEXT,
                    status TEXT DEFAULT 'active'
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
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]

    def get_system_stats(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            referrals = cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL").fetchone()[0]
            return total, referrals

db_manager = DataManager(DB_NAME)

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────
def get_main_reply_kb(uid: int):
    struct = [
        [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🔗 Реферальная ссылка")]
    ]
    if uid in ADMIN_IDS:
        struct.append([KeyboardButton(text="⚙️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=struct, resize_keyboard=True)

def get_admin_reply_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="🔙 Назад в меню")]
        ],
        resize_keyboard=True
    )

# ─── ЛОГИКА /START ────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start_handler(m: Message):
    uid = m.from_user.id
    full_name = m.from_user.full_name
    username = m.from_user.username
    
    ref_param = None
    args = m.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_param = int(args[1])

    db_manager.register_user(uid, full_name, username, ref_param)

    welcome_text = (
        "{name}, добро пожаловать в чат!\n\n"
        "Рады видеть тебя. Это пространство для тех, кто хочет развиваться, расти и выстраивать доход в комфортном темпе.\n\n"
        "Здесь: поддержка, честно про деньги и возможности — без давления и спешки, с уважением к каждому.\n\n"
        "Если ты хочешь в команду, напиши в чат «+» — подскажем, с чего лучше начать.\n\n"
        "Рады, что ты с нами."
    )
    await m.answer(welcome_text, reply_markup=get_main_reply_kb(uid))

# ─── ОБРАБОТКА СИМВОЛА "+" ────────────────────────────────────
@router.message(F.text == "+")
async def process_plus_trigger(m: Message):
    uid = m.from_user.id
    first_name = m.from_user.first_name or "Участник"

    # Уведомление администраторов
    for admin_id in ADMIN_IDS:
        try:
            adm_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Связаться", url=f"tg://user?id={uid}")]
            ])
            await bot.send_message(
                admin_id, 
                f"🚨 **НОВЫЙ ОТКЛИК (+)**\n👤 Имя: {m.from_user.full_name}\n🆔 ID: {uid}",
                reply_markup=adm_kb,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа {admin_id}: {e}")

    step_1_text = (
        f"Спасибо, {first_name}! \n\n"
        "Отлично, ты готова сделать первый шаг. \n"
        "Давай начнём с простого: я расскажу, какие возможности у нас есть и как комфортно подключиться к команде.\n\n"
        "Сначала небольшая рекомендация:\n"
        " 1. Ознакомься с нашим чек-листом для старта — он поможет понять, с чего начать.\n"
        " 2. Потом мы вместе выберем направление, которое тебе ближе: развитие бизнеса или покупка для себя.\n\n"
        "Если готова, могу сразу прислать чек-лист и пошаговое руководство, чтобы начать уже сегодня.\n\n"
        "Хочешь, чтобы я отправила его сейчас?"
    )
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="flow_send_checklist")],
        [InlineKeyboardButton(text="Уже есть чек-лист", callback_data="flow_already_have")]
    ])
    await m.answer(step_1_text, reply_markup=ikb)

# ─── ОБРАБОТКА CALLBACKS (ВОРОНКА) ─────────────────────────────
@router.callback_query(F.data == "flow_send_checklist")
async def flow_yes_step(cb: CallbackQuery):
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
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="flow_get_link_and_choice")]
    ])
    await cb.message.answer(text, reply_markup=ikb)
    await cb.answer()

@router.callback_query(F.data == "flow_get_link_and_choice")
async def flow_final_choice(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    doc_link = "https://docs.google.com/document/d/1lfw0xlnBjAOqMpo6utmjQ2w1QzFs7APON9WnJc_qI1w/edit?usp=sharing"
    
    text = (
        f"Замечательно, {name}! \n\n"
        "Вот твой чек-лист для старта — он поможет сделать первые шаги легко и уверенно:\n"
        f"[{doc_link}]\n\n"
        "Теперь давай определимся с первым действием, чтобы начать прямо сегодня:\n"
        " • Если хочешь попробовать себя в бизнесе, я покажу, с чего начать и как строить доход шаг за шагом.\n"
        " • Если хочешь начать с покупок для себя, расскажу, как использовать продукты и получать бонусы уже с первых заказов.\n\n"
        "Что тебе ближе на этом этапе: бизнес или покупки для себя?"
    )
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="final_biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="final_shop")]
    ])
    await cb.message.answer(text, reply_markup=ikb, disable_web_page_preview=True)
    await cb.answer()

@router.callback_query(F.data == "flow_already_have")
async def flow_already_have_step(cb: CallbackQuery):
    name = cb.from_user.first_name or "Участник"
    text = (
        f"Прекрасно, {name}! \n\n"
        "Раз чек-лист у тебя уже есть, давай определимся, с чего начать твой путь:\n"
        " • Развитие бизнеса — я покажу, как строить доход шаг за шагом и подключаться к команде.\n"
        " • Покупки для себя — расскажу, как выгодно использовать продукты и получать бонусы с первых заказов.\n\n"
        "Что тебе ближе на этом этапе: бизнес или покупки для себя?"
    )
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="final_biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="final_shop")]
    ])
    await cb.message.answer(text, reply_markup=ikb)
    await cb.answer()

# ─── ФИНАЛЬНЫЕ ОТВЕТЫ ─────────────────────────────────────────
@router.callback_query(F.data == "final_biz")
async def choice_biz_handler(cb: CallbackQuery):
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

@router.callback_query(F.data == "final_shop")
async def choice_shop_handler(cb: CallbackQuery):
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

# ─── АДМИНИСТРАТИВНЫЙ БЛОК ────────────────────────────────────
@router.message(F.text == "⚙️ Админ панель")
async def admin_panel_entry(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    total, refs = db_manager.get_system_stats()
    await m.answer(
        f"📊 **СТАТИСТИКА СООБЩЕСТВА**\n\nВсего участников: {total}\nПришли по рекомендации: {refs}",
        reply_markup=get_admin_reply_kb(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📢 Рассылка")
async def broadcast_init(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS:
        return
    await m.answer("Отправьте сообщение (текст или медиа) для массовой рассылки:", reply_markup=KeyboardButton(text="Отмена"))
    await state.set_state(AdminProcess.broadcast_message)

@router.message(AdminProcess.broadcast_message)
async def broadcast_execute(m: Message, state: FSMContext):
    if m.text == "Отмена":
        await state.clear()
        return await m.answer("Рассылка отменена.", reply_markup=get_admin_reply_kb())
    
    target_ids = db_manager.fetch_all_ids()
    success_count = 0
    
    await m.answer(f"Начинаю рассылку на {len(target_ids)} контактов...")
    
    for user_id in target_ids:
        try:
            await m.copy_to(chat_id=user_id)
            success_count += 1
            await asyncio.sleep(0.05) # Защита от Flood
        except (TelegramForbiddenError, Exception):
            continue

    await m.answer(f"✅ Рассылка завершена!\nУспешно отправлено: {success_count}", reply_markup=get_admin_reply_kb())
    await state.clear()

# ─── ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ───────────────────────────────────
@router.message(F.text == "📊 Моя статистика")
async def user_personal_stats(m: Message):
    uid = m.from_user.id
    with sqlite3.connect(DB_NAME) as conn:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (uid,)).fetchone()[0]
    await m.answer(f"📊 По твоей ссылке присоединилось: {count} чел.")

@router.message(F.text == "🔗 Реферальная ссылка")
async def user_get_ref_link(m: Message):
    bot_data = await bot.get_me()
    link = f"https://t.me/{bot_data.username}?start={m.from_user.id}"
    await m.answer(f"Твоя персональная ссылка для приглашений:\n`{link}`", parse_mode="Markdown")

@router.message(F.text == "🔙 Назад в меню")
async def back_to_menu_handler(m: Message):
    await m.answer("Возвращаемся в главное меню...", reply_markup=get_main_reply_kb(m.from_user.id))

# ─── ЗАПУСК ПРИЛОЖЕНИЯ ────────────────────────────────────────
async def main():
    logger.info("Инициализация системы и запуск Polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except Exception as exc:
        logger.critical(f"Критическая ошибка при работе бота: {exc}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Бот остановлен вручную.")
