from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler
from telegram import Update
from telegram.ext import filters
import logging
import re
import json

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Уникальный ADMIN_KEY для защиты административного доступа
ADMIN_KEY = 'General!2011'

# Токен вашего бота
TOKEN = '7670003878:AAFRA8Q0wxgrJtQrjC9GR_iIEXknxkuSykA'

# Имя файла для хранения данных
DATA_FILE = 'balances.json'

# Загружаем данные из файла при старте бота
try:
    with open(DATA_FILE, 'r') as file:
        balances = json.load(file)
except FileNotFoundError:
    balances = {}  # Если файл не найден, начинаем с пустого набора данных

# Функция для сохранения данных в файл
def save_data():
    with open(DATA_FILE, 'w') as file:
        json.dump(balances, file)

# Проверка, является ли пользователь владельцем аккаунта
def check_admin(update):
    admin_key = update.message.text.split()[1].strip() if len(update.message.text.split()) > 1 else ''
    return admin_key == ADMIN_KEY

# Обработчик для администраторов: настройка начального баланса пользователя
async def set_initial_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update):
        await update.message.reply_text("Доступ запрещен.")
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

    # Сохраняем данные после изменения
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
            f'{data["name"]}: '
            f'- $: {balance_dollars}$ '
            f'- CR: {balance_cr}CR'
        )
        report.append(line)
    return '\n'.join(report)

# Основной обработчик сообщений
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    msg = update.message.text.strip()

    # Парсим сообщение с помощью регулярного выражения
    pattern = r'^@(\w+)\s*([+-]?\d+)\$'  # Исправленное регулярное выражение
    result = re.search(pattern, msg)

    if result is None:
        pattern = r'^@(\w+)\s*([+-]?\d+)\#'  # Исправленное регулярное выражение
        result = re.search(pattern, msg)
        if result is None:
            print('Нужных сообщений нет')
            return
        else:
            username = result.group(1).strip().lower()
            cr_change = int(result.group(2))  # Теперь знак + или - учитывается

            # Обновление баланса пользователя
            balances.setdefault(username, {
                'name': '@' + username,
                'dollars': 0,
                'cr_units': 0
            })

            balances[username]['cr_units'] += cr_change

            # Сохраняем данные после изменения
            save_data()

            # Формируем и отправляем отчёт немедленно
            report = generate_report()
            await update.message.reply_text("Одобрено")
            await context.bot.send_message(chat_id=chat_id, text=report, message_thread_id=873)
            return

    username = result.group(1).strip().lower()
    dollars_change = int(result.group(2))  # Теперь знак + или - учитывается

    # Обновление баланса пользователя
    balances.setdefault(username, {
        'name': '@' + username,
        'dollars': 0,
        'cr_units': 0
    })

    balances[username]['dollars'] += dollars_change

    # Сохраняем данные после изменения
    save_data()

    # Формируем и отправляем отчёт немедленно
    report = generate_report()
    await update.message.reply_text("Одобрено")
    await context.bot.send_message(chat_id=chat_id, text=report, message_thread_id=873)

# Главный метод запуска бота
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем обработчики команд и сообщений
    application.add_handler(CommandHandler('set_balance', set_initial_balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Начинаем опрос сообщений
    application.run_polling()
    logger.info("Бот запущен!")

if __name__ == "__main__":
    main()