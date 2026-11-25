#!/usr/bin/env python3
"""Step 6: the busy hours of the owner's branches against the coffee shops and the other places around them.

  python3 analyze_hours.py

Run `python3 analyze.py` first. This reads Google's busy hours (popular times) collected by tracker.py and
exports/shops_ranked.csv, and writes exports/busy_hours.csv: for each branch of the owner that has busy
hours, every day and hour with the branch's own level next to the average of the coffee shops within 2 km,
of the specialty shops among them, and of all competitor branches in the city.

Google shows busy hours as a percentage of each shop's own busiest hour. They say when a shop is busy, not
how many customers it has. To compare shops, each shop's week is turned into shares that add up to 100: a
value of 1.2 means that 1.2% of that shop's week falls in that hour. Every shop counts the same in an average.

Google files the hours after midnight under the day the evening started, and so does this file.

When `python3 tracker.py around LAT LNG` has collected the mosques, schools, companies and malls around a
branch, two more files are written: exports/busy_hours_around.csv (the branch's week next to the average
week of each kind of place within 1.5 km) and exports/places_around.csv (the places themselves).
"""
from __future__ import annotations

import collections
import csv
import math

import tracker

NEARBY_KM = 2.0
AROUND_KM = 1.5  # the distance `tracker.py around` collects by default
# The searches of `tracker.py around` and what they find in practice.
KINDS = {"مسجد": "mosques", "مدرسة": "schools", "شركة": "companies and shops", "مول": "malls and big stores"}
DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
DAY_NAMES = dict(zip(DAYS, ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]))
HOURS = list(range(6, 24)) + list(range(0, 6))  # a day runs from 6 in the morning to the end of the night
WEEKDAYS = DAYS[:5]
# Parts of the week for the summary: name, days, hours.
PARTS = [
    ("Weekdays 6 to 9", WEEKDAYS, range(6, 9)),
    ("Weekdays 9 to 12", WEEKDAYS, range(9, 12)),
    ("Weekdays 12 to 16", WEEKDAYS, range(12, 16)),
    ("Weekdays 16 to 20", WEEKDAYS, range(16, 20)),
    ("Weekdays 20 to midnight", WEEKDAYS, range(20, 24)),
    ("Friday before noon", ["Fr"], range(6, 12)),
    ("Friday from noon", ["Fr"], range(12, 24)),
    ("Saturday before noon", ["Sa"], range(6, 12)),
    ("Saturday from noon", ["Sa"], range(12, 24)),
    ("After midnight, all days", DAYS, range(0, 6)),
]


def load_weeks(db) -> dict:
    """place_id -> {(day, hour): share of the shop's week}, from each shop's latest busy hours."""
    levels = collections.defaultdict(dict)
    for row in db.execute(
            "SELECT t.place_id, t.day, t.hour, t.occupancy_percent FROM popular_times t JOIN runs r USING (run_id) "
            "WHERE r.started_at = (SELECT MAX(r2.started_at) FROM popular_times t2 JOIN runs r2 USING (run_id) "
            "WHERE t2.place_id = t.place_id)"):
        levels[row["place_id"]][(row["day"], row["hour"])] = row["occupancy_percent"] or 0
    return to_shares(levels)


def load_around(db) -> tuple[list, dict]:
    """The places collected by `tracker.py around`, and their weeks as shares, like load_weeks."""
    levels = collections.defaultdict(dict)
    for row in db.execute("SELECT place_id, day, hour, occupancy_percent FROM nearby_times"):
        levels[row["place_id"]][(row["day"], row["hour"])] = row["occupancy_percent"] or 0
    return [dict(row) for row in db.execute("SELECT * FROM nearby_places")], to_shares(levels)


def to_shares(levels: dict) -> dict:
    weeks = {}
    for place_id, week in levels.items():
        total = sum(week.values())
        if total:
            weeks[place_id] = {slot: 100 * level / total for slot, level in week.items()}
    return weeks


def km_between(a: dict, b: dict) -> float:
    return math.hypot((float(a["lat"]) - float(b["lat"])) * 110.8,
                      (float(a["lng"]) - float(b["lng"])) * 111.32 * math.cos(math.radians(float(a["lat"]))))


def average(weeks: dict, place_ids: list) -> dict:
    return {(day, hour): sum(weeks[p].get((day, hour), 0) for p in place_ids) / len(place_ids)
            for day in DAYS for hour in HOURS} if place_ids else {}


def share(week: dict, days, hours) -> float:
    return sum(week.get((day, hour), 0) for day in days for hour in hours)


def follows(branch: dict, other: dict) -> float:
    """How closely another week follows the branch's week, over the hours when the branch has customers:
    1 is the same shape, 0 is no link (a correlation)."""
    slots = [slot for slot, level in branch.items() if level]
    x, y = [branch[slot] for slot in slots], [other.get(slot, 0) for slot in slots]
    mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
    spread = math.sqrt(sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y))
    return sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y)) / spread if spread else 0.0


def report_around(name: str, branch: dict, shop: dict, coffee: dict, places: list,
                  weeks: dict) -> tuple[list, list, list]:
    """Prints the branch's week next to each kind of place around it. Returns the header and the rows of
    busy_hours_around.csv, then the rows of places_around.csv."""
    kinds = {}
    for place in sorted(places, key=lambda place: -(place["reviews_count"] or 0)):
        kinds.setdefault(KINDS.get(place["search"], place["search"]), []).append(place)
    averages = {kind: average(weeks, [p["place_id"] for p in found if p["place_id"] in weeks])
                for kind, found in kinds.items()}
    averages = {kind: week for kind, week in averages.items() if week}

    print(f"\n{name}: other places within {AROUND_KM:g} km.")
    print(f"  {'kind':<24}{'found':>7}{'with busy hours':>17}{'follows the branch':>20}")
    for kind, found in kinds.items():
        with_hours = sum(p["place_id"] in weeks for p in found)
        print(f"  {kind:<24}{len(found):>7}{with_hours:>17}"
              f"{format(follows(branch, averages[kind]), '.2f') if kind in averages else '-':>20}")
    print(f"  {'coffee shops (2 km)':<24}{'':>7}{'':>17}{follows(branch, coffee):>20.2f}")
    print("  Share of the week (%):")
    print(f"  {'part of the week':<26}{'branch':>8}" + "".join(f"{kind:>{len(kind) + 2}}" for kind in averages))
    for part, days, hours in PARTS:
        print(f"  {part:<26}{share(branch, days, hours):>8.1f}"
              + "".join(f"{share(week, days, hours):>{len(kind) + 2}.1f}" for kind, week in averages.items()))

    hour_rows = [[name, DAY_NAMES[day], hour, round(branch.get((day, hour), 0), 2), round(coffee[(day, hour)], 2)]
                 + [round(week[(day, hour)], 2) for week in averages.values()] for day in DAYS for hour in HOURS]
    place_rows = []
    for kind, found in kinds.items():
        for place in found:
            week = weeks.get(place["place_id"])
            busiest = max(week, key=week.get) if week else None
            place_rows.append([name, kind, place["title"], place["category"], round(km_between(place, shop), 2),
                               place["rating"], place["reviews_count"], "yes" if week else "no",
                               f"{DAY_NAMES[busiest[0]]} {busiest[1]}:00" if busiest else "", place["url"]])
    return ["branch", "day", "hour", "branch_share", "nearby_coffee_share"] + [
        kind.replace(" ", "_") + "_share" for kind in averages], hour_rows, place_rows


def main() -> None:
    db = tracker.open_db()
    weeks = load_weeks(db)
    around_places, around_weeks = load_around(db)
    with open(tracker.ROOT / "exports" / "shops_ranked.csv", newline="", encoding="utf-8-sig") as f:
        shops = {row["place_id"]: row for row in csv.DictReader(f)}
    with open(tracker.ROOT / "competitors.csv", newline="", encoding="utf-8-sig") as f:
        groups = {row["place_id"]: row["group"] for row in csv.DictReader(f)}
    coffee = [p for p, shop in shops.items() if shop["type"] == "coffee" and p in weeks]
    competitors = average(weeks, [p for p in coffee if groups.get(p) not in (None, "my shop")])
    mine = [p for p, group in groups.items() if group == "my shop" and p in shops]
    without = [shops[p]["neighbourhood_en"] for p in mine if p not in weeks]

    rows, around_header, around_rows, place_rows = [], [], [], []
    for branch in (p for p in mine if p in weeks):
        name = shops[branch]["neighbourhood_en"]
        near = [p for p in coffee if p != branch and km_between(shops[p], shops[branch]) <= NEARBY_KM]
        nearby, specialty = average(weeks, near), average(weeks, [p for p in near if shops[p]["specialty"]])
        for day in DAYS:
            for hour in HOURS:
                slot = (day, hour)
                rows.append([name, DAY_NAMES[day], hour, round(weeks[branch].get(slot, 0), 2), round(nearby[slot], 2),
                             round(specialty[slot], 2) if specialty else "", round(competitors[slot], 2), len(near)])

        print(f"\n{name}: {len(near)} coffee shops with busy hours within {NEARBY_KM:g} km. Share of the week (%):")
        print(f"  {'part of the week':<26}{'branch':>8}{'nearby':>8}{'competitors':>13}")
        for part, days, hours in PARTS:
            print(f"  {part:<26}{share(weeks[branch], days, hours):>8.1f}{share(nearby, days, hours):>8.1f}"
                  f"{share(competitors, days, hours):>13.1f}")
        closed = [slot for slot in nearby if not weeks[branch].get(slot)]
        print(f"  Nearby shops get {sum(nearby[slot] for slot in closed):.0f}% of their week in hours when Google "
              "shows nobody at this branch.")
        around = [place for place in around_places if km_between(place, shops[branch]) <= AROUND_KM]
        if around:
            around_header, hour_rows, places = report_around(name, weeks[branch], shops[branch], nearby, around,
                                                             around_weeks)
            around_rows += hour_rows
            place_rows += places

    out = tracker.ROOT / "exports" / "busy_hours.csv"
    tracker.write_csv(out, ["branch", "day", "hour", "branch_share", "nearby_coffee_share", "nearby_specialty_share",
                            "competitor_share", "nearby_shops"], rows)
    if without:
        print(f"\nGoogle shows no busy hours for these branches: {', '.join(without)}.")
    print(f"Written to {out}")
    if around_rows:
        out = tracker.ROOT / "exports" / "busy_hours_around.csv"
        tracker.write_csv(out, around_header, around_rows)
        places_out = tracker.ROOT / "exports" / "places_around.csv"
        tracker.write_csv(places_out, ["branch", "kind", "name", "google_category", "km_from_branch", "rating",
                                       "reviews_count", "has_busy_hours", "busiest_time", "url"], place_rows)
        print(f"Written to {out} and {places_out}")


if __name__ == "__main__":
    main()
