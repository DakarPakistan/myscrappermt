import hashlib
import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
class YellowPagesProvider:
    def __init__(self, settings):
        self.base = settings.yellow_url
        self.timeout = settings.http_timeout
        self.delay = settings.request_delay
        self.max_pages = settings.max_pages
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "malta-business-directory/1.0"})
    def get(self, url, params=None):
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        time.sleep(self.delay)
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
    def fetch(self, query: str) -> list[dict]:
        slug = slugify(query)
        records, seen = [], set()
        category_url = f"{self.base}/{slug}/malta/"
        for page in range(1, self.max_pages + 1):
            soup = self.get(category_url, {"page": page} if page > 1 else None)
            links = self.listing_links(soup)
            fresh = [link for link in links if link not in seen]
            if not fresh:
                break
            for link in fresh:
                seen.add(link)
                records.append(self.detail(link))
            if len(fresh) < 20:
                break
        return records
    def listing_links(self, soup) -> list[str]:
        links = []
        for anchor in soup.select("a[href]"):
            url = urljoin(self.base, anchor["href"]).split("?")[0]
            path = urlparse(url).path.strip("/")
            if (url.startswith(self.base) and path and path.count("/") == 1
                    and path not in {"all-categories", "popular-categories"}):
                links.append(url)
        return list(dict.fromkeys(links))
    def detail(self, url: str) -> dict:
        soup = self.get(url)
        data = jsonld_business(soup) or {}
        name = data.get("name") or text(soup, ["h1", "title"]) or "Unnamed business"
        aggregate = data.get("aggregateRating") or {}
        address = data.get("address") or {}
        return {
            "source_id": hashlib.sha256(url.encode()).hexdigest()[:40],
            "name": name,
            "description": data.get("description") or meta(soup, "description"),
            "rating": number(aggregate.get("ratingValue")),
            "site": external_site(data.get("url"), data.get("sameAs"), self.base),
            "full_address": address_text(address),
            "latitude": number((data.get("geo") or {}).get("latitude")),
            "longitude": number((data.get("geo") or {}).get("longitude")),
            "contacts": contact_links(soup, data),
            "working_hours": hours(data),
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
def contact_links(soup, data):
    values = {"phone": data.get("telephone"), "email": data.get("email")}
    for anchor in soup.select("a[href]"):
        href = anchor["href"]
        if href.startswith("tel:"):
            values.setdefault("phone", href[4:])
        elif href.startswith("mailto:"):
            values.setdefault("email", href[7:].split("?")[0])
        elif any(site in href.lower() for site in ("facebook.", "instagram.", "linkedin.", "twitter.")):
            values.setdefault("social", []).append(href)
    return values


def hours(data):
    output = {}
    for item in data.get("openingHoursSpecification", []) or []:
        days = item.get("dayOfWeek", [])
        days = days if isinstance(days, list) else [days]
        value = f"{item.get('opens', '')}-{item.get('closes', '')}".strip("-")
        for day in days:
            output[str(day).split("/")[-1]] = value
    return output
