FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiohttp
RUN pip install --no-cache-dir h2
RUN pip install --no-cache-dir aiohttp-socks

COPY ofer.py .

ENTRYPOINT ["python3", "ofer.py", "flood", "proxy"]
