"""Классы данных"""
from datetime import datetime

import pandas as pd

MONTHS_RU = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
             "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


class Article: # Одна статья компании на Хабре
    # принимает название ссылку и дату публикации
    def __init__(self, title, link, published, views=0,
                 comments=0, length=0, read_time_min=0, tags=None, hubs=None,
                 complexity=""):
        self.title = title
        self.link = link
        self.published = published
        self.views = views
        self.comments = comments
        self.length = length
        self.read_time_min = read_time_min
        self.tags = tags or []
        self.hubs = hubs or []
        self.complexity = complexity

    # поля считаются из даты, поэтому храним их как свойства
    # декоратор обращается к методу как к атрибуту
    @property
    def year(self):
        return self.published.year

    @property
    def month(self):
        return self.published.month

    @property
    def weekday(self):
        return self.published.weekday()

    @property
    def hour(self):
        return self.published.hour

    # переопределение методов
    def __eq__(self, other):
        # две статьи одинаковые, если у них одна и та же ссылка
        if not isinstance(other, Article):
            return NotImplemented
        return self.link == other.link

    def __hash__(self):
        # раз переопределили __eq__, надо согласовать и hash
        return hash(self.link)

    def __lt__(self, other):
        # сортировка статей по дате
        if not isinstance(other, Article):
            return NotImplemented
        return self.published < other.published

    def __repr__(self):
        # первые символы названия
        return f"Article({self.title[:30]!r}, {self.published:%Y-%m-%d})"

    def to_dict(self):
        # статья в плоский словарь
        return {
            "title": self.title, "link": self.link, "published": self.published,
            "year": self.year, "month": self.month, "weekday": self.weekday,
            "hour": self.hour, "views": self.views, "comments": self.comments,
            "length": self.length, "read_time_min": self.read_time_min,
            "tags": ", ".join(self.tags), "hubs": ", ".join(self.hubs),
            "complexity": self.complexity,
        }


class ArticleCollection:
    # набор статей

    REQUIRED = ["title", "link", "published", "length"]

    def __init__(self, articles=None):
        self._articles = []
        for a in articles or []:
            self.add(a)

    def add(self, article):
        # использует Article.__eq__
        if article not in self._articles:
            self._articles.append(article)

    def __len__(self):
        return len(self._articles)

    def __iter__(self):
        return iter(self._articles)

    def __add__(self, other):
        # collection1 + collection2 = новая коллекция, дубли склеиваются
        if not isinstance(other, ArticleCollection):
            return NotImplemented
        return ArticleCollection(list(self) + list(other))

    def to_dataframe(self):
        df = pd.DataFrame([a.to_dict() for a in sorted(self._articles, reverse=True)])
        return df

    def to_csv_string(self):
        df = self.to_dataframe()
        return df.to_csv(index=False)

    @classmethod
    # метод вызывается у самого класса
    def from_csv(cls, source):
        """source - путь к файлу или файловый объект"""
        df = pd.read_csv(source)
        missing = [c for c in cls.REQUIRED if c not in df.columns]
        if missing:
            raise ValueError("В CSV не хватает колонок: " + ", ".join(missing))

        def split(value):
            # в список
            return [t.strip() for t in str(value).split(",") if t.strip()] \
                if pd.notna(value) else []

        def num(row, col):
            return int(row[col]) if col in df.columns and pd.notna(row[col]) else 0

        articles = []
        for _, row in df.iterrows():
            # преобразования
            published = pd.to_datetime(row["published"]).to_pydatetime()
            articles.append(Article(
                title=str(row["title"]), link=str(row["link"]), published=published,
                views=num(row, "views"), comments=num(row, "comments"),
                length=num(row, "length"), read_time_min=num(row, "read_time_min"),
                tags=split(row.get("tags")), hubs=split(row.get("hubs")),
                complexity=str(row["complexity"]) if pd.notna(row.get("complexity")) else "",
            ))
        return cls(articles)
