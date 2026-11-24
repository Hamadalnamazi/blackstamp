# Riyadh coffee market project: plan and progress

Goal: understand the Riyadh coffee market well enough to compete in it: who the competitors
are, what customers want, how people move around the shop, and where to open the next branch.

Last updated: 24 Nov 2026

## Steps

| # | Step | Status |
|---|------|--------|
| 1 | Collect all coffee shops in Riyadh (ratings, review counts, popular times), no reviews | DONE 24 Nov: 10,197 shops, cost $61.18 (run `bnDfHVoywfcWH8TF0`) |
| 2 | Check the data (shop count, district coverage, problems) and rank shops to choose competitors | ALMOST DONE 24 Nov: data checked, cleaned and ranked (`python3 analyze.py`). All 8 Black Stamp branches are now in the data (4 were added by a name search). Still open: the owner asked for a double check of specialty coffee shops; waiting for his yes on the cost (about $4 to $6) |
| 3 | Collect one year of reviews for the chosen shops | Waiting for step 2. `competitors.csv` has 50 shops: 8 Black Stamp, 15 Camel Step, 27 single specialty shops. Costs at most $34.96 |
| 4 | Analyse the reviews: what customers praise and complain about | Not started |
| 5 | Best place for a new branch: shop density, demand, gaps by neighbourhood; then add population and rent | Not started |
| 6 | People's behaviour around the owner's shop: popular times of mosques, schools, offices, malls nearby, against the shop's hourly sales | Not started. Needs the shop's name and location, and hourly sales |
| 7 | TikTok: accounts that influence coffee in Riyadh, and competitor activity. X later | Not started |
| 8 | Repeat the Google Maps run monthly to track who grows, closes or opens | Not started. Scheduling not set up |
| 9 | Proposed, not decided: present the results as a dashboard in the browser on the owner's Mac (map, competitors, customer voice, busy hours, branch locations), plus a short Arabic PDF report | Proposed |
| 10 | Idea, not decided: sell this as a service to other coffee owners (branch location reports, monthly competitor reports). Start with the owner's own shop as the sample report. Needs legal advice first (Google's terms, PDPL) | Idea only |

**Step 1 is finished. Current step: 2, the double check of specialty coffee shops (owner to approve the cost). After that: 3 (one year of reviews for the 50 shops in `competitors.csv`).**

## How to do each step

Step 1 is done. The shop list is in `exports/places_latest.csv`. To repeat it next month
(about $61 at today's shop count): `python3 tracker.py run`

Step 2. `python3 analyze.py` rebuilds three files in `exports/` from the latest full run:
`shops_ranked.csv` (every shop with type, brand, specialty mark, neighbourhood), `brands.csv`,
`neighbourhoods.csv`. The competitor list is `competitors.csv` in the project folder: delete rows
you do not want, or copy rows from `shops_ranked.csv` into it (the `place_id` column is the one
that matters).

To add shops the wide run missed, search for them by name. It costs $0.006 per shop found, and
each name is searched on its own. Give the Arabic and the English name:

    python3 tracker.py find "بلاك ستامب" "Black Stamp"

The double check of specialty coffee shops searches for the words these shops use in their names.
`--coffee-only` keeps only places Google lists as coffee shops:

    python3 tracker.py find "قهوة مختصة" "للقهوة المختصة" "محمصة" "specialty coffee" "speciality coffee" "roastery" "roasters" --coffee-only --limit 3000 --max-cost 6

Then run `python3 analyze.py` again.

Step 3. Each command shows the maximum cost and asks before starting. `--top N` takes the
most-reviewed shops, which are the most expensive ones, so use `--file` with a chosen list.
The first run (50 shops, at most $34.96):

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
- The owner's shop is Black Stamp (بلاك ستامب), a specialty roastery with 8 branches, all in
  Riyadh and all in the data: Al Nafal, Al Rayyan, Al Arid, Al Masif, Imam University (two
  branches), King Saud University and Princess Nourah University. The owner compares it to
  Camel Step (خطوة جمل).
- Competitors for the first review run (owner's choice: the best single specialty shops):
  Black Stamp itself (8 branches), Camel Step (15 open branches) and the 27 most-reviewed single
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
- The wide run does not find every shop. Name search on 24 Nov (run `TVNbqTaD6kcfaSS2P`, $0.14,
  24 places, 8 of them new): the wide run had found 4 of the 8 Black Stamp branches and 14 of the
  16 Camel Step coffee shops. The 6 missed coffee shops are all small (8 to 101 reviews). So 10,197
  is a minimum and small shops are under-counted, while shops with many reviews are well covered.
  The data now has 10,205 places, 9,324 of them coffee shops.
- That name search itself did not return 2 shops the wide run already had (Black Stamp Al Arid,
  Camel Step Al Taawun), because both names were searched in one run. `find` now runs one search
  per name. This fix is tested with a simulated Apify only, not with a real run yet.
- Brand grouping is automatic (from names and websites) and is a best guess for small brands.
- Reviews cost $0.0005 each. All shops together have 3.77 million reviews on Google (all years);
  the median shop has 90. The busiest shops have thousands each: the top 50 alone have 372,657,
  so choosing shops by "most reviews" is expensive. How many fall inside one year is not measured
  yet; the first review run will measure it.
- Budget, read from Apify on 24 Nov: $61.49 of the $100 monthly limit is used, so $38.51 is left.
  The limit starts again on 24 Dec 2026.

## Open questions for the owner

- Run the double check of specialty coffee shops now (about $4 to $6, cap $6), after the reviews,
  or not at all? Together with the reviews (at most $34.96) it can pass the $38.51 left this month.
- Is the list in `competitors.csv` right? Which specialty shops are missing from it?
- Which Black Stamp branch should step 6 (people's behaviour around the shop) start with, and can
  the owner share hourly sales for it?
