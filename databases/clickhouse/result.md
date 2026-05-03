# ClickHouse

## 1. Создание таблицы web_logs и наполнение данными

Создана таблица:

```sql
CREATE TABLE web_logs (
    log_time DateTime,
    ip String,
    url String,
    status_code UInt16,
    response_size UInt64
) ENGINE = MergeTree()
ORDER BY (log_time, status_code);
```

Данные добавлены из numbers(500000):

```sql
INSERT INTO web_logs
SELECT
    toDateTime('2024-03-01 00:00:00') + INTERVAL number SECOND,
    concat('192.168.0.', toString(number % 50)),
    arrayElement(['/home', '/api/users', '/api/orders', '/admin', '/products'], number % 5 + 1),
    arrayElement([200, 200, 200, 404, 500, 301, 200], number % 7 + 1),
    rand() % 1000000
FROM numbers(500000);
```

## 2. Топ-10 IP-адресов по количеству запросов

```sql
SELECT
    ip,
    count() AS requests
FROM web_logs
GROUP BY ip
ORDER BY requests DESC, ip ASC
LIMIT 10;
```

Результат:

```text
ip             requests
192.168.0.0       10000
192.168.0.1       10000
192.168.0.10      10000
192.168.0.11      10000
192.168.0.12      10000
192.168.0.13      10000
192.168.0.14      10000
192.168.0.15      10000
192.168.0.16      10000
192.168.0.17      10000
```

Данные распределены равномерно по 50 IP-адресам, поэтому у каждого IP по 10000 запросов.

## 3. Процент успешных и ошибочных запросов

```sql
SELECT
    round(countIf(status_code BETWEEN 200 AND 299) * 100 / count(), 2) AS success_2xx_pct,
    round(countIf(status_code BETWEEN 400 AND 599) * 100 / count(), 2) AS error_4xx_5xx_pct
FROM web_logs;
```

Результат:

```text
success_2xx_pct    error_4xx_5xx_pct
57.14              28.57
```

Успешные запросы 2xx составили 57.14%.
Ошибочные запросы 4xx и 5xx составили 28.57%.
Оставшиеся 14.29% - это редиректы 3xx.

## 4. Самый популярный URL и средний размер ответа

```sql
SELECT
    url,
    count() AS requests,
    round(avg(response_size), 2) AS avg_response_size
FROM web_logs
GROUP BY url
ORDER BY requests DESC, url ASC
LIMIT 1;
```

Результат:

```text
url       requests    avg_response_size
/admin    100000      501711.51
```

URL распределены равномерно, поэтому у каждого URL по 100000 запросов. При дополнительной сортировке первым идет /admin.

## 5. Час с наибольшим количеством ошибок 500

```sql
SELECT
    toStartOfHour(log_time) AS hour,
    count() AS errors_500
FROM web_logs
WHERE status_code = 500
GROUP BY hour
ORDER BY errors_500 DESC, hour ASC
LIMIT 1;
```

Результат:

```text
hour                   errors_500
2024-03-01 02:00:00    515
```

## 6. Сравнение ClickHouse и PostgreSQL

Создана таблица в ClickHouse:

```sql
CREATE TABLE sales_ch (
    sale_date DateTime,
    product_id UInt64,
    category String,
    quantity UInt32,
    price Float64,
    customer_id UInt64
) ENGINE = MergeTree()
ORDER BY (sale_date);
```

Создана таблица в PostgreSQL:

```sql
CREATE TABLE sales_pg (
    sale_date timestamp,
    product_id bigint,
    category text,
    quantity integer,
    price float8,
    customer_id bigint
);

CREATE INDEX idx_sales_pg_date ON sales_pg(sale_date);
CREATE INDEX idx_sales_pg_product ON sales_pg(product_id);
```

В обе таблицы добавлено по 1 000 000 строк.

Время вставки:

```text
ClickHouse:  0.084 s
PostgreSQL:  2.014 s
```

ClickHouse вставил 1 млн строк в 24 раза быстрее.

## 7. Запрос продаж за последний месяц

Последний месяц считался относительно максимальной даты в таблице.

ClickHouse:

```sql
SELECT
    category,
    count() AS sales_count,
    round(sum(quantity * price), 2) AS revenue
FROM sales_ch
WHERE sale_date >= (SELECT max(sale_date) FROM sales_ch) - INTERVAL 1 MONTH
GROUP BY category
ORDER BY category;
```

Результат:

```text
category       sales_count    revenue
Books          11161          3133790.26
Clothing       11160          3047803.90
Electronics    11160          3039028.08
Food           11160          3098624.94
```

PostgreSQL:

```sql
SELECT
    category,
    count(*) AS sales_count,
    round(sum(quantity * price)::numeric, 2) AS revenue
FROM sales_pg
WHERE sale_date >= (SELECT max(sale_date) FROM sales_pg) - interval '1 month'
GROUP BY category
ORDER BY category;
```

Результат:

```text
category       sales_count    revenue
Books          11160          3068240.63
Clothing       11160          3049150.68
Electronics    11161          3067941.80
Food           11160          3050079.03
```

## 8. Размер данных

ClickHouse:

```sql
SELECT
    table,
    formatReadableSize(sum(data_compressed_bytes)) AS compressed,
    formatReadableSize(sum(data_uncompressed_bytes)) AS uncompressed,
    round(sum(data_uncompressed_bytes) / sum(data_compressed_bytes), 2) AS compression_ratio
FROM system.parts
WHERE active
  AND database = 'default'
  AND table IN ('sales_ch', 'web_logs')
GROUP BY table
ORDER BY table;
```

Результат:

```text
table       compressed    uncompressed    compression_ratio
sales_ch    14.87 MiB     44.82 MiB       3.01
web_logs    4.34 MiB      23.84 MiB       5.49
```

PostgreSQL:

```sql
SELECT
    pg_size_pretty(pg_relation_size('sales_pg')) AS table_size,
    pg_size_pretty(pg_indexes_size('sales_pg')) AS indexes_size,
    pg_size_pretty(pg_total_relation_size('sales_pg')) AS total_size;
```

Результат:

```text
table_size    indexes_size    total_size
73 MB         29 MB           102 MB
```

Если сравнить sales_pg в PostgreSQL с sales_ch в ClickHouse, ClickHouse занимает в 6.88 раза меньше места:

```text
102 MB / 14.87 MiB ~= 6.88
```

## 9. Выводы

1. Быстрее вставил 1 млн строк ClickHouse: 0.084 s против 2.014 s у PostgreSQL.
2. ClickHouse сжал данные эффективнее: sales_ch занимает 14.87 MiB, а PostgreSQL вместе с индексами занимает 102 MB.
3. Для аналитики ClickHouse обычно лучше подходит, потому что это колоночная СУБД: она быстро читает нужные колонки, хорошо сжимает данные и эффективно выполняет агрегаты.
4. PostgreSQL - строковая транзакционная СУБД общего назначения. Она удобна для OLTP-задач: транзакций, частых обновлений, связей, ограничений и точечных запросов.
5. ClickHouse лучше использовать для логов, событий, метрик и отчетов. PostgreSQL лучше использовать как основную базу приложения.

## 10. Web UI

HTTP-интерфейс ClickHouse проверен:

```bash
curl 'http://localhost:8123/?user=default&password=password' \
  --data-binary 'SELECT version(), currentDatabase() FORMAT PrettyCompact'
```

Результат:

```text
version     currentDatabase()
26.3.9.8    default
```

Также открыт web UI:

```text
http://localhost:8123/play
```