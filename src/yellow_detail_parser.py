import re

DAYS = {
    "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
    "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday",
    "sunday": "Sunday",
}
HOURS_RE = re.compile(
    r"(?:\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}|closed|open 24 hours)", re.I
)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
SOCIAL_SITES = ("facebook.", "instagram.", "linkedin.", "twitter.", "youtube.")


def contacts(soup, data: dict) -> dict:
    found = {"phone": [], "email": [], "social": []}
    add(found["phone"], data.get("telephone"))
    add(found["email"], data.get("email"))
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        lower = href.lower()
        if lower.startswith("tel:"):
            add(found["phone"], href[4:])
        elif lower.startswith("mailto:"):
            add(found["email"], href[7:].split("?")[0])
        elif any(site in lower for site in SOCIAL_SITES):
            add(found["social"], href)
    for email in EMAIL_RE.findall(soup.get_text(" ", strip=True)):
        add(found["email"], email)
    return {kind: values for kind, values in found.items() if values}


def opening_hours(soup, data: dict) -> dict[str, str]:
    output = jsonld_hours(data)
    strings = [re.sub(r"\s+", " ", value).strip()
               for value in soup.stripped_strings]
    for index, value in enumerate(strings):
        day = DAYS.get(value.lower())
        if not day or day in output:
            continue
        for candidate in strings[index + 1:index + 5]:
            if match := HOURS_RE.search(candidate):
                output[day] = normalize_hours(match.group(0))
                break
    return output


def jsonld_hours(data: dict) -> dict[str, str]:
    output = {}
    specs = data.get("openingHoursSpecification", []) or []
    specs = [specs] if isinstance(specs, dict) else specs
    for item in specs:
        days = item.get("dayOfWeek", [])
        days = days if isinstance(days, list) else [days]
        value = f"{item.get('opens', '')} - {item.get('closes', '')}".strip(" -")
        for day in days:
            output[str(day).split("/")[-1]] = value
    return output


def normalize_hours(value: str) -> str:
    return re.sub(r"\s*[-–]\s*", " - ", value).title()


def add(target: list[str], value) -> None:
    values = value if isinstance(value, list) else [value]
    for item in values:
        item = str(item).strip() if item else ""
        if item and item not in target:
            target.append(item)
