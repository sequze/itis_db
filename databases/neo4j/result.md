# Neo4j

## 1. Создание структуры

```cypher
CREATE (alex:User {name: "Alex"}),
       (maria:User {name: "Maria"}),
       (john:User {name: "John"});

CREATE (inception:Movie {title: "Inception"}),
       (matrix:Movie {title: "The Matrix"});

MATCH (a:User {name: "Alex"}), (m:User {name: "Maria"})
CREATE (a)-[:FRIENDS]->(m);

MATCH (a:User {name: "Alex"}), (i:Movie {title: "Inception"})
CREATE (a)-[:WATCHED {rating: 5}]->(i);
```

Структура графа:

- Alex, Maria, John - узлы с меткой User.
- Inception, The Matrix - узлы с меткой Movie.
- Alex -> Maria - связь FRIENDS.
- Alex -> Inception - связь WATCHED с рейтингом 5.

## 2. Найти всех друзей Алекса

```cypher
MATCH (:User {name: "Alex"})-[:FRIENDS]->(friend:User)
RETURN friend.name AS friend;
```

Результат:

```text
friend
Maria
```

## 3. Найти фильмы, которые смотрели друзья Алекса, но не смотрел сам Алекс

```cypher
MATCH (:User {name: "Alex"})-[:FRIENDS]->(friend:User)-[:WATCHED]->(movie:Movie)
WHERE NOT EXISTS {
  MATCH (:User {name: "Alex"})-[:WATCHED]->(movie)
}
RETURN DISTINCT movie.title AS movie;
```

Результат:

```text
Пустой результат
```

Причина: по заданной структуре Maria является другом Alex, но у Maria нет связи WATCHED ни с одним фильмом.

## 4. Аналогичные запросы на SQL

Для SQL можно представить данные в виде таблиц:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE movies (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL
);

CREATE TABLE friends (
    user_id INT REFERENCES users(id),
    friend_id INT REFERENCES users(id),
    PRIMARY KEY (user_id, friend_id)
);

CREATE TABLE watched (
    user_id INT REFERENCES users(id),
    movie_id INT REFERENCES movies(id),
    rating INT,
    PRIMARY KEY (user_id, movie_id)
);
```

Найти всех друзей Алекса:

```sql
SELECT f.name AS friend
FROM users u
JOIN friends fr ON fr.user_id = u.id
JOIN users f ON f.id = fr.friend_id
WHERE u.name = 'Alex';
```

Найти фильмы, которые смотрели друзья Алекса, но не смотрел сам Алекс:

```sql
SELECT DISTINCT m.title AS movie
FROM users alex
JOIN friends fr ON fr.user_id = alex.id
JOIN users friend ON friend.id = fr.friend_id
JOIN watched fw ON fw.user_id = friend.id
JOIN movies m ON m.id = fw.movie_id
WHERE alex.name = 'Alex'
  AND NOT EXISTS (
    SELECT 1
    FROM watched aw
    WHERE aw.user_id = alex.id
      AND aw.movie_id = m.id
  );
```

## 5. Сравнение сложности и скорости

- В Neo4j связи между объектами хранятся напрямую. Поэтому запрос идет от Alex к его друзьям, а потом от друзей к фильмам. Для такой задачи это естественный путь по графу.
- В SQL связи обычно хранятся в отдельных таблицах, например friends и watched. Поэтому приходится делать несколько JOIN, чтобы сначала найти друзей, потом их фильмы, а потом проверить, что сам Alex эти фильмы не смотрел.
- На маленьком объеме данных разницы почти не будет: оба варианта выполнятся быстро.
- На большом объеме данных Neo4j обычно лучше подходит для таких задач, потому что он оптимизирован для обхода связей. SQL тоже может работать быстро, если правильно настроены индексы, но запрос получается сложнее и требует больше соединений таблиц.
- Вывод: для графовых задач, где важны связи между пользователями и объектами, лучше подходит Neo4j. Для обычных табличных данных удобнее SQL.
