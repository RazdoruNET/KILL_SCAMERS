## два режима воздействия на цель

* slow — медленные запросы с паузой и размазанным трафиком;
* flood — высокая интенсивность, меньше задержка и больше параллельных воркеров.

Также внедрил случайную jitter-паузы, чтобы поток выглядел менее регулярным.

## Использование:

python3 ofer.py slow
python3 ofer.py flood

Если аргумент не передан, используется режим по умолчанию — flood.


## Удаление контейнеров

docker rm -f $(docker ps -a -q --filter "name=ofer_")

## Создание образа

docker build -t ofer-app .

## Запуск пачки контейнеров

for i in {1..50}; do docker run -d --name "ofer_$i" --restart unless-stopped ofer-app; done
