"""Иерархия исключений для DNS API NIC.RU."""


class NicRuError(Exception):
    """Базовое исключение."""


class AuthenticationError(NicRuError):
    """Ошибка аутентификации (неверный логин/пароль, просрочен токен)."""


class TokenError(AuthenticationError):
    """Ошибка получения/обновления OAuth-токена."""


class ApiError(NicRuError):
    """Ошибка API NIC.RU (возвращена сервером в XML-ответе).

    :param code: код ошибки из ответа API
    :param message: текст ошибки
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class RecordNotFoundError(NicRuError):
    """Запись с указанным ID не найдена."""


class ZoneNotFoundError(NicRuError):
    """Зона не найдена."""


class ServiceNotFoundError(NicRuError):
    """Услуга не найдена."""


class ParseError(NicRuError):
    """Ошибка парсинга XML-ответа."""
