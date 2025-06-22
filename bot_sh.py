from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, JobQueue
from telegram import Update
from telegram.ext import filters
import logging
import re
import json
import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Админ-ключи и токены
ADMIN_KEY = 'Админ'
TOKEN = 'токен'

# Чат и топик, куда будут отправляться отчеты
CHAT_ID = '-1002779450871'
TOPIC_ID = 873

# Имя файла для хранения данных
DATA_FILE = 'balances.json'

# Загрузка данных из файла при старте бота
try:
    with open(DATA_FILE, 'r') as file:
        balances = json.load(file)
except FileNotFoundError:
    balances = {}

# Функция для сохранения данных в файл
def save_data():
    with open(DATA_FILE, 'w') as file:
        json.dump(balances, file)

# Проверка администратора
def check_admin(update):
    admin_key = update.message.text.split()[1].strip() if len(update.message.text.split()) > 1 else ''
    return admin_key == ADMIN_KEY

# Команда установки начального баланса пользователя
async def set_initial_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update):
        await update.message.reply_text("Доступ запрещён.")
        return

    args = context.args
    if len(args) != 4 or not args[2].isdigit() or not args[3].isdigit():
        await update.message.reply_text("Ошибка: неверный формат аргументов. Используйте /set_balance USERNAME ДОЛЛАРЫ CR")
        return

    username = args[1].strip().lower()
    initial_dollars = int(args[2])
    initial_cr = int(args[3])

    balances[username] = {
        'name': '@' + username,
        'dollars': initial_dollars,
        'cr_units': initial_cr
    }

    # Сохранение данных
    save_data()

    await update.message.reply_text(f"Установлен начальный баланс для '{args[1]}': ${initial_dollars}, CR: {initial_cr}.")

# Генерация отчета по балансу
def generate_report():
    report = ['Итоговый список изменений и текущий баланс участников:']
    for user in sorted(balances.keys()):
        data = balances[user]
        balance_dollars = data['dollars']
        balance_cr = data['cr_units']

        line = (
            f"{data['name']}: "
            f"- $: {balance_dollars}$ "
            f"- CR: {balance_cr}CR"
        )
        report.append(line)
    return "\n".join(report)

# Задача отправки ежедневного отчета в указанный чат и тему
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    report = generate_report()
    await context.bot.send_message(chat_id=CHAT_ID, text=report, message_thread_id=TOPIC_ID)

# Основная логика обработки сообщений
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        print("update.message is None Why?")
        return
    chat_id = update.message.chat_id
    msg = update.message.text.strip()

    # Регулярное выражение для парсинга суммы долларов
    pattern = r'^@(\w+)\s*([+-]?\d+)\$'
    result = re.search(pattern, msg)

    if result is None:
        # Регулярное выражение для парсинга единиц CR
        pattern = r'^@(\w+)\s*([+-]?\d+)\#'
        result = re.search(pattern, msg)
        if result is None:
            print('Подходящих сообщений нет.')
            return
        else:
            username = result.group(1).strip().lower()
            cr_change = int(result.group(2))

            # Обновление баланса пользователя
            balances.setdefault(username, {'name': '@' + username, 'dollars': 0, 'cr_units': 0})
            balances[username]['cr_units'] += cr_change

            # Сохранение данных
            save_data()

            await update.message.reply_text("Изменение принято.")
            return

    username = result.group(1).strip().lower()
    dollars_change = int(result.group(2))

    # Обновление баланса пользователя
    balances.setdefault(username, {'name': '@' + username, 'dollars': 0, 'cr_units': 0})
    balances[username]['dollars'] += dollars_change

    # Сохранение данных
    save_data()

    await update.message.reply_text("Изменение принято.")

# Запуск бота
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрация обработчиков команд и сообщений
    application.add_handler(CommandHandler('set_balance', set_initial_balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Использование встроенного планировщика для ежедневного отчета
    job_queue = application.job_queue
    job_queue.run_daily(send_daily_report, time=datetime.time(hour=21, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc))
    logger.info("Бот запущен!")
    # Начало опроса сообщений
    application.run_polling()


if __name__ == "__main__":
    main()