# ms-certbot-nicru

Новая реализация плагина Certbot для автоматического получения SSL-сертификатов через DNS-01 challenge на NIC.RU.

## Возможности

- Полная поддержка **всех типов DNS-записей** (A, AAAA, CNAME, NS, MX, TXT, SRV, SOA, PTR, DNAME, HINFO, NAPTR, RP)
- При парсинге неизвестный тип записи **логируется и пропускается**
- OAuth2 аутентификация по протоколу `password`
- WildCard-сертификаты (`*.example.com`)

## Отличия от старой версии (dns_nicru/sh_nic_api)

| Старая версия | Новая версия |
|---|---|
| Библиотека `sh_nic_api` (нет поддержки SRV) | Собственный клиент на `requests` + `xml.etree.ElementTree` |
| Падает при чтении зоны с SRV-записями | SRV парсится корректно |
| Привязана к старому `certbot` API | Совместима с `certbot >= 2.0` |

---

## Установка

### Если certbot установлен через pipx (рекомендуется)

```bash
# Перейти в папку проекта
cd /root/ms-certbot-nic/

# Влить пакет в виртуальное окружение certbot
pipx inject certbot .

# Проверить что плагин виден
certbot plugins | grep ms-dns-nicru
```

### Если certbot установлен через pip (обычный способ)

```bash
pip install .
```

---

## Параметры командной строки (специфичные для плагина)

| CLI-аргумент | По умолчанию | Обязательный | Назначение |
|---|---|---|---|
| `--authenticator ms-dns-nicru` | — | ✅ | Регистрация плагина в certbot |
| `--ms-dns-nicru-credentials <путь>` | — | ✅ | Путь к INI-файлу с учётными данными NIC.RU |
| `--ms-dns-nicru-propagation-seconds <N>` | **120** | ❌ | Время ожидания раскатки DNS-записи по миру перед проверкой ACME |

---

## INI-файл с учётными данными

Создайте файл (например `/etc/letsencrypt/nicru.ini`) и установите права `600`:

```bash
touch /etc/letsencrypt/nicru.ini
chmod 600 /etc/letsencrypt/nicru.ini
```

### Все ключи INI-файла

Формат ключей: `ms_dns_nicru_<имя_параметра>`

| Ключ | Обязательный | Назначение |
|---|---|---|
| `ms_dns_nicru_client_id` | ✅ | Идентификатор OAuth-приложения, зарегистрированного на NIC.RU |
| `ms_dns_nicru_client_secret` | ✅ | Секрет OAuth-приложения |
| `ms_dns_nicru_username` | ✅ | Логин договора (например `123/NIC-REG`) |
| `ms_dns_nicru_password` | ✅ | Административный или технический пароль от договора |
| `ms_dns_nicru_scope` | ✅ | Область доступа токена (например `.+:/dns-master/.+`) |
| `ms_dns_nicru_service` | ✅ | Идентификатор услуги DNS-master |
| `ms_dns_nicru_zone` | ✅ | Имя зоны в Punycode (например `example.com`) |

### Пример INI-файла

```ini
# NIC.RU credentials INI file
ms_dns_nicru_client_id = 12345
ms_dns_nicru_client_secret = abcdefghijklmnop
ms_dns_nicru_username = 123/NIC-REG
ms_dns_nicru_password = mypassword
ms_dns_nicru_scope = .+:/dns-master/.+
ms_dns_nicru_service = MYSERVICE
ms_dns_nicru_zone = example.com
```

---

## Использование

### WildCard сертификат

```bash
certbot certonly \
  --authenticator ms-dns-nicru \
  --ms-dns-nicru-credentials /etc/letsencrypt/nicru.ini \
  --ms-dns-nicru-propagation-seconds 300 \
  -d "*.example.com" \
  -d example.com
```

### Обычный сертификат

```bash
certbot certonly \
  --authenticator ms-dns-nicru \
  --ms-dns-nicru-credentials /etc/letsencrypt/nicru.ini \
  -d example.com
```

### Тестовый прогон (staging + dry-run)

```bash
certbot certonly \
  --authenticator ms-dns-nicru \
  --ms-dns-nicru-credentials /etc/letsencrypt/nicru.ini \
  -d "*.example.com" \
  -d example.com \
  --dry-run --test-cert \
  -v
```

---

## Требования

- Python >= 3.9
- certbot >= 2.0.0
- requests >= 2.25.0
- Активная услуга DNS-master на NIC.RU
- Зарегистрированное OAuth-приложение на NIC.RU

## Лицензия

MIT
