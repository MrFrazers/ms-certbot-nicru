"""HTTP-клиент для DNS API NIC.RU.

OAuth2 (password grant) + REST + XML для работы с ресурсными записями.
"""

from __future__ import annotations

import logging
from base64 import b64encode
from typing import Optional

import requests

from .exceptions import (
    AuthenticationError,
    TokenError,
    ApiError,
    RecordNotFoundError,
    NicRuError,
)
from .models import DnsRecord
from .xml_parser import parse_records, parse_zone, build_add_records_xml

logger = logging.getLogger(__name__)

API_BASE = "https://api.nic.ru"


class NicRuClient:
    """Клиент к API DNS-хостинга NIC.RU.

    :param client_id: идентификатор приложения OAuth
    :param client_secret: секрет приложения OAuth
    :param username: логин договора (например, 123/NIC-REG)
    :param password: пароль (административный или технический)
    :param scope: область доступа токена
    :param default_service: идентификатор услуги DNS-master
    :param default_zone: имя зоны в Punycode
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        scope: str,
        default_service: str,
        default_zone: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.scope = scope
        self.service = default_service
        self.zone = default_zone

        self._token: Optional[str] = None
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Аутентификация
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        """Возвращает токен (получает при первом обращении)."""
        if self._token is None:
            self._token = self._get_token()
        return self._token

    def _get_token(self) -> str:
        """Получает OAuth2 токен по паролю (grant_type=password)."""
        url = f"{API_BASE}/oauth/token"
        auth_header = b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "scope": self.scope,
        }

        resp = self._session.post(url, headers=headers, data=data)

        if resp.status_code != 200:
            raise TokenError(
                f"Ошибка получения токена (HTTP {resp.status_code}): {resp.text}"
            )

        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise TokenError(f"Токен не найден в ответе: {resp.text}")

        logger.info("Токен получен успешно")
        return access_token

    # ------------------------------------------------------------------
    # HTTP-хелперы
    # ------------------------------------------------------------------

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
        }

    def _url(self, path: str) -> str:
        """Собирает полный URL API."""
        return f"{API_BASE}{path}"

    def _records_url(self, record_id: Optional[int] = None) -> str:
        """URL для работы с ресурсными записями зоны."""
        base = f"/dns-master/services/{self.service}/zones/{self.zone}/records"
        if record_id is not None:
            return f"{base}/{record_id}"
        return base

    def _handle_response_error(self, response: requests.Response) -> None:
        """Обрабатывает HTTP-ошибки, пробуя извлечь ошибку из XML."""
        if response.status_code == 401:
            self._token = None  # сбросить просроченный токен
            raise AuthenticationError(f"Ошибка аутентификации: {response.text}")

        if response.status_code == 404:
            raise RecordNotFoundError(
                f"Запись не найдена (HTTP 404): {response.text}"
            )

        # Пробуем распарсить XML с ошибкой
        if "xml" in response.headers.get("Content-Type", "").lower():
            try:
                from xml.etree import ElementTree
                root = ElementTree.fromstring(response.text)
                errors = root.find("errors")
                if errors is not None:
                    for err in errors.findall("error"):
                        code = err.get("code", "unknown")
                        message = err.text or ""
                        raise ApiError(code=code, message=message)
            except ApiError:
                raise
            except Exception:
                pass

        raise NicRuError(f"HTTP {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Ресурсные записи (core API)
    # ------------------------------------------------------------------

    def get_records(self, zone: Optional[str] = None) -> list[DnsRecord]:
        """Получает список всех ресурсных записей зоны.

        :param zone: имя зоны (по умолчанию default_zone)
        """
        if zone is not None:
            self.zone = zone

        url = self._url(self._records_url())
        logger.debug("GET %s", url)

        resp = self._session.get(url, headers=self._auth_headers)

        if resp.status_code != 200:
            self._handle_response_error(resp)

        return parse_records(resp.text)

    def add_record(self, record: DnsRecord) -> None:
        """Добавляет ресурсную запись в зону."""
        url = self._url(self._records_url())
        xml_body = build_add_records_xml([record])

        headers = {
            **self._auth_headers,
            "Content-Type": "application/xml; charset=UTF-8",
        }

        logger.debug("PUT %s\n%s", url, xml_body)
        resp = self._session.put(url, headers=headers, data=xml_body.encode("utf-8"))

        if resp.status_code != 200:
            self._handle_response_error(resp)

        logger.info("Запись %s -> %s добавлена", record.rr_type, record.name)

    def delete_record(self, record_id: int) -> None:
        """Удаляет ресурсную запись по ID."""
        url = self._url(self._records_url(record_id))
        logger.debug("DELETE %s", url)

        resp = self._session.delete(url, headers=self._auth_headers)

        if resp.status_code != 200:
            self._handle_response_error(resp)

        logger.info("Запись #%d удалена", record_id)

    def commit(self) -> None:
        """Фиксирует изменения и выгружает зону на DNS-серверы."""
        url = self._url(
            f"/dns-master/services/{self.service}/zones/{self.zone}/commit"
        )
        logger.debug("POST %s", url)

        resp = self._session.post(url, headers=self._auth_headers)

        if resp.status_code != 200:
            self._handle_response_error(resp)

        logger.info("Изменения зафиксированы и выгружены на DNS-серверы")

    def rollback(self) -> None:
        """Отменяет несохранённые изменения в зоне."""
        url = self._url(
            f"/dns-master/services/{self.service}/zones/{self.zone}/rollback"
        )
        logger.debug("POST %s", url)

        resp = self._session.post(url, headers=self._auth_headers)

        if resp.status_code != 200:
            self._handle_response_error(resp)

        logger.info("Изменения отменены (rollback)")

    # ------------------------------------------------------------------
    # Зоны (опционально)
    # ------------------------------------------------------------------

    def get_zone_info(self) -> Optional[dict]:
        """Получает информацию о текущей зоне."""
        url = self._url(
            f"/dns-master/services/{self.service}/zones/{self.zone}"
        )
        resp = self._session.get(url, headers=self._auth_headers)

        if resp.status_code != 200:
            self._handle_response_error(resp)

        zone = parse_zone(resp.text)
        return zone.__dict__ if zone else None

    def get_zones(self) -> list[dict]:
        """Получает список всех зон на услуге."""
        url = self._url(
            f"/dns-master/services/{self.service}/zones"
        )
        resp = self._session.get(url, headers=self._auth_headers)

        if resp.status_code != 200:
            self._handle_response_error(resp)

        from .xml_parser import _parse_zones
        return [z.__dict__ for z in _parse_zones(resp.text)]
