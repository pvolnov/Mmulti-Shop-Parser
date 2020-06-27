from enum import Enum

import telebot
from telebot import types
import pandas as pd
from config import telegram_bot_key
from models import Items, Users, DialogState, TaskStatus


class btns:
    WAIT_OZON_FOR_LOAD = "Скачать товары с Ozon ⬇️"
    WAIT_OZON_FOR_PARSE = "Мониторить товары Ozon 🔄"
    WAIT_WILBERRIES_FOR_LOAD = "Скачать товары с Wilberries ⬇️"
    WAIT_WILBERRIES_FOR_PARSE = "Мониторить товары с Wilberries 🔄"


bot = telebot.TeleBot(telegram_bot_key)

parsels_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True,
                                             one_time_keyboard=True,
                                             row_width=2)
parsels_keyboard.add(
    types.KeyboardButton(text=btns.WAIT_WILBERRIES_FOR_LOAD),
    types.KeyboardButton(text=btns.WAIT_WILBERRIES_FOR_PARSE),
    types.KeyboardButton(text=btns.WAIT_OZON_FOR_LOAD),
    types.KeyboardButton(text=btns.WAIT_OZON_FOR_PARSE),
)


@bot.message_handler(commands=['start', 'menu', 'status'])
def start(message):
    if message.text == "/start":
        bot.send_message(message.chat.id, "Пришлите пароль для активации бота")
    elif message.text == "/menu":
        user = Users.get(Users.tel_id == message.chat.id)
        user.dstat = DialogState.MENU
        user.save()
        bot.send_message(message.chat.id, "Главное меню", reply_markup=parsels_keyboard)
    elif message.text == "/status":
        will_load = Items.select().where(Items.status == TaskStatus.FOR_LOAD).count()
        loaded = Items.select().where(Items.status == TaskStatus.LOAD_COMPLE).count()

        will_parse = Items.select().where(Items.status == TaskStatus.FOR_UPDATE).count()
        parsed = Items.select().where(Items.status == TaskStatus.UPDATE_COMPLE).count()
        bot.send_message(message.chat.id, f"Сохранено {loaded}/{loaded + will_load}\n"
                                          f"Обновлено {parsed}/{parsed + will_parse}")


@bot.message_handler(content_types=['document'])
def new_doc(message):
    user = Users.get(Users.tel_id == message.chat.id)
    print("Mew doc", user.dstat)
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open("file.xlsx", "wb") as f:
        f.write(downloaded_file)
    data = pd.read_excel("file.xlsx")
    urls = list(data["Ссылка"])
    if user.dstat == DialogState.WAIT_WILBERRIES_FOR_LOAD:
        items = [{"url": u,
                  "shop": "wilberries",
                  "status": TaskStatus.FOR_LOAD} for u in urls]
    elif user.dstat == DialogState.WAIT_WILBERRIES_FOR_PARSE:
        items = [{"url": u,
                  "shop": "wilberries",
                  "status": TaskStatus.FOR_UPDATE} for u in urls]
    elif user.dstat == DialogState.WAIT_OZON_FOR_PARSE:
        items = [{"url": u,
                  "shop": "ozon",
                  "status": TaskStatus.FOR_UPDATE} for u in urls]
    elif user.dstat == DialogState.WAIT_OZON_FOR_LOAD:
        items = [{"url": u,
                  "shop": "ozon",
                  "status": TaskStatus.FOR_LOAD} for u in urls]
    else:
        bot.reply_to(message, 'Error: incorrect message state')
        return

    Items.insert_many(items).execute()
    user.dstat = DialogState.MENU
    user.save()
    bot.reply_to(message, f'Sucsessfully added {len(items)} items', reply_markup=parsels_keyboard)


@bot.message_handler(content_types=["text"])
def text_mes(message):
    if message.text == "test":
        if Users.get_or_none(Users.tel_id == message.chat.id) is None:
            Users.create(tel_id=message.chat.id,
                         name=str(message.from_user.first_name) + " " + str(message.from_user.last_name))
        bot.send_message(message.chat.id, "Бот активирован", reply_markup=parsels_keyboard)
        return

    user = Users.get_or_none(Users.tel_id == message.chat.id)
    if user is None:
        bot.send_message(message.chat.id, "Неверный пароль!")
        return

    dstat = user.dstat
    if message.text == btns.WAIT_WILBERRIES_FOR_LOAD:
        user.dstat = DialogState.WAIT_WILBERRIES_FOR_LOAD

    elif message.text == btns.WAIT_WILBERRIES_FOR_PARSE:
        user.dstat = DialogState.WAIT_WILBERRIES_FOR_PARSE

    elif message.text == btns.WAIT_OZON_FOR_LOAD:
        user.dstat = DialogState.WAIT_OZON_FOR_LOAD

    elif message.text == btns.WAIT_OZON_FOR_PARSE:
        user.dstat = DialogState.WAIT_OZON_FOR_PARSE

    if dstat != user.dstat:
        user.save()
        bot.send_message(message.chat.id,
                         "Пришлите документ в формате <b>.xlsx</b> с колонкой 'Ссылка' или нажмите /menu для отмены.",
                         parse_mode="HTML")


print("Start")
bot.polling(none_stop=False, timeout=60)