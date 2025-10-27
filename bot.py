import json, os, asyncio, random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters import CommandStart
from aiohttp import web

# === Настройки ===
TOKEN = "8499397849:AAGgiXQhk6Wq0vIYFxMKicZwoIBFoqZNWJk"
ADMIN_ID = 7816374758  # замените на свой ID
DATA_FILE = "data.json"
CHANNELS_FILE = "channels.json"
START_DATE = "27.10.2025"
OWNER = "@winikson"
SUPPORT = "@winiksona"

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === База данных ===
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
    with open(file) as f:
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
            if member.status not in ("member","administrator","creator"):
                return False
        except: return False
    return True

# === Главное меню ===
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎲 Играть")
    kb.button(text="👤 Профиль")
    kb.button(text="💰 Ежедневный бонус")
    kb.button(text="📊 Статистика")
    kb.button(text="🆘 Поддержка")
    return kb.as_markup(resize_keyboard=True)

# === /start ===
@dp.message(CommandStart())
async def start(msg: types.Message):
    data = load_data()
    uid = str(msg.from_user.id)
    ref = msg.text.split(" ")[1] if len(msg.text.split())>1 else None
    if uid not in data:
        data[uid] = {"name": msg.from_user.full_name,"balance":0,"ref":ref,"last_bonus":"0"}
        save_data(data)
    if not await check_subscription(msg.from_user.id):
        chs = "\n".join(load_channels())
        return await msg.answer(f"⚠️ Подпишитесь на канал(ы):\n{chs}")
    await msg.answer("🎰 Добро пожаловать!",reply_markup=main_menu())

# === Игра ===
@dp.message(F.text=="🎲 Играть")
async def play(msg: types.Message):
    await msg.answer("Введите ставку:")
    await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_bet")

@dp.message(state="await_bet")
async def bet(msg: types.Message, state):
    data = load_data()
    uid = str(msg.from_user.id)
    try: bet = int(msg.text)
    except: return await msg.answer("Введите число.")
    if data[uid]["balance"]<bet:
        await msg.answer("Недостаточно средств!");return await state.clear()
    await msg.answer("🎲 Бросаем кубики...")
    user_dice = await msg.answer_dice("🎲")
    await asyncio.sleep(4)
    bot_dice = await msg.answer_dice("🎲")
    await asyncio.sleep(4)
    u,b = user_dice.dice.value, bot_dice.dice.value
    if u>b:
        data[uid]["balance"]+=bet; res=f"Вы выиграли! +{bet}💰"
    elif u<b:
        data[uid]["balance"]-=bet; res=f"Вы проиграли! -{bet}💰"
    else: res="Ничья!"
    save_data(data)
    await msg.answer(res,reply_markup=main_menu())
    await state.clear()

# === Профиль ===
@dp.message(F.text=="👤 Профиль")
async def prof(msg: types.Message):
    d=load_data();u=d[str(msg.from_user.id)]
    kb=ReplyKeyboardBuilder()
    for b in ["💵 Пополнить","💸 Вывести","🎁 Заработать","🔙 Назад"]: kb.button(text=b)
    await msg.answer(f"<b>👤 Профиль</b>\nНик: {u['name']}\nID: {msg.from_user.id}\nБаланс: {u['balance']} Gram",
                     reply_markup=kb.as_markup(resize_keyboard=True))

# === Назад ===
@dp.message(F.text=="🔙 Назад")
async def back(msg: types.Message): await msg.answer("Главное меню",reply_markup=main_menu())

# === Заработать ===
@dp.message(F.text=="🎁 Заработать")
async def earn(msg: types.Message):
    link=f"https://t.me/{(await bot.get_me()).username}?start={msg.from_user.id}"
    await msg.answer(f"🔗 Ваша реферальная ссылка:\n{link}\n\n💎 За каждого подписавшегося реферала: +1000 Gram")

# === Пополнить ===
@dp.message(F.text=="💵 Пополнить")
async def depo(msg: types.Message):
    await msg.answer("Введите сумму для пополнения:")
    await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_depo_sum")

@dp.message(state="await_depo_sum")
async def depo_sum(msg: types.Message, state):
    try: s=int(msg.text)
    except: return await msg.answer("Введите число.")
    await msg.answer("Отправьте ссылку на чек:")
    await state.update_data(sum=s)
    await state.set_state("await_depo_check")

@dp.message(state="await_depo_check")
async def depo_check(msg: types.Message, state):
    d=await state.get_data(); s=d["sum"]
    kb=InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить",callback_data=f"add_{msg.from_user.id}_{s}")
    kb.button(text="❌ Отказать",callback_data=f"deny_{msg.from_user.id}_{s}")
    await bot.send_message(ADMIN_ID,f"💰 Заявка на пополнение {s} Gram\nОт: {msg.from_user.full_name} ({msg.from_user.id})\nЧек: {msg.text}",
                           reply_markup=kb.as_markup())
    await msg.answer("✅ Заявка отправлена админу!");await state.clear()

# === Вывести ===
@dp.message(F.text=="💸 Вывести")
async def withdraw(msg: types.Message):
    await msg.answer("Введите сумму вывода:")
    await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_with_sum")

@dp.message(state="await_with_sum")
async def with_sum(msg: types.Message, state):
    try: s=int(msg.text)
    except: return await msg.answer("Введите число.")
    d=load_data();u=d[str(msg.from_user.id)]
    if u["balance"]<s: return await msg.answer("Недостаточно средств!")
    u["balance"]-=s;save_data(d)
    kb=InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить",callback_data=f"wdok_{msg.from_user.id}_{s}")
    kb.button(text="❌ Отказать",callback_data=f"wderr_{msg.from_user.id}_{s}")
    await bot.send_message(ADMIN_ID,f"💸 Заявка на вывод {s} Gram\nОт: {msg.from_user.full_name} ({msg.from_user.id})",
                           reply_markup=kb.as_markup())
    await msg.answer("✅ Заявка на вывод отправлена админу!");await state.clear()

# === Бонус ===
@dp.message(F.text=="💰 Ежедневный бонус")
async def bonus(msg: types.Message):
    d=load_data();u=d[str(msg.from_user.id)]
    now=datetime.now().strftime("%Y-%m-%d")
    if u["last_bonus"]!=now:
        u["last_bonus"]=now;u["balance"]+=500;save_data(d)
        await msg.answer("🎁 Вы получили 500 Gram!")
    else: await msg.answer("⏳ Бонус можно раз в день!")

# === Статистика ===
@dp.message(F.text=="📊 Статистика")
async def stat(msg: types.Message):
    d=load_data()
    await msg.answer(f"📊 Статистика\nДата старта: {START_DATE}\nВладелец: {OWNER}\nПоддержка: {SUPPORT}\nВсего пользователей: {len(d)}")

# === Поддержка ===
@dp.message(F.text=="🆘 Поддержка")
async def supp(msg: types.Message):
    await msg.answer("✍️ Напишите проблему одним сообщением:")
    await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_sup")

@dp.message(state="await_sup")
async def sup_send(msg: types.Message, state):
    kb=InlineKeyboardBuilder();kb.button(text="✉️ Ответить",callback_data=f"reply_{msg.from_user.id}")
    await bot.send_message(ADMIN_ID,f"📨 От {msg.from_user.full_name} ({msg.from_user.id}):\n{msg.text}",reply_markup=kb.as_markup())
    await msg.answer("✅ Отправлено в поддержку!");await state.clear()

# === Админ-панель ===
@dp.message(F.text=="/admin")
async def admin(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    kb=ReplyKeyboardBuilder()
    for b in ["💎 Выдать деньги","📢 Рассылка","📋 Каналы","💬 Написать игроку","🔙 Назад"]: kb.button(text=b)
    await msg.answer("👑 Админ-панель",reply_markup=kb.as_markup(resize_keyboard=True))

# --- Выдать деньги
@dp.message(F.text=="💎 Выдать деньги")
async def give_start(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    await msg.answer("Введите: ID сумма");await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_give")

@dp.message(state="await_give")
async def give_done(msg: types.Message,state):
    try:id_,s=msg.text.split();s=int(s)
    except:return await msg.answer("Формат: ID сумма")
    d=load_data()
    if id_ not in d:return await msg.answer("Игрок не найден")
    d[id_]["balance"]+=s;save_data(d)
    await msg.answer("✅ Выдано!");await bot.send_message(int(id_),f"💎 Вам начислено {s} Gram от админа!")
    await state.clear()

# --- Каналы
@dp.message(F.text=="📋 Каналы")
async def chans(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    ch=load_channels()
    await msg.answer(f"📋 Каналы: {', '.join(ch)}\n/add @channel — добавить\n/rem @channel — удалить")

@dp.message(F.text.startswith("/add"))
async def addch(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    ch=load_channels();c=msg.text.split()[1];ch.append(c);save_channels(ch)
    await msg.answer("✅ Добавлен канал")

@dp.message(F.text.startswith("/rem"))
async def remch(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    ch=load_channels();c=msg.text.split()[1]
    if c in ch:ch.remove(c);save_channels(ch)
    await msg.answer("🗑️ Удален канал")

# --- Рассылка
@dp.message(F.text=="📢 Рассылка")
async def broad(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    await msg.answer("Отправьте текст или фото (с подписью):")
    await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_broad")

@dp.message(state="await_broad",content_types=["text","photo"])
async def do_broad(msg: types.Message,state):
    d=load_data();sent=0
    for u in d:
        try:
            if msg.photo:
                await bot.send_photo(int(u),msg.photo[-1].file_id,caption=msg.caption or "")
            else: await bot.send_message(int(u),msg.text)
            sent+=1
        except: pass
    await msg.answer(f"✅ Разослано {sent} сообщений")
    await state.clear()

# --- Написать игроку
@dp.message(F.text=="💬 Написать игроку")
async def to_user(msg: types.Message):
    if msg.from_user.id!=ADMIN_ID:return
    await msg.answer("Введите: ID сообщение")
    await dp.current_state(chat=msg.chat.id,user=msg.from_user.id).set_state("await_msg")

@dp.message(state="await_msg")
async def send_user(msg: types.Message,state):
    try:id_,text=msg.text.split(" ",1)
    except:return await msg.answer("Формат: ID текст")
    await bot.send_message(int(id_),f"📩 Сообщение от админа:\n{text}")
    await msg.answer("✅ Отправлено!");await state.clear()

# === Callback для заявок ===
@dp.callback_query()
async def callbacks(c: types.CallbackQuery):
    d=load_data()
    parts=c.data.split("_")
    act=parts[0]
    if act=="add":
        uid, s = parts[1], int(parts[2])
        d[uid]["balance"]+=s;save_data(d)
        await bot.send_message(int(uid),f"✅ Пополнение +{s} Gram подтверждено!")
        await c.message.edit_text("✅ Подтверждено!")
    elif act=="deny":
        await bot.send_message(int(parts[1]),"❌ Пополнение отклонено.")
        await c.message.edit_text("❌ Отказано.")
    elif act=="wdok":
        uid,s=parts[1],int(parts[2])
        await bot.send_message(ADMIN_ID,"Введите ссылку на чек в ответ на это сообщение:")
        await bot.send_message(int(uid),f"✅ Вывод {s} Gram подтвержден, ожидайте чек в личных.")
    elif act=="wderr":
        uid,s=parts[1],int(parts[2])
        d[uid]["balance"]+=s;save_data(d)
        await bot.send_message(int(uid),"❌ Вывод отклонен, средства возвращены.")
        await c.message.edit_text("❌ Отказано и возврат.")
    elif act=="reply":
        uid=int(parts[1])
        await bot.send_message(ADMIN_ID,f"Напишите ответ для {uid}:")
        await dp.current_state(chat=c.message.chat.id,user=c.from_user.id).set_state("await_reply")
        await dp.current_state(chat=c.message.chat.id,user=c.from_user.id).update_data(uid=uid)

@dp.message(state="await_reply")
async def reply_to_user(msg: types.Message,state):
    d=await state.get_data()
    await bot.send_message(d["uid"],f"💬 Ответ от админа:\n{msg.text}")
    await msg.answer("✅ Ответ отправлен");await state.clear()

# === Flask для Koyeb (порт 8000) ===
app=web.Application()
async def handle(req): return web.Response(text="Bot OK on Koyeb :8000")
app.add_routes([web.get("/",handle)])

async def main():
    asyncio.create_task(dp.start_polling(bot))
    runner=web.AppRunner(app);await runner.setup()
    site=web.TCPSite(runner,"0.0.0.0",8000);await site.start()
    print("✅ Bot started on port 8000")
    while True: await asyncio.sleep(3600)

if __name__=="__main__":
    asyncio.run(main())
