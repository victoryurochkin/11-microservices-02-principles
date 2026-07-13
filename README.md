# Домашнее задание к занятию «Микросервисы: принципы» - Юрочкин В.А.

## Задача 1. API Gateway

API Gateway является единой точкой входа во внешние API микросервисной системы. Он принимает клиентские соединения, завершает TLS, проверяет правила доступа и направляет запросы в нужные backend-сервисы.

### Сравнение решений

| Критерий | NGINX Open Source | Kong Gateway | Traefik Proxy | Envoy Proxy |
|---|---|---|---|---|
| Маршрутизация | По host, URI, методу и другим параметрам; конфигурация в файлах | Routes и Services, декларативная конфигурация или Admin API | Динамические routers/services из Docker, Kubernetes и файлов | Гибкая L7-маршрутизация через статическую или xDS-конфигурацию |
| Проверка аутентификации | Basic Auth; внешняя проверка через `auth_request`; расширенные JWT/OIDC-возможности зависят от редакции и модулей | Плагины Key Auth, Basic Auth, JWT, OAuth 2.0 и другие | `ForwardAuth` делегирует проверку внешнему сервису | Фильтр `ext_authz` вызывает HTTP- или gRPC-сервис авторизации |
| Терминация HTTPS | Есть | Есть | Есть, включая автоматизацию ACME | Есть, включая mTLS |
| Балансировка | Round-robin по умолчанию, least connections, hash | Есть, включая upstream health checks | Есть, хорошо интегрирована с динамическими провайдерами | Расширенная балансировка и health checking |
| Изменение конфигурации | Обычно reload после проверки конфигурации | Через Admin API или декларативную конфигурацию | Автоматически отслеживает изменения провайдеров | Динамически через xDS, но control plane усложняет систему |
| Расширяемость | Модули NGINX и интеграция с внешними сервисами | Большой набор gateway-плагинов | Middleware и плагины | HTTP-фильтры и внешние control plane-компоненты |
| Сложность эксплуатации | Низкая | Средняя: дополнительные сущности, плагины, иногда БД/control plane | Низкая или средняя, особенно удобен в Docker/Kubernetes | Высокая без готовой платформы управления |
| Наиболее подходящий сценарий | Простой, быстрый и предсказуемый reverse proxy/API Gateway | Полноценная API-management-платформа | Динамическая cloud-native-инфраструктура | Service mesh, сложная маршрутизация, высоконагруженные платформы |

### Выбор

Для поставленной задачи выбран **NGINX Open Source**.

Причины выбора:

1. NGINX выполняет все обязательные требования: маршрутизирует запросы по URI и HTTP-методу, завершает HTTPS и может делегировать проверку токена сервису безопасности через директиву `auth_request`.
2. Решение не требует отдельной базы данных или control plane и состоит из одного небольшого контейнера.
3. Конфигурацию легко хранить в Git, проверять командой `nginx -t`, выпускать через CI/CD и откатывать вместе с версией приложения.
4. NGINX широко применяется как reverse proxy и балансировщик, поэтому его проще сопровождать небольшой DevOps-команде.
5. Для текущего набора требований Kong или Envoy создадут дополнительную эксплуатационную сложность. Их имеет смысл выбирать, когда компании нужны централизованное управление большим количеством API, developer portal, сложные политики, сервисная сеть или динамический control plane.

Проверка аутентификации организована следующим образом: перед передачей защищённого запроса NGINX выполняет внутренний subrequest в сервис `security`. Ответ `2xx` разрешает исходный запрос, а `401` или `403` запрещает его.

Для production-среды HTTPS завершается на NGINX в `server` с `listen 443 ssl`, а сертификат и ключ подключаются через `ssl_certificate` и `ssl_certificate_key`. Сертификаты следует получать и обновлять через ACME-клиент или cert-manager, а закрытые ключи хранить в менеджере секретов.

## Задача 2. Брокер сообщений

### Сравнение брокеров

| Критерий | RabbitMQ | Apache Kafka | NATS JetStream | ActiveMQ Artemis |
|---|---|---|---|---|
| Кластеризация и отказоустойчивость | Кластер; quorum queues и streams реплицируются с использованием Raft | Распределённый кластер, партиции и реплики | Кластеры NATS, репликация JetStream streams | Кластеризация, replication/shared store, HA-пары |
| Хранение сообщений на диске | Durable messages; quorum queues сохраняют данные на диск | Дисковый append-only log является основой архитектуры | File storage в JetStream | Journal на диске, поддержка persistence |
| Скорость | Высокая для очередей задач и маршрутизации сообщений | Очень высокая пропускная способность для потоков событий | Очень низкая задержка и высокая скорость | Высокая, но обычно выбирается для JMS/enterprise-интеграций |
| Форматы сообщений | Не навязывает формат payload; JSON, XML, Protobuf, бинарные данные | Байтовые записи; формат задают producer/consumer и serializer | Произвольный байтовый payload | Произвольные сообщения; JMS-типы и несколько протоколов |
| Разграничение доступа | Users, virtual hosts, permissions на configure/write/read | ACL на topics, consumer groups и cluster operations | Accounts, users, publish/subscribe permissions по subjects | Users, roles и permissions на addresses/queues |
| Протоколы и клиенты | AMQP 0-9-1, AMQP 1.0, MQTT, STOMP через плагины; много клиентов | Собственный протокол и развитая экосистема клиентов | Собственный лёгкий протокол, WebSocket, MQTT | AMQP, MQTT, STOMP, OpenWire, Core, JMS |
| Маршрутизация | Очень гибкая: exchanges direct/topic/fanout/headers | Основная модель — topics и partitions | Subjects и wildcard-подписки | Addresses, queues, multicast/anycast |
| Простота эксплуатации | Высокая: понятная модель, management UI, зрелые инструменты | Средняя или низкая: необходимо управлять партициями, retention и capacity planning | Высокая для базового сценария, но JetStream требует понимания retention и replication | Средняя, особенно в Java/JMS-среде |
| Оптимальный сценарий | Очереди заданий, команды, интеграция микросервисов, сложная маршрутизация | Event streaming, аналитика, event sourcing, большие объёмы истории | Cloud-native messaging с минимальной задержкой | Корпоративные Java/JMS-системы и интеграции |

### Выбор

Для рассматриваемой микросервисной системы выбран **RabbitMQ с quorum queues**.

Обоснование:

1. Quorum queues являются реплицируемыми очередями на основе Raft и предназначены для высокой доступности и сохранности данных.
2. Сообщения могут сохраняться на диск до подтверждения обработки потребителем. Для надёжной доставки необходимо использовать durable quorum queue, persistent messages, publisher confirms и manual acknowledgements.
3. RabbitMQ обеспечивает достаточную скорость для большинства операций интернет-магазина: создание заказа, резервирование товара, уведомления, интеграция с оплатой и доставкой.
4. Брокер не ограничивает формат payload. Команды и события можно передавать в JSON, Avro, Protobuf или бинарном формате. Для совместимости необходимо отдельно вести версионирование схем сообщений.
5. Virtual hosts, пользователи и permissions позволяют разделить права команд и сервисов на чтение, запись и конфигурирование exchanges/queues.
6. RabbitMQ проще эксплуатировать, чем Kafka, если системе не требуется долговременное хранение огромного потока событий и многократное независимое перечитывание истории.
7. Management UI, CLI, Prometheus-метрики и большое количество клиентских библиотек упрощают диагностику и сопровождение.

Рекомендуемая production-конфигурация: нечётное количество узлов, обычно три; quorum queues с тремя репликами; SSD/NVMe; балансировщик перед брокерами; publisher confirms; manual acknowledgements; dead-letter exchanges; retry-политики; TLS; отдельные пользователи и virtual hosts; мониторинг размера очередей, unacked-сообщений, диска, памяти и состояния quorum.

Kafka следует выбрать вместо RabbitMQ, если основной сценарий — потоковая аналитика, event sourcing, хранение истории событий в течение длительного времени и многократное чтение одного потока независимыми группами потребителей. NATS JetStream подходит, если приоритетом являются минимальная задержка, простая cloud-native-модель subjects и небольшой операционный overhead.

## Задача 3*. Практическая реализация API Gateway

### Архитектура

В проект входят:

- `gateway` — NGINX, единственная внешняя точка входа;
- `security` — регистрация, вход, выдача и проверка JWT;
- `uploader` — проверка изображения, преобразование в JPEG, сжатие и загрузка в MinIO;
- `minio` — S3-совместимое объектное хранилище;
- `minio-init` — создаёт бакет `images` и включает чтение объектов для совместимого маршрута `/images/...`.

Все backend-сервисы находятся во внутренней Docker-сети и не публикуют порты на хост. Наружу опубликован только порт `80` API Gateway.

### Маршрутизация

| Внешний маршрут | Доступ | Backend-маршрут |
|---|---|---|
| `POST /v1/register` | анонимный | `security POST /v1/user` |
| `POST /register` | анонимный, совместимый alias | `security POST /v1/user` |
| `POST /v1/token` | анонимный | `security POST /v1/token` |
| `POST /token` | анонимный, маршрут из примера задания | `security POST /v1/token` |
| `GET /v1/user` | Bearer JWT | `security GET /v1/user` |
| `POST /v1/upload` | Bearer JWT | `uploader POST /v1/upload` |
| `POST /upload` | Bearer JWT, маршрут из примера задания | `uploader POST /v1/upload` |
| `GET /v1/user/{image}` | Bearer JWT | `minio GET /images/{image}` |
| `GET /images/{image}` | публичный совместимый alias | `minio GET /images/{image}` |

В условии есть расхождение: описание требует защищённый `GET /v1/user/{image}`, а пример проверки использует публичный `GET /images/{image}` без заголовка `Authorization`. Поэтому реализованы оба маршрута. Для production-системы бакет следует оставить закрытым, защитить `/images/` через `auth_request` или выдавать клиенту краткоживущий presigned URL.

### Структура проекта

```text
.
├── docker-compose.yml
├── .env.example
├── .gitignore
├── nginx
│   └── nginx.conf
├── security
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── uploader
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── test.sh
└── README.md
```

### Запуск

```bash
cp .env.example .env
```

Для точного воспроизведения JWT из примера задания в демонстрации используется слабый секрет `secret`. Для обычной проверки можно оставить его, но в любой реальной среде `JWT_SECRET` и `MINIO_ROOT_PASSWORD` необходимо заменить, после чего выполнить:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f gateway security uploader minio-init
```

Проверка конфигурации NGINX:

```bash
docker compose exec gateway nginx -t
```

### Ручное тестирование

#### 1. Проверка шлюза

```bash
curl -i http://localhost/health
```

#### 2. Регистрация нового пользователя

```bash
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -d '{"login":"alice","password":"strong-password"}' \
  http://localhost/v1/register
```

Пользователь `bob` с паролем `qwe123` уже создан в демонстрационном сервисе, чтобы команда из задания выполнялась сразу после запуска.

#### 3. Авторизация

```bash
curl -sS -X POST \
  -H 'Content-Type: application/json' \
  -d '{"login":"bob","password":"qwe123"}' \
  http://localhost/token
```

Из ответа необходимо скопировать значение `access_token`:

```bash
TOKEN='полученный_JWT'
```

#### 4. Проверка защищённого маршрута

```bash
curl -i \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost/v1/user
```

Без токена запрос должен получить `401 Unauthorized`:

```bash
curl -i http://localhost/v1/user
```

#### 5. Загрузка изображения

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @yourfilename.jpg \
  http://localhost/upload
```

Ответ содержит сгенерированное имя объекта:

```json
{
  "object": "4e6df220-295e-4231-82bc-45e4b1484430.jpg",
  "url": "/images/4e6df220-295e-4231-82bc-45e4b1484430.jpg",
  "size": 12345
}
```

#### 6. Получение изображения по совместимому публичному маршруту

```bash
curl -f \
  http://localhost/images/4e6df220-295e-4231-82bc-45e4b1484430.jpg \
  --output result.jpg
```

#### 7. Получение изображения по защищённому маршруту из текстового условия

```bash
curl -f \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost/v1/user/4e6df220-295e-4231-82bc-45e4b1484430.jpg \
  --output protected-result.jpg
```

### Проверка точными командами из условия

Демонстрационный секрет подобран так, чтобы JWT из условия для пользователя `bob` проходил проверку:

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"login":"bob", "password":"qwe123"}' \
  http://localhost/token
```

```bash
curl -X POST \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJib2IifQ.hiMVLmssoTsy1MqbmIoviDeFPvo-nCd92d4UFiN2O2I' \
  -H 'Content-Type: octet/stream' \
  --data-binary @yourfilename.jpg \
  http://localhost/upload
```

Имя загруженного объекта нужно взять из JSON-ответа и подставить в команду:

```bash
curl -X GET \
  http://localhost/images/OBJECT_NAME.jpg \
  --output result.jpg
```

### Автоматическая проверка

```bash
./test.sh ./yourfilename.jpg
```

Скрипт получает JWT, проверяет пользователя, загружает изображение и скачивает его через оба маршрута.

### Остановка и очистка

```bash
docker compose down
```

Удаление вместе с объектами MinIO:

```bash
docker compose down -v
```

---

## Источники

1. [NGINX: ngx_http_auth_request_module](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html)
2. [NGINX: HTTP proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
3. [NGINX: SSL module](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
4. [Kong Gateway features](https://docs.konghq.com/install/source)
5. [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
6. [Envoy external authorization](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_authz_filter)
7. [RabbitMQ quorum queues](https://www.rabbitmq.com/docs/quorum-queues)
8. [RabbitMQ clustering](https://www.rabbitmq.com/docs/clustering)
9. [RabbitMQ persistence configuration](https://www.rabbitmq.com/docs/persistence-conf)
10. [Apache Kafka documentation](https://kafka.apache.org/documentation/)
11. [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)
12. [ActiveMQ Artemis documentation](https://artemis.apache.org/components/artemis/documentation/latest/)
