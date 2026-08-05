#!/bin/bash

# ЗАБАНИТЬ АЙПИ РЕШИЛ ШУТНИК ))) ХОТЬ ОБЛОЖИСЬ БЛОКИРОВКАМИ ТУТ ТЫСЯЧИ IP И СПИСОК ОБНОВЛЯЕТСЯ КАЖДЫЕ 5 МИНУТ
PROXY_URL="https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/all/data.txt" 
PROXY_FILE="proxies.txt"

echo "Загружаем свежий список прокси из ProxyScrape..."

if ! curl -sSf "$PROXY_URL" -o "$PROXY_FILE"; then
    echo "Ошибка: Не удалось загрузить прокси список!"
    exit 1
fi

mapfile -t PROXY_LIST < "$PROXY_FILE"
NUM_PROXIES=${#PROXY_LIST[@]}

if [ "$NUM_PROXIES" -eq 0 ]; then
    echo "Ошибка: Список прокси пуст!"
    exit 1
fi

echo "Успешно загружено $NUM_PROXIES прокси. Начинаем запуск контейнеров..."

echo "Собираем образ... "
docker build -t ofer-app-rapid .

echo "Запуск контейнеров... Всего прокси в пуле: $NUM_PROXIES"

for i in {1..100}; do
    CURRENT_PROXY=${PROXY_LIST[$(( (i-1) % NUM_PROXIES ))]}
    CONTAINER_NAME="ofer_$i"

    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -e PROXY_URL="$CURRENT_PROXY" \
        ofer-app >/dev/null

    echo "[$i/100] Контейнер $CONTAINER_NAME запущен через прокси $CURRENT_PROXY"
done

echo "Все контейнеры успешно запущены!"
