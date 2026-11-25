#!/usr/bin/env python3
"""Step 4: what customers praise and complain about, for the brands in competitors.csv.

  python3 analyze_reviews.py

Reads the reviews collected with `tracker.py reviews` and writes to exports/:
  review_brands.csv     one row per brand: stars, scores for food, service and atmosphere, replies, prices.
                        The columns ending in "_answers" say how many reviews a number rests on; few answers = weak number
  review_branches.csv   the same for every shop
  review_topics.csv     for every brand and topic: how many reviews praise it and how many complain
  review_mentions.csv   every praise or complaint that was found, with the sentence, to read them yourself
  review_months.csv     reviews and stars per brand and month

Topics are found by words, not by a person reading: a sentence that names a topic (price, staff, ...) is
praise or a complaint by the words around it ("expensive", "slow", "delicious", "not clean"). For a few
topics, when a review names the topic without any such word, its stars decide (5 = praise, 1 or 2 =
complaint). This is right for most sentences, not all, so read review_mentions.csv before acting on a number.
"""
from __future__ import annotations

import collections
import csv
import json
import re
import statistics

import tracker

MY_SHOP = "my shop"
MY_NAME = "Black Stamp"

MARKS = re.compile(r"[\u064B-\u065F\u0670\u0640\u200e\u200f]")
LETTERS = str.maketrans("أإآٱىة", "اااايه")
# Sentences end at punctuation, a line break, or a word that turns praise into a complaint ("but").
CLAUSE_END = re.compile(r"<br>|[\n.!?؟،,؛;:()\-–|/]+|\s(?:لكن|ولكن|بس|الا ان|غير ان|but|however|although)\s")
WORD = re.compile(r"[^\W_]+")
# A word of praise after one of these is a complaint ("not clean"), and the other way round ("no waiting").
NEGATORS = {"مو", "مب", "موب", "مش", "ماهو", "ماهي", "مهو", "غير", "ليس", "ليست", "لا", "ما", "مافي", "مافيه", "ماكان", "بدون",
            "بلا", "عدم", "not", "no", "never", "without", "isnt", "wasnt", "dont", "didnt"}
LINKS = {"فيه", "فيها", "في", "كان", "اي", "هناك", "any", "a", "the"}
# "The parking is easy" is not praise in a sentence that wishes for it or denies it.
# "ولا احلي" (nothing better) is praise, not "not the best".
BEST = {"احلي", "اروع", "الذ", "افضل", "اجمل", "اطيب", "غلطه"}
# A word of praise or complaint counts for a topic only when it is this close to the topic's name, in words.
# Many reviews are one long sentence without a full stop, about several things.
REACH = 3
WISHES = NEGATORS | {"اتمني", "ياليت", "ليت", "لو", "wish"}

PRAISE = re.compile(
    r"^(ممتاز\w*|حلو|حلوه|حلوين|لذيذ\w*|رائع\w*|جميل\w*|روعه|رهيب\w*|يجنن|تجنن|خيال\w*|فخم\w*|زين|زينه|كويس\w*|"
    r"جيد\w*|افضل|احلي|الذ|اروع|اجمل|اطيب|اطلق|مميز\w*|يستاهل\w*|يفوز|تفوز|ابداع|مبدع\w*|اسطور\w*|موزون\w*|مضبوط\w*|راقي\w*|"
    r"اشكر\w*|شكرا|شكر|نشكر\w*|ماقصر\w*|"
    r"good|great|nice|amazing|excellent|best|love|loved|lovely|delicious|perfect|wonderful|awesome|tasty|thank|thanks)$")
COMPLAINT = re.compile(
    r"^(سي[ءئ]\w*|سيئ\w*|سئ\w*|اسوء|اسوا|سوء|زفت|فاشل\w*|ردي\w*|مقرف\w*|خايس\w*|تعبان\w*|عادي\w*|للاسف|"
    r"مخيب\w*|ماعجبني|ماحبيت|ماتنشرب|متدني\w*|"
    r"bad|worst|terrible|poor|awful|horrible|disappointing|disappointed|average|mediocre)$")


def words(pattern: str) -> re.Pattern:
    return re.compile(rf"^(?:{pattern})$")


def has(pattern: re.Pattern | None, token: str) -> bool:
    """Does the word match, as written or without a leading "and" (و) or "the" (ال)?"""
    if not pattern:
        return False
    if pattern.match(token):
        return True
    for prefix in ("وال", "ال", "و", "لل"):
        if token.startswith(prefix) and len(token) - len(prefix) >= 3 and pattern.match(token[len(prefix):]):
            return True
    return False


# Words are written without "the" (ال) and "and" (و): `has` tries the word with and without them.
# For each topic: words that only name it, words that are a complaint by themselves, words that are praise by
# themselves. All are matched against whole words after the text is simplified (see `simplify`). "bad_phrase"
# and "good_phrase" are for complaints and praise that need two words ("price is high"). "stars" says when the
# stars of the review may decide for a sentence that names the topic without praise or complaint: complaints
# tell a story that names many things ("I ordered a coffee and the cashier..."), so it is allowed only where
# naming the topic in a bad review nearly always means a complaint about it.
TOPICS = {
    "Coffee taste": {
        "names": words(r"قهوه|قهوتهم|قهوتكم|البن|والبن|بنهم|محصول|محاصيل\w*|اسبريسو|لاتيه|كورتادو|امريكانو|"
                       r"فلات|v60|في60|دريب|كابتشينو|طعم|طعمه|طعمها|نكهه|coffee|espresso|latte|cortado|"
                       r"americano|flat|taste|beans|cappuccino"),
        "bad": words(r"محروق\w*|حامض\w*|ماصخ\w*|burnt|sour|bitter|watery"),
        "good": None,
        "bad_phrase": re.compile(r"ما ?تنشرب|ما ?ينشرب|(طعم\w*|كانه|كانها|اشرب|زي|مثل|قهوه) (ال)?(مويه|مويا|ماء)\b"),
        "stars": "praise",
    },
    "Staff and service": {
        "names": words(r"موظف\w*|كاشير|باريستا|تعامل\w*|خدمه|خدمته\w*|"
                       r"استقبال\w*|ستاف|طاقم|عامل|عمال|الشباب|staff|service|barista|baristas|cashier|team"),
        "bad": words(r"وقح\w*|مستفز\w*|يتجاهل\w*|تجاهل\w*|rude|unfriendly|impolite"),
        "good": words(r"خلوق\w*|بشوش\w*|محترم\w*|خدوم\w*|متعاون\w*|لطيف\w*|friendly|helpful|welcoming|polite|kind"),
        "stars": "both",
    },
    "Speed and waiting": {
        "names": None,
        "bad": words(r"بطي[ءئ]\w*|بطئ\w*|تاخير|تاخر\w*|انتظرت\w*|انتظر|ننتظر|انتظار|طولوا|يطولون|طابور|"
                     r"slow|waiting|waited|wait|delay|delayed"),
        "good": words(r"سريع\w*|سرعه|fast|quick|quickly"),
    },
    "Price": {
        "names": words(r"سعر\w*|اسعار\w*|price|prices|priced"),
        "bad": words(r"غالي\w*|expensive|overpriced|pricey"),
        "good": words(r"رخيص\w*|cheap|affordable|reasonable"),
        "bad_phrase": re.compile(r"(سعر|اسعار)\w* .{0,15}(عالي|مرتفع|مبالغ)|مبالغ \w+ .{0,10}(سعر|اسعار)"),
        "good_phrase": re.compile(r"(سعر|اسعار)\w* .{0,12}(مناسب|معقول)"),
    },
    "Desserts and food": {
        "names": words(r"حلا|حلي|حلويات|كيك\w*|كوكيز|تشيز|بسبوسه|ساندوتش\w*|سندوتش\w*|"
                       r"كرواسون|معجنات|مخبوزات|بودينق|تيراميسو|براوني|فطاير|سناك\w*|"
                       r"dessert|desserts|cake|cakes|cookie|cookies|croissant|sandwich|pastry|pastries|food"),
        "bad": words(r"يابس\w*|بايت|بايته|ناشف\w*|stale"),
        "good": None,
        "stars": "praise",
    },
    "Place and seating": {
        "names": words(r"مكان|جلسات|جلسه|كراسي|طاولات|طاوله|ديكور|اجواء|الجو|والجو|"
                       r"place|seating|seats|chairs|tables|atmosphere|ambiance|ambience|vibe|vibes|interior"),
        "bad": words(r"ضيق\w*|cramped"),
        "good": words(r"رايق\w*|هادي\w*|هادئ\w*|مريح\w*|مرتب\w*|واسع\w*|cozy|cosy|calm|quiet|comfortable|spacious"),
        "stars": "praise",
    },
    "Crowded": {
        # Kept apart from the place: a crowd is also a sign that the shop is popular.
        "names": None,
        "bad": words(r"زحمه|ازدحام|مزدحم\w*|crowded"),
        "good": None,
        "complaints_only": True,
    },
    "Noise and music": {
        # Reviews name the music almost only to ask for it to be lowered or stopped.
        "names": None,
        "bad": words(r"ازعاج|موسيقي|اغاني|noisy|loud|music|songs"),
        "good": None,
        "bad_phrase": re.compile(r"صوت\w* .{0,10}(عالي|مرتفع)"),
        "complaints_only": True,
    },
    "Cleanliness": {
        "names": words(r"نظافه|نظافته\w*|cleanliness|hygiene"),
        "bad": words(r"وصخ\w*|وسخ\w*|قذر\w*|حشر\w*|ذباب|صرصور|صراصير|شعره|dirty|filthy"),
        "good": words(r"نظيف\w*|clean"),
        "stars": "both",
    },
    "Parking": {
        # "مواقف" also means "situations", so it counts only next to a word about cars or space.
        "names": words(r"باركن\w*|parking"),
        "bad": None,
        "good": None,
        "bad_phrase": re.compile(r"(مافي|مافيه|لا يوجد|لايوجد|صعب\w*|قله|قليله|ضيق\w*) .{0,20}(مواقف|باركن)|"
                                 r"(مواقف|باركن)\w* .{0,20}(صعب|قليل|ضيق|مافي|زحمه|معدوم|ممتلئ)|no parking"),
        "good_phrase": re.compile(r"(مواقف|باركن)\w* .{0,20}(متوفر|كثير|واسع|سهل)"),
    },
    "Wrong or missing order": {
        "names": None,
        "bad": words(r"نسوا|forgot"),
        "good": None,
        "bad_phrase": re.compile(r"(طلب\w*|الحساب|الفاتوره) .{0,25}(غلط|خطا|ناقص)|(غلط\w*|خطا|اخطاء|لخبط\w*) (في |ب|بال|في ال)?(ال)?(طلب|حساب)|"
                                 r"wrong (order|one|drink|item|coffee)|missing"),
        "complaints_only": True,
    },
    "Small cup or portion, too much ice": {
        "names": None,
        "bad": None,
        "good": None,
        "bad_phrase": re.compile(r"(كوب|حجم)\w* .{0,25}(ناقص|صغير|نص|فاضي)|ثلج كثير|كله ثلج|كلها ثلج|نصه ثلج|نصها ثلج|"
                                 r"مليان ثلج|too much ice|half (empty|full)"),
    },
    "Drive-through": {
        "names": words(r"درايف|ثرو|شباك|drive|drivethru"),
        "bad": None,
        "good": None,
    },
    "Closed when it should be open": {
        "names": None,
        "bad": words(r"مقفلين|مسكرين|يقفلون|يسكرون"),
        "good": None,
        "bad_phrase": re.compile(r"(لقيت\w*|طلع|القاه|جيت\w*|وصلت) .{0,20}(مقفل|مغلق|مسكر)|(فرع|محل|كوفي) (مقفل|مغلق|مسكر)|"
                                 r"وهو مقفل|ساعات العمل|(was|is|were|are) closed"),
        "complaints_only": True,
    },
}

DETAIL = {"الطعام": "food", "الخدمة": "service", "الأجواء": "atmosphere"}


def simplify(text: str) -> str:
    """Lower case, one spelling for each Arabic letter, and "مرررره" becomes "مره"."""
    text = MARKS.sub("", text.lower()).translate(LETTERS).replace("'", "").replace("’", "")
    return re.sub(r"(.)\1{2,}", r"\1", text)


def clause_mentions(clause: str) -> dict:
    """Topics in one sentence as {topic: "good" | "bad" | "named"}; "named" means no word of praise or complaint."""
    tokens = WORD.findall(clause)

    def negator(i: int) -> bool:
        if i < 0 or (tokens[i] == "ولا" and tokens[i + 1] in BEST):
            return False
        return tokens[i] in NEGATORS or tokens[i].lstrip("و") in NEGATORS

    # "not clean", and also "no ... in it" as in "ما فيه زحمه" (there is no crowd)
    negated = [negator(i - 1) or (i > 1 and tokens[i - 1] in LINKS and negator(i - 2)) for i in range(len(tokens))]
    tones = {}  # position of each general word of praise or complaint
    for i, token in enumerate(tokens):
        if token == "غلطه" and i > 0 and tokens[i - 1] == "ولا":
            tones[i] = "good"  # "ولا غلطه": flawless
        elif has(PRAISE, token) or has(COMPLAINT, token):
            tones[i] = "good" if has(PRAISE, token) != negated[i] else "bad"
    found = {}
    for topic, rule in TOPICS.items():
        own = None  # the topic's own words of praise or complaint win over the general ones
        if rule.get("bad_phrase") and rule["bad_phrase"].search(clause):
            own = "bad"
        elif rule.get("good_phrase") and rule["good_phrase"].search(clause):
            own = "bad" if WISHES & set(tokens) else "good"
        for i, token in enumerate(tokens):
            if own:
                break
            if has(rule["bad"], token):
                own = "good" if negated[i] else "bad"
            elif has(rule["good"], token):
                own = "bad" if negated[i] else "good"
        if own == "good" and rule.get("complaints_only"):
            own = None
        if own:
            found[topic] = own
            continue
        names = [i for i, token in enumerate(tokens) if has(rule["names"], token)]
        if names:
            # the nearest general word decides; when two are equally near, the one after the name
            # ("القهوه لذيذه والموظف سيء": the coffee is tasty, the staff are bad)
            near = [(abs(j - i), j < i, side) for i in names for j, side in tones.items() if abs(j - i) <= REACH]
            found[topic] = min(near)[2] if near else "named"
    return found


def review_mentions(text: str, stars: int) -> list:
    """(topic, "good" | "bad", sentence) for one review; each topic at most once per side."""
    out, seen, named = [], set(), []
    for clause in CLAUSE_END.split(simplify(text)):
        clause = clause.strip() if clause else ""
        if not clause:
            continue
        for topic, side in clause_mentions(clause).items():
            if side == "named":
                named.append((topic, clause))
            elif (topic, side) not in seen:
                seen.add((topic, side))
                out.append((topic, side, clause))
    # Topics that were only named: the stars decide, but only for clear reviews.
    side = "good" if stars == 5 else "bad" if stars <= 2 else None
    if side:
        for topic, clause in named:
            allowed = TOPICS[topic].get("stars")
            if (allowed == "both" or (allowed == "praise" and side == "good")) and not any(t == topic for t, _ in seen):
                seen.add((topic, side))
                out.append((topic, side, clause))
    return out


def spend(band: str | None) -> float | None:
    """Middle of a "price per person" band such as "20–40 SAR"."""
    numbers = [int(n) for n in re.findall(r"\d+", band or "")]
    if not numbers:
        return None
    return sum(numbers[:2]) / 2 if len(numbers) >= 2 else numbers[0] + 20


def share(part: int, whole: int) -> float | str:
    return round(100 * part / whole, 1) if whole else ""


def average(values: list, digits: int = 2) -> float | str:
    return round(statistics.mean(values), digits) if values else ""


def summary(reviews: list) -> dict:
    """The numbers for one group of reviews (a brand or a shop)."""
    low = [r for r in reviews if r["stars"] <= 2]
    context = collections.defaultdict(list)
    for r in reviews:
        for key, value in r["context"].items():
            context[key].append(value)
    waits = context["وقت الانتظار"]
    parking = [v for v in context["مساحة موقف السيارات"] if "لست" not in v]
    spends = [s for s in map(spend, context["السعر للشخص الواحد"]) if s]
    row = {
        "reviews_last_year": len(reviews),
        "stars": average([r["stars"] for r in reviews]),
        "five_star_percent": share(sum(r["stars"] == 5 for r in reviews), len(reviews)),
        "one_two_star_percent": share(len(low), len(reviews)),
        "one_two_star_reviews": len(low),
        "reviews_with_text": sum(bool(r["text"]) for r in reviews),
    }
    for arabic, english in DETAIL.items():
        row[f"{english}_score"] = average([r["detail"][arabic] for r in reviews if r["detail"].get(arabic)])
    row.update({
        "score_answers": sum(bool(r["detail"]) for r in reviews),
        "owner_reply_percent": share(sum(r["replied"] for r in reviews), len(reviews)),
        "owner_reply_to_one_two_star_percent": share(sum(r["replied"] for r in low), len(low)),
        "spend_per_person_sar": average(spends, 0),
        "spend_answers": len(spends),
        "no_wait_percent": share(sum(v == "بلا انتظار" for v in waits), len(waits)),
        "wait_answers": len(waits),
        "parking_hard_percent": share(sum("الصعب" in v for v in parking), len(parking)),
        "parking_answers": len(parking),
    })
    return row


def load() -> tuple[list, dict]:
    db = tracker.open_db()
    with open(tracker.ROOT / "competitors.csv", newline="", encoding="utf-8-sig") as f:
        shops = {row["place_id"]: row for row in csv.DictReader(f)}
    reviews = []
    for r in db.execute("SELECT place_id, published_at, stars, text, owner_response, detailed_rating, context FROM reviews"):
        if r["place_id"] not in shops or not r["stars"]:
            continue
        group = shops[r["place_id"]]["group"]
        reviews.append({
            "place_id": r["place_id"], "brand": MY_NAME if group == MY_SHOP else group, "month": r["published_at"][:7],
            "stars": r["stars"], "text": (r["text"] or "").strip(), "replied": bool(r["owner_response"]),
            "detail": json.loads(r["detailed_rating"] or "{}"), "context": json.loads(r["context"] or "{}"),
        })
    return reviews, shops


def main() -> None:
    reviews, shops = load()
    if not reviews:
        raise SystemExit("No reviews yet. Collect them first with: python3 tracker.py reviews --file competitors.csv")
    by_brand, by_shop = collections.defaultdict(list), collections.defaultdict(list)
    for r in reviews:
        by_brand[r["brand"]].append(r)
        by_shop[r["place_id"]].append(r)

    mentions = []
    for r in reviews:
        if r["text"]:
            for topic, side, clause in review_mentions(r["text"], r["stars"]):
                mentions.append({"brand": r["brand"], "shop": shops[r["place_id"]]["name"],
                                 "neighbourhood": shops[r["place_id"]]["neighbourhood"], "place_id": r["place_id"],
                                 "month": r["month"], "stars": r["stars"], "topic": topic,
                                 "kind": "praise" if side == "good" else "complaint", "sentence": clause,
                                 "review": r["text"].replace("<br>", " ").replace("\n", " ")})

    brands = sorted(by_brand, key=lambda b: (b != MY_NAME, -len(by_brand[b])))
    brand_rows = [{"brand": b, "shops": len({r["place_id"] for r in by_brand[b]}), **summary(by_brand[b])} for b in brands]
    shop_rows = [{"brand": MY_NAME if shops[p]["group"] == MY_SHOP else shops[p]["group"], "shop": shops[p]["name"],
                  "neighbourhood": shops[p]["neighbourhood"], "place_id": p, **summary(by_shop[p])}
                 for p in sorted(by_shop, key=lambda p: (brands.index(by_shop[p][0]["brand"]), -len(by_shop[p])))]

    counts = collections.Counter((m["brand"], m["topic"], m["kind"]) for m in mentions)
    with_text = {b: sum(bool(r["text"]) for r in by_brand[b]) for b in brands}
    topic_rows = []
    for b in brands + ["All competitors"]:
        members = [x for x in brands if x != MY_NAME] if b == "All competitors" else [b]
        texts = sum(with_text[x] for x in members)
        for topic in TOPICS:
            praise = sum(counts[(x, topic, "praise")] for x in members)
            complaint = sum(counts[(x, topic, "complaint")] for x in members)
            topic_rows.append({"brand": b, "topic": topic, "reviews_with_text": texts, "praise": praise,
                               "complaints": complaint, "praise_per_100_reviews": share(praise, texts),
                               "complaints_per_100_reviews": share(complaint, texts)})

    months = collections.defaultdict(list)
    for r in reviews:
        months[(r["brand"], r["month"])].append(r["stars"])
    month_rows = [{"brand": b, "month": m, "reviews": len(v), "stars": average(v)}
                  for (b, m), v in sorted(months.items(), key=lambda kv: (brands.index(kv[0][0]), kv[0][1]))]

    out = tracker.ROOT / "exports"
    out.mkdir(exist_ok=True)
    for name, rows in (("review_brands.csv", brand_rows), ("review_branches.csv", shop_rows),
                       ("review_topics.csv", topic_rows), ("review_mentions.csv", mentions),
                       ("review_months.csv", month_rows)):
        tracker.write_csv(out / name, list(rows[0]), (list(row.values()) for row in rows))

    texts = sum(with_text.values())
    print(f"{len(reviews)} reviews of {len(by_shop)} shops in {len(brands)} brands; {texts} have text.")
    print(f"{len(mentions)} praises and complaints found in {len({(m['place_id'], m['review']) for m in mentions})} reviews.")
    print(f"Written to {out}: review_brands.csv, review_branches.csv, review_topics.csv, review_mentions.csv, "
          "review_months.csv")


if __name__ == "__main__":
    main()
