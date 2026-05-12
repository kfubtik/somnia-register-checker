# Somnia Register Checker

Python-скрипт для проверки eligibility на `https://register.somnia.network/`.

Скрипт работает только с публичными адресами. Приватные ключи, seed-фразы, подписи и подключение кошелька не используются.

## Файлы

Основной скрипт:

```txt
somnia_register_checker.py
```

Файл с адресами:

```txt
addresses.txt
```

Файл с прокси:

```txt
proxies.txt
```

Файл результата:

```txt
somnia_register_results.txt
```

## Установка

Нужен только Python 3.10+.

Проверить версию:

```bash
python --version
```

Дополнительные библиотеки устанавливать не нужно.

## addresses.txt

Один адрес на строку:

```txt
0x1111111111111111111111111111111111111111
0x2222222222222222222222222222222222222222
```

Пустые строки и строки с `#` пропускаются.

## proxies.txt

Один proxy на строку:

```txt
http://user:pass@host:port
user:pass@host:port
host:port
```

Если прокси не нужны, оставь файл пустым или не используй его.

Прокси используются по кругу: первый адрес через первый proxy, второй через второй proxy, и так далее.

## Запуск

Обычный запуск:

```bash
python somnia_register_checker.py
```

Указать свои файлы:

```bash
python somnia_register_checker.py --addresses my_addresses.txt --proxies my_proxies.txt --output result.txt
```

Запуск без прокси:

```bash
python somnia_register_checker.py --addresses addresses.txt
```

Задержка между запросами:

```bash
python somnia_register_checker.py --delay 1
```

## Что выводится в консоль

Во время работы:

```txt
[1/10] 0x... - not eligible - allocation: 0
[2/10] 0x... - eligible - allocation: 123.45
```

В конце:

```txt
Checked wallets: 10
Eligible wallets: 2
Total allocation: 246.9 SOMI
Saved results to somnia_register_results.txt
```

## Результат в TXT

Формат строк:

```txt
address - eligible/not eligible - allocation: amount
```

Пример:

```txt
0x2222222222222222222222222222222222222222 - not eligible - allocation: 0
0x1111111111111111111111111111111111111111 - eligible - allocation: 100
```

Если запрос упал, в строке будет ошибка:

```txt
0x... - not eligible - allocation: 0 - error: HTTP 403
```

## Параметры

```txt
--addresses   путь к TXT с адресами, по умолчанию addresses.txt
--proxies     путь к TXT с proxy, по умолчанию proxies.txt
--output      путь к TXT результату, по умолчанию somnia_register_results.txt
--delay       задержка между запросами, по умолчанию 0.2 секунды
--timeout     timeout HTTP-запроса, по умолчанию 30 секунд
```

## Как определяется eligible

Скрипт отправляет запрос:

```txt
POST https://register.somnia.network/api/eligibility
```

Тело запроса:

```json
{
  "evmAddresses": ["0x..."]
}
```

Адрес считается eligible, если API возвращает `eligible: true` или `total` больше `0`.
