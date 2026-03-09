import asyncio, sqlite3, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
API_TOKEN = '8649187707:AAGOBrbr5oaL7Z-bynQk2_sclF6Rt49QjDo'
ADMIN_IDS = [8065108309, 1613877823]
DB_NAME = "community_pro.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def init_db():
    conn = sqlite3.connect(DB_NAME);
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users 
                   (user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, 
                    referrer_id INTEGER, reg_date TEXT, step INTEGER DEFAULT 0)""")
    conn.commit();
    conn.close()


init_db()


# Уведомление о запуске
async def notify_admins():
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm, "✅ <b>Бот запущен и работает исправно!</b>", parse_mode="HTML")
        except:
            pass


@dp.message(CommandStart())
async def cmd_start(m: types.Message):
    uid, name, uname = m.from_user.id, m.from_user.full_name, m.from_user.username
    ref = m.text.split()[1] if len(m.text.split()) > 1 else None

    conn = sqlite3.connect(DB_NAME);
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (user_id, name, username, referrer_id, reg_date) VALUES (?,?,?,?,?)",
                    (uid, name, uname, ref, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    else:
        cur.execute("UPDATE users SET name = ?, username = ? WHERE user_id = ?", (name, uname, uid))
    conn.commit();
    conn.close()

    kb = [[KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🔗 Реферальная ссылка")]]
    if uid in ADMIN_IDS: kb.append([KeyboardButton(text="⚙️ Админ-панель")])

    welcome_text = (f"{name}, добро пожаловать в чат!\n\n"
                    f"Рады видеть тебя. Это пространство для тех, кто хочет развиваться, "
                    f"расти и выстраивать доход в комфортном темпе.\n\n"
                    f"Здесь: поддержка, честно про деньги и возможности — без давления и спешки, "
                    f"с уважением к каждому.\n\n"
                    f"Если ты хочешь в команду, напиши в чат <b>«+»</b> — подскажем, с чего лучше начать.\n\n"
                    f"Рады, что ты с нами.")
    await m.answer(welcome_text, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True), parse_mode="HTML")


@dp.message(F.text == "📊 Моя статистика")
async def show_stats(m: types.Message):
    conn = sqlite3.connect(DB_NAME);
    cur = conn.cursor()
    cur.execute("SELECT name, username FROM users WHERE referrer_id = ?", (m.from_user.id,))
    refs = cur.fetchall();
    conn.close()
    if not refs: return await m.answer("📊 У вас нет приглашенных.")
    text = f"📊 Вы пригласили: {len(refs)} чел.\n\n" + "\n".join(
        [f"{i + 1}. @{r[1]}" if r[1] else f"{i + 1}. {r[0]}" for i, r in enumerate(refs)])
    await m.answer(text)


@dp.message(F.text == "🔗 Реферальная ссылка")
async def show_link(m: types.Message):
    me = await bot.get_me()
    await m.answer(f"🔗 Ссылка: <code>https://t.me/{me.username}?start={m.from_user.id}</code>", parse_mode="HTML")


@dp.message(F.chat.type == "private")
async def msg_handler(m: types.Message):
    if m.from_user.id in ADMIN_IDS or not m.text: return
    if m.text.strip() == "+":
        for adm in ADMIN_IDS: await bot.send_message(adm,
                                                     f"🔥 ОТКЛИК [+] от {m.from_user.full_name}\nID:{m.from_user.id}")
        return await m.reply("Принято!")
    for adm in ADMIN_IDS: await bot.send_message(adm,
                                                 f"📩 Сообщение от {m.from_user.full_name}\nID:{m.from_user.id}\n\n{m.text}")
    await m.answer("Передано админу.")


async def main():
    await notify_admins()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
