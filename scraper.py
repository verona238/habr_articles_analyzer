# скрапер Хабра
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from models import Article, ArticleCollection

MSK = timezone(timedelta(hours=3))
HEADERS = {"User-Agent": "Mozilla/5.0 (student project, company articles analysis)"}


def to_int(text, default=0):
    # '+9', '−3', ' 105 ' преобразуется в число
    if not text:
        return default
    text = text.replace("\u2212", "-").replace("\u2013", "-")
    m = re.search(r"-?\d+", text.replace("\xa0", "").replace(" ", ""))
    return int(m.group()) if m else default


def parse_views(text):
    #'7,3K' -> 7300, '23К' -> 23000, '950' -> 950
    if not text:
        return 0
    m = re.match(r"([\d.]+)\s*([KkКк]?)", text.strip().replace(",", ".").replace("\xa0", ""))
    if not m:
        return 0
    try:
        num = float(m.group(1))
    except ValueError:
        return 0
    return int(round(num * 1000)) if m.group(2) else int(num)


def parse_count(text):
    # 'Комментарии 4' -> 4, 'В закладки 1,2K' -> 1200, берется первое число в тексте
    if not text:
        return None
    # K/К считаем тысячей, только если за ней не идёт слово ("4Комментарии")
    m = re.search(r"\d[\d.,]*(?:[KkКк](?![A-Za-zА-Яа-яЁё]))?", text.replace("\xa0", " "))
    return parse_views(m.group()) if m else None


def first_text(soup, selectors):
    # текст первого найденного селектора
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(" ", strip=True)
    return ""


def first_count(soup, selectors):
    # перебираются все элементы по селекторам, берется первый, где есть цифра
    for sel in selectors:
        for el in soup.select(sel):
            value = parse_count(el.get_text(" ", strip=True))
            if value is not None:
                return value
    return 0


class HabrScraper:
    def __init__(self, delay=1.0, timeout=15):
        self.delay = delay # пауза между запросами
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.errors = [] # сюда складываем статьи, которые не удалось разобрать

    def _get(self, url):
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.text

    @staticmethod
    def check_url(url):
        # ограничение только habr.com
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or parsed.hostname != "habr.com":
            raise ValueError("Нужна ссылка на habr.com, например "
                             "https://habr.com/ru/companies/ctsg/articles/")

    @staticmethod
    def parse_links(html, base="https://habr.com"):
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select("a.tm-title__link"):
            href = a.get("href")
            if href:
                links.append(urljoin(base, href))
        return links

    @staticmethod
    def parse_article(html, url):
        soup = BeautifulSoup(html, "html.parser")

        time_tag = soup.select_one("time[datetime]")
        if time_tag is None:
            raise ValueError("не нашли дату публикации")
        dt = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
        published = dt.astimezone(MSK).replace(tzinfo=None)

        body = soup.select_one(".article-body")
        length = len(body.get_text(" ", strip=True).split()) if body else 0

        return Article(
            title=first_text(soup, ["h1.tm-title", "h1"]) or url,
            link=url,
            published=published,
            views=first_count(soup, [".tm-article-presenter__snippet .tm-icon-counter__value",
                                     ".tm-icon-counter__value"]),
            comments=first_count(soup, [
                ".tm-article-sticky-panel__icons .article-comments-counter-link-wrapper",
                ".article-comments-counter-link"]),
            length=length,
            read_time_min=to_int(first_text(soup, [".tm-article-reading-time__label"])),
            tags=[a.get_text(strip=True) for a in soup.select(".tm-tags-list__link")],
            hubs=[a.get_text(strip=True) for a in soup.select(".tm-hubs-list__link")],
            complexity=first_text(soup, [".tm-article-complexity__label"]),
        )

    def collect_links(self, listing_url, max_pages=3):
        links = []
        for page in range(1, max_pages + 1):
            url = listing_url if page == 1 else listing_url.rstrip("/") + f"/page{page}/"
            try:
                found = self.parse_links(self._get(url))
            except requests.HTTPError:
                if page == 1:
                    raise
                break                       # страницы кончились (404)
            new = [l for l in found if l not in links]
            if not new:
                break
            links.extend(new)
            time.sleep(self.delay)
        return links

    def scrape_company(self, listing_url, max_pages=3, max_articles=30):
        self.check_url(listing_url)
        self.errors = []
        collection = ArticleCollection()
        for link in self.collect_links(listing_url, max_pages)[:max_articles]:
            try:
                collection.add(self.parse_article(self._get(link), link))
            except (requests.RequestException, ValueError) as e:
                self.errors.append(f"{link}: {e}")
            time.sleep(self.delay)
        return collection
