# Riyadh coffee market project: plan and progress

Goal: understand the Riyadh coffee market well enough to compete in it: who the competitors
are, what customers want, how people move around the shop, and where to open the next branch.

Last updated: 25 Nov 2026

## Steps

| # | Step | Status |
|---|------|--------|
| 1 | Collect all coffee shops in Riyadh (ratings, review counts, popular times), no reviews | DONE 24 Nov: 10,197 shops, cost $61.18 (run `bnDfHVoywfcWH8TF0`) |
| 2 | Check the data (shop count, district coverage, problems) and rank shops to choose competitors | DONE 25 Nov: data checked, cleaned and ranked (`python3 analyze.py`). Places that are not coffee are removed, which leaves 7,654 coffee shops (shisha cafes found by their review words were removed on 25 Nov), and every shop has its real neighbourhood. The double check of specialty coffee shops ran on 25 Nov: 527 shops found, 23 of them new, cost $4.13. Dunkin, Starbucks and the other big chains are kept as coffee shops. Specialty cafes that do not say specialty or roastery in their name are counted since 25 Nov, from their own description on Google and the words in their reviews (cost $0): 1,798 specialty shops instead of 720 |
| 3 | Collect one year of reviews for the chosen shops | DONE 25 Nov: 128 shops (19 competitor brands and Black Stamp), 36,583 reviews from the last year, cost $18.94. Run 1 `35BGGfy1Kiy5kavE6`: 31 shops, 11,812 reviews, $6.06. Run 2 `HM5BKT70eOadGHGn3`: 97 shops, 24,771 reviews, $12.88 |
| 4 | Analyse the reviews: what customers praise and complain about | DONE 25 Nov: 36,588 reviews of 126 shops analysed (`python3 analyze_reviews.py`), Black Stamp against 19 brands, and every low Black Stamp review read. Cost $0 |
| 5 | Best place for a new branch: shop density, demand, gaps by neighbourhood; then add population and rent | DONE 25 Nov, as far as free open data goes: map of specialty shops and roasteries, crowded neighbourhoods, and a shortlist of neighbourhoods with people, income, homes and offices rented, home rent and land price. Cost $0. Updated 25 Nov with the wider count of specialty shops: the shortlist has 24 neighbourhoods (13 before). To study first: Al Olaya, Al Yasmeen and Al Malqa (clear gaps), Al Muhammadiyah (smaller gap), and three that sit on the line, Hittin, Al Yarmuk and West Umm Al Hamam. Hittin has 51 specialty shops against 57 usual, which is close to normal; before the wider count it looked like 13 against 22. Not in any open source: shop rent per neighbourhood (the owner's quotes are needed), parking, the exact street |
| 6 | People's behaviour around the owner's shop: popular times of mosques, schools, offices, malls nearby, against the shop's hourly sales | DONE 25 Nov, as far as Google's data goes. First part, cost $0: the busy hours of Al Nafal and Al Rayyan against the coffee shops within 2 km and the competitor branches. Second part, cost $1.16 (run `TsAiAHAsGrRMiGG35`): 232 mosques, schools, companies and malls within 1.5 km of the Al Rayyan branch, compared with the branch's busy hours (`python3 analyze_hours.py`). Google's busy hours stand in for sales (owner's decision). Limits: Google shows no busy hours for any school or office there, and for only 10 of 62 mosques; Al Nafal was not collected |
| 7 | TikTok: accounts that influence coffee in Riyadh, and competitor activity. X later | Not started |
| 8 | Repeat the Google Maps run monthly to track who grows, closes or opens | Not started. Scheduling not set up |
| 9 | Proposed, not decided: present the results as a dashboard in the browser on the owner's Mac (map, competitors, customer voice, busy hours, branch locations), plus a short Arabic PDF report | Proposed |
| 10 | Idea, not decided: sell this as a service to other coffee owners (branch location reports, monthly competitor reports). Start with the owner's own shop as the sample report. Needs legal advice first (Google's terms, PDPL) | Idea only |

**Steps 1 to 6 are finished. Next step: 7 (TikTok: accounts that influence coffee in Riyadh, and competitor activity). It is not started; it uses Apify money, and the cost will be stated before any run. $14.28 is left this month; the limit starts again on 24 Dec 2026.**

## How to do each step

Step 1 is done. The shop list is in `exports/places_latest.csv`. To repeat it next month
(about $61 at today's shop count): `python3 tracker.py run`

Step 2. `python3 analyze.py` rebuilds three files in `exports/` from the latest full run:
`shops_ranked.csv` (every shop with type, brand, specialty mark, neighbourhood; the column
`specialty_sign` says why a shop is marked as specialty), `brands.csv`,
`neighbourhoods.csv` (also used for step 5: specialty shops, the usual number, and the room left
in each neighbourhood). The competitor list is `competitors.csv` in the project folder: delete rows
you do not want, or copy rows from `shops_ranked.csv` into it (the `place_id` column is the one
that matters).

To add shops the wide run missed, search for them by name. It costs $0.006 per shop found
($0.007 with `--coffee-only`), and each name is searched on its own. Give the Arabic and the
English name:

    python3 tracker.py find "بلاك ستامب" "Black Stamp"

The double check of specialty coffee shops searches for the words these shops use in their names.
`--coffee-only` keeps only places Google lists as coffee shops. It was run on 25 Nov ($4.13, 25
minutes), so run it again only together with a new monthly run:

    python3 tracker.py find "قهوة مختصة" "للقهوة المختصة" "محمصة" "specialty coffee" "speciality coffee" "roastery" "roasters" --coffee-only --limit 3000 --max-cost 6

Then run `python3 analyze.py` again.

Step 3. Each command shows the maximum cost and asks before starting. `--top N` takes the
most-reviewed shops, which are the most expensive ones, so use `--file` with a chosen list.
`competitors.csv` is the full competitor list (128 shops). Each run has its own file, so no
shop is paid for twice. Run 1 (`reviews_run1.csv`, 31 shops) and run 2 (`reviews_run2.csv`, 97
shops) are both done, so do not run them again. For new shops, make a new file with the same
columns and give a cap that fits the month's money:

    python3 tracker.py reviews --file NEW_FILE.csv --max-cost 10

Other forms:

    python3 tracker.py reviews --top 300
    python3 tracker.py reviews --all

If a run stops at the cost cap: `python3 tracker.py continue`

Step 4. `python3 analyze_reviews.py` is free and rebuilds five files in `exports/` from the collected
reviews of the shops in `competitors.csv`: `review_brands.csv` (stars, scores, replies, spend per
brand), `review_branches.csv` (the same per shop), `review_topics.csv` (praise and complaints per brand
and topic), `review_mentions.csv` (every praise or complaint found, with its sentence, to read) and
`review_months.csv`. Run it again after new reviews are collected.

Step 5. `python3 analyze.py` also writes the step 5 numbers into `exports/neighbourhoods.csv`. The
columns after `busiest_specialty_shop` are copied from `riyadh_neighbourhood_data.csv` in the project
folder (one row per neighbourhood, 197 rows). That file was built once, on 25 Nov 2026, with a
temporary script that is not kept in the project, from these free sources:

- `people_older_count`, `saudi_percent_older`, `monthly_income_older_sar`: the Nine Tenths district map
  (map.910ths.sa), collected in November 2020 by the GitHub project alioh/Saudi-Districts-Dataset
  (file `riyadh_districts.csv`). The year of the count is not stated; its total for Riyadh is 6.0
  million, which fits about 2015.
- `people_2025_model`: WorldPop 2025 population map at 100 metres (R2025A v1, constrained, DOI
  10.5258/SOTON/WP00839), summed inside each neighbourhood border. It is a model, not a count.
- `homes_rented_last_year`, `shops_rented_last_year`, `offices_rented_last_year`,
  `showrooms_rented_last_year`, `apartment_rent_*`, `villa_rent_sar_per_year`: Real Estate General
  Authority (REGA) rental indicators from Ejar contracts, the four quarters from April 2025 to March
  2026, read from the GitHub copy civillizard/Saudi-Real-Estate-Data (`rega/quarterlies/rental/`).
  Apartment rent is shown when there were 20 or more contracts.
- `commercial_land_*`, `residential_land_*`: REGA sales indicators from Ministry of Justice deeds,
  October 2024 to September 2025 (`rega/quarterlies/sales/`). Price is total value divided by total
  area, shown for commercial land when there were 5 or more sales.

To refresh these numbers next year, the file has to be built again from the newer REGA quarters.

Step 6. `python3 analyze_hours.py` is free. Run `python3 analyze.py` first. It writes
`exports/busy_hours.csv`: for each Black Stamp branch that has busy hours on Google, every day and
hour with the branch next to the coffee shops within 2 km, the specialty shops among them, and the
competitor branches. Google shows busy hours as a percentage of each shop's own busiest hour, so
they say when a shop is busy, not how many customers it has. The file turns each shop's week into
shares that add up to 100, so the shape of the week can be compared between shops.

The places around a branch (mosques, schools, companies, malls) are collected with a paid run. It
costs $0.005 per place, at most $2.00 for the four searches, and it stops at $2.50. Al Rayyan was
collected on 25 Nov ($1.16), so do not run it again. For another branch, give the branch's map
point (latitude, then longitude; they are in `exports/shops_ranked.csv`). For Al Nafal:

    python3 tracker.py around 24.781728 46.6837225

Then run `python3 analyze_hours.py` again. It adds two files for every branch that has places
collected within 1.5 km: `exports/busy_hours_around.csv` (every day and hour: the branch next to
the average mosque, company or shop, and mall) and `exports/places_around.csv` (the places
themselves, with the distance from the branch and each place's busiest time).

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
- Competitors (owner's decision 24 Nov, replaces the earlier list of single shops): a competitor
  must be a specialty coffee brand with branches. Single shops are not competitors.
- Camel Step is the owner's example of a competitor, not the only one: competitors are the
  brands that are like it. In the data, "like Camel Step" means all three of: (1) Google lists
  the branches as a coffee roastery, in any category, or the name says roastery; (2) the brand
  has its own website; (3) it has 3 to 30 branches, so it is neither a single shop nor a mass
  chain. Shuffle is included without a website on Google because it is clearly a roastery with
  branches.
- Added to the competitor list on 25 Nov (owner's decision), so it now has 19 brands and 128
  shops. Three more roastery brands that pass the three tests: Filter (3 branches), Najd (4; the
  Qurtubah branch is named "محمصة نجد" and has no website, so it is a likely match, not a sure
  one), Roasting House (3; its warehouse is left out). Three brands that say "specialty" in their
  name but not "roastery": Ratio (10), Sama (9), Canto (3). Two more listings of brands already on
  the list: Flame's second King Saud University branch, and "Shovel Al Ban", a second Google
  listing 10 metres from Shuffle's Al Quds branch. Not added: "Flame" in Al Rimayah (inside King
  Abdulaziz Medical City; nothing links it to the Flame brand).
- The competitor list before those additions (13 brands, Riyadh branches only): Camel Step (15
  branches: 14 open and 1 that Google marks permanently closed), Woods (4), Hajeen (8),
  Elixir Bunn (6), Breehant (3), IDMI (5), Shuffle (21), Coyard (7), Knoll (3), Flame (4),
  Hai (3), Temper (3), 12 Cups (4). Black Stamp's own 8 branches are in the file too, for
  comparison.
- Left out although they pass the three tests, because their names suggest another kind of
  business: Ashjar Cafe, Mothhelah, Aal Al-Kaif, By The Way, NoSound. The owner can add them.
- Reviews are collected in two runs (24 Nov). Run 1: Black Stamp, Camel Step and Hajeen (at
  most $17.13), which also measures the real cost of a year of reviews. Run 2: as many of the
  other brands as the money left allows; the rest after the limit resets on 24 Dec.
- Camel Step also has 9 branches outside Riyadh (Jeddah, Abha, Makkah, Al Khobar, Hail, AlUla,
  Madinah, Dubai). They are not collected: the project is Riyadh only.
- Order of spending (24 Nov): the reviews run comes first. The double check of specialty coffee
  shops runs after it, and only if enough of the month's money is left.
- What counts as a coffee shop (owner's request 25 Nov: remove what is not coffee). Google's main
  category must be cafe or coffee, and the place is removed when its name or another Google
  category says tea, lounge, diwaniya, shisha, restaurant, buffet, bakery, juice or similar,
  unless the name also says coffee (for lounges: unless it says specialty or roastery). Google
  has no mark for shisha, so since 25 Nov (owner's decision) a cafe is also removed as a shisha
  cafe when shisha (شيشة, معسل, أرجيلة) is among the words Google shows as most used in its
  reviews, unless its name says specialty or roastery. Shisha cafes with few reviews have no such
  words and are still counted.
- What counts as a specialty shop on the map: the shop's name or Google category says roastery,
  or its name says specialty, or its brand is in `competitors.csv`. Chains with more than 30
  branches (Barn's, Tim Hortons, Wooden) are not counted although Google lists them as
  roasteries, and neither are traditional roasters that sell beans, nuts and spices.
- Added to that on 25 Nov (owner's request: count the specialty cafes that do not say it in their
  name). Two weaker signs also mark a shop as specialty: (1) its own description on Google says
  specialty coffee (قهوة مختصة); (2) the words Google shows as most used in its reviews include the
  crop (محصول), V60, drip coffee or specialty coffee. A shop with shisha among its review words is
  not marked by these two signs. As before, a brand is specialty when at least half of its
  branches show a sign, and chains with more than 30 branches are left out. The words are in
  `analyze.py` (`SPECIALTY_DESCRIPTION`, `SPECIALTY_REVIEW_WORDS`).
- The large brands the wider count added (Caribou, Shqaf, Nevana, Drip, Parole, Peet's, Ara,
  Saheel, Hall, Recaf, Coffee Window): the owner does not know whether they are specialty (25
  Nov), so they stay counted, because they call themselves specialty.
- A shop's neighbourhood is the one whose border contains its map point. The borders are in
  `riyadh_districts.json` (Saudi national address map, from the GitHub project
  homaily/Saudi-Arabia-Regions-Cities-and-Districts, licence GPL-2.0; check the licence before
  selling anything built on it, step 10).
- How "crowded" is measured (step 5). Riyadh has one specialty shop for every 1,491 Google
  reviews of its coffee shops (with the wider count and without shisha cafes, 25 Nov; it was 3,888
  with the narrow count and 4,011 before the double check). A neighbourhood's coffee reviews
  divided by 1,491 is its usual number of specialty shops. The line of 5 shops above or below
  usual is kept, but it is an easier line to cross now that the count is 2.5 times larger, so read
  the gap against the usual number too (Al Olaya has 61 against 93 usual; Hittin 51 against 57).
  A neighbourhood that passes by less than one shop can fall on either side when the data changes
  a little: Hittin was off the list before the shisha cafes were removed and on it after. High crowded: 5 or more above usual. Low crowded: 5 or more below.
- Step 5 uses free open data only, and no single score: the numbers are shown side by side with a
  reading in words, because each source has a different weakness. Credit the sources when the
  results are shown to others: Nine Tenths and the Saudi Districts Dataset authors, WorldPop, and
  REGA (KSA Open Data Licence). Check these licences again before selling anything (step 10).
- Step 5 groups (25 Nov). Study first: low crowded, 4 km or more from every Black Stamp street
  branch, and at least one competitor branch there got more than the Riyadh average of 297 reviews
  last year. Close to a branch: less than 3 km from a street branch. Possible: the rest.
- Distance to "your nearest street branch" leaves out the university branches (King Saud, Imam,
  Princess Nourah), because they serve the campus. The street branches are Al Nafal, Al Rayyan, Al
  Arid and Al Masif. `km_to_my_nearest_branch` still counts all eight.
- Not done without the owner's approval: collecting "shop for rent" adverts from property websites
  (Aqar and similar) to estimate shop rent per neighbourhood.
- How praise and complaints are found (step 4): by word rules in `analyze_reviews.py`, not by a
  person or an AI model. A sentence that names a topic (coffee taste, staff, waiting, price, desserts,
  place, crowd, noise, cleanliness, parking, wrong order, cup size, drive-through, closed) counts as
  praise or a complaint by the words next to it. In a check of 100 found sentences, about 9 of 10
  were right. Numbers are per 100 written reviews. Black Stamp's own problems were counted by reading
  all 95 of its written reviews with 1 to 3 stars.
- Ratio, Sama and Canto stay in the analysis and are shown as a separate group until the owner says
  whether they are competitors.
- Step 6 (owner's decisions, 25 Nov). The places around a branch are collected for Al Rayyan
  only, with at most $2.50. The owner does not share hourly sales: Google's busy hours of the
  branch are used in their place. So step 6 shows when the branch is busy, not how much it sells.
- The project is saved on GitHub as the private repo `Hamadalnamazi/blackstamp`. The Apify key
  and the collected data are not uploaded.

## Measured so far

- Test run, 24 Nov: 20 shops, cost $0.12.
- Full run, 24 Nov: 10,197 shops, cost $61.18, which is $0.006 per shop without reviews.
  All shops are inside the search rectangle. 508 are marked temporarily closed, none permanently.
  About 500 have no rating yet. Popular times were available for 6,283 shops (62%).
- Step 2 check, after the stricter cleaning of 25 Nov: of 10,205 places, 7,867 are coffee shops.
  2,338 are not: 877 tea shops, 514 lounges, diwaniyas and shisha cafes, 404 bakery, dessert, juice
  or food places, 543 other. 4,355 coffee shops are single shops and 3,512 are branches of 564
  brands. Largest brands by branches: Dunkin 326, Coffee Address 188, Starbucks 179, Barn's 158,
  Mezaj Maghribi 103. Neighbourhoods with the most coffee shops: Tuwaiq 287, Al Olaya 249,
  Dhahrat Laban 221, Hittin 179. Median rating 4.4. (Before this cleaning the count was 9,324.)
- The wide run does not find every shop. Name search on 24 Nov (run `TVNbqTaD6kcfaSS2P`, $0.14,
  24 places, 8 of them new): the wide run had found 4 of the 8 Black Stamp branches and 14 of the
  16 Camel Step coffee shops. The 6 missed coffee shops are all small (8 to 101 reviews). So 10,197
  is a minimum and small shops are under-counted, while shops with many reviews are well covered.
  The data now has 10,205 places.
- That name search itself did not return 2 shops the wide run already had (Black Stamp Al Arid,
  Camel Step Al Taawun), because both names were searched in one run. `find` now runs one search
  per name. This fix worked in the real run of 25 Nov (seven names, seven runs).
- Double check of specialty coffee shops, 25 Nov (runs `lfT9Ox6XHQ8tW3xgS`, `EkZEXxrmNv3GJwxok`,
  `sJwmFTOJccSWPiDAz`, `wkupqoNxSvm1WcTZw`, `BCntmAaQbgQQa3Ktn`, `W9rjjYzgdXy8H5dnQ`,
  `hkLiF5qz7CMjXJJRr`): seven name searches, 25 minutes, $4.13, which is $0.007 per shop because
  `--coffee-only` adds a second filter charge. 527 different shops found: 504 were already in the
  data and 23 are new (22 coffee shops and one nut shop). The data now has 10,228 places and 7,889
  coffee shops: 4,367 single shops and 3,522 branches of brands. Specialty shops: 720 (347
  roasteries and 373 that say specialty in their name), up from 697.
- How complete the specialty list is, from the same check. The wide run had 504 of the 527 shops
  the name searches returned (96%). The name searches returned 488 of the 506 coffee shops already
  known with those words in their name (96%), so each method misses about 4%. Most missed shops
  are small (middle value 10 reviews), but not all: the wide run had missed a Breehant branch with
  1,316 reviews, and the name searches did not return Fuji Cafe with 1,244. A few shops are likely
  still missing. Shops without specialty or roastery in their name cannot be found this way.
- Two branches of competitor brands were found by the double check and are not in
  `competitors.csv`, so their reviews are not collected: Breehant in Al Salam (1,316 reviews, its
  second largest branch) and Shuffle in Al Nahdah (540 reviews).
- What the double check changes in step 5: the shortlist of 13 neighbourhoods is the same. West
  Naseem is now high crowded (13 high crowded neighbourhoods). Hittin and Al Taawun each have one
  more specialty shop (13 and 8).
- Wider count of specialty shops, 25 Nov, cost $0. The runs had already collected two texts per
  shop that were not saved in the database: the shop's own description on Google (4,061 of the
  7,889 coffee shops have one) and the words Google shows as most used in its reviews (5,697 have
  them). They are now saved in the table `place_texts`, and every new run saves them too. The old
  runs were filled in once from the files in `data/raw/` with a temporary script.
- Result of the wider count: 1,801 specialty coffee shops (362 roasteries and 1,439 specialty),
  which is 23% of coffee shops; it was 720. Why they are marked: name 583, Google category 92,
  competitor list 4, own description 633, review words 349, brand 140. The 1,081 added shops are
  626 single shops and 455 branches of brands. No shop lost its mark.
- How good the two new signs are. Tested on the 664 shops already known as specialty that have a
  description or review words: the new signs alone find 73% of them (103 of 124 on the competitor
  list). Read by eye, about 95 of the added shops: roughly 85 to 90 in 100 look right. The
  description is the shop's own claim, like its name, and some ordinary cafes, dessert shops and
  kiosks use the word. 1,795 coffee shops, mostly small, have neither text, so specialty shops
  among them are still missed. The limit is smaller, not gone.
- Largest brands added by the wider count, for the owner to check: Caribou (17 branches), Shqaf
  (14), Nevana (13), Drip (10), Parole (9), Peet's (8), Ara (8), Saheel (8), Hall (7), Recaf (7),
  Coffee Window (7).
- What the wider count changes in step 5 (same rules). High crowded: 22 neighbourhoods (13
  before); new ones include Al Rimal, Middle Oraija, Al Janadriyah, Ishbiliyah, Badr, Al Hamra and
  Al Nuzha. Low crowded without a Black Stamp branch: 24 (13 before). Study first (6): Al Olaya
  (61 specialty shops against 99 usual), Al Yasmeen (30 against 49), Al Malqa (44 against 59), Al
  Muhammadiyah (31 against 38), Al Yarmuk (18 against 24) and West Umm Al Hamam (8 against 13);
  the last two pass the line of 5 narrowly. Close to a branch (5): Al Taawun, Ar Rabie, King Fahd,
  Al Nada, Al Manar. Possible (13): Al Mughrazat, Al Sulaimaniyah, Al Nakheel, Al Woroud, Al
  Shohda, North Mathar, Al Ghadeer, Namar, Al Sahafah, Irqah, Assafarat, Al Faisaliyah, Shubra.
  Left the list: Hittin (51 against 56 usual) and Al Muruj (26 against 30).
- The new neighbourhoods to study first, in the same order as the step 5 numbers below (people
  older count and 2025 model in thousands, homes rented, offices rented, apartment rent, commercial
  land per m², km to the nearest street branch). Al Yasmeen 103 and 93, 11,095, 1,101, 50,300,
  21,920, 5.8 km; it has 6 competitor branches that got 703 reviews each last year on average,
  and Breehant's largest branch. Al Yarmuk 77 and 72, 19,021, 511, 29,300, 6,810, 10.4 km. West
  Umm Al Hamam 38 and 31, 6,014, 141, 25,900, 9,760, 8.3 km.
- Shisha, seen in the same data: 236 coffee shops have shisha among their review words and were
  still counted as coffee shops, because nothing in their name or Google category says it.
- Shisha cafes removed, 25 Nov (owner's decision), cost $0. 235 of those 236 are now counted as
  lounges and shisha cafes (one stays because its name says specialty), with 115,809 reviews
  between them. None is on the competitor list. Most were in Al Olaya (20) and Al Woroud (19).
  This replaces the counts above: of 10,228 places, 7,654 are coffee shops (4,167 single shops
  and 3,487 branches of brands). Not coffee: 877 tea shops, 751 lounges, diwaniyas and shisha
  cafes, 402 bakery, dessert or food, 544 other. Specialty shops: 1,798 (360 roasteries and 1,438
  specialty), 23% of coffee shops. Most coffee shops: Tuwaiq 285, Al Olaya 230, Dhahrat Laban 216,
  Hittin 175.
- Step 5 after the shisha cafes were removed (this replaces the lists above). High crowded: 21
  neighbourhoods (Al Hamra left). Low crowded without a Black Stamp branch: 24. Study first (7),
  with specialty shops against the usual number: Al Olaya 61 against 93, Al Yasmeen 30 against
  50, Al Malqa 44 against 60, Al Muhammadiyah 30 against 38, and on the line West Umm Al Hamam 8
  against 14, Al Yarmuk 18 against 24, Hittin 51 against 57. Close to a branch (5): Al Taawun, Ar
  Rabie, King Fahd, Al Nada, Al Manar. Possible (12): Al Nakheel, Al Mughrazat, Al Sulaimaniyah, Al
  Shohda, North Mathar, Al Ghadeer, Al Sahafah, Namar, Irqah, Assafarat, Al Faisaliyah, Shubra.
  Al Woroud left the list (its coffee reviews fell with the shisha cafes) and Hittin came back by
  half a shop; Al Muruj is just under the line (26 against 31).
- Step 6, first part, 25 Nov, cost $0. Share of the week in each part of the week, in this order:
  the branch, the coffee shops within 2 km (83 around Al Nafal, 90 around Al Rayyan), all
  competitor branches.
  Al Nafal: weekdays 9 to 12: 13.5, 8.9, 9.8. Weekdays 12 to 16: 24.1, 13.3, 14.2. Weekdays 16 to
  20: 22.9, 16.6, 16.4. Weekdays 20 to midnight: 15.2, 18.8, 17.7. Friday and Saturday together:
  16.9, 24.8, 24.5. After midnight: 1.0, 11.0, 10.3.
  Al Rayyan: weekdays 6 to 12: 20.4, 14.6, 16.8. Weekdays 12 to 16: 15.5, 12.3, 14.2. Weekdays 20
  to midnight: 22.2, 20.0, 17.7. Friday and Saturday together: 22.6, 25.0, 24.5. After midnight:
  1.1, 10.4, 10.3.
- Step 6, what it shows. Al Nafal is a daytime shop: it is busiest at 4 in the afternoon on
  weekdays, while more than half of the coffee shops around it (58%) are busiest between 8 and 10
  at night. Al Rayyan is an evening shop like its neighbours (busiest at 10 at night), with a stronger
  morning than they have, and Friday afternoon is its busiest time of the week. Both branches open
  at noon on Friday and Saturday and close at midnight (1 at night on Thursday and Friday). The
  shops around them get 13 to 14% of their week in hours when the branch shows nobody: about 10%
  after midnight, 2% on Friday morning and 2.5% on Saturday morning.
- Step 6, limits. These are shares of each shop's own week, not customer counts: a small shop
  and a large shop count the same. Shops open all night raise the after-midnight share. Six
  branches have no busy hours on Google. Sales by hour are needed to turn shares into money.
- Step 6, second part, 25 Nov (run `TsAiAHAsGrRMiGG35`, 10 minutes, $1.16, which is $0.005 per
  place). Four searches within 1.5 km of the Al Rayyan branch found 232 places. Mosques: 62, and
  10 have busy hours. Schools, nurseries and kindergartens: 60, and none has busy hours (30 show
  opening hours: most open between 6 and 7:30 in the morning and close between 1 and 3, Sunday to
  Thursday). "Company" (شركة): 100, the limit of the search; most are houses, residential
  buildings and small shops, only 3 are company offices, and the 14 with busy hours are all shops
  (print shops, building supplies, wholesalers). Malls: 10, all with busy hours: 5 shopping
  centres, 2 supermarkets, a bowling hall, a gift shop and a children's play place. The largest
  are Shopping World (عالم التسوق, 6,361 reviews, 1.2 km), Wi-Fi Bowling (3,785, 0.7 km) and Al
  Fawzan Center (2,205, 1.2 km).
- Step 6, second part, share of the week in this order: the Al Rayyan branch, malls and big stores,
  shops, mosques. Weekdays 6 to 9: 8.6, 2.9, 4.6, 6.1. Weekdays 9 to 12: 11.8, 9.6, 12.3, 6.8.
  Weekdays 12 to 16: 15.5, 11.4, 15.9, 13.9. Weekdays 16 to 20: 18.1, 22.0, 20.2, 21.6. Weekdays 20
  to midnight: 22.2, 20.9, 17.4, 8.3. Friday before noon: 0, 0.9, 1.8, 5.8. Friday from noon: 12.4,
  10.6, 8.9, 10.8. After midnight: 1.1, 7.3, 4.5, 15.6. How closely each week follows the branch's
  week in its open hours (1 is the same shape, 0 is no link): coffee shops within 2 km 0.78, malls
  0.70, shops 0.55, mosques 0.14.
- Step 6, second part, what it shows.
  (1) Evening prayers. On weekdays the mosques are fullest from 5 to 8 in the evening (18% of
  their week) and empty quickly after 8. The branch does the opposite: it climbs from 8 and is
  busiest from 9 to 11 at night. Its evening crowd comes after the Isha prayer.
  (2) Weekend nights. From 8 to midnight the branch gets 4.9% and 5.0% of its week on Tuesday and
  Wednesday and 3.7% on Thursday, its weakest night. The malls are the reverse: 4.0% on Tuesday
  and Wednesday, 4.8% on Thursday and 5.2% on Friday, and the three largest are busiest on Friday
  between 8 and 10 at night. On Friday the branch is busiest from 5 to 7 in the evening and falls
  after that, while the malls are at their fullest from 8 to 10.
  (3) Friday prayer. From 10 in the morning to 1 on Friday is the busiest time of the mosques'
  week (6.6% of it, mostly at three Friday mosques 1.4 to 1.5 km away). The branch opens at 12.
  Its first hour is as quiet as noon on a weekday, and it fills slowly towards 5, so no rush after
  the prayer shows in the data.
  (4) Mornings. The branch gets 8.6% of its week on weekdays from 6 to 9, against 6.7% for the
  coffee shops around it and 2.9% for the malls. There are 60 schools and nurseries within 1.5 km
  (8 within 500 metres), which fits parents and staff on the school run, but Google has no school
  busy hours, so this is not proven.
  (5) No office effect can be measured: Google shows busy hours for no office near the branch.
- Step 6, second part, limits. Only 10 of 62 mosques have busy hours, and some of those are rough
  (a flat line all day). A small shop and a large mall count the same in an average. Google's busy
  hours are averages over recent weeks, so prayer times, which move during the year, are blurred
  by about an hour. These are shares of each place's own week, not numbers of people.
- Serdab (سرداب), checked 25 Nov at the owner's request: it is in the data with four listings
  under that name. Al Arid 4.5 stars and 1,344 reviews, Al Narjis 4.6 and 401, Dhahrat Laban 4.3
  and 88, Tuwaiq 4.4 and 50. The Al Arid shop is 0.5 km from Black Stamp's Al Arid branch (110
  reviews). Serdab was found by the first big run but was not marked as specialty until the wider
  count, because its name does not say it. Its reviews are not collected (it is not on the
  competitor list), and the data cannot confirm that all four listings have one owner.
- Dunkin and Starbucks, checked 25 Nov: both are kept as coffee shops. Starbucks 181 listings, all
  kept. Dunkin 327 of 328 kept; the one removed is the Dunkin head office, which Google lists as a
  dessert restaurant. Barn's 161, Coffee Address 183 and Tim Hortons 63 are all kept too. They are
  not counted as specialty shops and are not competitors.
- The project folder is in iCloud Drive, and iCloud removes the local copy of large files it has
  not seen used for a while (the 187 MB database and the files in `exports/`). The first command
  after that waits for the download (2.5 minutes on 25 Nov) and needs internet.
- Brand grouping is automatic (from names and websites) and is a best guess for small brands.
  Known error: the brand shown as "قوبا" with 8 branches is really three different shops (قوبا,
  كابو with 3 branches, فوت with 3 branches) joined by the shared words "محمصة وقهوة مختصة" after
  the "|" in their names. Not fixed yet in `analyze.py`. Check a brand's branches by eye before
  adding it to the competitor list.
- Neighbourhood names from Google are not clean (579 different labels, many of them codes or
  words such as "District"). Fixed on 25 Nov: neighbourhoods now come from the official borders.
  170 neighbourhoods have a coffee shop; 28 coffee shops fall outside every border. Google's label
  agrees with the border for 94% of the shops that have a real label. Dunkin is in 108
  neighbourhoods.
- Reviews run 1, 25 Nov (run `35BGGfy1Kiy5kavE6`): 31 shops, 11,812 reviews from the last year,
  cost $6.06 against a worst case of $17.13. So 35% of these shops' reviews are from the last
  year: Black Stamp 28%, Camel Step 24%, Hajeen 48%. Use 35% to estimate, 50% to be careful.
- Reviews run 2, 25 Nov (run `HM5BKT70eOadGHGn3`): 97 shops, 24,771 reviews from the last year,
  cost $12.88 against a worst case of $49.68. Both runs together: 128 shops, 36,583 reviews,
  $18.94. A competitor branch got 297 reviews in the last year on average.
- Step 5, first version, 25 Nov. 697 coffee shops are specialty: 338 roasteries and 359 that say
  specialty in their name (9% of coffee shops). High crowded neighbourhoods: Al Khaleej, West
  Oraija, East Naseem, Al Nadheem, King Saud University, Tuwaiq, Al Aziziyah, Dhahrat Laban, King
  Faisal, Al Rawdah, Al Mahdiyah, Al Nadwah. Low crowded, without a Black Stamp branch (13): Al
  Olaya, Hittin, Al Muhammadiyah, Al Nakheel, Al Malqa, Al Mughrazat, Al Muruj, Al Taawun, Al
  Ghadeer, Al Manar, Ar Rabie, King Fahd, North Mathar. To study first, because competitor
  branches there got more reviews last year than average: Al Muhammadiyah (1,120 per branch), Al
  Olaya (670), Al Malqa (501), Al Taawun (487; it is 1.8 km from the Al Nafal branch). Weak:
  Hittin (175), Al Nakheel (145; Camel Step closed there), Al Mughrazat (31). The other six have
  no competitor branch to measure. Limits: rent, population and income are not in the data;
  specialty cafes that do not say specialty or roastery are not counted, and there are many in the
  north; coffee reviews are totals for all years.
- Step 5, finished 25 Nov. The 13 shortlisted neighbourhoods, in this order: people living there
  (older count and 2025 model, in thousands), homes rented in a year, offices rented in a year,
  average apartment rent in SAR a year, commercial land in SAR per m² (when 5 or more sales), km to
  the nearest street branch.
  Study first: Al Malqa 61 and 19, 15,763, 1,302, 54,400, 7,400, 8.3 km. Al Olaya 113 and 93, 15,266,
  4,734, 50,200, 13,770, 6.7 km. Hittin 26 and 15, 4,830, 327, 63,900, 14,690, 8.1 km. Al
  Muhammadiyah 17 and 35, 1,526, 612, 51,500, no land price, 4.3 km.
  Possible: Al Nakheel 32 and 50, 3,365, 382, 57,700, 13,540, 5.8 km. Al Mughrazat 18 and 24, 2,465,
  140, 43,300, 4,960, 4.0 km. Al Ghadeer 27 and 34, 2,099, 116, 47,200, no land price, 3.4 km. North
  Mathar 15 and 32, 796, 319, 46,200, no land price, 7.7 km.
  Close to a branch: Al Muruj 41 and 37, 5,896, 626, 38,600, no land price, 2.1 km. Al Taawun 40 and
  33, 4,585, 452, 44,300, no land price, 1.8 km. Al Manar 29 and 35, 2,804, 73, 33,600, 4,470, 2.3 km.
  Ar Rabie 30 and 39, 4,061, 597, 47,900, 13,680, 2.6 km. King Fahd 38 and 39, 2,665, 377, 36,700,
  11,070, 2.2 km.
- Step 5, the middle neighbourhood of Riyadh for comparison: 3,528 homes and 110 offices rented in a
  year, apartment rent 26,700 SAR a year, commercial land 3,850 SAR per m². Al Olaya has the most
  office contracts in the city (4,734, one of every eight). Hittin has the third highest apartment
  rent and Al Nakheel the fourth. Al Malqa is 10th for homes rented and 4th for offices. Monthly
  income (older count): Al Muhammadiyah 12,500 SAR is the highest on the list; the middle
  neighbourhood has 8,100.
- Step 5, shop rent. The official data has no shop rent per neighbourhood (only the number of shop
  contracts). The only official figure is the Riyadh average: 820 SAR per m² a year at the end of
  2024 (722 at the start of 2023), about 30,000 shop contracts a quarter.
- Step 5, the same numbers for the owner's street branches (branch reviews last year, homes rented,
  offices rented, apartment rent): Al Nafal 372, 3,806, 173, 39,900. Al Rayyan 327, 3,633, 248,
  38,300. Al Arid 110, 16,493, 1,329, 43,400. Al Masif 20, 5,997, 383, 34,000. Al Nafal and Al Masif
  are 2.8 km apart.
- Step 5, how much the new numbers explain. Across neighbourhoods, reviews per coffee shop rise
  with apartment rent, land price and income (rank correlation 0.6 to 0.7). But for one branch the
  link is weak: among 123 competitor branches, reviews last year rise a little with offices rented
  nearby (0.38) and not with people (0.04) or income (-0.05). Al Arid shows the same: more homes and
  offices than Al Malqa, and the branch got 110 reviews. So the neighbourhood numbers choose where
  to look, and the street, parking and shop decide the result.
- Step 5, limits of the people numbers. The 2025 model spreads people evenly over built-up land
  (about 8 to 9 thousand per km²), so it is too low for Al Malqa (19 thousand) and Hittin (15
  thousand). The older count is out of date for the fast-growing north.
- Step 4, 25 Nov. Reviews from 25 Nov 2025 to 25 Nov 2026: 36,588 of 126 shops, 25,189 with text.
  Black Stamp: 948 reviews, 4.54 stars, 8th of 20 brands (competitors 4.50; Sama 4.72, Hajeen 4.65,
  Woods 4.62, Camel Step 4.52, Elixir Bunn lowest at 3.98). 8.2% of its reviews have 1 or 2 stars
  (competitors 9.7%).
- Step 4, strengths. Per 100 written reviews, Black Stamp's coffee is praised 53.5 times
  (competitors 39.0; only Najd is higher at 54.0), desserts 14.3 (8.7), the place 28.3 (20.6), staff
  42.7 (43.7). It answers 86.5% of reviews and 88.5% of 1 and 2 star reviews (competitors 40.5% and
  54.5%; Camel Step 0.3%).
- Step 4, weaknesses. Black Stamp gets 118 reviews per branch a year against 302 at competitors
  (Woods 980, Hajeen 896). Al Nafal and Al Rayyan carry 74% of its reviews. Problems in its 95 low
  reviews with text, counted by reading: coffee taste 19 (4 say it is not as good as before), staff
  behaviour 17 (11 at Al Rayyan), waiting for orders 15 (3 name Nuqta app orders), comfort of the
  place 15 (chairs, tables, sockets, air conditioning), food and desserts 16 (5 of them sold out),
  closed when Google says open 6 (Al Arid, Imam University, Al Masif), online store orders 5, price 3.
  Al Rayyan has the most 1 and 2 star reviews of the large branches (11%). Weak months: January
  (4.12), February (4.20), September (4.18).
- Step 4, a limit found in the data. Only 60 of Black Stamp's 948 reviews (6%) carry Google's scores
  for food, service and atmosphere and the spend per person, against 69% at competitors, so those
  numbers are weak for Black Stamp. Likely reason, not proven: its branches have the main Google
  category "coffee roastery" and Hajeen and Woods have "cafe".
- Step 4 changes how to read step 5. Reviews per branch also measure how much staff ask for reviews:
  the share of written reviews that give 5 stars and thank an employee runs from 2.5% (Flame) to
  17.6% (Hajeen). Al Muhammadiyah's 1,120 reviews per competitor branch come mostly from one Hajeen
  branch that opened in December 2025 (1,674 reviews in its first year). Treat it as a strong sign,
  not as proof.
- What the 25 Nov additions change in the competitor list: before, 13 brands, 94 shops, 115,149
  reviews (all years), rating 4.43. With the roastery additions: 16 brands, 106 shops, 119,579
  reviews, rating 4.43. With the specialty brands too: 19 brands, 128 shops, 132,346 reviews,
  rating 4.42. The three specialty brands alone: 22 shops, 12,767 reviews, rating 4.32.
- Reviews cost $0.0005 each. All shops together have 3.77 million reviews on Google (all years);
  the median shop has 90. The busiest shops have thousands each: the top 50 alone have 372,657,
  so choosing shops by "most reviews" is expensive. How many fall inside one year is not measured
  yet; the first review run will measure it.
- Busy hours (Google popular times) already collected in step 1 and not analysed yet, checked 25
  Nov: 99 of the 128 shops in `competitors.csv` have them. Black Stamp: only 2 of 8 branches (Al
  Nafal and Al Rayyan); Google shows none for the other six, which have few reviews. Competitors:
  97 of 120 (Hajeen 8 of 8, Camel Step 11 of 15, Shuffle 12 of 22). So step 6 can use Google busy
  hours for Al Nafal or Al Rayyan only, and a comparison of busy hours with competitors costs $0.
- Budget, read from Apify on 25 Nov after the step 6 run: $85.72 of the $100 monthly limit is
  used, so $14.28 is left. The limit starts again on 24 Dec 2026. (After both review runs it was
  $80.43 used, and after the double check $84.56.)

## Open questions for the owner

- Are Ratio, Sama and Canto real competitors? They are in the review analysis as a separate group.
  If they are not competitors, say so and they will be removed.
- Step 4: should the main Google category of the branches change from "coffee roastery" to "cafe"?
  It is the owner's decision and it can change how the shop appears in Google searches, so test it
  on one branch first.
- Add the two competitor branches the double check found (Breehant Al Salam, Shuffle Al Nahdah)
  to `competitors.csv` and collect their year of reviews? At most $0.94, likely about $0.40.
- Step 5: which of the neighbourhoods to study first (Al Olaya, Al Yasmeen, Al Malqa, Al
  Muhammadiyah, and on the line Hittin, Al Yarmuk and West Umm Al Hamam) does the owner already know to be
  too expensive or unsuitable? Rent quotes for shops there (SAR per m² a year, or per shop) would
  fill the main gap in the data.
- Step 5: collect "shop for rent" adverts for those neighbourhoods from a property website, to
  estimate shop rent? It needs the owner's approval, and any cost will be stated first.
- Serdab has a shop 0.5 km from the Al Arid branch with 12 times its reviews. Should Serdab be
  added to the competitor list and its year of reviews collected? Four shops: at most $0.96,
  likely about $0.40.
- Is "Flame" inside King Abdulaziz Medical City (Al Rimayah) a branch of the Flame roastery?
- Is the list in `competitors.csv` right? Which brands like Camel Step are missing from it, and
  is any brand on it not a real competitor?
- Step 6: Thursday night is the Al Rayyan branch's weakest night, and Friday night falls after 7
  while the malls nearby fill up. Does the branch's own till show the same? The owner can check
  this without sharing the numbers.
- Step 6: collect the same places around Al Nafal, to compare the two branches? At most $2.50,
  likely about $1.20.
