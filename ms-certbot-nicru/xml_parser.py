"""Парсинг XML-ответов API NIC.RU и генерация XML-запросов."""

from __future__ import annotations

import logging
from typing import Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

from .exceptions import ApiError, ParseError
from .models import (
    DnsRecord,
    Zone,
    Service,
    record_factory,
    ARecord,
    AAAARecord,
    CNAMERecord,
    NSRecord,
    PTRRecord,
    DNAMERecord,
    MXRecord,
    TXTRecord,
    SRVRecord,
    HINFORecord,
    NAPTRRecord,
    RPRecord,
    SOARecord,
)

logger = logging.getLogger(__name__)


# ======================================================================
# Парсинг XML → объекты Python
# ======================================================================

def _element_text(el: Optional[Element], path: str, default: str = "") -> str:
    """Получить текст из вложенного элемента по относительному XPath."""
    if el is None:
        return default
    child = el.find(path)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _element_int(el: Optional[Element], path: str, default: int = 0) -> int:
    text = _element_text(el, path, str(default))
    try:
        return int(text)
    except ValueError:
        return default


def _element_bool(el: Optional[Element], path: str, default: bool = False) -> bool:
    text = _element_text(el, path, str(default).lower())
    return text == "true"


def _parse_services(xml_str: str) -> list[Service]:
    """Парсинг <data><service .../></data>."""
    root = ElementTree.fromstring(xml_str)
    _check_status(root)
    data = root.find("data")
    if data is None:
        return []
    services = []
    for svc_el in data.findall("service"):
        services.append(Service(
            name=svc_el.get("name", ""),
            admin=svc_el.get("admin", ""),
            payer=svc_el.get("payer", ""),
            tariff=svc_el.get("tariff", ""),
            enable=_element_bool(svc_el, None, True) if svc_el.get("enable") else True,
            # Атрибуты XML
        ))
    return services


def _parse_zones(xml_str: str) -> list[Zone]:
    """Парсинг <data><zone .../></data>."""
    root = ElementTree.fromstring(xml_str)
    _check_status(root)
    data = root.find("data")
    if data is None:
        return []
    zones = []
    for z_el in data.findall("zone"):
        zones.append(Zone(
            id=int(z_el.get("id", 0)),
            admin=z_el.get("admin", ""),
            name=z_el.get("name", ""),
            idn_name=z_el.get("idn-name", ""),
            service=z_el.get("service", ""),
            payer=z_el.get("payer", ""),
            enable=z_el.get("enable", "true") == "true",
            has_changes=z_el.get("has-changes", "false") == "true",
            has_primary=z_el.get("has-primary", "true") == "true",
        ))
    return zones


def parse_zone(xml_str: str) -> Optional[Zone]:
    """Парсинг одиночной зоны из ответа."""
    zones = _parse_zones(xml_str)
    return zones[0] if zones else None


# ---------------------------------------------------------------------------
# Парсинг ресурсных записей (главное!)
# ---------------------------------------------------------------------------

def _parse_one_record(rr_el: Element) -> Optional[DnsRecord]:
    """Парсит один <rr> элемент в DnsRecord. Возвращает None если тип неизвестен."""
    rtype = _element_text(rr_el, "type")
    cls = record_factory(rtype)

    if cls is None:
        logger.warning("Неизвестный тип записи: %s (пропускаем)", rtype)
        return None

    rec = cls.__new__(cls)
    rec.id = int(rr_el.get("id", 0))
    rec.name = _element_text(rr_el, "name", "@")
    ttl_text = _element_text(rr_el, "ttl", "3600")
    try:
        rec.ttl = int(ttl_text)
    except ValueError:
        rec.ttl = 3600

    # Каждый тип парсим индивидуально
    if rtype == "SOA":
        soa = rr_el.find("soa")
        if soa is not None:
            rec.mname = _element_text(soa, "mname/name")
            rec.rname = _element_text(soa, "rname/name")
            rec.serial = _element_int(soa, "serial")
            rec.refresh = _element_int(soa, "refresh")
            rec.retry = _element_int(soa, "retry")
            rec.expire = _element_int(soa, "expire")
            rec.minimum = _element_int(soa, "minimum")

    elif rtype == "A":
        rec.a = _element_text(rr_el, "a")

    elif rtype == "AAAA":
        rec.aaaa = _element_text(rr_el, "aaaa")

    elif rtype == "CNAME":
        rec.cname = _element_text(rr_el, "cname/name")

    elif rtype == "NS":
        rec.ns = _element_text(rr_el, "ns/name")

    elif rtype == "PTR":
        rec.ptr = _element_text(rr_el, "ptr/name")

    elif rtype == "DNAME":
        rec.dname = _element_text(rr_el, "dname/name")

    elif rtype == "MX":
        mx = rr_el.find("mx")
        if mx is not None:
            rec.preference = _element_int(mx, "preference")
            rec.exchange = _element_text(mx, "exchange/name")

    elif rtype == "TXT":
        txt = rr_el.find("txt")
        if txt is not None:
            rec.strings = [s.strip() if s.text else "" for s in txt.findall("string")]

    elif rtype == "SRV":
        srv = rr_el.find("srv")
        if srv is not None:
            rec.priority = _element_int(srv, "priority")
            rec.weight = _element_int(srv, "weight")
            rec.port = _element_int(srv, "port")
            rec.target = _element_text(srv, "target/name")

    elif rtype == "HINFO":
        hinfo = rr_el.find("hinfo")
        if hinfo is not None:
            rec.hardware = _element_text(hinfo, "hardware")
            rec.os = _element_text(hinfo, "os")

    elif rtype == "NAPTR":
        naptr = rr_el.find("naptr")
        if naptr is not None:
            rec.order = _element_int(naptr, "order")
            rec.preference = _element_int(naptr, "preference")
            rec.flags = _element_text(naptr, "flags")
            rec.service = _element_text(naptr, "service")
            rec.regexp = _element_text(naptr, "regexp")
            rec.replacement = _element_text(naptr, "replacement/name")

    elif rtype == "RP":
        rp = rr_el.find("rp")
        if rp is not None:
            rec.mbox_dname = _element_text(rp, "mbox-dname/name")
            rec.txt_dname = _element_text(rp, "txt-dname/name")

    return rec


def parse_records(xml_str: str) -> list[DnsRecord]:
    """Парсинг ответа на GET .../records."""
    root = ElementTree.fromstring(xml_str)
    _check_status(root)

    records = []
    for zone_el in root.findall(".//zone"):
        for rr_el in zone_el.findall("rr"):
            try:
                rec = _parse_one_record(rr_el)
                if rec is not None:
                    records.append(rec)
            except Exception as e:
                logger.warning("Ошибка парсинга записи: %s (пропускаем)", e)
                continue

    return records


# ======================================================================
# Проверка статуса ответа
# ======================================================================

def _check_status(root: Element) -> None:
    """Проверяет <status> в XML-ответе и выбрасывает ApiError если fail."""
    status_el = root.find("status")
    if status_el is not None and status_el.text == "fail":
        errors_el = root.find("errors")
        if errors_el is not None:
            for err in errors_el.findall("error"):
                code = err.get("code", "unknown")
                message = err.text or ""
                raise ApiError(code=code, message=message)
        raise ParseError("Статус fail без указания ошибок")


# ======================================================================
# Генерация XML-запроса для создания записей
# ======================================================================

def build_add_records_xml(records: list[DnsRecord]) -> str:
    """Генерирует XML для PUT .../records."""
    root = Element("request")
    rr_list = SubElement(root, "rr-list")

    for rec in records:
        rr = SubElement(rr_list, "rr")
        SubElement(rr, "name").text = rec.name
        SubElement(rr, "type").text = rec.rr_type

        if rec.ttl > 0:
            SubElement(rr, "ttl").text = str(rec.ttl)

        _build_type_specific(rr, rec)

    return _tostring(root)


def _build_type_specific(rr: Element, rec: DnsRecord) -> None:
    """Добавляет типоспецифичные XML-элементы."""
    rtype = rec.rr_type

    if rtype == "SOA":
        soa = SubElement(rr, "soa")
        mname = SubElement(soa, "mname")
        SubElement(mname, "name").text = rec.mname
        rname = SubElement(soa, "rname")
        SubElement(rname, "name").text = rec.rname
        SubElement(soa, "serial").text = str(rec.serial)
        SubElement(soa, "refresh").text = str(rec.refresh)
        SubElement(soa, "retry").text = str(rec.retry)
        SubElement(soa, "expire").text = str(rec.expire)
        SubElement(soa, "minimum").text = str(rec.minimum)

    elif rtype == "A":
        SubElement(rr, "a").text = rec.a

    elif rtype == "AAAA":
        SubElement(rr, "aaaa").text = rec.aaaa

    elif rtype == "CNAME":
        cname = SubElement(rr, "cname")
        SubElement(cname, "name").text = rec.cname

    elif rtype == "NS":
        ns = SubElement(rr, "ns")
        SubElement(ns, "name").text = rec.ns

    elif rtype == "PTR":
        ptr = SubElement(rr, "ptr")
        SubElement(ptr, "name").text = rec.ptr

    elif rtype == "DNAME":
        dname = SubElement(rr, "dname")
        SubElement(dname, "name").text = rec.dname

    elif rtype == "MX":
        mx = SubElement(rr, "mx")
        SubElement(mx, "preference").text = str(rec.preference)
        exchange = SubElement(mx, "exchange")
        SubElement(exchange, "name").text = rec.exchange

    elif rtype == "TXT":
        txt = SubElement(rr, "txt")
        for s in rec.strings:
            SubElement(txt, "string").text = s

    elif rtype == "SRV":
        srv = SubElement(rr, "srv")
        SubElement(srv, "priority").text = str(rec.priority)
        SubElement(srv, "weight").text = str(rec.weight)
        SubElement(srv, "port").text = str(rec.port)
        target = SubElement(srv, "target")
        SubElement(target, "name").text = rec.target

    elif rtype == "HINFO":
        hinfo = SubElement(rr, "hinfo")
        SubElement(hinfo, "hardware").text = rec.hardware
        SubElement(hinfo, "os").text = rec.os

    elif rtype == "NAPTR":
        naptr = SubElement(rr, "naptr")
        SubElement(naptr, "order").text = str(rec.order)
        SubElement(naptr, "preference").text = str(rec.preference)
        SubElement(naptr, "flags").text = rec.flags
        SubElement(naptr, "service").text = rec.service
        SubElement(naptr, "regexp").text = rec.regexp
        replacement = SubElement(naptr, "replacement")
        SubElement(replacement, "name").text = rec.replacement

    elif rtype == "RP":
        rp = SubElement(rr, "rp")
        mbox = SubElement(rp, "mbox-dname")
        SubElement(mbox, "name").text = rec.mbox_dname
        txtd = SubElement(rp, "txt-dname")
        SubElement(txtd, "name").text = rec.txt_dname


def _tostring(element: Element) -> str:
    """Сериализует XML элемент в строку."""
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(
        element, encoding="unicode"
    )
