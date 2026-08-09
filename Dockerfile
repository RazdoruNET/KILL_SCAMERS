FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiohttp
RUN pip install --no-cache-dir h2
RUN pip install --no-cache-dir aiohttp-socks
RUN pip install --no-cache-dir fake_useragent

COPY zapros.py .

ENTRYPOINT ["python3", "zapros.py", "proxy"]
