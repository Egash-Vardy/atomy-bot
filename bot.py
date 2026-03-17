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
        except:
            pass


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
        f"{name}, добро пожаловать в чат!\n\n"
        "Рады видеть тебя. Это пространство для тех, кто хочет развиваться, "
        "расти и выстраивать доход в комфортном темпе.\n\n"
        "Здесь: поддержка, честно про деньги и возможности — без давления и спешки, "
        "с уважением к каждому.\n\n"
        "Если ты хочешь в команду, напиши в чат «+» — подскажем, с чего лучше начать.\n\n"
        "Рады, что ты с нами."
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
        await m.answer("📊 У вас нет приглашённых.")
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
    await m.answer(f"Ваша ссылка:\n{link}")


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

    text = f"⚙️ Админ панель\n\n👥 Пользователей: {total}\n🤝 Приглашённых: {refs}"
    await m.answer(text)


# ─── Обработка всех сообщений в ЛС ────────────────────────────
@router.message(F.chat.type == "private")
async def any_private_message(m: Message):
    if m.from_user.id in ADMIN_IDS:
        return

    if not m.text:
        return

    text = m.text.strip()

    if text == "+":
        name = m.from_user.first_name or "Без имени"
        full_name = m.from_user.full_name
        user_id = m.from_user.id
        username = f"@{m.from_user.username}" if m.from_user.username else "нет"

        # Яркое уведомление админам (вариант 3)
        for adm in ADMIN_IDS:
            try:
                kb_admin = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✉️ Написать сразу",
                        url=f"tg://user?id={user_id}"
                    )],
                    [InlineKeyboardButton(
                        text="👤 Профиль",
                        url=f"https://t.me/{m.from_user.username}" if m.from_user.username else "https://t.me"
                    )]
                ])

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

        # Ответ пользователю
        reply_text = f"""Спасибо, {name}! 💪

Ты сделала крутой шаг — мы уже в деле!

Сейчас кто-то из команды свяжется с тобой лично и расскажет:
• как комфортно стартовать
• какие варианты подходят именно тебе
• что делать дальше без спешки и давления

Пока ждёшь — можешь сказать, что тебе интереснее всего: бизнес, покупки или пока просто посмотреть? ❤️

(или просто подожди сообщения от нас)"""

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Бизнес выглядит круто", callback_data="biz"),
                InlineKeyboardButton(text="Покупки и бонусы", callback_data="shop")
            ],
            [InlineKeyboardButton(text="Пришли чек-лист", callback_data="yes")]
        ])

        await m.answer(reply_text, reply_markup=kb)
        return

    # Все остальные сообщения — пересылаем админам
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                f"📩 Сообщение от {m.from_user.full_name} (id {m.from_user.id})\n\n{m.text}"
            )
        except:
            pass


# ─── Inline-кнопки ────────────────────────────────────────────
@router.callback_query(F.data == "yes")
async def callback_yes(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = f"""Супер, {name}!

Вот твой чек-лист для старта:

1. Ознакомься с возможностями
2. Выбери путь
3. Начни действовать

Хочешь выбрать направление?"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="choose")],
    ])

    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "have")
async def callback_have(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="shop")],
    ])

    await cb.message.answer("Тогда выбери направление:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "choose")
async def callback_choose(cb: CallbackQuery):
    name = cb.from_user.first_name
    text = f"""Замечательно, {name}!

Скачать чек-лист:
https://docs.google.com/document/d/1lfw0xlnBjAOqMpo6utmjQ2w1QzFs7APON9WnJc_qI1w/edit?usp=sharing

Что тебе ближе?"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бизнес", callback_data="biz")],
        [InlineKeyboardButton(text="Покупки", callback_data="shop")],
    ])

    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.in_({"biz", "shop"}))
async def callback_direction(cb: CallbackQuery):
    name = cb.from_user.first_name
    direction = "бизнесе" if cb.data == "biz" else "покупках"

    text = f"""Супер, {name}!

Начнём твой старт в {direction}.

1. Я пришлю инструкцию
2. Помогу построить план / сделать заказ
3. Буду сопровождать

Скоро напишу тебе лично.
"""

    await cb.message.answer(text)
    await cb.answer()


# ─── ЗАПУСК ───────────────────────────────────────────────────
async def main():
    await notify_admins()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
