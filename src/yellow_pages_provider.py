import hashlib
import json
import re
import time
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.yellow_detail_parser import contacts, opening_hours
class YellowPagesProvider:
    def __init__(self, settings):
        self.base = settings.yellow_url
        self.timeout = settings.http_timeout
        self.delay = settings.request_delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "malta-business-directory/1.0"})
    def get(self, url, params=None):
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        time.sleep(self.delay)
        body = response.text.lower()
        verification = ("performing security verification",
                        "verify you are human", "verifies you are not a bot",
                        "cf-chl-")
        if any(marker in body for marker in verification):
            raise RuntimeError(f"Yellow security verification encountered: {url}")
        return BeautifulSoup(response.text, "html.parser")
    def discover_categories(self) -> list[tuple[str, str]]:
        soup = self.get(f"{self.base}/all-categories/")
        found = {}
        for link in soup.select("a[href]"):
            url = urljoin(self.base, link["href"])
            path = urlparse(url).path.strip("/")
            if path and path.count("/") == 1 and url.startswith(self.base):
                name = link.get_text(" ", strip=True)
                if name and len(name) < 120:
                    found[path] = name
        return [(name, slug) for slug, name in sorted(found.items())]
    def page_links(self, query: str, page: int) -> list[str]:
        slug = slugify(query)
        category_url = f"{self.base}/{slug}/malta/"
        page_url = category_url if page == 1 else f"{category_url}pageno={page}"
        return self.listing_links(self.get(page_url), slug)

    def source_id(self, url: str) -> str:
        path = unquote(urlparse(url).path).strip("/")
        first_segment = path.split("/")[0] if path else url
        business_slug = first_segment.split("_", 1)[0].lower()
        return hashlib.sha256(f"yellow:{business_slug}".encode()).hexdigest()[:40]
    def listing_links(self, soup, category_slug: str) -> list[str]:
        links = []
        for anchor in soup.select("a[href]"):
            url = urljoin(self.base, anchor["href"]).split("?")[0]
            path = urlparse(url).path.strip("/")
            parts = path.split("/") if path else []
            same_host = urlparse(url).netloc == urlparse(self.base).netloc
            decoded = unquote(path).lower()
            modern = len(parts) == 2 and parts[1].lower() == category_slug
            legacy = (len(parts) == 1
                      and f"_{category_slug}+" in decoded)
            if same_host and (modern or legacy):
                links.append(url)
        unique = {}
        for url in links:
            unique.setdefault(self.source_id(url), url)
        return list(unique.values())
    def detail(self, url: str) -> dict:
        soup = self.get(url)
        data = jsonld_business(soup) or {}
        name = data.get("name") or text(soup, ["h1", "title"]) or "Unnamed business"
        aggregate = data.get("aggregateRating") or {}
        address = data.get("address") or {}
        return {
            "source_id": self.source_id(url),
            "name": name,
            "description": data.get("description") or meta(soup, "description"),
            "rating": number(aggregate.get("ratingValue")),
            "site": external_site(data.get("url"), data.get("sameAs"), self.base),
            "full_address": address_text(address),
            "latitude": number((data.get("geo") or {}).get("latitude")),
            "longitude": number((data.get("geo") or {}).get("longitude")),
            "contacts": contacts(soup, data),
            "working_hours": opening_hours(soup, data),
            "is_head_office": False,
            "listing_url": url,
        }
def slugify(value):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")
def jsonld_business(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.string or script.text)
        except (TypeError, json.JSONDecodeError):
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            kind = str(item.get("@type", "")) if isinstance(item, dict) else ""
            if "Business" in kind or "Organization" in kind:
                return item
    return {}
def text(soup, selectors):
    for selector in selectors:
        if node := soup.select_one(selector):
            return node.get_text(" ", strip=True)
    return None
def meta(soup, name):
    node = soup.select_one(f'meta[name="{name}"]')
    return node.get("content") if node else None
def number(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
def address_text(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    parts = [value.get(key) for key in
             ("streetAddress", "addressLocality", "postalCode", "addressCountry")]
    return ", ".join(str(part) for part in parts if part)
def external_site(url, same_as, base):
    values = [url] if isinstance(url, str) else []
    values += same_as if isinstance(same_as, list) else ([same_as] if same_as else [])
    for value in values:
        if isinstance(value, str) and not value.startswith(base):
            return value
    return None
