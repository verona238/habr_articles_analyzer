from collections import Counter

import pandas as pd

from models import MONTHS_RU, WEEKDAYS_RU

# по этим показателям строю топы
METRICS = {"views": "Просмотры", "comments": "Комментарии"}


class Analyzer: # класс, который считает статистику по коллекции статей
    def __init__(self, collection): # конструктор
        self.collection = collection
        self.df = collection.to_dataframe() # коллекция переводится в датафрейм

    def summary(self): # метод возвращает словарь с общей статистикой по коллекции
        df = self.df
        return {
            "count": len(df),
            "first": df["published"].min(),
            "last": df["published"].max(),
            "views": int(df["views"].sum()),
            "avg_length": int(df["length"].mean()),
            "avg_read": round(df["read_time_min"].mean(), 1),
        }

    def top_by(self, metric, n=5): # метод по выбранной метрике выводит топ статей
        # например, по просмотрам top_by("views"), по умолчанию выведет 5 статей
        return self.df.nlargest(n, metric)

    def top_overall(self, n=5):
        # в скольких топах засветилась статья
        hits = Counter()
        for metric in METRICS:
            hits.update(self.top_by(metric, n)["link"]) # для каждой метрики берутся топ n статей, и их ссылки складываются в общий счетчик
        df = self.df.copy()
        df["total_hits"] = df["link"].map(hits).fillna(0).astype(int) # для хитов добавляется
        # ссылка, кто не попал в топ - 0
        df = df[df["total_hits"] > 0]
        # при равенстве хитов выше ставим ту, у которой больше просмотров
        return df.sort_values(["total_hits", "views"], ascending=False).head(n)

    def by_month(self):
        """Число статей по годам и месяцам"""
        years = range(self.df["year"].min(), self.df["year"].max() + 1)
        # матрица
        full = pd.MultiIndex.from_product([years, range(1, 13)], names=["year", "month"])
        counts = (self.df.groupby(["year", "month"]).size()
                  .reindex(full, fill_value=0).reset_index(name="count"))
        counts["month_name"] = counts["month"].map(lambda m: MONTHS_RU[m - 1])
        return counts

    def by_weekday(self):
        # сколько статей вышло на днях недели
        years = range(self.df["year"].min(), self.df["year"].max() + 1)
        full = pd.MultiIndex.from_product([years, range(7)], names=["year", "weekday"])
        # получается series
        counts = (self.df.groupby(["year", "weekday"]).size()
                  .reindex(full, fill_value=0).reset_index(name="count")) # в нормальный вид
        counts["weekday_name"] = counts["weekday"].map(lambda d: WEEKDAYS_RU[d])
        return counts
