"""DNS Authenticator for NIC.RU — Certbot plugin.

Реализует DNS-01 challenge через REST API NIC.RU.
Совместим с certbot >= 2.0 (альтернатива dns_nicru).
"""

from __future__ import annotations

import logging

import zope.interface

from certbot import errors, interfaces
from certbot.plugins import dns_common

from .client import NicRuClient
from .models import TXTRecord
from .exceptions import NicRuError

logger = logging.getLogger(__name__)


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for NIC.RU.

    Использует REST API NIC.RU для выполнения DNS-01 challenge.
    """

    description = (
        "Obtain certificates using a DNS TXT record "
        "(if you are using NIC.RU for DNS)."
    )

    # TTL для _acme-challenge записей (рекомендуется низкое значение)
    ttl: int = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials: dns_common.CredentialsConfiguration | None = None
        self._client: NicRuClient | None = None

    @classmethod
    def add_parser_arguments(cls, add):
        super().add_parser_arguments(
            add, default_propagation_seconds=120
        )
        add("credentials", help="NIC.RU credentials INI file.")

    def more_info(self) -> str:
        return (
            "This plugin configures a DNS TXT record to respond to "
            "a dns-01 challenge using the NIC.RU Remote REST API.\n"
            "New implementation with full SRV record support."

        )

    # ------------------------------------------------------------------
    # Настройка учётных данных
    # ------------------------------------------------------------------

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            "credentials",
            "NIC.RU credentials INI file",
            {
                "client_id": "OAuth application ID",
                "client_secret": "OAuth application secret",
                "username": "Contract login (e.g., 123/NIC-REG)",
                "password": "Administrative or technical password",
                "scope": "OAuth scope (e.g., .+:/dns-master/.+)",
                "service": "DNS-master service name",
                "zone": "DNS zone name (Punycode)",
            },
        )

    # ------------------------------------------------------------------
    # DNS-01 Challenge
    # ------------------------------------------------------------------

    def _perform(
        self, domain: str, validation_name: str, validation: str
    ) -> None:
        """Добавляет TXT-запись _acme-challenge для верификации."""
        client = self._get_client()

        name = self._extract_name(validation_name, client.zone)

        record = TXTRecord(
            name=name,
            ttl=self.ttl,
            strings=[validation],
        )

        try:
            client.add_record(record)
            client.commit()
            logger.info(
                "ACME challenge record added: %s TXT %s", name, validation
            )
        except NicRuError as e:
            raise errors.PluginError(f"Failed to add TXT record: {e}")

    def _cleanup(
        self, domain: str, validation_name: str, validation: str
    ) -> None:
        """Удаляет _acme-challenge TXT-запись после верификации."""
        client = self._get_client()

        name = self._extract_name(validation_name, client.zone)

        try:
            # Получаем все записи и ищем нужную
            for record in client.get_records():
                if getattr(record, "name", "") != name:
                    continue
                if record.rr_type != "TXT":
                    continue
                # Проверяем значение TXT
                txt_value = getattr(record, "txt", "")
                if txt_value == validation and record.id:
                    client.delete_record(record.id)
                    logger.info(
                        "ACME challenge record #%d deleted: %s",
                        record.id,
                        name,
                    )

            client.commit()
        except NicRuError as e:
            raise errors.PluginError(f"Failed to delete TXT record: {e}")

    # ------------------------------------------------------------------
    # Хелперы
    # ------------------------------------------------------------------

    def _get_client(self) -> NicRuClient:
        """Лениво создаёт и кеширует HTTP-клиент."""
        if self._client is not None:
            return self._client

        if self.credentials is None:
            raise errors.PluginError("Credentials not configured")

        self._client = NicRuClient(
            client_id=self.credentials.conf("client_id"),
            client_secret=self.credentials.conf("client_secret"),
            username=self.credentials.conf("username"),
            password=self.credentials.conf("password"),
            scope=self.credentials.conf("scope"),
            default_service=self.credentials.conf("service"),
            default_zone=self.credentials.conf("zone"),
        )

        try:
            _ = self._client.token  # триггерит получение токена
        except NicRuError as e:
            raise errors.PluginError(f"Authentication failed: {e}")

        return self._client

    @staticmethod
    def _extract_name(name: str, zone: str) -> str:
        """Извлекает имя поддомена для _acme-challenge записи.

        Из: _acme-challenge.sub.example.com
        В:  _acme-challenge.sub  (при zone=example.com)
        """
        # Убираем зону из имени
        if name.endswith(f".{zone}"):
            name = name[: -(len(zone) + 1)]
        # Убираем wildcard-префикс если есть
        if name.startswith("*."):
            name = name[2:]
        return name
