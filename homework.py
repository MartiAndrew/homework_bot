from http import HTTPStatus
import logging
import os
import time
from typing import NoReturn

from dotenv import load_dotenv
import requests
import telegram

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, Путь - %(pathname)s, %(message)s'
)
stream_handler.setFormatter(formatter)
logger.debug('Старт Бота')


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot: telegram.Bot, message: str) -> NoReturn:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Сообщение отправлено {message}')
    except telegram.TelegramError as telegram_error:
        logger.error(f'Не удалось отправить сообщение {telegram_error}')


def get_api_answer(timestamp: int) -> dict:
    """Запрос к эндпоинту API Yandex Practicum."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.exceptions.RequestException as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')
        raise exceptions.EmptyResponseFromAPI(
            f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        code_api_msg = (
            f'{ENDPOINT} недоступен.'
            f' Код ответа API: {response.status_code}')
        logger.error(code_api_msg)
        raise exceptions.InvalidResponseCode(code_api_msg)
    return response.json()


def check_response(response: dict) -> list:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает из информации статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> NoReturn:
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствие обязательных переменных окружения!')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    preview_message = None
    while True:
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
                logger.debug('Новые статусы работы отсутствуют')
        except KeyError as error:
            message = f'Сбой в работе программы, не найден ключ: {error}'
            if message != preview_message:
                send_message(bot, message)
            preview_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
