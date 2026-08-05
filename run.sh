#!/bin/bash

cat << 'EOF' > proxies.txt
85.142.254.32:1080
213.213.210.44:1080
EOF

mapfile -t PROXY_LIST < proxies.txt
NUM_PROXIES=${#PROXY_LIST[@]}

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
