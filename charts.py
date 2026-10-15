import plotly.express as px

from models import MONTHS_RU, WEEKDAYS_RU

# цвета годов для графиков
PALETTE = ["#3A77B9", "#E07B39", "#385E8C", "#7FA8D6", "#B5651D"]


class ChartBuilder:
    def __init__(self, analyzer):
        self.analyzer = analyzer # строит таблицы по аналайзеру

    @staticmethod # метод без self
    def _finish(fig):
        fig.update_layout(font_family="Montserrat, sans-serif", plot_bgcolor="white",
                          margin=dict(l=40, r=20, t=50, b=40), legend_title_text="Год")
        fig.update_xaxes(gridcolor="#e5e9f0")
        fig.update_yaxes(gridcolor="#e5e9f0")
        # plotly.js подтягиваем с CDN, иначе страница весит +3 МБ
        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    def months(self):
        df = self.analyzer.by_month()
        df["year"] = df["year"].astype(str)
        fig = px.bar(df, x="month_name", y="count", color="year",
                     category_orders={"month_name": MONTHS_RU},
                     color_discrete_sequence=PALETTE,
                     labels={"month_name": "", "count": "Статей"},
                     title="Число статей по месяцам")
        return self._finish(fig)

    def weekdays(self):
        df = self.analyzer.by_weekday()
        df["year"] = df["year"].astype(str)
        fig = px.bar(df, y="weekday_name", x="count", color="year", orientation="h",
                     category_orders={"weekday_name": WEEKDAYS_RU[::-1]},
                     color_discrete_sequence=PALETTE,
                     labels={"weekday_name": "", "count": "Статей"},
                     title="Статьи по дням недели")
        return self._finish(fig)

    def length_by_year(self):
        df = self.analyzer.df.copy()
        df["year"] = df["year"].astype(str)
        fig = px.box(df, x="year", y="length", color="year", points="all",
                     hover_name="title", color_discrete_sequence=PALETTE,
                     labels={"year": "", "length": "Слов в статье"},
                     title="Длина статьи по годам")
        fig.update_layout(showlegend=False)
        return self._finish(fig)

    def top_articles(self, n=10):
        df = self.analyzer.top_by("views", n).copy()
        df["year"] = df["year"].astype(str)
        # длинные заголовки режем, иначе они съедают весь график
        df["short"] = df["title"].map(lambda t: t if len(t) <= 40 else t[:40] + "…")
        fig = px.bar(df, y="short", x="views", color="year", orientation="h",
                     hover_name="title", color_discrete_sequence=PALETTE,
                     labels={"short": "", "views": "Просмотры"},
                     title=f"Топ-{n} статей по просмотрам")
        fig.update_yaxes(autorange="reversed")      # самая популярная сверху
        return self._finish(fig)

    def all(self):
        return {"months": self.months(), "weekdays": self.weekdays(),
                "length": self.length_by_year(), "top": self.top_articles()}
