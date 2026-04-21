from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from openai import OpenAI
import pytesseract
from PIL import Image
import base64
import random
import json
import os
import time

# путь к tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# AI
client = OpenAI(
    api_key="sk-311xncCaKfgk9xLBY7ai0vQ1lbxOJCNDs5ESUL1wzv5MkBp3",
    base_url="https://neuroapi.host/v1"
)

TOKEN = "8628508181:AAGndR2wiohyuJ_E4EIhspnpMQen-LhQ1AM"

DATA_FILE = "users.json"


# ========================
# 📁 ПАМЯТЬ
# ========================
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


users = load_users()


# ========================
# 💬 ДИАЛОГ КАК ПОДРУГА
# ========================
async def chat_like_friend(user_text, user):

    prompt = f"""
Ты — подруга, которая разбирается в уходе за кожей.

Общайся на "ты".
Пиши просто и по-человечески.

Данные:
Имя: {user.get("name")}
Тип кожи: {user.get("skin")}

Если человек не прислал продукт — просто поддержи диалог и дай совет.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text[:500]}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        print("Ошибка диалога:", e)
        return "Что-то подвисло 😅 Напиши ещё раз"


# ========================
# 🔬 АНАЛИЗ
# ========================
async def analyze_ingredients(content, user):

    prompt = f"""
Ты — подруга, которая хорошо разбирается в уходе за кожей.

Общайся ТОЛЬКО на "ты". Никаких "вы".

Пиши живо, по-человечески, без ощущения, что это бот.
Без звездочек (*), без сложного форматирования.

Текст должен быть разделён на понятные блоки, например:

Плюсы:
текст

Минусы:
текст

Но без нумерации и без символов типа "*".

Твоя задача — объяснить продукт так, чтобы было понятно, подходит он или нет.

Если это состав — разбери его.
Если это продукт — сначала скажи, что это.

Обязательно раскрой:
— что это за продукт
— плюсы
— минусы
— для какого типа кожи подходит
— как использовать
— с чем сочетать
— с чем не стоит сочетать
— аналоги (1 дешевле, 1 дороже)
— итог

ВАЖНО:
У пользователя тип кожи: {user.get("skin") if user.get("skin") else "неизвестен"}

Если тип кожи известен:
обязательно отдельно укажи, подходит ли продукт ИМЕННО ему.

Но при этом всё равно опиши для всех типов кожи.

В конце:
— задай 1–2 вопроса
— дай короткий дружеский совет

Тон:
спокойный, дружелюбный, как подруга.
Можно иногда добавить мнение (например: "я бы такое взяла").
Без перегруза и без заумных слов.
"""

    content = str(content)[:1000]

    for i in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ]
            )
            return response.choices[0].message.content

        except Exception as e:
            print("Ошибка AI:", e)
            time.sleep(2)

    return "Не получилось загрузить 😅 Попробуй ещё раз"


# ========================
# 🚀 START
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)

    if user_id not in users:
        users[user_id] = {"name": None, "skin": None}
        save_users(users)

    await update.message.reply_text(
        "Привет 💗\n\n"
        "Давай познакомимся! Как тебя зовут?"
    )


# ========================
# ✍️ ТЕКСТ
# ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)
    user_text = update.message.text

    if user_id not in users:
        users[user_id] = {"name": None, "skin": None}

    user = users[user_id]

    # имя
    if user["name"] is None:
        user["name"] = user_text
        save_users(users)

        await update.message.reply_text(
            f"Очень приятно, {user_text} 💗\n\n"
            "Какой у тебя тип кожи?\n\n"
            "— сухая\n— жирная\n— комбинированная\n— чувствительная"
        )
        return

    # тип кожи
    if user["skin"] is None:
        user["skin"] = user_text
        save_users(users)

        await update.message.reply_text(
            "Запомнила 🫶 Теперь присылай продукт или состав"
        )
        return

    text_lower = user_text.lower()

    is_analysis = (
        "," in text_lower or
        "aqua" in text_lower or
        "water" in text_lower
    )

    if not is_analysis:
        reply = await chat_like_friend(user_text, user)
        await update.message.reply_text(reply)
        return

    await update.message.reply_text("Сейчас посмотрю 👀")

    analysis = await analyze_ingredients(user_text, user)

    await update.message.reply_text(f"{user['name']},\n\n{analysis}")


# ========================
# 📸 ФОТО
# ========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)
    user = users.get(user_id, {})

    await update.message.reply_text("Сейчас посмотрю 👀")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    await file.download_to_drive("photo.jpg")

    with open("photo.jpg", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    content = [
        {"type": "text", "text": "Что это за косметический продукт?"},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
    ]

    analysis = await analyze_ingredients(content, user)

    await update.message.reply_text(f"{user.get('name','')},\n\n{analysis}")


# ========================
# ❗️ ОШИБКИ
# ========================
async def error_handler(update, context):
    print("Ошибка:", context.error)


# ========================
# 🚀 ЗАПУСК
# ========================
from telegram.request import HTTPXRequest

request = HTTPXRequest(connect_timeout=20, read_timeout=20)

app = ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.add_error_handler(error_handler)

print("Бот запущен...")
app.run_polling()

