from pathlib import Path

import requests
from flask import Flask, Response, render_template, request

from analysis import METRICS, Analyzer
from charts import ChartBuilder
from models import ArticleCollection
from scraper import HabrScraper

app = Flask(__name__)
DEMO_PATH = Path(__file__).parent / "data" / "demo.csv"

# Последний результат держим в памяти для скачивания CSV и объединения с прошлым
_last = {"collection": None}


def load_collection(form, files):
    # Парсинг статей из выбранного источника
    source = form.get("source", "demo")
    warnings = []
    # смотря что выбрал пользак
    if source == "demo":
        collection = ArticleCollection.from_csv(DEMO_PATH)
    elif source == "csv":
        f = files.get("csv_file")
        if not f or not f.filename:
            raise ValueError("Выберите CSV-файл.")
        collection = ArticleCollection.from_csv(f.stream)
    elif source == "url":
        url = form.get("url", "").strip()
        scraper = HabrScraper(delay=1.0)
        collection = scraper.scrape_company(
            url,
            max_pages=int(form.get("max_pages", 2)),
            max_articles=int(form.get("max_articles", 20)),
        )
        warnings = scraper.errors
    else:
        raise ValueError("Неизвестный источник данных.")

    # галочка объединить, тут работает метод __add__ ArticleCollection
    if form.get("merge") and _last["collection"] is not None:
        collection = _last["collection"] + collection

    if len(collection) == 0:
        raise ValueError("Статьи не найдены. Проверьте ссылку или файл.")
    return collection, warnings


def fmt(df):
    # подготовка таблицы к показу
    rows = df.to_dict("records")
    for r in rows:
        r["date"] = r["published"].strftime("%d.%m.%Y")
    return rows


@app.route("/")
def index():
    return render_template("index.html", result=None, error=None)


@app.route("/analyze", methods=["POST"]) # обработчик аналайзера
def analyze():
    try:
        collection, warnings = load_collection(request.form, request.files)
    except (ValueError, requests.RequestException) as e:
        return render_template("index.html", result=None, error=str(e)), 400

    _last["collection"] = collection
    analyzer = Analyzer(collection)
    result = {
        "summary": analyzer.summary(),
        "top": fmt(analyzer.top_overall()),
        "tops": {title: fmt(analyzer.top_by(key)) for key, title in METRICS.items()},
        "all": fmt(analyzer.df),
        "charts": ChartBuilder(analyzer).all(),
        "warnings": warnings,
    }
    return render_template("index.html", result=result, error=None)


@app.route("/download.csv") # обработчик скачивания
def download():
    if _last["collection"] is None:
        return "Сначала загрузите данные.", 404
    # utf-8-sig, чтобы Excel не ломал кириллицу
    data = _last["collection"].to_csv_string().encode("utf-8-sig")
    return Response(data, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=habr_articles.csv"})


if __name__ == "__main__":
    app.run(debug=True)
