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

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
dp.include_router(router)


# Реальные публичные ссылки на стикеры (webp / tgs)
# Взяты из официальных паков Telegram — работают без загрузки
STICKER_WELCOME = "https://t.me/addstickers/AnimatedRocket/rocket.webp"          # ракета / приветствие
STICKER_THANK   = "https://t.me/addstickers/AnimatedHearts/heart_red.tgs"       # красное сердце (анимация)
STICKER_FIRE    = "https://t.me/addstickers/FireEmoji/fire.webp"                # огонь
STICKER_WAIT    = "https://t.me/addstickers/CoffeeBreak/coffee.tgs"             # кофе / подожди
STICKER_GOOD    = "https://t.me/addstickers/OkEmoji/ok_hand.webp"               # ок / супер


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
            await bot.send_sticker(adm, STICKER_FIRE)
            await bot.send_message(adm, "✅ Бот запущен")
        except Exception as e:
            logging.error(f"Ошибка уведомления админа {adm}: {e}")


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
        "Здесь: поддержка, честно про деньги и возможности — без давления и спешки, "
        "с уважением к каждому.\n\n"
        "Если ты хочешь в команду, напиши в чат «+» — подскажем, с чего лучше начать.\n\n"
        "Рады, что ты с нами ❤️"
    )

    try:
        await bot.send_sticker(m.chat.id, STICKER_WELCOME)
    except:
        pass  # если стикер не загрузится — не падает бот

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
        await bot.send_sticker(m.chat.id, STICKER_WAIT)
        await m.answer("📊 У вас пока нет приглашённых.")
        return

    text = f"📊 Вы пригласили: {len(rows)}\n\n"
    for i, (name, username) in enumerate(rows, 1):
        text += f"{i}. @{username}\n" if username else f"{i}. {name}\n"

    await bot.send_sticker(m.chat.id, STICKER_GOOD)
    await m.answer(text)


# ─── Реферальная ссылка ──────────────────────────────────────
@router.message(F.text == "🔗 Реферальная ссылка")
async def ref_link(m: Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    await bot.send_sticker(m.chat.id, STICKER_FIRE)
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

    text = (
        f"⚙️ Админ панель\n\n"
        f"👥 Всего пользователей: {total}\n"
        f"🤝 Приглашённых: {refs}\n\n"
        "Выберите действие:"
    )

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )

    await bot.send_sticker(m.chat.id, STICKER_GOOD)
    await m.answer(text, reply_markup=kb)


# ─── Обработка всех сообщений в ЛС ────────────────────────────
@router.message(F.chat.type == "private")
async def any_private_message(m: Message):
    uid = m.from_user.id

    if uid in ADMIN_IDS:
        return

    if not m.text:
        return

    text = m.text.strip()

    if text == "+":
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

                await bot.send_sticker(adm, STICKER_FIRE)
                await bot.send_message(
                    adm,
                    f"🚨 НОВЫЙ + ОТКЛИК 🚨\n\n"
                    f"👤 {full_name}\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"📛 {username}\n"
                    f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Готов(а) присоединиться к команде! 🔥",
                    reply_markup=kb_admin,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Ошибка отправки админу {adm}: {e}")

        # Ответ пользователю + кнопки
        reply_text = f"""Спасибо, {name}! 💪

Ты сделала крутой шаг — мы уже в деле!

Сейчас кто-то из команды свяжется с тобой и расскажет, как комфортно начать.

А пока выбери, что тебе ближе всего:
"""

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1. Бизнес", callback_data="biz")],
            [InlineKeyboardButton(text="2. Покупки", callback_data="shop")],
            [InlineKeyboardButton(text="3. Чек-лист", callback_data="yes")]
        ])

        await bot.send_sticker(m.chat.id, STICKER_THANK)
        await m.answer(reply_text, reply_markup=kb)
        return

    # Остальные сообщения — админам
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                f"📩 Сообщение от {m.from_user.full_name} (id {uid})\n\n{m.text}"
            )
        except:
            pass


# ─── Inline-кнопки ────────────────────────────────────────────
@router.callback_query(F.data == "yes")
async def callback_yes(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = f"""Вот твой чек-лист для старта:\n\nЧЕК-ЛИСТ[](https://clipr.cc/RC4rz)"""

    await bot.send_sticker(cb.message.chat.id, STICKER_GOOD)
    await cb.message.answer(text)
    await cb.answer()


@router.callback_query(F.data.in_({"biz", "shop"}))
async def callback_direction(cb: CallbackQuery):
    name = cb.from_user.first_name
    direction = "бизнесе" if cb.data == "biz" else "покупках"

    text = f"""Супер, {name}!

Начнём твой старт в {direction}.

Скоро свяжусь с тобой лично и пришлю всё необходимое 🚀"""

    await bot.send_sticker(cb.message.chat.id, STICKER_FIRE)
    await cb.message.answer(text)
    await cb.answer()


# ─── ЗАПУСК ───────────────────────────────────────────────────
async def main():
    await notify_admins()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
