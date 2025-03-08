import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import re
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен вашего Telegram-бота
TELEGRAM_BOT_TOKEN = '7920863521:AAHk148sZ7suZTmGFBARqE55iEII2GViuY4'

# Together AI API ключ
TOGETHER_AI_API_KEY = '2165ec5065898c6227d7f541961c1f1071a59fb437f7994baa7310153fa17c0b'
TOGETHER_AI_API_URL = 'https://api.together.ai/chat/completions'

# Функция для форматирования текста (Markdown → HTML)
def format_message(text):
    # Жирный текст: **текст** → <b>текст</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Курсив: *текст* → <i>текст</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text

# Функция для взаимодействия с Together AI
async def get_ai_response(messages):
    headers = {
        'Authorization': f'Bearer {TOGETHER_AI_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo',  # Укажите модель
        'messages': messages,  # Передаем всю историю диалога
        'max_tokens': 300,  # Увеличиваем лимит токенов
        'temperature': 0.7,  # Контролируем креативность
    }
    try:
        response = requests.post(TOGETHER_AI_API_URL, headers=headers, json=data)
        logging.info(f"Together AI Response: {response.status_code}, {response.text}")  # Логируем ответ
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            return "Извините, произошла ошибка. Попробуйте позже."
    except Exception as e:
        logging.error(f"Error in get_ai_response: {e}")  # Логируем ошибку
        return "Извините, произошла ошибка. Попробуйте позже."

# Проверка на завершенность ответа
def is_response_complete(response):
    # Проверяем, заканчивается ли ответ на знак препинания
    return response.endswith(('.', '!', '?', '...'))

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Привет! Я ваш виртуальный психолог. 😊\n"
        "Я здесь, чтобы помочь вам справиться с тревогой, стрессом и другими эмоциями.\n"
        "Напишите мне, что вас беспокоит, и я постараюсь помочь!"
    )
    await update.message.reply_text(welcome_message)
    context.user_data['messages'] = []  # Инициализируем историю диалога

# Анимация "Печатаю..."
async def animate_typing(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    dots = 0
    max_dots = 3
    while True:
        dots = (dots + 1) % (max_dots + 1)
        text = "Печатаю" + "." * dots
        try:
            await message.edit_text(text)
        except Exception as e:
            logging.error(f"Error editing message: {e}")
        await asyncio.sleep(0.5)  # Задержка между обновлениями

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Добавляем сообщение пользователя в историю диалога
    if 'messages' not in context.user_data:
        context.user_data['messages'] = []
    context.user_data['messages'].append({'role': 'user', 'content': user_message})

    # Запускаем анимацию "Печатаю..."
    typing_message = await update.message.reply_text("Печатаю")
    animation_task = asyncio.create_task(animate_typing(update, context, typing_message))

    # Получаем ответ от Together AI
    ai_response = await get_ai_response(context.user_data['messages'])

    # Если ответ обрезан, дополняем его
    if not is_response_complete(ai_response):
        context.user_data['messages'].append({'role': 'assistant', 'content': ai_response})
        additional_response = await get_ai_response(context.user_data['messages'])
        ai_response += " " + additional_response

    # Добавляем ответ бота в историю диалога
    context.user_data['messages'].append({'role': 'assistant', 'content': ai_response})

    # Останавливаем анимацию
    animation_task.cancel()

    # Форматируем и отправляем окончательный ответ
    formatted_response = format_message(ai_response)
    await typing_message.edit_text(formatted_response, parse_mode='HTML')

# Основная функция
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()