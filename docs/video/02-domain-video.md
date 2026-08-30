# 02 — دامنه ویدئو

```python
class Movie(Base):
    id, title, description, genre, year, file_id FK->files.id, thumbnail, duration, featured bool

class Series(Base):
    id, title, description, genre, year

class Episode(Base):
    id, series_id FK, season, episode, title, file_id FK, duration

class Genre(Base): id, name unique
```

- Seed از `File.file_type=video` با backfill script.
- Index: genre, featured, year.
