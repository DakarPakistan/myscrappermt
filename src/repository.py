import json

CONTACT_FIELDS = {
    "phone": "phone", "phones": "phone", "whatsapp": "whatsapp",
    "email": "email", "emails": "email", "facebook": "facebook",
    "instagram": "instagram", "linkedin": "linkedin", "twitter": "twitter",
    "youtube": "youtube", "social": "social", "social_links": "social",
}


def save_business(connection, category_id: int, element: dict) -> int:
    source_id = (element.get("source_id") or element.get("place_id")
                 or element.get("google_id") or element.get("cid"))
    if not source_id:
        raise ValueError("Yellow Pages result has no stable identifier")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO businesses
              (category_id, source, source_id, name, description, ratings, website_url,
               is_detail_completed, raw_data)
            VALUES (%s, 'yellow_malta', %s, %s, %s, %s, %s, TRUE, %s::jsonb)
            ON CONFLICT (source, source_id) DO UPDATE SET
              name = EXCLUDED.name, description = EXCLUDED.description,
              ratings = EXCLUDED.ratings, website_url = EXCLUDED.website_url,
              is_detail_completed = TRUE, raw_data = EXCLUDED.raw_data,
              updated_at = NOW()
            RETURNING id
            """,
            (category_id, source_id, element.get("name", "Unnamed business"),
             element.get("description"), element.get("rating"),
             element.get("site"), json.dumps(element)),
        )
        business_id = cursor.fetchone()["id"]
        cursor.execute(
            """INSERT INTO business_categories (business_id, category_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING""",
            (business_id, category_id),
        )
        save_location(cursor, business_id, element)
        save_contacts(cursor, business_id, element)
        save_timings(cursor, business_id, element)
        return business_id


def attach_category(connection, business_id: int, category_id: int) -> None:
    connection.execute(
        """INSERT INTO business_categories (business_id, category_id)
        VALUES (%s, %s) ON CONFLICT DO NOTHING""",
        (business_id, category_id),
    )


def save_location(cursor, business_id: int, element: dict) -> None:
    cursor.execute(
        """
        INSERT INTO locations
          (business_id, address, latitude, longitude, is_head_office)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (business_id, is_head_office) DO UPDATE SET
          address = EXCLUDED.address, latitude = EXCLUDED.latitude,
          longitude = EXCLUDED.longitude
        """,
        (business_id, element.get("full_address"), element.get("latitude"),
         element.get("longitude"), bool(element.get("is_head_office", False))),
    )


def save_contacts(cursor, business_id: int, element: dict) -> None:
    element = {**element, **(element.get("contacts") or {})}
    for field, contact_type in CONTACT_FIELDS.items():
        for value in values(element.get(field)):
            cursor.execute(
                """INSERT INTO contacts (business_id, contact_type, contact_value)
                VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                (business_id, contact_type, value),
            )


def save_timings(cursor, business_id: int, element: dict) -> None:
    for day, hours in (element.get("working_hours") or {}).items():
        cursor.execute(
            """INSERT INTO business_timings (business_id, day_of_week, hours_text)
            VALUES (%s, %s, %s) ON CONFLICT (business_id, day_of_week)
            DO UPDATE SET hours_text = EXCLUDED.hours_text""",
            (business_id, day, hours),
        )


def values(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for nested in value.values() for item in values(nested)]
    if isinstance(value, list):
        return [item for nested in value for item in values(nested)]
    return [str(value)]
