import asyncio
import sqlite3
import logging
from datetime import datetime

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

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
API_TOKEN = "8649187707:AAGOBrbr5oaL7Z-bynQk2_sclF6Rt49QjDo"
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
dp.include_router(router)

# ─── БАЗА ДАННЫХ ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            referrer_id INTEGER,
            reg_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ─── УВЕДОМЛЕНИЕ АДМИНОВ ПРИ ЗАПУСКЕ ──────────────────────────
async def notify_admins():
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm, "✅ Бот запущен")
        except Exception as e:
            logger.error(f"Ошибка уведомления админа {adm}: {e}")

# ─── /start ───────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(m: Message):
    uid = m.from_user.id
    name = m.from_user.full_name
    username = m.from_user.username or None

    ref = None
    if len(m.text.split()) > 1:
        try:
            ref = int(m.text.split()[1])
        except ValueError:
            pass

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, name, username, referrer_id, reg_date) VALUES (?, ?, ?, ?, ?)",
            (uid, name, username, ref, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
    conn.commit()
    conn.close()

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🔗 Реферальная ссылка")],
        ],
        resize_keyboard=True,
    )

    if uid in ADMIN_IDS:
        kb.keyboard.append([KeyboardButton(text="⚙️ Админ панель")])

    text = (
        f"{name}, добро пожаловать в чат! 🚀\n\n"
        "Рады видеть тебя. Это пространство для тех, кто хочет развиваться, "
        "расти и выстраивать доход в комфортном темпе.\n\n"
        "Если ты хочешь в команду, напиши «+» — подскажем, с чего начать.\n\n"
        "Рады, что ты с нами ❤️"
    )

    await m.answer(text, reply_markup=kb)

# ─── Статистика ───────────────────────────────────────────────
@router.message(F.text == "📊 Моя статистика")
async def stats(m: Message):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name, username FROM users WHERE referrer_id = ?", (m.from_user.id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await m.answer("📊 У вас пока нет приглашённых.")
        return

    text = f"📊 Вы пригласили: {len(rows)}\n\n"
    for i, (name, username) in enumerate(rows, 1):
        text += f"{i}. @{username}\n" if username else f"{i}. {name}\n"

    await m.answer(text)

# ─── Реферальная ссылка ──────────────────────────────────────
@router.message(F.text == "🔗 Реферальная ссылка")
async def ref_link(m: Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    await m.answer(f"Твоя реферальная ссылка:\n{link}")

# ─── Админ-панель ─────────────────────────────────────────────
@router.message(F.text == "⚙️ Админ панель")
async def admin_panel(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL")
    refs = cur.fetchone()[0]
    conn.close()

    text = f"⚙️ Админ панель\n\n👥 Всего: {total}\n🤝 Приглашённых: {refs}"
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )

    await m.answer(text, reply_markup=kb)

# ─── Главный обработчик сообщений в ЛС ────────────────────────
@router.message(F.chat.type == "private")
async def any_private_message(m: Message):
    uid = m.from_user.id
    text = (m.text or "").strip()

    logger.info(f"Получено сообщение от {uid}: '{text}'")

    if uid in ADMIN_IDS:
        logger.info("Сообщение от админа — пропускаем обработку")
        return

    if not text:
        logger.info("Сообщение пустое или без текста — игнор")
        return

    if text == "+":
        logger.info(f"Обнаружен '+' от пользователя {uid}")

        name = m.from_user.first_name or "Без имени"
        full_name = m.from_user.full_name
        user_id = m.from_user.id
        username = f"@{m.from_user.username}" if m.from_user.username else "нет"

        # Уведомление админам
        for adm in ADMIN_IDS:
            try:
                kb_admin = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✉️ Написать сразу", url=f"tg://user?id={user_id}")],
                    [InlineKeyboardButton(text="👤 Профиль", url=f"https://t.me/{m.from_user.username}" if m.from_user.username else "https://t.me")]
                ])

                await bot.send_message(
                    adm,
                    f"🚨 НОВЫЙ + ОТКЛИК 🚨\n\n"
                    f"👤 {full_name}\n"
                    f"🆔 {user_id}\n"
                    f"📛 {username}\n"
                    f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Хочет в команду!",
                    reply_markup=kb_admin,
                    parse_mode="HTML"
                )
                logger.info(f"Уведомление отправлено админу {adm}")
            except Exception as e:
                logger.error(f"Ошибка отправки админу {adm}: {e}")

        # Ответ пользователю
        reply_text = f"""Спасибо, {name}! 💪

Ты сделала крутой шаг!

Сейчас с тобой свяжутся и расскажут, как начать комфортно.

Выбери, что тебе ближе:
"""

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1. Бизнес", callback_data="biz")],
            [InlineKeyboardButton(text="2. Покупки", callback_data="shop")],
            [InlineKeyboardButton(text="3. Чек-лист", callback_data="yes")]
        ])

        await m.answer(reply_text, reply_markup=kb)
        logger.info(f"Ответ с кнопками отправлен пользователю {uid}")
        return

    # Пересылка остальных сообщений админам
    logger.info(f"Пересылаем обычное сообщение от {uid} админам")
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                f"📩 От {m.from_user.full_name} (id {uid})\n\n{text}"
            )
        except Exception as e:
            logger.error(f"Ошибка пересылки админу {adm}: {e}")

# ─── Inline-кнопки ────────────────────────────────────────────
@router.callback_query(F.data == "yes")
async def callback_yes(cb: CallbackQuery):
    text = "Вот твой чек-лист:\n\nЧЕК-ЛИСТ[](https://clipr.cc/RC4rz)"
    await cb.message.answer(text)
    await cb.answer()

@router.callback_query(F.data.in_({"biz", "shop"}))
async def callback_direction(cb: CallbackQuery):
    direction = "бизнесе" if cb.data == "biz" else "покупках"
    text = f"Супер!\nНачнём твой старт в {direction}.\nСкоро свяжусь лично 🚀"
    await cb.message.answer(text)
    await cb.answer()

# ─── ЗАПУСК ───────────────────────────────────────────────────
async def main():
    await notify_admins()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
