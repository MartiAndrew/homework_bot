from telegram import Bot
import requests
import logging
import time
import sys
import os
from dotenv import load_dotenv
import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except exceptions.TelegramError as error:
        raise exceptions.TelegramError(
            f'Не удалось отправить сообщение {error}'
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API Yandex Practicum"""
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
        homeworks = homeworks.json()
        return homeworks
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации"""
    if isinstance(response, dict):
        print('Ответ содержит словарь')
        if isinstance(response['homeworks'], list):
            print('Ответ содержит список домашних работ')
            return True
    print('Поменялась структура документации!')
    return False


def parse_status(homework):
    """Извлекает из информации статус домашней работы"""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    preview_message = None
    while check_tokens():
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                homework = (response.get('homeworks'))[0]
                timestamp = response.get('current_date', int(time.time()))
                message = parse_status(homework)
                if message != preview_message:
                    send_message(bot, message)
                preview_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)
    else:


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, %(message)s'
        ),
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
