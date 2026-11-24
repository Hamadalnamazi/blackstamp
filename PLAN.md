# Riyadh coffee market project: plan and progress

Goal: understand the Riyadh coffee market well enough to compete in it: who the competitors
are, what customers want, how people move around the shop, and where to open the next branch.

Last updated: 24 Nov 2026

## Steps

| # | Step | Status |
|---|------|--------|
| 1 | Collect all coffee shops in Riyadh (ratings, review counts, popular times), no reviews | DONE 24 Nov: 10,197 shops, cost $61.18 (run `bnDfHVoywfcWH8TF0`) |
| 2 | Check the data (shop count, district coverage, problems) and rank shops to choose competitors | REOPENED 24 Nov: data checked, cleaned and ranked (`python3 analyze.py`), but the owner's own shop is incomplete: Black Stamp has 8 branches and the data has 4. Find the missing branches by name before step 3 |
| 3 | Collect one year of reviews for the chosen shops | Waiting for step 2. `competitors.csv` has 44 shops (at most $34.82) and still needs the missing Black Stamp branches |
| 4 | Analyse the reviews: what customers praise and complain about | Not started |
| 5 | Best place for a new branch: shop density, demand, gaps by neighbourhood; then add population and rent | Not started |
| 6 | People's behaviour around the owner's shop: popular times of mosques, schools, offices, malls nearby, against the shop's hourly sales | Not started. Needs the shop's name and location, and hourly sales |
| 7 | TikTok: accounts that influence coffee in Riyadh, and competitor activity. X later | Not started |
| 8 | Repeat the Google Maps run monthly to track who grows, closes or opens | Not started. Scheduling not set up |
| 9 | Proposed, not decided: present the results as a dashboard in the browser on the owner's Mac (map, competitors, customer voice, busy hours, branch locations), plus a short Arabic PDF report | Proposed |
| 10 | Idea, not decided: sell this as a service to other coffee owners (branch location reports, monthly competitor reports). Start with the owner's own shop as the sample report. Needs legal advice first (Google's terms, PDPL) | Idea only |

**Step 1 is finished. Current step: 2, find the missing Black Stamp branches by name (at most $0.24). After that: 3 (one year of reviews for the shops in `competitors.csv`).**

## How to do each step

Step 1 is done. The shop list is in `exports/places_latest.csv`. To repeat it next month
(about $61 at today's shop count): `python3 tracker.py run`

Step 2. `python3 analyze.py` rebuilds three files in `exports/` from the latest full run:
`shops_ranked.csv` (every shop with type, brand, specialty mark, neighbourhood), `brands.csv`,
`neighbourhoods.csv`. The competitor list is `competitors.csv` in the project folder: delete rows
you do not want, or copy rows from `shops_ranked.csv` into it (the `place_id` column is the one
that matters).

To add shops the wide run missed, search for them by name. It costs $0.006 per shop found:

    python3 tracker.py find "بلاك ستامب" "Black Stamp"

Then run `python3 analyze.py` again.

Step 3. Each command shows the maximum cost and asks before starting. `--top N` takes the
most-reviewed shops, which are the most expensive ones, so use `--file` with a chosen list.
The first run (44 shops, at most $34.82, fits the money left this month):

    python3 tracker.py reviews --file competitors.csv --max-cost 38

Other forms:

    python3 tracker.py reviews --top 300
    python3 tracker.py reviews --all

If a run stops at the cost cap: `python3 tracker.py continue`

## Decisions made

- Tool: Apify "Google Maps Scraper", Starter plan. Starter allows at most $100 of usage per month.
- Area: Riyadh only, as a rectangle in `config.json` (lat 24.40 to 25.05, lng 46.45 to 47.05).
- Language of results: Arabic.
- Reviewer names are collected (personal data under Saudi PDPL; the owner's responsibility).
- Reviews are off for the whole-city run. A year of reviews is collected only for chosen shops,
  because a year for every shop does not fit the $100 limit.
- Delivery app prices: later, not now.
- The owner's shop is Black Stamp (بلاك ستامب), a specialty roastery. The owner says it has 8
  branches. The data has 4: Al Nafal, Al Rayyan, Al Arid and Imam University. The owner compares it
  to Camel Step (خطوة جمل).
- Competitors for the first review run (owner's choice: the best single specialty shops):
  Black Stamp itself (4 branches), Camel Step (13 open branches) and the 27 most-reviewed single
  specialty shops rated 4.3 or higher. "Specialty" means Google lists the shop as a roastery or
  its name says specialty or roastery, so specialty shops that do not say it in their name are
  missed and must be added by hand.
- Second review run, once the real cost per shop is known: specialty brands with several branches
  (Woods, Hajeen, Breehant, IDMI, Shuffle and similar).

## Measured so far

- Test run, 24 Nov: 20 shops, cost $0.12.
- Full run, 24 Nov: 10,197 shops, cost $61.18, which is $0.006 per shop without reviews.
  All shops are inside the search rectangle. 508 are marked temporarily closed, none permanently.
  About 500 have no rating yet. Popular times were available for 6,283 shops (62%).
- Step 2 check: 9,318 are coffee shops; 879 are not (338 bakery, dessert or tea; 541 other such
  as restaurants, petrol stations, shisha cafes). 5,479 coffee shops are single shops and 3,839 are
  branches of 669 brands. Largest brands by branches: Dunkin 327, Coffee Address 188, Starbucks 179,
  Barn's 158, Mezaj Maghribi 103. Neighbourhoods with the most coffee shops: Tuwaiq 341, Al Olaya
  322, Dhahrat Laban 279, Al Rimal 236. Median rating 4.4.
- The wide run does not find every shop. Two Black Stamp branches that are on Google Maps inside
  the search area are not in the data: one at King Saud University (about 36 reviews) and one at
  Princess Nourah University (about 8 reviews). Both are small branches inside a campus. So 10,197
  is a minimum, and small shops are under-counted; by how much is not measured yet. Shops that
  matter must be added by name with `python3 tracker.py find`.
- Brand grouping is automatic (from names and websites) and is a best guess for small brands.
- Reviews cost $0.0005 each. All shops together have 3.77 million reviews on Google (all years);
  the median shop has 90. The busiest shops have thousands each: the top 50 alone have 372,657,
  so choosing shops by "most reviews" is expensive. How many fall inside one year is not measured
  yet; the first review run will measure it.
- Budget, read from Apify on 24 Nov: $61.34 of the $100 monthly limit is used, so $38.66 is left.
  The limit starts again on 24 Dec 2026.

## Open questions for the owner

- Where are the 8 Black Stamp branches (neighbourhood or place)? Are all 8 in Riyadh and open?
- Is the list in `competitors.csv` right? Which specialty shops are missing from it?
- Which Black Stamp branch should step 6 (people's behaviour around the shop) start with, and can
  the owner share hourly sales for it?
