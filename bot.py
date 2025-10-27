import json
import os
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiohttp import web

# === Настройки ===
TOKEN = "8499397849:AAGgiXQhk6Wq0vIYFxMKicZwoIBFoqZNWJk"
ADMIN_ID = 7816374758
DATA_FILE = "data.json"
CHANNELS_FILE = "channels.json"
START_DATE = "18.10.2025"
OWNER = "@winikson"
SUPPORT = "@winiksona"
CHANNEL_FOR_LOGS = "@wnref"  # канал, куда бот шлет “Игрок сделал вывод с бота”

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# === JSON база ===
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_data(): return load_json(DATA_FILE, {})
def save_data(d): save_json(DATA_FILE, d)
def load_channels(): return load_json(CHANNELS_FILE, ["@example_channel"])
def save_channels(c): save_json(CHANNELS_FILE, c)

# === Проверка подписки ===
async def check_subscription(user_id):
    for ch in load_channels():
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except:
            return False
    return True

# === Главное меню ===
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎲 Играть", "👤 Профиль")
    kb.add("💰 Ежедневный бонус", "📊 Статистика")
    kb.add("🆘 Поддержка")
    return kb

# === Старт ===
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    data = load_data()
    uid = str(msg.from_user.id)
    ref = msg.text.split(" ")[1] if len(msg.text.split()) > 1 else None
    if uid not in data:
        data[uid] = {"name": msg.from_user.full_name, "balance": 0, "ref": ref, "last_bonus": "0"}
    save_data(data)

    if not await check_subscription(msg.from_user.id):
        chs = "\n".join(load_channels())
        return await msg.answer(f"⚠️ Подпишитесь на канал(ы):\n{chs}")

    # Реферальная система
    if ref and ref in data and ref != uid:
        data[ref]["balance"] += 1000
        save_data(data)
        await bot.send_message(ref, f"👤 Новый реферал: {msg.from_user.full_name} +1000 Gram!")

    await msg.answer("🎰 Добро пожаловать!", reply_markup=main_menu())

# === Игра ===
@dp.message_handler(lambda m: m.text == "🎲 Играть")
async def play(msg: types.Message):
    await msg.answer("Введите ставку:")

    @dp.message_handler(lambda m: m.text.isdigit())
    async def bet(m: types.Message):
        data = load_data()
        uid = str(m.from_user.id)
        bet = int(m.text)
        if data[uid]["balance"] < bet:
            return await m.answer("Недостаточно средств!")

        await m.answer("🎲 Кидаем кубики...")
        user_dice = await m.answer_dice("🎲")
        await asyncio.sleep(4)
        bot_dice = await m.answer_dice("🎲")
        await asyncio.sleep(4)

        u, b = user_dice.dice.value, bot_dice.dice.value
        if u > b:
            data[uid]["balance"] += bet
            res = f"Вы выиграли! +{bet}💰"
        elif u < b:
            data[uid]["balance"] -= bet
            res = f"Вы проиграли! -{bet}💰"
        else:
            res = "Ничья!"
        save_data(data)
        await m.answer(res, reply_markup=main_menu())

# === Профиль ===
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def prof(msg: types.Message):
    d = load_data()
    u = d[str(msg.from_user.id)]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💵 Пополнить", "💸 Вывести")
    kb.add("🎁 Заработать", "🔙 Назад")
    await msg.answer(f"<b>👤 Профиль</b>\nНик: {u['name']}\nID: {msg.from_user.id}\nБаланс: {u['balance']} Gram",
                     reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🔙 Назад")
async def back(msg: types.Message): await msg.answer("Главное меню", reply_markup=main_menu())

# === Пополнить ===
@dp.message_handler(lambda m: m.text == "💵 Пополнить")
async def depo(msg: types.Message):
    await msg.answer("Введите сумму для пополнения:")

    @dp.message_handler(lambda m: m.text.isdigit())
    async def get_sum(m: types.Message):
        sum_ = int(m.text)
        await m.answer("Отправьте ссылку на чек:")
        @dp.message_handler()
        async def get_check(x: types.Message):
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"add_{x.from_user.id}_{sum_}"))
            kb.add(types.InlineKeyboardButton("❌ Отказать", callback_data=f"deny_{x.from_user.id}_{sum_}"))
            await bot.send_message(ADMIN_ID, f"💰 Пополнение {sum_} Gram от {x.from_user.full_name} ({x.from_user.id})\nЧек: {x.text}", reply_markup=kb)
            await x.answer("✅ Заявка отправлена админу!", reply_markup=main_menu())

# === Вывести ===
@dp.message_handler(lambda m: m.text == "💸 Вывести")
async def withdraw(msg: types.Message):
    await msg.answer("Введите сумму для вывода:")

    @dp.message_handler(lambda m: m.text.isdigit())
    async def with_sum(m: types.Message):
        s = int(m.text)
        d = load_data()
        uid = str(m.from_user.id)
        if d[uid]["balance"] < s:
            return await m.answer("Недостаточно средств!")
        d[uid]["balance"] -= s
        save_data(d)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"wdok_{uid}_{s}"))
        kb.add(types.InlineKeyboardButton("❌ Отказать", callback_data=f"wderr_{uid}_{s}"))
        await bot.send_message(ADMIN_ID, f"💸 Заявка на вывод {s} Gram от {m.from_user.full_name} ({uid})", reply_markup=kb)
        await m.answer("✅ Заявка отправлена админу!", reply_markup=main_menu())

# === Ежедневный бонус ===
@dp.message_handler(lambda m: m.text == "💰 Ежедневный бонус")
async def bonus(msg: types.Message):
    d = load_data()
    uid = str(msg.from_user.id)
    now = datetime.now().strftime("%Y-%m-%d")
    if d[uid]["last_bonus"] != now:
        d[uid]["balance"] += 500
        d[uid]["last_bonus"] = now
        save_data(d)
        await msg.answer("🎁 Вы получили 500 Gram!")
    else:
        await msg.answer("⏳ Бонус доступен раз в день!")

# === Статистика ===
@dp.message_handler(lambda m: m.text == "📊 Статистика")
async def stat(msg: types.Message):
    d = load_data()
    await msg.answer(f"📊 Статистика\nДата старта: {START_DATE}\nВладелец: {OWNER}\nПоддержка: {SUPPORT}\nВсего пользователей: {len(d)}")

# === Поддержка ===
@dp.message_handler(lambda m: m.text == "🆘 Поддержка")
async def supp(msg: types.Message):
    await msg.answer("✍️ Напиши свою проблему:")
    @dp.message_handler()
    async def send_support(m: types.Message):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_{m.from_user.id}"))
        await bot.send_message(ADMIN_ID, f"📩 От {m.from_user.full_name} ({m.from_user.id}):\n{m.text}", reply_markup=kb)
        await m.answer("✅ Отправлено в поддержку!", reply_markup=main_menu())

# === CALLBACK кнопки админа ===
@dp.callback_query_handler(lambda c: True)
async def callbacks(c: types.CallbackQuery):
    d = load_data()
    if c.data.startswith("add_"):
        uid, s = c.data.split("_")[1], int(c.data.split("_")[2])
        d[uid]["balance"] += s
        save_data(d)
        await bot.send_message(int(uid), f"✅ Пополнение +{s} Gram подтверждено!")
        await c.message.edit_text("✅ Подтверждено.")
    elif c.data.startswith("deny_"):
        await bot.send_message(int(c.data.split("_")[1]), "❌ Пополнение отклонено.")
        await c.message.edit_text("❌ Отказано.")
    elif c.data.startswith("wdok_"):
        uid, s = c.data.split("_")[1], int(c.data.split("_")[2])
        await bot.send_message(int(uid), f"✅ Вывод {s} Gram подтвержден!")
        await bot.send_message(CHANNEL_FOR_LOGS, "💸 Игрок сделал вывод с бота 💸")
        await c.message.edit_text("✅ Подтверждено.")
    elif c.data.startswith("wderr_"):
        uid, s = c.data.split("_")[1], int(c.data.split("_")[2])
        d[uid]["balance"] += s
        save_data(d)
        await bot.send_message(int(uid), "❌ Вывод отклонён, средства возвращены.")
        await c.message.edit_text("❌ Отказано.")
    elif c.data.startswith("reply_"):
        uid = int(c.data.split("_")[1])
        await bot.send_message(ADMIN_ID, f"Ответ для {uid}:")
        @dp.message_handler()
        async def send_ans(m: types.Message):
            await bot.send_message(uid, f"💬 Ответ от админа:\n{m.text}")
            await m.answer("✅ Отправлено!")

# === Автопост в канал каждые 5-10 мин ===
async def auto_post():
    while True:
        try:
            await bot.send_message(CHANNEL_FOR_LOGS, "💸 Игрок сделал вывод с бота 💸")
        except: pass
        await asyncio.sleep(random.randint(300, 600))

# === Flask-сервер для Koyeb ===
app = web.Application()
async def handle(request): return web.Response(text="Bot OK on Koyeb 8000")
app.add_routes([web.get("/", handle)])

async def main():
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True))
    loop.create_task(auto_post())
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    print("✅ Bot started on port 8000")
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
