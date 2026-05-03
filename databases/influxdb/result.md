# InfluxDB: промышленные датчики
 
Наполнение данными промышленных датчиков

Данные записаны в формате line protocol:

```text
current,motor_id=M-1001,type=induction,load=high value=145.5
current,motor_id=M-1001,type=induction,load=high value=151.2
current,motor_id=M-1002,type=servo,load=medium value=82.7

pressure,pipe_id=MP-01,section=main,zone=A value=4.2
pressure,pipe_id=MP-01,section=main,zone=A value=4.8
pressure,pipe_id=MP-02,section=backup,zone=B value=2.9

vibration,machine_id=CN-01,axis=X,zone=A value=0.37
vibration,machine_id=CN-01,axis=Y,zone=A value=0.52

temperature,sensor_id=T-77,area=workshop,zone=C value=71.4
temperature,sensor_id=T-78,area=compressor,zone=B value=88.9
```

Команда записи:

```bash
docker exec influxdb influx write \
  --bucket mybucket \
  --org myorg \
  --token my-token-123 \
  'current,motor_id=M-1001,type=induction,load=high value=145.5'
```

## Базовые запросы

### Просмотреть все данные за последние 30 минут

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._field == "value")
```

Результат: найдено 10 записей.

### Посмотреть измерения только 1 датчика

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "current" and r.motor_id == "M-1001")
```

Результат:

```text
M-1001: 145.5, 151.2
```

### Максимальное значение на 1 датчике

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "current" and r.motor_id == "M-1001")
  |> max()
```

Результат:

```text
151.2
```

### Среднее значение на датчике

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "pressure" and r.pipe_id == "MP-01")
  |> mean()
```

Результат:

```text
4.5
```

### Аналитический запрос 1: ток выше 100 А

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "current" and r._value > 100.0)
```

Результат:

```text
M-1001: 145.5, 151.2
```

### Аналитический запрос 2: давление выше 4.5 bar

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "pressure" and r._value > 4.5)
```

Результат:

```text
MP-01: 4.8
```

### Аналитический запрос 3: температура выше 80 градусов

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "temperature" and r._value > 80.0)
```

Результат:

```text
T-78: 88.9
```

### Запрос на агрегацию данных

Среднее значение по каждому типу измерения:

```flux
from(bucket: "mybucket")
  |> range(start: -30m)
  |> filter(fn: (r) => r._field == "value")
  |> group(columns: ["_measurement"])
  |> mean()
```

Результат:

```text
current: 126.47
pressure: 3.97
temperature: 80.15
vibration: 0.445
```

## 5. Дашборд с графиками

Создан дашборд:

```text
Industrial Sensors Dashboard
```

В дашборд добавлены 2 графика:

- Motor current - график потребляемого тока электродвигателей.
- Pipeline pressure - график давления в трубопроводах.

Результат:

```text
Industrial Sensors Dashboard, Num Cells: 2
```
