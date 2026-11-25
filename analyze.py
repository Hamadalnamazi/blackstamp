#!/usr/bin/env python3
"""Step 2: clean the shop list, group branches into brands and rank shops, brands and neighbourhoods.

  python3 analyze.py

Reads the latest full run, plus shops added later with `tracker.py find`, and writes to exports/:
  shops_ranked.csv     every shop with its type, brand, specialty mark and neighbourhood, busiest first.
                       specialty_sign says why a shop is marked: its name, its Google category, its own
                       description, the words in its reviews, the competitor list, or its brand
  brands.csv           one row per brand with two or more branches
  neighbourhoods.csv   one row per neighbourhood (coffee shops only), with its specialty shops and the
                       room left for more of them: usual_specialty_shops is what the neighbourhood would
                       have at the city's average of specialty shops per coffee review, and
                       room_for_specialty_shops is that minus the specialty shops it has. The columns
                       after busiest_specialty_shop (people, income, rents, land price) are copied from
                       riyadh_neighbourhood_data.csv; PLAN.md says where each one comes from

A shop's neighbourhood is the one whose border contains the shop's map point. The borders are in
riyadh_districts.json (Saudi national address map, via github.com/homaily/Saudi-Arabia-Regions-Cities-and-Districts,
licence GPL-2.0). Google's own neighbourhood labels are kept in the google_neighbourhood column.

Brand grouping is a best guess from shop names and websites, so check a brand before relying on it.
"""
from __future__ import annotations

import collections
import csv
import json
import math
import re
from urllib.parse import urlparse

import tracker

# Main Google category decides the type. Shops in the other two groups were found only
# because "cafe" or "coffee" is one of their secondary categories.
COFFEE = {"كافيه", "مقهى", "متجر القهوة", "مقهى إسبرسو", "محمصة قهوة", "كشك لبيع القهوة", "مقهى فني",
          "Cafe", "Coffee shop", "Coffee store", "Espresso bar", "Coffee roasters", "Coffee stand", "Art cafe"}
TEA = {"مقهى لشرب الشاي", "مخزن الشاي", "شاي الحليب اللؤلؤي"}
BAKERY_DESSERT = {"متجر حلويات", "مطعم مخبوزات محلاة", "مخبز", "مقهى مشروبات الشيكولاتة", "متجر شيكولاتة",
                  "متجر الكعك", "بوظة", "مطعم حلويات", "محل الفطائر", "متجر عصائر", "الحلويات", "محل كعك",
                  "محل فطائر", "بوفيه الحلويات وأطباق الحلو"}
# Google lists many tea shops, shisha lounges and diwaniyas under "cafe". Their name or one of their other
# categories gives them away, and so does shisha among the words Google shows as most used in their reviews.
# A name that also says coffee (or specialty, for lounges) stays a coffee shop.
SHISHA = {"مقهى للشيشة/الأرجيلة", "لاونج بار", "متجر مستلزمات الشيشة", "ملهى ليلي"}
LOUNGE_NAME = re.compile(r"لاونج|lounge|ديواني|شيش|معسل|[اأ]رجيل|نارجيل|shisha|hookah", re.IGNORECASE)
SHISHA_REVIEW_WORDS = re.compile(r"شيش|معسل|ارجيل|shisha|hookah")  # matched after simplify()
TEA_NAME = re.compile(r"\b[وبل]?(ال|لل)?(شاي|شاهي|كرك)\b|\btea\b|\bkarak\b", re.IGNORECASE)
FOOD_NAME = re.compile(r"مطعم|بوفي|restaurant|فطائر|bakery|مخبز|سينابون|cinnabon|حلويات|sweets|كيك|cake|بيتزا|pizza|"
                       r"برجر|برغر|burger|عصير|عصائر|juice|[آا]يس كريم|ice cream|كريب|crepe|وافل|waffle", re.IGNORECASE)
COFFEE_NAME = re.compile(r"قهو|coffee|كوفي|محمص|roast|espresso|[اإ]سبريسو", re.IGNORECASE)
CAFE_NAME = re.compile(COFFEE_NAME.pattern + r"|كافي|cafe|café|مقه[ىي]", re.IGNORECASE)

# Sites where the brand is the first part of the path (instagram.com/brand), not the host name.
SHARED_HOSTS = {"instagram.com", "linktr.ee", "tiktok.com", "snapchat.com", "facebook.com", "twitter.com", "x.com",
                "youtube.com", "sites.google.com", "linkin.bio", "taplink.cc", "beacons.ai", "salla.sa", "zid.store",
                "t.me", "bio.link", "linkbio.co", "msha.ke", "campsite.bio", "lnk.bio", "heylink.me", "linkin1.com"}
SHARED_PATH_WORDS = {"view", "add", "site", "pages", "p"}  # sites.google.com/view/brand, snapchat.com/add/brand
# Links that say nothing about the brand, and company sites shared by several different brands.
IGNORED_HOSTS = {"wa.me", "api.whatsapp.com", "google.com", "g.page", "goo.gl", "maps.app.goo.gl", "bit.ly", "t.co",
                 "apps.apple.com", "play.google.com", "onelink.me", "qrco.de", "hungerstation.com", "jahez.net",
                 "americanarestaurants.com", "archi-fnb.com", "docs.google.com", "drive.google.com", "forms.gle",
                 "maps.google.com", "share.google", "tinyurl.com", "twlm.solutions", "calendar.visitsaudi.com"}

# A shop looks like a roastery when Google lists it as one (in any of its categories) or its name says so,
# and like a specialty shop when its name says specialty. Shops that roast and sell beans, nuts and
# spices the traditional way are not counted, and neither are mass chains that Google also lists as roasteries.
ROASTERY = {"محمصة قهوة", "Coffee roasters"}
ROASTERY_NAME = re.compile(r"محمص|roast", re.IGNORECASE)
SPECIALTY_NAME = re.compile(r"مختص|specialty|speciality", re.IGNORECASE)
TRADITIONAL_NAME = re.compile(r"محامص|مطاحن|مكسرات|عطار|بهارات")
MASS_CHAIN_BRANCHES = 30
# Many specialty shops say neither word in their name. Two weaker signs find them: the shop's own
# description on Google says specialty coffee, or the words Google shows as most used in its reviews
# include the crop, V60, drip coffee or specialty coffee. Shisha among the review words cancels both.
# These patterns are matched against text that went through simplify(), so ة is written ه.
SPECIALTY_DESCRIPTION = re.compile(r"قهوه\s+(ال)?مختصه|special(i)?ty\s+(coffee|cafe)")
SPECIALTY_REVIEW_WORDS = re.compile(r"محصول|محاصيل|\bcrop\b|v\s?60|في\s?60|مختص|special(i)?ty|drip|دريب|مقطر|"
                                    r"pour\s?over|كيمكس|chemex|ايروبرس|aeropress")

ARABIC_MARKS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
ARABIC_LETTERS = str.maketrans("أإآٱىة", "اااايه")
BRANCH_SUFFIX = re.compile(r"\s[-–—]\s|[(،,]|\bفرع\b|\bbranch\b", re.IGNORECASE)


def simplify(text: str) -> str:
    text = ARABIC_MARKS.sub("", text.lower()).translate(ARABIC_LETTERS)
    return re.sub(r"[^\w\s]", " ", re.sub(r"['’`]", "", text))


GENERIC_WORDS = set(simplify(
    "coffee cafe café caffe kaffee specialty speciality roastery roasters roaster roasting house shop the and "
    "كافيه كافية كوفي كوفى كافي كوفيه مقهى ومقهى قهوة القهوة للقهوة مختصة المختصة محمصة ومحمصة شوب"
).split())


def name_keys(title: str, neighbourhood_names: set) -> list:
    """Brand keys taken from a shop name: each part between "|", without branch suffix and generic words.

    The first part is the name itself. Later parts are the name in the other language, but can also be a
    slogan, so the caller only keeps a later part if some shop uses it as its name.
    """
    keys = []
    for part in re.split(r"[|｜/]", title or ""):
        words = [w for w in simplify(BRANCH_SUFFIX.split(part)[0]).split() if w not in GENERIC_WORDS]
        key = " ".join(words)
        if len(key) >= 3 and not key.isdigit() and key not in neighbourhood_names:
            keys.append("name:" + key)
    return keys


def website_key(website: str | None) -> str | None:
    if not website:
        return None
    url = urlparse(website if "//" in website else "//" + website)
    host = (url.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if not host or host in IGNORED_HOSTS:
        return None
    if host in SHARED_HOSTS:
        parts = [p.lower().lstrip("@") for p in url.path.split("/") if p and p.lower() not in SHARED_PATH_WORDS]
        return f"site:{host}/{parts[0]}" if parts else None
    return "site:" + host


def neighbourhood_name(raw: str | None) -> str:
    name = (raw or "").strip()
    return name[3:].strip() if name.startswith("حي ") else name


def load_districts() -> list:
    """Neighbourhood borders, smallest first so that the most exact one wins where two overlap."""
    districts = json.loads((tracker.ROOT / "riyadh_districts.json").read_text(encoding="utf-8"))
    for district in districts:
        points = [point for ring in district["rings"] for point in ring]
        district["box"] = (min(p[0] for p in points), max(p[0] for p in points),
                           min(p[1] for p in points), max(p[1] for p in points))
        district["centre"] = ((district["box"][0] + district["box"][1]) / 2, (district["box"][2] + district["box"][3]) / 2)
    return sorted(districts, key=lambda d: d["area_km2"])


def in_ring(lat: float, lng: float, ring: list) -> bool:
    inside, (lat2, lng2) = False, ring[-1]
    for lat1, lng1 in ring:
        if (lat1 > lat) != (lat2 > lat) and lng < (lng2 - lng1) * (lat - lat1) / (lat2 - lat1) + lng1:
            inside = not inside
        lat2, lng2 = lat1, lng1
    return inside


def district_at(lat: float, lng: float, districts: list) -> dict | None:
    for district in districts:
        south, north, west, east = district["box"]
        # Inside an odd number of rings: a ring inside another ring is a hole.
        if south <= lat <= north and west <= lng <= east and sum(in_ring(lat, lng, r) for r in district["rings"]) % 2:
            return district
    return None


def load_facts() -> tuple[list, dict]:
    """People, income, rents and land price per neighbourhood (step 5): the column names and {neighbourhood: row}."""
    path = tracker.ROOT / "riyadh_neighbourhood_data.csv"
    if not path.exists():
        return [], {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [c for c in rows[0] if c != "neighbourhood"], {row.pop("neighbourhood"): row for row in rows}


def km_between(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return math.hypot((lat1 - lat2) * 110.8, (lng1 - lng2) * 111.32 * math.cos(math.radians(lat1)))


def shop_type(category: str | None, categories: list, name: str, review_words: list) -> str:
    if category in TEA:
        return "tea shop"
    if category in BAKERY_DESSERT:
        return "bakery, dessert or food"
    if category not in COFFEE:
        return "other"
    specialty = ROASTERY_NAME.search(name) or SPECIALTY_NAME.search(name)
    shisha = (LOUNGE_NAME.search(name) or SHISHA & set(categories)
              or SHISHA_REVIEW_WORDS.search(simplify(" | ".join(review_words))))
    if shisha and not specialty:
        return "lounge, diwaniya or shisha"
    if TEA_NAME.search(name) and not COFFEE_NAME.search(name):
        return "tea shop"
    if FOOD_NAME.search(name) and not CAFE_NAME.search(name):
        return "bakery, dessert or food"
    return "coffee"


def looks_specialty(shop: dict) -> tuple[str, str]:
    """What the shop looks like ("roastery", "specialty" or "") and the sign that says so."""
    if ROASTERY_NAME.search(shop["name"]):
        return "roastery", "name"
    if SPECIALTY_NAME.search(shop["name"]):
        return "specialty", "name"
    if TRADITIONAL_NAME.search(shop["name"]):
        return "", ""
    if ROASTERY & set(shop["categories"]):
        return "roastery", "google category"
    review_words = simplify(" | ".join(shop["review_words"]))
    if SHISHA_REVIEW_WORDS.search(review_words):
        return "", ""
    if SPECIALTY_DESCRIPTION.search(simplify(shop["description"])):
        return "specialty", "own description"
    if SPECIALTY_REVIEW_WORDS.search(review_words):
        return "specialty", "review words"
    return "", ""


def load_competitors() -> dict:
    """place_id -> group for the shops in competitors.csv ("my shop" is the owner's own brand)."""
    path = tracker.ROOT / "competitors.csv"
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {row["place_id"]: row["group"] for row in csv.DictReader(f)}


def group_brands(shops: list, competitors: dict) -> None:
    """Give every shop a brand: shops that share a website or a name key are the same brand."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for shop in shops:
        keys = sorted(shop["keys"]) or ["place:" + shop["place_id"]]
        for key in keys[1:]:
            parent[find(key)] = find(keys[0])
        shop["group"] = keys[0]
    groups = collections.defaultdict(list)
    for shop in shops:
        groups[find(shop["group"])].append(shop)
    for members in groups.values():
        # Name the brand after its most common shop name.
        brand = collections.Counter(m["name"] for m in members).most_common(1)[0][0]
        # The whole brand is specialty when at least half of its branches look it, or it is in competitors.csv.
        signs = [looks_specialty(m) for m in members]
        looking = sum(bool(look) for look, _ in signs)
        # Roastery or specialty is decided by the name and Google category alone, the two strong signs.
        looks = collections.Counter(look for look, sign in signs if sign in ("name", "google category"))
        listed = any(m["place_id"] in competitors for m in members)
        specialty = ""
        if listed:
            specialty = "roastery" if looks["roastery"] >= looks["specialty"] else "specialty"
        elif looking * 2 >= len(members) and len(members) <= MASS_CHAIN_BRANCHES:
            specialty = "roastery" if looks["roastery"] and looks["roastery"] * 2 >= sum(looks.values()) else "specialty"
        for m, (_, sign) in zip(members, signs):
            m["brand"], m["brand_branches"], m["specialty"] = brand, len(members), specialty
            # Why the shop is marked: its own sign, or else the competitor list or the brand's other branches.
            m["specialty_sign"] = (sign or ("competitor list" if listed else "brand")) if specialty else ""
            m["mine"] = "yes" if competitors.get(m["place_id"]) == "my shop" else ""


def weighted_rating(shops: list) -> float | str:
    rated = [(s["rating"], s["reviews_count"]) for s in shops if s["rating"] and s["reviews_count"]]
    total = sum(count for _, count in rated)
    return round(sum(rating * count for rating, count in rated) / total, 2) if total else ""


def load_shops(db) -> list:
    run = db.execute("SELECT run_id, started_at FROM runs WHERE imported = 1 AND is_full = 1 AND complete = 1 "
                     "ORDER BY started_at DESC LIMIT 1").fetchone()
    if not run:
        raise SystemExit("No complete full run yet. Run `python3 tracker.py run` first.")
    since = (run["started_at"],)
    with_times = {row[0] for row in db.execute("SELECT DISTINCT t.place_id FROM popular_times t "
                                               "JOIN runs r USING (run_id) WHERE r.started_at >= ?", since)}
    # Shops whose reviews of the last year were collected (the competitor list), and how many they got.
    with_year = {row[0] for row in db.execute("SELECT DISTINCT s.place_id FROM snapshots s JOIN runs r USING (run_id) "
                                              "WHERE r.reviews_since LIKE '%year%'")}
    last_year = dict(db.execute("SELECT place_id, COUNT(*) FROM reviews GROUP BY place_id").fetchall())
    texts = {row["place_id"]: row for row in db.execute("SELECT * FROM place_texts")}
    shops, districts = [], load_districts()
    # The latest snapshot of every shop seen in that run or later; later runs add shops found by name.
    for row in db.execute("SELECT p.*, s.rating, s.reviews_count, s.temporarily_closed, s.additional_info "
                          "FROM places p JOIN snapshots s USING (place_id) JOIN runs r USING (run_id) "
                          "WHERE r.started_at >= ? AND r.started_at = (SELECT MAX(r2.started_at) FROM snapshots s2 "
                          "JOIN runs r2 USING (run_id) WHERE s2.place_id = p.place_id)", since):
        name, categories = (row["title"] or "").strip(), json.loads(row["categories"] or "[]")
        district = district_at(row["lat"], row["lng"], districts) or {}
        text = texts.get(row["place_id"])
        review_words = json.loads(text["review_words"] or "[]") if text else []
        shops.append({
            "place_id": row["place_id"], "name": name, "category": row["category"], "categories": categories,
            "review_words": review_words, "description": (text["owner_description"] or "") if text else "",
            "type": shop_type(row["category"], categories, name, review_words),
            "neighbourhood": district.get("name", ""), "neighbourhood_en": district.get("name_en", ""),
            "google_neighbourhood": neighbourhood_name(row["neighborhood"]),
            "rating": row["rating"], "reviews_count": row["reviews_count"] or 0,
            "reviews_last_year": last_year.get(row["place_id"], 0) if row["place_id"] in with_year else "",
            "temporarily_closed": "yes" if row["temporarily_closed"] else "",
            "popular_times": "yes" if row["place_id"] in with_times else "",
            "drive_through": tracker.service_flags(row["additional_info"])["Drive-through"],
            "lat": row["lat"], "lng": row["lng"], "website": row["website"], "url": row["url"],
        })
    neighbourhoods = {simplify(s[column]).strip() for s in shops
                      for column in ("neighbourhood", "google_neighbourhood") if s[column]}
    for shop in shops:
        shop["name_keys"] = name_keys(shop["name"], neighbourhoods)
    used_as_name = {shop["name_keys"][0] for shop in shops if shop["name_keys"]}
    for shop in shops:
        shop["keys"] = set(shop["name_keys"][:1]) | {key for key in shop["name_keys"][1:] if key in used_as_name}
        if website_key(shop["website"]):
            shop["keys"].add(website_key(shop["website"]))
    # A key that only one shop has cannot link it to anything.
    counts = collections.Counter(key for shop in shops for key in shop["keys"])
    for shop in shops:
        shop["keys"] = {key for key in shop["keys"] if counts[key] > 1}
    group_brands(shops, load_competitors())
    return shops


def summarise(shops: list) -> tuple[list, list]:
    by_brand, by_area = collections.defaultdict(list), collections.defaultdict(list)
    for shop in shops:
        if shop["brand_branches"] > 1:
            by_brand[shop["brand"]].append(shop)
        if shop["type"] == "coffee" and shop["neighbourhood"]:
            by_area[shop["neighbourhood"]].append(shop)
    brands = [{
        "brand": brand, "branches": len(members), "total_reviews": sum(m["reviews_count"] for m in members),
        "rating": weighted_rating(members),
        "neighbourhoods": len({m["neighbourhood"] for m in members if m["neighbourhood"]}),
        "drive_through_branches": sum(m["drive_through"] == "yes" for m in members),
        "type": collections.Counter(m["type"] for m in members).most_common(1)[0][0],
        "specialty": members[0]["specialty"],
    } for brand, members in by_brand.items()]

    districts = {d["name"]: d for d in load_districts()}
    mine = [s for s in shops if s["mine"]]
    # A branch inside a university serves the campus, so a new shop near it does not take its customers.
    street = [s for s in mine if not s["neighbourhood"].startswith(("جامعة", "مطار"))]
    fact_columns, facts = load_facts()
    # Specialty shops the whole city has for each review its coffee shops have. A neighbourhood with the
    # city's usual share would have (its coffee reviews x this rate) specialty shops.
    counted = [s for members in by_area.values() for s in members]
    rate = sum(bool(s["specialty"]) for s in counted) / sum(s["reviews_count"] for s in counted)
    areas = []
    for area, members in by_area.items():
        specialty = [m for m in members if m["specialty"]]
        with_year = [m for m in members if m["reviews_last_year"] != ""]
        reviews = sum(m["reviews_count"] for m in members)
        lat, lng = sum(m["lat"] for m in members) / len(members), sum(m["lng"] for m in members) / len(members)
        areas.append({
            "neighbourhood": area, "neighbourhood_en": districts[area]["name_en"], "city": districts[area]["city"],
            "area_km2": districts[area]["area_km2"], "coffee_shops": len(members), "total_reviews": reviews,
            "rating": weighted_rating(members),
            "chain_branches": sum(m["brand_branches"] > 1 for m in members),
            "independent_shops": sum(m["brand_branches"] == 1 for m in members),
            "specialty_shops": len(specialty),
            "roastery_shops": sum(m["specialty"] == "roastery" for m in specialty),
            "specialty_reviews": sum(m["reviews_count"] for m in specialty),
            "specialty_rating": weighted_rating(specialty),
            "usual_specialty_shops": round(reviews * rate, 1),
            "room_for_specialty_shops": round(reviews * rate - len(specialty), 1),
            "shops_with_a_year_of_reviews": len(with_year),
            "their_reviews_last_year": sum(m["reviews_last_year"] for m in with_year) if with_year else "",
            "my_branches": sum(bool(m["mine"]) for m in members),
            "km_to_my_nearest_branch": round(min(km_between(lat, lng, m["lat"], m["lng"]) for m in mine), 1) if mine else "",
            "km_to_my_nearest_street_branch": round(min(km_between(lat, lng, m["lat"], m["lng"]) for m in street), 1) if street else "",
            "busiest_shop": max(members, key=lambda m: m["reviews_count"])["name"],
            "busiest_specialty_shop": max(specialty, key=lambda m: m["reviews_count"])["name"] if specialty else "",
            **{column: facts.get(area, {}).get(column, "") for column in fact_columns},
        })
    brands.sort(key=lambda b: b["branches"], reverse=True)
    areas.sort(key=lambda a: a["coffee_shops"], reverse=True)
    return brands, areas


def main() -> None:
    shops = load_shops(tracker.open_db())
    shops.sort(key=lambda s: s["reviews_count"], reverse=True)
    brands, areas = summarise(shops)
    out = tracker.ROOT / "exports"
    out.mkdir(exist_ok=True)
    shop_columns = ["place_id", "name", "brand", "brand_branches", "type", "specialty", "specialty_sign", "category",
                    "neighbourhood",
                    "neighbourhood_en", "google_neighbourhood", "rating", "reviews_count", "reviews_last_year",
                    "temporarily_closed",
                    "popular_times", "drive_through", "lat", "lng", "url"]
    tracker.write_csv(out / "shops_ranked.csv", shop_columns, ([s[c] for c in shop_columns] for s in shops))
    tracker.write_csv(out / "brands.csv", list(brands[0]), (list(b.values()) for b in brands))
    tracker.write_csv(out / "neighbourhoods.csv", list(areas[0]), (list(a.values()) for a in areas))

    types = collections.Counter(s["type"] for s in shops)
    coffee = [s for s in shops if s["type"] == "coffee"]
    print(f"{len(shops)} places: {types['coffee']} coffee shops. Not coffee: {types['tea shop']} tea shops, "
          f"{types['lounge, diwaniya or shisha']} lounges, diwaniyas and shisha cafes, "
          f"{types['bakery, dessert or food']} bakery, dessert or food, {types['other']} other.")
    print(f"Coffee shops: {sum(s['brand_branches'] > 1 for s in coffee)} are branches of a brand, "
          f"{sum(s['brand_branches'] == 1 for s in coffee)} are single shops. "
          f"{sum(s['specialty'] == 'roastery' for s in coffee)} are roasteries and "
          f"{sum(s['specialty'] == 'specialty' for s in coffee)} more are specialty shops.")
    signs = collections.Counter(s["specialty_sign"] for s in coffee if s["specialty"])
    print("Why they are marked: " + ", ".join(f"{sign} {count}" for sign, count in signs.most_common()) + ".")
    print(f"{len(brands)} brands with two or more branches, {len(areas)} neighbourhoods with a coffee shop, "
          f"{sum(not s['neighbourhood'] for s in coffee)} coffee shops outside the neighbourhood borders.")
    print(f"Written to {out}: shops_ranked.csv, brands.csv, neighbourhoods.csv")


if __name__ == "__main__":
    main()
