# MongoDB

## 1. Создание коллекций и наполнение данными

Использована база данных:

```js
const dbx = db.getSiblingDB("music_hw");
```

Созданы 3 коллекции:

- users
- albums
- tracks

Связи через ObjectId:

- albums.artistId ссылается на users._id
- tracks.albumId ссылается на albums._id
- tracks.artistId ссылается на users._id

В документах есть вложенные JSON-объекты и массивы:

- subscription: { plan, months }
- roles: [...]
- tags: [...]
- stats: { likes, plays }
- features: [...]
- meta: { explicit, bpm }

Количество документов:

```text
users: 3
albums: 3
tracks: 4
```

Пример вставки пользователей:

```js
const users = dbx.users.insertMany([
  {
    username: "timur",
    email: "timur@example.com",
    country: "Russia",
    subscription: { plan: "free", months: 3 },
    roles: ["listener"],
  },
  {
    username: "amir",
    email: "amir@example.com",
    country: "Russia",
    subscription: { plan: "premium", months: 12 },
    roles: ["artist", "listener"],
  },
  {
    username: "sofia",
    email: "sofia@example.com",
    country: "Georgia",
    subscription: { plan: "free", months: 1 },
    roles: ["listener"],
  },
]);
```

Пример вставки альбомов со ссылкой на пользователя:

```js
const timurId = users.insertedIds[0];
const amirId = users.insertedIds[1];

const albums = dbx.albums.insertMany([
  {
    title: "Night Signals",
    artistId: amirId,
    year: 2024,
    tags: ["rap", "electronic"],
    stats: { likes: 120, plays: 5200 },
  },
  {
    title: "Study Beats",
    artistId: timurId,
    year: 2023,
    tags: ["lo-fi", "instrumental"],
    stats: { likes: 45, plays: 1400 },
  },
]);
```

Пример вставки треков со ссылками на альбом и автора:

```js
dbx.tracks.insertMany([
  {
    title: "Hello Bandits",
    durationMs: 180000,
    albumId: albums.insertedIds[0],
    artistId: amirId,
    genre: "Hip-Hop",
    features: ["bass", "synth"],
    meta: { explicit: false, bpm: 92 },
    createdAt: new Date("2024-03-01T10:00:00Z"),
  },
]);
```

## 2. Find-запрос 1

Найти пользователей из России:

```js
dbx.users.find({ country: "Russia" });
```

Результат:

```text
[
  {
    _id: ObjectId('69f767e0b97fae70133d88b3'),
    username: 'timur',
    email: 'timur@example.com',
    country: 'Russia',
    subscription: { plan: 'free', months: 3 },
    roles: [ 'listener' ]
  },
  {
    _id: ObjectId('69f767e0b97fae70133d88b4'),
    username: 'amir',
    email: 'amir@example.com',
    country: 'Russia',
    subscription: { plan: 'premium', months: 12 },
    roles: [ 'artist', 'listener' ]
  }
]
```

## 3. Find-запрос 2 с projection

Найти Hip-Hop треки и вывести только название, жанр и длительность:

```js
dbx.tracks.find(
  { genre: "Hip-Hop" },
  { _id: 0, title: 1, genre: 1, durationMs: 1 },
);
```

Результат:

```text
[
  {
    title: 'Hello Bandits',
    durationMs: 180000,
    genre: 'Hip-Hop'
  },
  {
    title: 'Midnight Query',
    durationMs: 210000,
    genre: 'Hip-Hop'
  }
]
```

## 4. Update-запрос 1

Обновить подписку пользователя timur и добавить ему роль artist:

```js
dbx.users.updateOne(
  { username: "timur" },
  {
    $set: { "subscription.plan": "premium", "subscription.months": 6 },
    $addToSet: { roles: "artist" },
  },
);
```

Результат:

```text
{
  acknowledged: true,
  insertedId: null,
  matchedCount: 1,
  modifiedCount: 1,
  upsertedCount: 0
}
```

Проверка:

```js
dbx.users.find(
  { username: "timur" },
  { _id: 0, username: 1, subscription: 1, roles: 1 },
);
```

Результат:

```text
[
  {
    username: 'timur',
    subscription: { plan: 'premium', months: 6 },
    roles: [ 'listener', 'artist' ]
  }
]
```

## 5. Update-запрос 2

Обновить все треки жанра Hip-Hop: поменять жанр на Rap и записать дату обновления.

```js
dbx.tracks.updateMany(
  { genre: "Hip-Hop" },
  { $set: { genre: "Rap" }, $currentDate: { updatedAt: true } },
);
```

Результат:

```text
{
  acknowledged: true,
  insertedId: null,
  matchedCount: 2,
  modifiedCount: 2,
  upsertedCount: 0
}
```

Проверка:

```js
dbx.tracks.find(
  { genre: "Rap" },
  { _id: 0, title: 1, genre: 1, updatedAt: 1 },
);
```

Результат:

```text
[
  {
    title: 'Hello Bandits',
    genre: 'Rap',
    updatedAt: ISODate('2026-05-03T15:21:16.348Z')
  },
  {
    title: 'Midnight Query',
    genre: 'Rap',
    updatedAt: ISODate('2026-05-03T15:21:16.348Z')
  }
]
```

## 6. Aggregate-запрос

Посчитать по каждому альбому количество треков, суммарную длительность и средний BPM.
Для связи tracks.albumId -> albums._id используется $lookup.

```js
dbx.tracks.aggregate([
  {
    $lookup: {
      from: "albums",
      localField: "albumId",
      foreignField: "_id",
      as: "album",
    },
  },
  { $unwind: "$album" },
  {
    $group: {
      _id: "$album.title",
      trackCount: { $sum: 1 },
      totalDurationMs: { $sum: "$durationMs" },
      avgBpm: { $avg: "$meta.bpm" },
    },
  },
  { $sort: { totalDurationMs: -1 } },
]);
```

Результат:

```text
[
  {
    _id: 'Night Signals',
    trackCount: 2,
    totalDurationMs: 390000,
    avgBpm: 95
  },
  {
    _id: 'Study Beats',
    trackCount: 1,
    totalDurationMs: 240000,
    avgBpm: 76
  },
  {
    _id: 'City Echo',
    trackCount: 1,
    totalDurationMs: 160000,
    avgBpm: 124
  }
]
```


- MongoDB поднята в Docker Compose.
- Созданы 3 коллекции: users, albums, tracks.
- Коллекции связаны через ObjectId.
- В документах используются вложенные объекты и массивы.
- Написаны 2 find запроса, один из них с projection.
- Написаны 2 update запроса.
- Написан aggregate запрос с $lookup, $group и $sort.
