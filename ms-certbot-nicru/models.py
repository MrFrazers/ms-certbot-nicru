"""Модели данных DNS API NIC.RU."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Базовые
# ---------------------------------------------------------------------------

@dataclass
class DnsRecord:
    """Базовый класс ресурсной записи DNS."""

    id: Optional[int] = None
    name: str = "@"
    ttl: int = 3600

    @property
    def rr_type(self) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# SOA
# ---------------------------------------------------------------------------

@dataclass
class SOARecord(DnsRecord):
    mname: str = ""
    rname: str = ""
    serial: int = 0
    refresh: int = 14400
    retry: int = 3600
    expire: int = 2592000
    minimum: int = 600

    @property
    def rr_type(self) -> str:
        return "SOA"


# ---------------------------------------------------------------------------
# A / AAAA
# ---------------------------------------------------------------------------

@dataclass
class ARecord(DnsRecord):
    a: str = ""

    @property
    def rr_type(self) -> str:
        return "A"


@dataclass
class AAAARecord(DnsRecord):
    aaaa: str = ""

    @property
    def rr_type(self) -> str:
        return "AAAA"


# ---------------------------------------------------------------------------
# CNAME / NS / PTR / DNAME
# ---------------------------------------------------------------------------

@dataclass
class CNAMERecord(DnsRecord):
    cname: str = ""

    @property
    def rr_type(self) -> str:
        return "CNAME"


@dataclass
class NSRecord(DnsRecord):
    ns: str = ""

    @property
    def rr_type(self) -> str:
        return "NS"


@dataclass
class PTRRecord(DnsRecord):
    ptr: str = ""

    @property
    def rr_type(self) -> str:
        return "PTR"


@dataclass
class DNAMERecord(DnsRecord):
    dname: str = ""

    @property
    def rr_type(self) -> str:
        return "DNAME"


# ---------------------------------------------------------------------------
# MX
# ---------------------------------------------------------------------------

@dataclass
class MXRecord(DnsRecord):
    preference: int = 10
    exchange: str = ""

    @property
    def rr_type(self) -> str:
        return "MX"


# ---------------------------------------------------------------------------
# TXT
# ---------------------------------------------------------------------------

@dataclass
class TXTRecord(DnsRecord):
    strings: list[str] = field(default_factory=list)

    @property
    def rr_type(self) -> str:
        return "TXT"

    @property
    def txt(self) -> str:
        return "".join(self.strings)


# ---------------------------------------------------------------------------
# SRV — ключевая запись, из-за которой всё переписываем!
# ---------------------------------------------------------------------------

@dataclass
class SRVRecord(DnsRecord):
    priority: int = 0
    weight: int = 0
    port: int = 0
    target: str = ""

    @property
    def rr_type(self) -> str:
        return "SRV"


# ---------------------------------------------------------------------------
# HINFO
# ---------------------------------------------------------------------------

@dataclass
class HINFORecord(DnsRecord):
    hardware: str = ""
    os: str = ""

    @property
    def rr_type(self) -> str:
        return "HINFO"


# ---------------------------------------------------------------------------
# NAPTR
# ---------------------------------------------------------------------------

@dataclass
class NAPTRRecord(DnsRecord):
    order: int = 0
    preference: int = 0
    flags: str = ""
    service: str = ""
    regexp: str = ""
    replacement: str = ""

    @property
    def rr_type(self) -> str:
        return "NAPTR"


# ---------------------------------------------------------------------------
# RP
# ---------------------------------------------------------------------------

@dataclass
class RPRecord(DnsRecord):
    mbox_dname: str = ""
    txt_dname: str = ""

    @property
    def rr_type(self) -> str:
        return "RP"


# ---------------------------------------------------------------------------
# Вспомогательные модели
# ---------------------------------------------------------------------------

@dataclass
class Zone:
    """Доменная зона."""

    id: int = 0
    admin: str = ""
    name: str = ""
    idn_name: str = ""
    service: str = ""
    payer: str = ""
    enable: bool = True
    has_changes: bool = False
    has_primary: bool = True


@dataclass
class Service:
    """Услуга DNS-хостинга."""

    name: str = ""
    admin: str = ""
    payer: str = ""
    tariff: str = ""
    enable: bool = True
    has_primary: bool = True
    domains_limit: int = 0
    domains_num: int = 0
    rr_limit: int = 0
    rr_num: int = 0


# ---------------------------------------------------------------------------
# Фабрика
# ---------------------------------------------------------------------------

_RECORD_TYPE_MAP: dict[str, type[DnsRecord]] = {
    "SOA": SOARecord,
    "A": ARecord,
    "AAAA": AAAARecord,
    "CNAME": CNAMERecord,
    "NS": NSRecord,
    "PTR": PTRRecord,
    "DNAME": DNAMERecord,
    "MX": MXRecord,
    "TXT": TXTRecord,
    "SRV": SRVRecord,
    "HINFO": HINFORecord,
    "NAPTR": NAPTRRecord,
    "RP": RPRecord,
}


def record_factory(rr_type: str) -> type[DnsRecord] | None:
    """Возвращает класс записи по строковому типу или None."""
    return _RECORD_TYPE_MAP.get(rr_type.upper())
