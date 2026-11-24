#!/usr/bin/env python3
"""Competitor tracker for Riyadh coffee shops (Google Maps data via Apify).

Each run saves a dated snapshot of every coffee shop (rating, review count,
open/closed, popular times) plus the reviews published since the previous run,
so changes can be compared over time.

  python3 tracker.py run --limit 20    small test run (a few cents)
  python3 tracker.py run               full run
  python3 tracker.py reviews --top 300 one year of reviews for chosen shops (also --file, --all, --period)
  python3 tracker.py find "NAME"       add shops the wide run missed, by searching for their name
  python3 tracker.py continue          carry on the last run if it stopped at the cost cap
  python3 tracker.py export            write CSV files to exports/
  python3 tracker.py status            list runs and totals
  python3 tracker.py import RUN_ID     load a run started on apify.com (e.g. by a schedule)

Settings are in config.json. The Apify API token goes in .env (APIFY_TOKEN=...).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
API = "https://api.apify.com/v2"
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
PAGE_SIZE = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    dataset_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    is_full INTEGER,              -- 1 = meant to cover the whole search area, 0 = test run with --limit
    complete INTEGER DEFAULT 0,   -- 1 = finished normally without stopping at the cost cap
    reviews_since TEXT,
    max_cost_usd REAL,
    cost_usd REAL,
    charged_events TEXT,
    places INTEGER,
    new_reviews INTEGER,
    imported INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    title TEXT, category TEXT, categories TEXT,
    address TEXT, neighborhood TEXT, street TEXT, city TEXT,
    lat REAL, lng REAL, phone TEXT, website TEXT, price TEXT, url TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
    place_id TEXT, run_id TEXT, scraped_at TEXT,
    rating REAL, reviews_count INTEGER,
    stars_1 INTEGER, stars_2 INTEGER, stars_3 INTEGER, stars_4 INTEGER, stars_5 INTEGER,
    permanently_closed INTEGER, temporarily_closed INTEGER,
    opening_hours TEXT, additional_info TEXT,
    PRIMARY KEY (place_id, run_id)
);
CREATE TABLE IF NOT EXISTS popular_times (
    place_id TEXT, run_id TEXT, day TEXT, hour INTEGER, occupancy_percent INTEGER,
    PRIMARY KEY (place_id, run_id, day, hour)
);
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    place_id TEXT, published_at TEXT, stars INTEGER,
    text TEXT, text_translated TEXT, likes INTEGER,
    owner_response TEXT, owner_response_at TEXT,
    detailed_rating TEXT, context TEXT, origin TEXT, reviewer_name TEXT,
    first_seen_run TEXT
);
CREATE INDEX IF NOT EXISTS reviews_place ON reviews (place_id, published_at);
"""


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"Apify API error {status}: {message}")
        self.status = status


# ---------------------------------------------------------------- setup

def load_config(root: Path = ROOT) -> dict:
    with (root / "config.json").open(encoding="utf-8") as f:
        return json.load(f)


def load_token(root: Path = ROOT) -> str:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    env_file = root / ".env"
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "APIFY_TOKEN":
                token = value.strip().strip("\"'")
    if not token:
        sys.exit(
            "No Apify token found. Open the .env file and paste your token after APIFY_TOKEN=\n"
            "Get it at https://console.apify.com/settings/integrations"
        )
    return token


def open_db(root: Path = ROOT) -> sqlite3.Connection:
    (root / "data" / "raw").mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(root / "data" / "tracker.db"))
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


# ---------------------------------------------------------------- Apify API

def api(method: str, path: str, token: str, params: dict | None = None, body=None):
    url = API + path + ("?" + urlencode(params) if params else "")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for attempt in range(6):
        try:
            with urlopen(Request(url, data=data, method=method, headers=headers), timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            # Only retry requests that are safe to repeat; a retried POST could start a second paid run.
            if (e.code == 429 or e.code >= 500) and method == "GET" and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            try:
                detail = json.loads(detail)["error"]["message"]
            except (ValueError, KeyError, TypeError):
                pass
            raise ApiError(e.code, detail) from None
        except (OSError, HTTPException, ValueError) as e:
            # Connection failures, timeouts, and replies that were cut off before they were complete.
            if method == "GET" and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            hint = ("" if method == "GET" else " The request may still have reached Apify: check "
                    "https://console.apify.com/actors/runs before starting again.")
            raise ApiError(0, f"network problem: {e!r}.{hint}") from None


def wait_for_run(token: str, run_id: str) -> dict:
    last_message, offline = None, False
    while True:
        try:
            run = api("GET", f"/actor-runs/{run_id}", token, {"waitForFinish": 60})["data"]
        except ApiError as e:
            if e.status != 0:
                raise
            # The run lives on Apify's servers, so a lost connection here never stops it.
            if not offline:
                print("  Connection to Apify lost. The run itself keeps going; trying again every 30 seconds...",
                      flush=True)
                offline = True
            time.sleep(30)
            continue
        if offline:
            print("  Connection restored.", flush=True)
            offline = False
        message = run.get("statusMessage")
        if message and message != last_message:
            print(f"  [{run['status']}] {message}", flush=True)
            last_message = message
        if run["status"] in TERMINAL_STATUSES:
            return run


def iter_dataset_items(token: str, dataset_id: str, raw_path: Path):
    """Yield every item of a dataset, keeping a raw copy on disk so a run never has to be paid for twice."""
    if raw_path.exists():
        with raw_path.open(encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)
        return
    partial = raw_path.with_suffix(".part")
    offset = 0
    with partial.open("w", encoding="utf-8") as f:
        while True:
            page = api("GET", f"/datasets/{dataset_id}/items", token,
                       {"format": "json", "offset": offset, "limit": PAGE_SIZE})
            if not page:
                break
            for item in page:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                yield item
            offset += len(page)
    partial.rename(raw_path)


# ---------------------------------------------------------------- actor input

def build_input(cfg: dict, reviews_since: str | None, limit: int | None) -> dict:
    terms = cfg["search_terms"]
    actor_input = {
        # The place limit applies per search term, so a test run uses only the first term.
        "searchStringsArray": terms[:1] if limit else terms,
        "customGeolocation": cfg["search_area"],
        "language": cfg.get("language", "en"),
        "scrapePlaceDetailPage": True,  # needed for popular times
    }
    if cfg.get("category_filter"):
        actor_input["categoryFilterWords"] = cfg["category_filter"]
    if limit:
        actor_input["maxCrawledPlacesPerSearch"] = limit
    if reviews_since:
        actor_input.update(review_input(cfg, reviews_since))
    return actor_input


def review_input(cfg: dict, since: str) -> dict:
    return {
        "maxReviews": 99999,
        "reviewsSort": "newest",  # required by the actor when a start date is set
        "reviewsStartDate": since,
        "reviewsOrigin": "google",
        "scrapeReviewsPersonalData": bool((cfg.get("reviews") or {}).get("include_reviewer_names", False)),
    }


def reviews_start(db: sqlite3.Connection, cfg: dict) -> str | None:
    """Reviews are fetched from just before the last full run; the first run uses the configured period."""
    reviews = cfg.get("reviews") or {}
    if not reviews.get("enabled", True):
        return None
    last = db.execute(
        "SELECT started_at FROM runs WHERE imported = 1 AND is_full = 1 AND complete = 1 "
        "AND reviews_since IS NOT NULL ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if not last:
        return reviews.get("first_run_period", "1 month")
    since = datetime.strptime(last["started_at"][:10], "%Y-%m-%d") - timedelta(days=reviews.get("overlap_days", 2))
    return since.strftime("%Y-%m-%d")


# ---------------------------------------------------------------- import

def as_json(value) -> str | None:
    return json.dumps(value, ensure_ascii=False) if value else None


def import_items(db: sqlite3.Connection, run_id: str, items) -> tuple[int, int]:
    place_ids = set()
    for item in items:
        place_id = item.get("placeId")
        if not place_id:
            continue
        place_ids.add(place_id)
        location = item.get("location") or {}
        db.execute(
            "INSERT OR REPLACE INTO places VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (place_id, item.get("title"), item.get("categoryName"), as_json(item.get("categories")),
             item.get("address"), item.get("neighborhood"), item.get("street"), item.get("city"),
             location.get("lat"), location.get("lng"), item.get("phone"), item.get("website"),
             item.get("price"), item.get("url")),
        )
        dist = item.get("reviewsDistribution") or {}
        db.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (place_id, run_id, item.get("scrapedAt"), item.get("totalScore"), item.get("reviewsCount"),
             dist.get("oneStar"), dist.get("twoStar"), dist.get("threeStar"), dist.get("fourStar"),
             dist.get("fiveStar"), int(bool(item.get("permanentlyClosed"))),
             int(bool(item.get("temporarilyClosed"))), as_json(item.get("openingHours")),
             as_json(item.get("additionalInfo"))),
        )
        histogram = item.get("popularTimesHistogram")
        if isinstance(histogram, dict):
            for day, hours in histogram.items():
                for entry in hours or []:
                    if isinstance(entry, dict) and entry.get("hour") is not None:
                        db.execute("INSERT OR REPLACE INTO popular_times VALUES (?,?,?,?,?)",
                                   (place_id, run_id, day, entry["hour"], entry.get("occupancyPercent")))
        for review in item.get("reviews") or []:
            review_id = review.get("reviewId")
            if not review_id:
                continue
            db.execute(
                "INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(review_id) DO UPDATE SET likes = excluded.likes, "
                "owner_response = excluded.owner_response, owner_response_at = excluded.owner_response_at",
                (review_id, place_id, review.get("publishedAtDate"), review.get("stars"), review.get("text"),
                 review.get("textTranslated"), review.get("likesCount"), review.get("responseFromOwnerText"),
                 review.get("responseFromOwnerDate"), as_json(review.get("reviewDetailedRating")),
                 as_json(review.get("reviewContext")), review.get("reviewOrigin"), review.get("name"), run_id),
            )
    new_reviews = db.execute("SELECT COUNT(*) FROM reviews WHERE first_seen_run = ?", (run_id,)).fetchone()[0]
    return len(place_ids), new_reviews


def hit_cap(cost: float | None, cap: float | None) -> bool:
    """The actor stops charging just below the cap, so allow a small margin."""
    return bool(cap and cost and cost >= cap - max(0.02 * cap, 0.05))


def run_cap(db: sqlite3.Connection, run: dict) -> float | None:
    row = db.execute("SELECT max_cost_usd FROM runs WHERE run_id = ?", (run["id"],)).fetchone()
    return (row["max_cost_usd"] if row else None) or (run.get("options") or {}).get("maxTotalChargeUsd")


def finish_run(db: sqlite3.Connection, token: str, run: dict, root: Path = ROOT) -> None:
    run_id = run["id"]
    raw_path = root / "data" / "raw" / f"{run_id}.jsonl"
    print("Downloading results...", flush=True)
    places, new_reviews = import_items(db, run_id, iter_dataset_items(token, run["defaultDatasetId"], raw_path))

    cost, cap = run.get("usageTotalUsd"), run_cap(db, run)
    capped = hit_cap(cost, cap)
    complete = run["status"] == "SUCCEEDED" and not capped
    db.execute(
        "UPDATE runs SET status = ?, finished_at = ?, cost_usd = ?, charged_events = ?, places = ?, "
        "new_reviews = ?, complete = ?, imported = 1 WHERE run_id = ?",
        (run["status"], run.get("finishedAt"), cost, as_json(run.get("chargedEventCounts")), places,
         new_reviews, int(complete), run_id),
    )
    db.commit()

    cost_text = f"${cost:.2f}" if cost is not None else "see Apify console"
    print(f"Run {run_id}: {run['status']}. {places} places, {new_reviews} new reviews, cost {cost_text}.")
    with_times = db.execute("SELECT COUNT(DISTINCT place_id) FROM popular_times WHERE run_id = ?",
                            (run_id,)).fetchone()[0]
    print(f"Popular times were available for {with_times} of {places} places.")
    if not complete:
        reason = f"stopped at the ${cap:.2f} cost cap" if capped else "did not finish normally"
        print(f"WARNING: the run {reason}, so this snapshot is incomplete. What was collected is saved.\n"
              "To continue the same run from where it stopped: python3 tracker.py continue")


def ask_new_cap(cost: float, cap: float) -> float | None:
    print(f"The run stopped at the ${cap:.2f} cost cap before finishing (spent ${cost:.2f} so far).")
    while True:
        try:
            answer = input("To continue the same run from where it stopped, type a new total cap in USD "
                           f"(for example {cap * 2:.0f}), or press Enter to stop here: ").strip()
        except EOFError:
            return None
        if not answer:
            return None
        try:
            new_cap = float(answer.lstrip("$"))
        except ValueError:
            print("Please type a number.")
            continue
        if new_cap > cost:
            return new_cap
        print(f"The new cap must be higher than the ${cost:.2f} already spent.")


def resurrect(db: sqlite3.Connection, token: str, run_id: str, new_cap: float | None, root: Path = ROOT) -> None:
    """Restart a stopped run on Apify with the same storage, so it carries on instead of starting over."""
    run = api("POST", f"/actor-runs/{run_id}/resurrect", token,
              {"maxTotalChargeUsd": new_cap} if new_cap else None)["data"]
    db.execute("UPDATE runs SET status = ?, imported = 0, complete = 0, "
               "max_cost_usd = COALESCE(?, max_cost_usd) WHERE run_id = ?", (run["status"], new_cap, run_id))
    db.commit()
    # The saved copy of the results is now out of date; it is downloaded again when the run finishes.
    raw_path = root / "data" / "raw" / f"{run_id}.jsonl"
    if raw_path.exists():
        raw_path.unlink()
    print(f"Continuing run {run_id}" + (f" with a total cap of ${new_cap:.2f}." if new_cap else "."))


def wait_and_collect(db: sqlite3.Connection, token: str, run_id: str, interactive: bool) -> bool:
    """Wait for a run, offer to extend it if it stops at the cost cap, then save its results."""
    print("Waiting for the run to finish. A large run can take hours; it is safe to press Ctrl+C "
          "and run `python3 tracker.py run` again later to collect it.")
    while True:
        try:
            run = wait_for_run(token, run_id)
        except KeyboardInterrupt:
            print("\nStopped waiting. The run continues on Apify. Run `python3 tracker.py run` again to collect it.")
            return False
        except ApiError as e:
            if e.status == 404:
                db.execute("UPDATE runs SET status = 'NOT-FOUND', imported = 1 WHERE run_id = ?", (run_id,))
                db.commit()
                sys.exit(f"Run {run_id} no longer exists on Apify. It was removed from the pending list.")
            raise
        cost, cap = run.get("usageTotalUsd"), run_cap(db, run)
        if not (interactive and run["status"] == "SUCCEEDED" and hit_cap(cost, cap)):
            break
        new_cap = ask_new_cap(cost, cap)
        if new_cap is None:
            break
        resurrect(db, token, run_id, new_cap)
    finish_run(db, token, run)
    return True


# ---------------------------------------------------------------- commands

def cmd_run(args) -> None:
    cfg, token, db = load_config(), load_token(), open_db()
    pending = db.execute("SELECT run_id FROM runs WHERE imported = 0 ORDER BY started_at DESC LIMIT 1").fetchone()
    if pending:
        run_id = pending["run_id"]
        print(f"Resuming unfinished run {run_id} (no new run is started).")
    else:
        since = reviews_start(db, cfg)
        actor_input = build_input(cfg, since, args.limit)
        cap = args.max_cost if args.max_cost is not None else cfg.get("max_cost_usd_per_run")
        print("About to start a paid Apify run:")
        print(f"  search terms : {', '.join(actor_input['searchStringsArray'])}")
        print(f"  places       : {'up to ' + str(args.limit) + ' (test run)' if args.limit else 'all in the search area'}")
        print(f"  reviews      : {'published since ' + since if since else 'not collected'}")
        print(f"  cost cap     : {'$' + format(cap, '.2f') if cap else 'none (pay as you go)'}")
        if not args.yes and input("Start? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Nothing was started.")
            return
        actor = cfg.get("actor", "compass/crawler-google-places").replace("/", "~")
        run = api("POST", f"/acts/{actor}/runs", token,
                  {"maxTotalChargeUsd": cap} if cap else None, actor_input)["data"]
        run_id = run["id"]
        db.execute(
            "INSERT INTO runs (run_id, dataset_id, started_at, status, is_full, reviews_since, max_cost_usd) "
            "VALUES (?,?,?,?,?,?,?)",
            (run_id, run["defaultDatasetId"], run["startedAt"], run["status"], 0 if args.limit else 1, since, cap),
        )
        db.commit()
        print(f"Started run {run_id}: https://console.apify.com/actors/runs/{run_id}")

    if wait_and_collect(db, token, run_id, interactive=not args.yes):
        cmd_export(args)


LATEST_SNAPSHOTS = (
    "SELECT p.place_id, p.title, s.reviews_count, s.permanently_closed FROM places p "
    "JOIN snapshots s USING (place_id) JOIN runs r USING (run_id) WHERE r.started_at = ("
    "SELECT MAX(r2.started_at) FROM snapshots s2 JOIN runs r2 USING (run_id) WHERE s2.place_id = p.place_id)"
)
PERIOD_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}|\d+\s*(minute|hour|day|week|month|year)s?")


def select_shops(db: sqlite3.Connection, args) -> list:
    """The shops to collect reviews for, each with its latest review count."""
    shops = {row["place_id"]: row for row in db.execute(LATEST_SNAPSHOTS)}
    if args.file:
        with open(args.file, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if not rows or "place_id" not in rows[0]:
            sys.exit(f"{args.file} needs a column named place_id (keep that column from places_latest.csv).")
        wanted = {row["place_id"].strip() for row in rows if row["place_id"].strip()}
        unknown = wanted - shops.keys()
        if unknown:
            print(f"Skipping {len(unknown)} place IDs from the file that are not in the tracker's data.")
        return [shops[place_id] for place_id in sorted(wanted & shops.keys())]
    open_shops = sorted((s for s in shops.values() if not s["permanently_closed"]),
                        key=lambda s: s["reviews_count"] or 0, reverse=True)
    return open_shops if args.all else open_shops[:args.top]


def cmd_reviews(args) -> None:
    cfg, token, db = load_config(), load_token(), open_db()
    if not PERIOD_PATTERN.fullmatch(args.period):
        sys.exit('The period must look like "1 year", "6 months", "30 days" or a date such as 2026-01-01.')
    if db.execute("SELECT 1 FROM runs WHERE imported = 0").fetchone():
        sys.exit("Another run is not collected yet. Finish it first with: python3 tracker.py run")
    # The actor only accepts this form of Google place ID.
    shops = [s for s in select_shops(db, args)
             if len(s["place_id"]) == 27 and s["place_id"][:4] in ("ChIJ", "GhIJ")]
    ids = [s["place_id"] for s in shops]
    if not ids:
        sys.exit("No shops selected. Run `python3 tracker.py run` first so the tracker has a shop list.")

    prices = cfg.get("prices_usd") or {}
    total_reviews = sum(s["reviews_count"] or 0 for s in shops)
    most = len(ids) * prices.get("per_shop_with_reviews", 0.005) + total_reviews * prices.get("per_review", 0.0005)
    cap = args.max_cost if args.max_cost is not None else cfg.get("max_cost_usd_per_run")
    print("About to start a paid Apify run:")
    print(f"  shops        : {len(ids)}")
    print(f"  reviews      : published since {args.period}")
    print(f"  cost         : at most about ${most:,.2f}. That is the cost if all {total_reviews:,} reviews these")
    print("                 shops have on Google were inside the period; the real cost is lower.")
    print(f"  cost cap     : {'$' + format(cap, '.2f') if cap else 'none (pay as you go)'}")
    if cap and most > cap:
        print("  note         : the run may stop at the cap before all shops are done. You can then raise the cap")
        print("                 and continue it, or cancel now and choose fewer shops.")
    if not args.yes and input("Start? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Cancelled. Nothing was started.")
        return

    actor_input = {"placeIds": ids, "language": cfg.get("language", "en"), "scrapePlaceDetailPage": True,
                   **review_input(cfg, args.period)}
    actor = cfg.get("actor", "compass/crawler-google-places").replace("/", "~")
    run = api("POST", f"/acts/{actor}/runs", token, {"maxTotalChargeUsd": cap} if cap else None, actor_input)["data"]
    db.execute(
        "INSERT INTO runs (run_id, dataset_id, started_at, status, is_full, reviews_since, max_cost_usd) "
        "VALUES (?,?,?,?,0,?,?)",
        (run["id"], run["defaultDatasetId"], run["startedAt"], run["status"], args.period, cap),
    )
    db.commit()
    print(f"Started run {run['id']}: https://console.apify.com/actors/runs/{run['id']}")
    if wait_and_collect(db, token, run["id"], interactive=not args.yes):
        cmd_export(args)


def cmd_find(args) -> None:
    """Search for shops by name. The wide run misses some small shops; a name search finds them."""
    cfg, token, db = load_config(), load_token(), open_db()
    if db.execute("SELECT 1 FROM runs WHERE imported = 0").fetchone():
        sys.exit("Another run is not collected yet. Finish it first with: python3 tracker.py run")
    per_shop = (cfg.get("prices_usd") or {}).get("per_shop", 0.006)
    cap = args.max_cost
    print("About to start a paid Apify run:")
    print(f"  names        : {', '.join(args.names)}")
    print(f"  places       : shops in the search area with one of these names in their title, "
          f"up to {args.limit} per name")
    print(f"  cost         : ${per_shop} per shop found, so at most about ${len(args.names) * args.limit * per_shop:.2f}")
    print(f"  cost cap     : ${cap:.2f}")
    if not args.yes and input("Start? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Cancelled. Nothing was started.")
        return

    # No category filter: a branch can be listed on Google under an unexpected category.
    actor_input = {"searchStringsArray": args.names, "searchMatching": "only_includes",
                   "customGeolocation": cfg["search_area"], "language": cfg.get("language", "en"),
                   "scrapePlaceDetailPage": True, "maxCrawledPlacesPerSearch": args.limit}
    actor = cfg.get("actor", "compass/crawler-google-places").replace("/", "~")
    run = api("POST", f"/acts/{actor}/runs", token, {"maxTotalChargeUsd": cap}, actor_input)["data"]
    db.execute(
        "INSERT INTO runs (run_id, dataset_id, started_at, status, is_full, max_cost_usd) VALUES (?,?,?,?,0,?)",
        (run["id"], run["defaultDatasetId"], run["startedAt"], run["status"], cap),
    )
    db.commit()
    print(f"Started run {run['id']}: https://console.apify.com/actors/runs/{run['id']}")
    if not wait_and_collect(db, token, run["id"], interactive=not args.yes):
        return
    found = db.execute(
        "SELECT p.title, p.neighborhood, s.rating, s.reviews_count, "
        "(SELECT COUNT(*) FROM snapshots s2 WHERE s2.place_id = p.place_id) AS times_seen "
        "FROM snapshots s JOIN places p USING (place_id) WHERE s.run_id = ? ORDER BY s.reviews_count DESC",
        (run["id"],)).fetchall()
    for row in found:
        print(f"  {'NEW    ' if row['times_seen'] == 1 else 'known  '} {row['title']} | {row['neighborhood'] or '-'} | "
              f"rating {row['rating'] or '-'} | {row['reviews_count'] or 0} reviews")
    print(f"{sum(row['times_seen'] == 1 for row in found)} of these {len(found)} shops were not in the tracker before.")
    cmd_export(args)


def cmd_continue(args) -> None:
    token, db = load_token(), open_db()
    row = db.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if not row:
        sys.exit("No runs yet. Start with: python3 tracker.py run --limit 20")
    run_id = row["run_id"]
    if not row["imported"]:
        print(f"Run {run_id} is already in progress.")
    elif row["complete"]:
        print("The last run finished completely. There is nothing to continue.")
        return
    else:
        cost, cap, new_cap = row["cost_usd"], row["max_cost_usd"], args.max_cost
        if new_cap is None and hit_cap(cost, cap):
            new_cap = ask_new_cap(cost, cap)
            if new_cap is None:
                print("Cancelled. Nothing was started.")
                return
        if new_cap is not None and cost and new_cap <= cost:
            sys.exit(f"The new cap must be higher than the ${cost:.2f} already spent.")
        resurrect(db, token, run_id, new_cap)
    if wait_and_collect(db, token, run_id, interactive=True):
        cmd_export(args)


def cmd_import(args) -> None:
    token, db = load_token(), open_db()
    run = api("GET", f"/actor-runs/{args.run_id}", token)["data"]
    if run["status"] not in TERMINAL_STATUSES:
        sys.exit(f"Run {args.run_id} is still {run['status']}. Try again when it has finished.")
    db.execute(
        "INSERT OR IGNORE INTO runs (run_id, dataset_id, started_at, status, is_full) VALUES (?,?,?,?,?)",
        (run["id"], run["defaultDatasetId"], run["startedAt"], run["status"], 0 if args.partial else 1),
    )
    finish_run(db, token, run)
    cmd_export(args)


def cmd_status(args) -> None:
    db = open_db()
    runs = db.execute("SELECT * FROM runs ORDER BY started_at").fetchall()
    if not runs:
        print("No runs yet. Start with: python3 tracker.py run --limit 20")
        return
    for r in runs:
        # "partial" = a --limit test or a reviews run for selected shops
        kind = "partial" if not r["is_full"] else ("full" if r["complete"] or not r["imported"] else "full, incomplete")
        cost = f"${r['cost_usd']:.2f}" if r["cost_usd"] is not None else "-"
        state = r["status"] if r["imported"] else f"{r['status']} (not collected yet)"
        print(f"{(r['started_at'] or '')[:16]}  {r['run_id']}  {state:<12} {kind:<16} "
              f"places={r['places'] or 0}  new_reviews={r['new_reviews'] or 0}  cost={cost}")
    totals = [db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("places", "snapshots", "reviews")]
    print(f"Total: {totals[0]} places, {totals[1]} snapshots, {totals[2]} reviews.")


SERVICE_FLAGS = ["Dine-in", "Takeout", "Delivery", "Drive-through", "Outdoor seating"]
# Google's labels for the same options when "language" in config.json is "ar".
ARABIC_SERVICE_LABELS = {
    "الجلوس داخل المكان": "Dine-in",
    "طعام سفري": "Takeout",
    "خدمة التوصيل": "Delivery",
    "خدمة الطلب أثناء القيادة": "Drive-through",
    "أماكن جلوس في الهواء الطلق": "Outdoor seating",
}


def service_flags(additional_info: str | None) -> dict:
    flags = dict.fromkeys(SERVICE_FLAGS, "")
    for options in (json.loads(additional_info) if additional_info else {}).values():
        for option in options or []:
            for name, value in (option or {}).items():
                name = ARABIC_SERVICE_LABELS.get(name, name)
                if name in flags:
                    flags[name] = "yes" if value else "no"
    return flags


def write_csv(path: Path, header: list[str], rows) -> int:
    count = 0
    # utf-8-sig so Excel shows Arabic text correctly
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def cmd_export(args, root: Path = ROOT) -> None:
    db = open_db(root)
    out = root / "exports"
    out.mkdir(exist_ok=True)

    full_runs = db.execute("SELECT run_id, started_at FROM runs WHERE imported = 1 AND is_full = 1 "
                           "AND complete = 1 ORDER BY started_at").fetchall()
    latest_full = full_runs[-1] if full_runs else None
    history: dict[str, list] = {}
    for snap in db.execute("SELECT s.*, r.started_at AS run_started FROM snapshots s JOIN runs r USING (run_id) "
                           "ORDER BY s.place_id, r.started_at"):
        history.setdefault(snap["place_id"], []).append(snap)

    def status_of(snaps) -> str:
        first, last = snaps[0], snaps[-1]
        if last["permanently_closed"]:
            return "permanently closed"
        if last["temporarily_closed"]:
            return "temporarily closed"
        if latest_full and last["run_started"] < latest_full["started_at"]:
            return "not found in latest run"
        if len(full_runs) >= 2 and first["run_started"] >= latest_full["started_at"]:
            return "new"
        return "open"

    def latest_rows():
        for place in db.execute("SELECT * FROM places ORDER BY title"):
            snaps = history.get(place["place_id"])
            if not snaps:
                continue
            last, prev = snaps[-1], (snaps[-2] if len(snaps) > 1 else None)

            def change(field):
                if prev is None or last[field] is None or prev[field] is None:
                    return ""
                return round(last[field] - prev[field], 2)

            yield [place["place_id"], place["title"], status_of(snaps), place["category"], place["neighborhood"],
                   place["address"], place["lat"], place["lng"], place["phone"], place["website"], place["price"],
                   last["rating"], last["reviews_count"], last["run_started"][:10],
                   prev["run_started"][:10] if prev else "", change("rating"), change("reviews_count"),
                   last["stars_1"], last["stars_2"], last["stars_3"], last["stars_4"], last["stars_5"],
                   *service_flags(last["additional_info"]).values(), place["url"]]

    counts = {
        "places_latest.csv": write_csv(
            out / "places_latest.csv",
            ["place_id", "name", "status", "category", "neighborhood", "address", "lat", "lng", "phone", "website",
             "price", "rating", "reviews_count", "snapshot_date", "previous_snapshot_date", "rating_change",
             "new_reviews_since_previous", "stars_1", "stars_2", "stars_3", "stars_4", "stars_5",
             *[flag.lower().replace("-", "_").replace(" ", "_") for flag in SERVICE_FLAGS], "google_maps_url"],
            latest_rows()),
        "rating_history.csv": write_csv(
            out / "rating_history.csv",
            ["place_id", "name", "snapshot_date", "rating", "reviews_count", "permanently_closed",
             "temporarily_closed"],
            db.execute("SELECT s.place_id, p.title, substr(r.started_at, 1, 10), s.rating, s.reviews_count, "
                       "s.permanently_closed, s.temporarily_closed FROM snapshots s JOIN runs r USING (run_id) "
                       "JOIN places p USING (place_id) ORDER BY p.title, r.started_at")),
        "reviews.csv": write_csv(
            out / "reviews.csv",
            ["place_id", "name", "review_id", "published_at", "stars", "text", "text_translated", "likes",
             "owner_response", "owner_response_at", "detailed_rating", "reviewer_name"],
            db.execute("SELECT v.place_id, p.title, v.review_id, v.published_at, v.stars, v.text, "
                       "v.text_translated, v.likes, v.owner_response, v.owner_response_at, v.detailed_rating, "
                       "v.reviewer_name "
                       "FROM reviews v JOIN places p USING (place_id) ORDER BY v.published_at DESC")),
        # Latest available histogram per place (Google does not show popular times for every shop).
        "popular_times.csv": write_csv(
            out / "popular_times.csv",
            ["place_id", "name", "snapshot_date", "day", "hour", "occupancy_percent"],
            db.execute("SELECT t.place_id, p.title, substr(r.started_at, 1, 10), t.day, t.hour, "
                       "t.occupancy_percent FROM popular_times t JOIN runs r USING (run_id) "
                       "JOIN places p USING (place_id) WHERE r.started_at = (SELECT MAX(r2.started_at) "
                       "FROM popular_times t2 JOIN runs r2 USING (run_id) WHERE t2.place_id = t.place_id) "
                       "ORDER BY p.title, t.day, t.hour")),
    }
    print(f"Exported to {out}:")
    for name, count in counts.items():
        print(f"  {name}: {count} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Track Riyadh coffee shops on Google Maps over time.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="start a scrape (or resume an unfinished one) and save a snapshot")
    run.add_argument("--limit", type=int, help="test run: scrape at most this many places")
    run.add_argument("--max-cost", type=float, help="cost cap in USD for this run (overrides config.json)")
    run.add_argument("--yes", action="store_true", help="do not ask for confirmation (for scheduled runs)")
    run.set_defaults(func=cmd_run)

    rev = sub.add_parser("reviews", help="collect reviews for chosen shops that are already in the tracker")
    which = rev.add_mutually_exclusive_group(required=True)
    which.add_argument("--top", type=int, metavar="N", help="the N open shops with the most reviews")
    which.add_argument("--file", help="a CSV file with a place_id column, e.g. a filtered copy of places_latest.csv")
    which.add_argument("--all", action="store_true", help="every open shop")
    rev.add_argument("--period", default="1 year", help='how far back to go, e.g. "1 year" or "6 months" (default: 1 year)')
    rev.add_argument("--max-cost", type=float, help="cost cap in USD for this run (overrides config.json)")
    rev.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    rev.set_defaults(func=cmd_reviews)

    find = sub.add_parser("find", help="search for shops by name and add the ones the wide run missed")
    find.add_argument("names", nargs="+", help='shop or brand names as written on Google Maps, e.g. "بلاك ستامب"')
    find.add_argument("--limit", type=int, default=20, help="most shops to take per name (default: 20)")
    find.add_argument("--max-cost", type=float, default=1.0, help="cost cap in USD for this run (default: 1)")
    find.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    find.set_defaults(func=cmd_find)

    cont = sub.add_parser("continue", help="carry on the last run from where it stopped (cost cap or failure)")
    cont.add_argument("--max-cost", type=float, help="new total cost cap in USD for the run")
    cont.set_defaults(func=cmd_continue)

    imp = sub.add_parser("import", help="load a finished run that was started on apify.com")
    imp.add_argument("run_id")
    imp.add_argument("--partial", action="store_true", help="the run did not cover the whole search area")
    imp.set_defaults(func=cmd_import)

    sub.add_parser("export", help="write CSV files to exports/").set_defaults(func=cmd_export)
    sub.add_parser("status", help="list runs and totals").set_defaults(func=cmd_status)

    args = parser.parse_args()
    try:
        args.func(args)
    except ApiError as e:
        sys.exit(str(e))
    except KeyboardInterrupt:
        sys.exit("\nStopped. Nothing is lost. Run the same command again to carry on.")


if __name__ == "__main__":
    main()
