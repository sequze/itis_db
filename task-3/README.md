# Дз 3

## GIN индексы

### 1 запрос

```sql
SELECT c.id, c.user_id, c.track_id, c.content
FROM comment c
WHERE to_tsvector('russian', coalesce(c.content, ''))
      @@ websearch_to_tsquery('russian', 'сильный вокал и бас');
```

Без индекса: cost 31884, Parallel Seq Scan
![1_1.png](screenshots/1_1.png)

Добавляем GIN: cost 2811 (Bitmap)

```sql
CREATE INDEX IF NOT EXISTS idx_comment_content_fts_gin
    ON comment USING GIN (to_tsvector('english', coalesce(content, '')));
```
![1_2.png](screenshots/1_2.png)

С Gist: 2842

### 2 запрос

```sql
SELECT u.id, u.username, u.email
FROM "user" u
WHERE u.username ILIKE '%amir%';
```

Без индекса: cost 6363 (Parallel Seq Scan)

![1_3.png](screenshots/2_1.png)

С Gin: 3862 (Bitmap)

![1_4.png](screenshots/2_2.png)

### 3) Поиск по JSONB в профиле пользователя (`user_profile.preferences`)

```sql
CREATE INDEX idx_user_profile_preferences_gin
    ON user_profile USING GIN (preferences);
```

```sql
SELECT up.id, up.user_id, up.preferences
FROM user_profile up
WHERE up.preferences @> '{"language":"ru","notifications":true}'::jsonb;
```

Без индекса: cost 11125 (Seq scan)

![1_5.png](screenshots/3_1.png)

С индексом: cost 9119 (Bitmap)

![1_6.png](screenshots/3_2.png)

### 4) Полнотекстовый поиск по био пользователя (`user_profile.bio`)

```sql
CREATE INDEX idx_user_profile_bio_fts_gin
    ON user_profile USING GIN (to_tsvector('english', coalesce(bio, '')));
```

```sql
SELECT up.id, up.user_id, up.bio
FROM user_profile up
WHERE to_tsvector('english', coalesce(up.bio, ''))
      @@ websearch_to_tsquery('english', 'Office College');
```
Без индекса: 36344 (Seq scan)

![4_1.png](screenshots/4_1.png)

С индексом: 46.34 (Bitmap)

![4_2.png](screenshots/4_2.png)

### 5) Полнотекстовый поиск по названию трека (`track.title`)

```sql
CREATE INDEX idx_track_title_fts_gin
    ON track USING GIN (to_tsvector('english', title));
```

```sql
SELECT t.id, t.title
FROM track t
WHERE to_tsvector('english', t.title)
      @@ plainto_tsquery('english', 'Night rain');
```

Без индекса: cost 42231 (Seq scan)
![5_1.png](screenshots/5_1.png)

С индексом: cost 2457 (Bitmap)

![5_2.png](screenshots/5_2.png)



