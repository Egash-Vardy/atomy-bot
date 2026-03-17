import asyncio, sqlite3, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
API_TOKEN = "8649187707:AAGOBrbr5oaL7Z-bynQk2_sclF6Rt49QjDo"
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# --- БАЗА ---
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


# --- УВЕДОМЛЕНИЕ АДМИНОВ ---
async def notify_admins():
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm, "✅ Бот запущен")
        except:
            pass


# --- /START ---
@dp.message(CommandStart())
async def cmd_start(m: types.Message):

    uid = m.from_user.id
    name = m.from_user.full_name
    username = m.from_user.username

    ref = None
    if len(m.text.split()) > 1:
        ref = m.text.split()[1]

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cur.fetchone():

        cur.execute(
            "INSERT INTO users VALUES(?,?,?,?,?)",
            (uid, name, username, ref, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )

    conn.commit()
    conn.close()

    kb = [
        [
            KeyboardButton(text="📊 Моя статистика"),
            KeyboardButton(text="🔗 Реферальная ссылка")
        ]
    ]

    if uid in ADMIN_IDS:
        kb.append([KeyboardButton(text="⚙️ Админ панель")])

    text = (
        f"{name}, добро пожаловать в чат!\n\n"
        "Рады видеть тебя. Это пространство для тех, кто хочет развиваться, "
        "расти и выстраивать доход в комфортном темпе.\n\n"
        "Здесь: поддержка, честно про деньги и возможности — без давления и спешки, "
        "с уважением к каждому.\n\n"
        "Если ты хочешь в команду, напиши в чат «+» — подскажем, с чего лучше начать.\n\n"
        "Рады, что ты с нами."
    )

    await m.answer(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )


# --- СТАТИСТИКА ---
@dp.message(F.text == "📊 Моя статистика")
async def stats(m: types.Message):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT name,username FROM users WHERE referrer_id=?",
        (m.from_user.id,)
    )

    rows = cur.fetchall()
    conn.close()

    if not rows:
        await m.answer("📊 У вас нет приглашённых.")
        return

    text = f"📊 Вы пригласили: {len(rows)}\n\n"

    for i, r in enumerate(rows):
        if r[1]:
            text += f"{i+1}. @{r[1]}\n"
        else:
            text += f"{i+1}. {r[0]}\n"

    await m.answer(text)


# --- РЕФ ССЫЛКА ---
@dp.message(F.text == "🔗 Реферальная ссылка")
async def ref(m: types.Message):

    me = await bot.get_me()

    await m.answer(
        f"Ваша ссылка:\nhttps://t.me/{me.username}?start={m.from_user.id}"
    )


# --- АДМИН ПАНЕЛЬ ---
@dp.message(F.text == "⚙️ Админ панель")
async def admin_panel(m: types.Message):

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
        "⚙️ Админ панель\n\n"
        f"👥 Пользователей: {total}\n"
        f"🤝 Приглашённых: {refs}"
    )

    await m.answer(text)


# --- ОБЩИЙ ЧАТ ---
@dp.message(F.chat.type == "private")
async def messages(m: types.Message):

    if m.from_user.id in ADMIN_IDS:
        return

    if not m.text:
        return

    # --- "+" ---
    if m.text.strip() == "+":

        name = m.from_user.first_name

        for adm in ADMIN_IDS:
            await bot.send_message(
                adm,
                f"🔥 Отклик +\n{m.from_user.full_name}\nID:{m.from_user.id}"
            )

        text = f"""Спасибо, {name}!

Отлично, ты готова сделать первый шаг.

Давай начнём с простого: я расскажу, какие возможности у нас есть и как комфортно подключиться к команде.

Сначала небольшая рекомендация:

1. Ознакомься с нашим чек-листом для старта.
2. Потом мы выберем направление.

Хочешь, чтобы я отправила его сейчас?
"""

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="yes")],
                [InlineKeyboardButton(text="Уже есть чек-лист", callback_data="have")]
            ]
        )

        await m.answer(text, reply_markup=kb)
        return

    # сообщение админу
    for adm in ADMIN_IDS:
        await bot.send_message(
            adm,
            f"📩 Сообщение\n{m.from_user.full_name}\n{m.text}"
        )


# --- КНОПКИ ---

@dp.callback_query(F.data == "yes")
async def checklist(cb: types.CallbackQuery):

    name = cb.from_user.first_name

    text = f"""Супер, {name}!

Вот твой чек-лист для старта:

1. Ознакомься с возможностями
2. Выбери путь
3. Начни действовать

Хочешь выбрать направление?
"""

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="choose")]
        ]
    )

    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "choose")
async def choose(cb: types.CallbackQuery):

    name = cb.from_user.first_name

    text = f"""Замечательно, {name}!

Скачать чек-лист:
https://docs.google.com/document/d/1lfw0xlnBjAOqMpo6utmjQ2w1QzFs7APON9WnJc_qI1w/edit?usp=sharing

Что тебе ближе?
"""

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Бизнес", callback_data="biz")],
            [InlineKeyboardButton(text="Покупки", callback_data="shop")]
        ]
    )

    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "biz")
async def biz(cb: types.CallbackQuery):

    name = cb.from_user.first_name

    text = f"""Супер, {name}!

Начнём твой старт в бизнесе.

1. Я пришлю инструкцию
2. Помогу построить план
3. Буду сопровождать

Скоро напишу тебе лично.
"""

    await cb.message.answer(text)
    await cb.answer()


@dp.callback_query(F.data == "shop")
async def shop(cb: types.CallbackQuery):

    name = cb.from_user.first_name

    text = f"""Прекрасно, {name}!

Начнём с покупок.

1. Я пришлю список продуктов
2. Помогу сделать заказ
3. Покажу как получать бонусы

Скоро напишу тебе лично.
"""

    await cb.message.answer(text)
    await cb.answer()


@dp.callback_query(F.data == "have")
async def have(cb: types.CallbackQuery):

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Бизнес", callback_data="biz")],
            [InlineKeyboardButton(text="Покупки", callback_data="shop")]
        ]
    )

    await cb.message.answer(
        "Тогда выбери направление:",
        reply_markup=kb
    )

    await cb.answer()


# --- ЗАПУСК ---
async def main():
    await notify_admins()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
