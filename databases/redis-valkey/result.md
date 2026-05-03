# Redis / Valkey

## 1. Hash — данные о студентах

Созданы 3 студента. Каждый студент хранится в Hash с ключом student:<id>.

```bash
docker exec redis redis-cli HSET student:1 name Alice group ITIS-11 gpa 4.7
docker exec redis redis-cli HSET student:2 name Bob group ITIS-12 gpa 4.4
docker exec redis redis-cli HSET student:3 name Carol group ITIS-11 gpa 4.9
```

Результат для каждой команды:

```text
3
```

Проверка данных:

```redis
HGETALL student:1
```

Результат:

```text
name
Alice
group
ITIS-11
gpa
4.7
```

```redis
HGETALL student:2
```

Результат:

```text
name
Bob
group
ITIS-12
gpa
4.4
```

```redis
HGETALL student:3
```

Результат:

```text
name
Carol
group
ITIS-11
gpa
4.9
```

## 2. Sorted Set — лидерборд по GPA

Создан рейтинг студентов. В Sorted Set score равен GPA, member равен имени студента.

```redis
ZADD students:gpa 4.7 Alice 4.4 Bob 4.9 Carol
```

Результат:

```text
3
```

Топ-3 по убыванию GPA:

```redis
ZREVRANGE students:gpa 0 2 WITHSCORES
```

Результат:

```text
Carol
4.9
Alice
4.7
Bob
4.4
```

## 3. List — очередь задач

Добавлены 5 задач в очередь через RPUSH:

```redis
RPUSH task_queue \
  'task:prepare-report' \
  'task:send-email' \
  'task:backup-db' \
  'task:clear-cache' \
  'task:deploy-release'
```

Результат:

```text
5
```

Забраны 3 задачи по FIFO:

```redis
LPOP task_queue 3
```

Результат:

```text
task:prepare-report
task:send-email
task:backup-db
```

Оставшиеся задачи:

```redis
LRANGE task_queue 0 -1
```

Результат:

```text
task:clear-cache
task:deploy-release
```

## 4. TTL — время жизни ключа

Создан ключ с TTL 10 секунд:

```redis
SET temp:key 'temporary value' EX 10
```

Результат:

```text
OK
```

Проверка оставшегося времени:

```redis
TTL temp:key
```

Результат:

```text
4
```

После ожидания ключ исчез:

```redis
TTL temp:key
GET temp:key
```

Результат:

```text
-2

```

TTL = -2 означает, что ключа больше нет.

## 5. Транзакция MULTI/EXEC

Смоделирован перевод 1 балла GPA от студента 1 к студенту 2.
В транзакции обновлены Hash и Sorted Set, чтобы лидерборд остался согласованным с данными студентов.

```redis
MULTI
HINCRBYFLOAT student:1 gpa -1
HINCRBYFLOAT student:2 gpa 1
ZINCRBY students:gpa -1 Alice
ZINCRBY students:gpa 1 Bob
EXEC
```

Результат:

```text
OK
QUEUED
QUEUED
QUEUED
QUEUED
3.7
5.4
3.7
5.4
```

Проверка после транзакции:

```bash
docker exec redis redis-cli HMGET student:1 name gpa
docker exec redis redis-cli HMGET student:2 name gpa
```

Результат:

```text
Alice
3.7

Bob
5.4
```

Обновленный лидерборд:

```bash
docker exec redis redis-cli ZREVRANGE students:gpa 0 2 WITHSCORES
```

Результат:

```text
Bob
5.4
Carol
4.9
Alice
3.7
```

## 6. Pub/Sub

В первом терминале запущен подписчик:

```bash
docker exec -it redis redis-cli
```

```redis
SUBSCRIBE news
```

Результат подписки:

```text
subscribe
news
1
```

Во втором терминале опубликованы сообщения:

```bash
docker exec redis redis-cli PUBLISH news 'Hello from Redis!'
docker exec redis redis-cli PUBLISH news 'Second message'
```

Результат для каждой публикации:

```text
1
```

Подписчик получил сообщения:

```text
message
news
Second message

message
news
Hello from Redis!
```

Вывод: Pub/Sub работает, канал news принимает опубликованные сообщения.
