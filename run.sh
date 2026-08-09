#!/bin/bash

echo "Собираем образ... "
docker build -t ofer-app-flood .

echo "Запуск контейнеров... Всего прокси в пуле: $NUM_PROXIES"

for i in {1..25}; do 
    docker run -d --name "ofer_$i" --restart unless-stopped ofer-app-flood; 
    echo "[$i/100] Контейнер ofer_$i запущен"
done

echo "Все контейнеры успешно запущены!"
