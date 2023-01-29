import telegram
import requests
import logging
import time
import sys
import os
from dotenv import load_dotenv
import exceptions
from http import HTTPStatus

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
        logging.debug(f'Сообщение отправлено {message}')
    except telegram.TelegramError as telegram_error:
        logging.error(f'Не удалось отправить сообщение {telegram_error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API Yandex Practicum"""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if response.status_code != 200:
            code_api_msg = (
                f'{ENDPOINT} недоступен.'
                f' Код ответа API: {response.status_code}')
            logging.error(code_api_msg)
            raise exceptions.InvalidResponseCode(code_api_msg)
        homeworks = response.json()
        return homeworks
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации"""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    if 'homeworks' not in response:
        raise exceptions.EmptyResponseFromAPI('Пустой ответ от API')
    return homeworks


def parse_status(homework):
    """Извлекает из информации статус домашней работы"""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
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
            else:
                logging.debug('Новые статусы работы отсутствуют')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != preview_message:
                send_message(bot, message)
            preview_message = message
        finally:
            time.sleep(RETRY_PERIOD)
    else:
        logging.critical('Отсутствие обязательных переменных окружения!')


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, %(message)s'
        ),
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
