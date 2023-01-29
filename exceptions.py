class TelegramError(Exception):
    """Ошибка отправки телеграм-бота"""
    pass


class InvalidResponseCode(Exception):
    """Не верный код ответа."""
    pass


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API"""
    pass
