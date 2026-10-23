import os
import threading
import telebot
from flask import Flask
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)

# --- НАСТРОЙКИ ---
TOKEN = "8558398620:AAG0ZnUUIif8VXmUGz0doZ0g7JwzhD2MEtQ"
CHANNEL_ID = "@ne_avito_ru"  # ⚠️ Укажите ваш реальный канал
MODERATION_CHAT_ID = 8768838896  # ⚠️ Укажите ваш числовой ID модератора
# -----------------

bot = telebot.TeleBot(TOKEN)
user_data = {}
pending_posts = {}


@bot.message_handler(commands=["start"])
def start_flow(message):
  chat_id = message.chat.id
  user_data[chat_id] = {"state": "WAITING_TITLE", "photos": []}
  bot.send_message(
      chat_id,
      "👋 Привет! Начнем создание объявления.\n\n📝 Введите название товара"
      " (или текст, который будет в начале поста):",
  )


@bot.message_handler(commands=["ready"])
def ready_handler(message):
  chat_id = message.chat.id
  if (
      chat_id in user_data
      and user_data[chat_id].get("state") == "WAITING_PHOTOS"
  ):
    if not user_data[chat_id]["photos"]:
      bot.send_message(
          chat_id, "❌ Вы не загрузили ни одной фотографии! Отправьте хотя бы одну."
      )
      return

    user_data[chat_id]["state"] = "PREVIEW"
    d = user_data[chat_id]

    caption = (
        f"{d['title']}\n"
        f"🔺Город: {d['city']}\n"
        f"🟢Цена: {d['price']}\n"
        f"🔵Связь с продавцом: {d['contact']}\n\n"
        "Добавить объявление \n"
        "бесплатно 👉 @ne_avitoo_bot\n\n"
        "❗Если нужно объявление из вашего города. \n"
        "То в поиске сверху вбейте свой город. Три точки, поиск.👆"
    )
    d["caption"] = caption

    bot.send_message(chat_id, "👀 Вот предварительный просмотр вашего поста:")

    photos = d["photos"]
    if len(photos) == 1:
      bot.send_photo(chat_id, photos[0], caption=caption)
    else:
      media = []
      for i in range(len(photos)):
        if i == 0:
          media.append(InputMediaPhoto(photos[0], caption=caption))
        else:
          media.append(InputMediaPhoto(photos[i]))
      bot.send_media_group(chat_id, media)

    bot.send_message(
        chat_id,
        "❓ **Верно?**\n\nЕсли нужно изменить — отправьте **`/no`** (все начнется"
        " заново).\nЕсли всё правильно, отправьте команду **`/go`**, чтобы"
        " отправить объявление на модерацию!",
    )
  else:
    bot.send_message(
        chat_id,
        "Сначала начните создание объявления с помощью команды /start.",
    )


@bot.message_handler(content_types=["photo"])
def photo_handler(message):
  chat_id = message.chat.id
  if (
      chat_id in user_data
      and user_data[chat_id].get("state") == "WAITING_PHOTOS"
  ):
    photos = user_data[chat_id]["photos"]
    if len(photos) >= 10:
      bot.send_message(
          chat_id,
          "⚠️ Максимум можно загрузить 10 фотографий.\nОтправьте команду"
          " **`/ready`**, чтобы завершить загрузку.",
      )
      return

    photos.append(message.photo[-1].file_id)
    bot.send_message(
        chat_id,
        f"📸 Фото добавлено ({len(photos)}/10).\nМожете отправить еще или"
        " напишите команду **`/ready`**, когда закончите.",
    )
  else:
    bot.send_message(
        chat_id,
        "Сейчас не нужно отправлять фото. Начните с команды /start или следуйте"
        " инструкциям бота.",
    )


@bot.message_handler(func=lambda message: True, content_types=["text"])
def text_handler(message):
  chat_id = message.chat.id
  text = message.text.strip()

  if chat_id not in user_data:
    if text == "/start":
      start_flow(message)
    else:
      bot.send_message(
          chat_id, "Чтобы начать работу, отправьте команду /start"
      )
    return

  state = user_data[chat_id].get("state")

  if state == "WAITING_TITLE":
    user_data[chat_id]["title"] = text
    user_data[chat_id]["state"] = "WAITING_CITY"
    bot.send_message(chat_id, "🔺 Укажите город:")

  elif state == "WAITING_CITY":
    user_data[chat_id]["city"] = text
    user_data[chat_id]["state"] = "WAITING_PRICE"
    bot.send_message(chat_id, "🟢 Укажите цену:")

  elif state == "WAITING_PRICE":
    user_data[chat_id]["price"] = text
    user_data[chat_id]["state"] = "WAITING_CONTACT"
    bot.send_message(
        chat_id,
        "🔵 Укажите связь с продавцом (например, `@geloyan` или ваш контакт):",
    )

  elif state == "WAITING_CONTACT":
    user_data[chat_id]["contact"] = text
    user_data[chat_id]["state"] = "WAITING_PHOTOS"
    bot.send_message(
        chat_id,
        "📸 Отлично! Теперь отправьте от **1 до 10 фотографий** (можно по одной"
        " или альбомом).\n\nКак закончите загрузку фото, отправьте команду"
        " **`/ready`**.",
    )

  elif state == "PREVIEW":
    if text == "/go":
      d = user_data.get(chat_id)
      if not d:
        return

      pending_posts[chat_id] = {"photos": d["photos"], "caption": d["caption"]}

      markup = InlineKeyboardMarkup()
      markup.add(
          InlineKeyboardButton(
              "✅ Одобрить", callback_data=f"approve_{chat_id}"
          ),
          InlineKeyboardButton(
              "❌ Отклонить", callback_data=f"reject_{chat_id}"
          ),
      )

      try:
        bot.send_message(
            MODERATION_CHAT_ID,
            f"🔔 **Новое объявление на модерацию** от пользователя (ID:"
            f" `{chat_id}`):",
        )
        photos = d["photos"]
        caption = d["caption"]

        if len(photos) == 1:
          bot.send_photo(
              MODERATION_CHAT_ID, photos[0], caption=caption, reply_markup=markup
          )
        else:
          media = []
          for i in range(len(photos)):
            if i == 0:
              media.append(InputMediaPhoto(photos[0], caption=caption))
            else:
              media.append(InputMediaPhoto(photos[i]))
          bot.send_media_group(MODERATION_CHAT_ID, media)
          bot.send_message(
              MODERATION_CHAT_ID,
              "👆 Проверьте объявление выше. Решение:",
              reply_markup=markup,
          )

        bot.send_message(
            chat_id,
            "⏳ Ваше объявление успешно отправлено модератору на проверку!",
        )
      except Exception as e:
        bot.send_message(
            chat_id, f"❌ Ошибка при отправке на модерацию: {e}"
        )

      user_data.pop(chat_id, None)

    elif text == "/no":
      user_data.pop(chat_id, None)
      bot.send_message(
          chat_id,
          "❌ Отменено. Давайте начнем заново. Отправьте команду /start",
      )
    else:
      bot.send_message(
          chat_id,
          "Пожалуйста, отправьте команду **`/go`** для отправки модератору или"
          " **`/no`** для сброса.",
      )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("approve_", "reject_"))
)
def moderation_callback(call):
  action, target_chat_id_str = call.data.split("_")
  target_chat_id = int(target_chat_id_str)

  post_info = pending_posts.get(target_chat_id)

  if action == "approve":
    if not post_info:
      bot.answer_callback_query(
          call.id,
          "⚠️ Данные объявления не найдены (возможно, бот перезапускался).",
      )
      return

    try:
      photos = post_info["photos"]
      caption = post_info["caption"]

      if len(photos) == 1:
        bot.send_photo(CHANNEL_ID, photos[0], caption=caption)
      else:
        media = []
        for i in range(len(photos)):
          if i == 0:
            media.append(InputMediaPhoto(photos[0], caption=caption))
          else:
            media.append(InputMediaPhoto(photos[i]))
        bot.send_media_group(CHANNEL_ID, media)

      bot.send_message(
          target_chat_id,
          "🎉 Поздравляем! Ваше объявление прошло модерацию и опубликовано в"
          " канале.",
      )

      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=call.message.text
          + "\n\n**✅ СТАТУС: Одобрено и опубликовано**",
      )
      bot.answer_callback_query(call.id, "Объявление успешно одобрено!")

    except Exception as e:
      bot.answer_callback_query(call.id, f"Ошибка публикации: {e}")

  elif action == "reject":
    try:
      bot.send_message(
          target_chat_id,
          "❌ К сожалению, ваше объявление было отклонено модератором.",
      )
    except:
      pass

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=call.message.text + "\n\n**❌ СТАТУС: Отклонено**",
      )
    except:
      pass

    bot.answer_callback_query(call.id, "Объявление отклонено.")

  pending_posts.pop(target_chat_id, None)


# --- МИНИ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ ХОСТИНГА ---
app = Flask(__name__)


@app.route("/")
def index():
  return "Бот работает 24/7!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
  # Запускаем Flask в фоновом потоке
  t = threading.Thread(target=run_flask)
  t.start()

  print("Бот запущен на облачном сервере...")
  bot.infinity_polling(skip_pending=True)
