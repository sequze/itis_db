# Cassandra

## 1. Инициализация БД с репликацией

Создан файл docker-compose.yml с двумя нодами Cassandra:

```yaml
services:
  node1:
    image: cassandra:latest
    container_name: cassandra-node1
    ports:
      - "9042:9042"
    environment:
      - CASSANDRA_CLUSTER_NAME=TestCluster
      - CASSANDRA_ENDPOINT_SNITCH=GossipingPropertyFileSnitch
      - MAX_HEAP_SIZE=256M
      - HEAP_NEWSIZE=64M

  node2:
    image: cassandra:latest
    container_name: cassandra-node2
    environment:
      - CASSANDRA_CLUSTER_NAME=TestCluster
      - CASSANDRA_SEEDS=node1
      - CASSANDRA_ENDPOINT_SNITCH=GossipingPropertyFileSnitch
      - MAX_HEAP_SIZE=256M
      - HEAP_NEWSIZE=64M
```

Результат:

```text
Datacenter: dc1
===============
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
--  Address        Load       Tokens  Owns (effective)  Host ID                               Rack
UN  192.168.160.2  119.8 KiB  16      100.0%            f2f10b5f-028d-4ce8-8de7-6b6fe1e1a348  rack1
UN  192.168.160.3  114.6 KiB  16      100.0%            e3e0bf01-6be6-48e2-974e-6833be5a8c29  rack1
```

Создан keyspace university с фактором репликации 2:

```cql
CREATE KEYSPACE university
WITH replication = {
  'class': 'SimpleStrategy',
  'replication_factor': 2
};
```

Результат:

```text
CREATE KEYSPACE university WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '2'} AND durable_writes = true;
```

## 2. Создание таблицы и данных

Создана таблица student_grades:

```cql
CREATE TABLE student_grades (
  student_id uuid,
  created_at timestamp,
  subject text,
  grade int,
  PRIMARY KEY (student_id, created_at)
) WITH CLUSTERING ORDER BY (created_at DESC);
```

student_id является Partition Key, created_at является Clustering Key.

Для двух студентов сгенерированы UUID через uuid(), затем каждому студенту добавлена вторая оценка.

Итоговые данные:

```text
 student_id                           | created_at                      | subject   | grade
--------------------------------------+---------------------------------+-----------+-------
 839a4370-1d76-4936-9b0f-c6166f9cc664 | 2026-05-03 12:00:00.000000+0000 |      Math |     5
 839a4370-1d76-4936-9b0f-c6166f9cc664 | 2026-05-03 11:00:00.000000+0000 | Cassandra |     4
 641eb178-af27-4daf-ad37-d58f39d6e76b | 2026-05-03 13:00:00.000000+0000 | Databases |     4
 641eb178-af27-4daf-ad37-d58f39d6e76b | 2026-05-03 10:00:00.000000+0000 | Databases |     5
```

## 3. Проверка распределения данных

UUID студентов:

```text
839a4370-1d76-4936-9b0f-c6166f9cc664
641eb178-af27-4daf-ad37-d58f39d6e76b
```

Команда для первого UUID:

```bash
docker exec cassandra-node1 nodetool getendpoints university student_grades 839a4370-1d76-4936-9b0f-c6166f9cc664
```

Результат:

```text
192.168.160.3
192.168.160.2
```

Команда для второго UUID:

```bash
docker exec cassandra-node1 nodetool getendpoints university student_grades 641eb178-af27-4daf-ad37-d58f39d6e76b
```

Результат:

```text
192.168.160.2
192.168.160.3
```

Вывод: так как у keyspace university фактор репликации равен 2, данные каждого partition key находятся на обеих нодах.

## 4. Работа с фильтрацией

Запрос по неключевому полю subject:

```cql
SELECT * FROM university.student_grades WHERE subject = 'Databases';
```

Результат:

```text
InvalidRequest: Error from server: code=2200 [Invalid query] message="Cannot execute this query as it might involve data filtering and thus may have unpredictable performance. If you want to execute this query despite the performance unpredictability, use ALLOW FILTERING"
```

Этот запрос не выполняется без ALLOW FILTERING, потому что subject не входит в ключ таблицы.

Запрос с ALLOW FILTERING:

```cql
SELECT * FROM university.student_grades WHERE subject = 'Databases' ALLOW FILTERING;
```

Результат:

```text
 student_id                           | created_at                      | grade | subject
--------------------------------------+---------------------------------+-------+-----------
 641eb178-af27-4daf-ad37-d58f39d6e76b | 2026-05-03 13:00:00.000000+0000 |     4 | Databases
 641eb178-af27-4daf-ad37-d58f39d6e76b | 2026-05-03 10:00:00.000000+0000 |     5 | Databases
```
