class InvalidResponseCode(Exception):
    """Не верный код ответа."""


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API"""


class RequestExceptionError(Exception):
    """Ошибка запроса."""
