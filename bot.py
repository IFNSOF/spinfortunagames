import json
import os
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiohttp import web

# === НАСТРОЙКИ ===
TOKEN = "8499397849:AAGgiXQhk6Wq0vIYFxMKicZwoIBFoqZNWJk"             # <-- сюда токен
ADMIN_ID = 7816374758            # <-- сюда свой ID
CHANNEL_FOR_LOGS = "@wnref"  # <-- канал для авто сообщений
START_DATE = "27.10.2025"
OWNER = "@winikson"
SUPPORT = "@winiksona"

DATA_FILE = "data.json"
CHANNELS_FILE = "channels.json"

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# === JSON база ===
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f: json.dump(default, f)
    with open(file) as f: return json.load(f)
def save_json(file, d): open(file, "w").write(json.dumps(d, indent=2))
def load_data(): return load_json(DATA_FILE, {})
def save_data(d): save_json(DATA_FILE, d)
def load_channels(): return load_json(CHANNELS_FILE, ["@example_channel"])
def save_channels(c): save_json(CHANNELS_FILE, c)

# === Проверка подписки ===
async def check_subscription(uid):
    for ch in load_channels():
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status not in ("member", "administrator", "creator"):
                return False
        except: return False
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
        return await msg.answer(f"⚠️ Подпишитесь на канал(ы):\n" + "\n".join(load_channels()))
    # Реферальная награда
    if ref and ref in data and ref != uid:
        data[ref]["balance"] += 1000; save_data(data)
        await bot.send_message(ref, f"👥 Новый реферал: {msg.from_user.full_name} +1000 Gram")
    await msg.answer("🎰 Добро пожаловать!", reply_markup=main_menu())

# === Игра ===
@dp.message_handler(lambda m: m.text == "🎲 Играть")
async def play(msg: types.Message):
    await msg.answer("Введите ставку:")

    @dp.message_handler(lambda m: m.text.isdigit())
    async def bet(m: types.Message):
        d = load_data(); uid = str(m.from_user.id); bet = int(m.text)
        if d[uid]["balance"] < bet: return await m.answer("Недостаточно средств!")
        await m.answer("🎲 Кидаем кубики...")
        user = await m.answer_dice("🎲"); await asyncio.sleep(4)
        botd = await m.answer_dice("🎲"); await asyncio.sleep(4)
        u, b = user.dice.value, botd.dice.value
        if u > b: d[uid]["balance"] += bet; res=f"Вы выиграли! +{bet}"
        elif u < b: d[uid]["balance"] -= bet; res=f"Вы проиграли! -{bet}"
        else: res="Ничья!"
        save_data(d); await m.answer(res, reply_markup=main_menu())

# === Профиль ===
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    d=load_data();u=d[str(msg.from_user.id)]
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💵 Пополнить","💸 Вывести");kb.add("🎁 Заработать","🔙 Назад")
    await msg.answer(f"<b>👤 Профиль</b>\nНик: {u['name']}\nID: {msg.from_user.id}\nБаланс: {u['balance']} Gram",reply_markup=kb)

@dp.message_handler(lambda m:m.text=="🔙 Назад")
async def back(m): await m.answer("Главное меню",reply_markup=main_menu())

# === Ежедневный бонус ===
@dp.message_handler(lambda m:m.text=="💰 Ежедневный бонус")
async def bonus(m):
    d=load_data();uid=str(m.from_user.id);now=datetime.now().strftime("%Y-%m-%d")
    if d[uid]["last_bonus"]!=now:
        d[uid]["balance"]+=500;d[uid]["last_bonus"]=now;save_data(d)
        await m.answer("🎁 +500 Gram!")
    else: await m.answer("⏳ Раз в день!")

# === Статистика ===
@dp.message_handler(lambda m:m.text=="📊 Статистика")
async def stats(m):
    d=load_data()
    await m.answer(f"📊 Статистика\nДата старта: {START_DATE}\nВладелец: {OWNER}\nПоддержка: {SUPPORT}\nВсего пользователей: {len(d)}")

# === Поддержка ===
@dp.message_handler(lambda m:m.text=="🆘 Поддержка")
async def support(m):
    await m.answer("✍️ Опиши проблему:")
    @dp.message_handler()
    async def sup(msg:types.Message):
        kb=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✉️ Ответить",callback_data=f"reply_{msg.from_user.id}"))
        await bot.send_message(ADMIN_ID,f"📩 От {msg.from_user.full_name} ({msg.from_user.id}):\n{msg.text}",reply_markup=kb)
        await msg.answer("✅ Отправлено!",reply_markup=main_menu())

# === CALLBACK админ ===
@dp.callback_query_handler(lambda c:True)
async def cb(c:types.CallbackQuery):
    d=load_data();data=c.data
    if data.startswith("reply_"):
        uid=int(data.split("_")[1])
        await bot.send_message(ADMIN_ID,f"Введите ответ для {uid}:")
        @dp.message_handler()
        async def ans(m:types.Message):
            await bot.send_message(uid,f"💬 Ответ от админа:\n{m.text}")
            await m.answer("✅ Отправлено!")
    elif data.startswith("add_"):
        uid,s=data.split("_")[1],int(data.split("_")[2]);d[uid]["balance"]+=s;save_data(d)
        await bot.send_message(int(uid),f"✅ Пополнение +{s} Gram")
        await c.message.edit_text("✅ Подтверждено.")
    elif data.startswith("deny_"):
        await bot.send_message(int(data.split("_")[1]),"❌ Пополнение отклонено.");await c.message.edit_text("❌ Отказано.")
    elif data.startswith("wdok_"):
        uid,s=data.split("_")[1],int(data.split("_")[2])
        await bot.send_message(int(uid),f"✅ Вывод {s} Gram подтвержден!")
        try: await bot.send_message(CHANNEL_FOR_LOGS,"💸 Игрок сделал вывод с бота 💸")
        except: pass
        await c.message.edit_text("✅ Подтверждено.")
    elif data.startswith("wderr_"):
        uid,s=data.split("_")[1],int(data.split("_")[2])
        d[uid]["balance"]+=s;save_data(d)
        await bot.send_message(int(uid),"❌ Вывод отклонен, средства возвращены.")
        await c.message.edit_text("❌ Отказано.")

# === Автопост в канал ===
async def auto_post():
    while True:
        try: await bot.send_message(CHANNEL_FOR_LOGS,"💸 Игрок сделал вывод с бота 💸")
        except: pass
        await asyncio.sleep(random.randint(300,600))

# === Flask/AIOHTTP для Koyeb ===
app=web.Application()
async def handle(req): return web.Response(text="Bot running on port 8000")
app.add_routes([web.get("/",handle)])

# === Запуск ===
async def start_all():
    loop=asyncio.get_event_loop()
    loop.create_task(auto_post())
    runner=web.AppRunner(app);await runner.setup()
    site=web.TCPSite(runner,"0.0.0.0",8000);await site.start()
    print("✅ Bot started on 8000")
    await executor.start_polling(dp,skip_updates=True)

if __name__=="__main__":
    asyncio.get_event_loop().run_until_complete(start_all())
