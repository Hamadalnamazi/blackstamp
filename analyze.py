#!/usr/bin/env python3
"""Step 2: clean the shop list, group branches into brands and rank shops, brands and neighbourhoods.

  python3 analyze.py

Reads the latest full run, plus shops added later with `tracker.py find`, and writes to exports/:
  shops_ranked.csv     every shop with its type, brand, specialty mark and neighbourhood, busiest first
  brands.csv           one row per brand with two or more branches
  neighbourhoods.csv   one row per neighbourhood (coffee shops only)

Brand grouping is a best guess from shop names and websites, so check a brand before relying on it.
"""
from __future__ import annotations

import collections
import re
from urllib.parse import urlparse

import tracker

# Main Google category decides the type. Shops in the other two groups were found only
# because "cafe" or "coffee" is one of their secondary categories.
COFFEE = {"كافيه", "مقهى", "متجر القهوة", "مقهى إسبرسو", "محمصة قهوة", "كشك لبيع القهوة", "مقهى فني",
          "Cafe", "Coffee shop", "Coffee store", "Espresso bar", "Coffee roasters", "Coffee stand", "Art cafe"}
BAKERY_DESSERT_TEA = {"مقهى لشرب الشاي", "متجر حلويات", "مطعم مخبوزات محلاة", "مخبز", "مخزن الشاي",
                      "مقهى مشروبات الشيكولاتة", "متجر شيكولاتة", "متجر الكعك", "شاي الحليب اللؤلؤي", "بوظة",
                      "مطعم حلويات", "محل الفطائر", "متجر عصائر", "الحلويات", "محل كعك", "محل فطائر",
                      "بوفيه الحلويات وأطباق الحلو"}

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

# A shop counts as specialty when Google lists it as a roastery or its name says so. Specialty shops
# that do not say it in their name (Camel Step, for example) are missed.
ROASTERY = {"محمصة قهوة", "Coffee roasters"}
SPECIALTY_NAME = re.compile(r"مختص|محمص|specialty|speciality|roast", re.IGNORECASE)

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


def shop_type(category: str | None) -> str:
    if category in COFFEE:
        return "coffee"
    return "bakery, dessert or tea" if category in BAKERY_DESSERT_TEA else "other"


def group_brands(shops: list) -> None:
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
        # The whole brand is specialty when at least half of its branches look specialty.
        looks_specialty = sum(m["category"] in ROASTERY or bool(SPECIALTY_NAME.search(m["name"])) for m in members)
        specialty = "yes" if looks_specialty * 2 >= len(members) else ""
        for m in members:
            m["brand"], m["brand_branches"], m["specialty"] = brand, len(members), specialty


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
    shops = []
    # The latest snapshot of every shop seen in that run or later; later runs add shops found by name.
    for row in db.execute("SELECT p.*, s.rating, s.reviews_count, s.temporarily_closed, s.additional_info "
                          "FROM places p JOIN snapshots s USING (place_id) JOIN runs r USING (run_id) "
                          "WHERE r.started_at >= ? AND r.started_at = (SELECT MAX(r2.started_at) FROM snapshots s2 "
                          "JOIN runs r2 USING (run_id) WHERE s2.place_id = p.place_id)", since):
        shops.append({
            "place_id": row["place_id"], "name": (row["title"] or "").strip(), "category": row["category"],
            "type": shop_type(row["category"]), "neighbourhood": neighbourhood_name(row["neighborhood"]),
            "rating": row["rating"], "reviews_count": row["reviews_count"] or 0,
            "temporarily_closed": "yes" if row["temporarily_closed"] else "",
            "popular_times": "yes" if row["place_id"] in with_times else "",
            "drive_through": tracker.service_flags(row["additional_info"])["Drive-through"],
            "lat": row["lat"], "lng": row["lng"], "website": row["website"], "url": row["url"],
        })
    neighbourhoods = {simplify(s["neighbourhood"]).strip() for s in shops if s["neighbourhood"]}
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
    group_brands(shops)
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
        "rating": weighted_rating(members), "neighbourhoods": len({m["neighbourhood"] for m in members}),
        "drive_through_branches": sum(m["drive_through"] == "yes" for m in members),
        "type": collections.Counter(m["type"] for m in members).most_common(1)[0][0],
    } for brand, members in by_brand.items()]
    areas = [{
        "neighbourhood": area, "coffee_shops": len(members),
        "total_reviews": sum(m["reviews_count"] for m in members), "rating": weighted_rating(members),
        "chain_branches": sum(m["brand_branches"] > 1 for m in members),
        "independent_shops": sum(m["brand_branches"] == 1 for m in members),
        "busiest_shop": max(members, key=lambda m: m["reviews_count"])["name"],
    } for area, members in by_area.items()]
    brands.sort(key=lambda b: b["branches"], reverse=True)
    areas.sort(key=lambda a: a["coffee_shops"], reverse=True)
    return brands, areas


def main() -> None:
    shops = load_shops(tracker.open_db())
    shops.sort(key=lambda s: s["reviews_count"], reverse=True)
    brands, areas = summarise(shops)
    out = tracker.ROOT / "exports"
    out.mkdir(exist_ok=True)
    shop_columns = ["place_id", "name", "brand", "brand_branches", "type", "specialty", "category", "neighbourhood",
                    "rating", "reviews_count", "temporarily_closed", "popular_times", "drive_through", "lat", "lng", "url"]
    tracker.write_csv(out / "shops_ranked.csv", shop_columns, ([s[c] for c in shop_columns] for s in shops))
    tracker.write_csv(out / "brands.csv", list(brands[0]), (list(b.values()) for b in brands))
    tracker.write_csv(out / "neighbourhoods.csv", list(areas[0]), (list(a.values()) for a in areas))

    types = collections.Counter(s["type"] for s in shops)
    coffee = [s for s in shops if s["type"] == "coffee"]
    print(f"{len(shops)} shops: {types['coffee']} coffee, {types['bakery, dessert or tea']} bakery/dessert/tea, "
          f"{types['other']} other.")
    print(f"Coffee shops: {sum(s['brand_branches'] > 1 for s in coffee)} are branches of a brand, "
          f"{sum(s['brand_branches'] == 1 for s in coffee)} are single shops.")
    print(f"{len(brands)} brands with two or more branches, {len(areas)} neighbourhoods.")
    print(f"Written to {out}: shops_ranked.csv, brands.csv, neighbourhoods.csv")


if __name__ == "__main__":
    main()
