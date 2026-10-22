# Non-ISU sources of per-Program music (issue #3)

Researched 2026-10-22. Question: which non-ISU sources give the music for a Skater's or Team's Programs per Season, how complete are they for 2004–05 to today across Disciplines and levels, how structured and scrapeable are they, and what do their licences and ToS allow?

## Answer in one paragraph

**Wikipedia is the only non-ISU source worth building on.** Its EN program tables cover nearly every senior entrant back to 2004–05 and most of the top ~12 at Junior Worlds. JA and RU add native-script names and fill some EN gaps. The text is CC BY-SA 4.0, the facts can be reused without attribution, and the API and dumps are allowed for bots. The cost is parsing. The tables come in three wikitext formats (only 47 articles use the structured template), they use rowspans, and the cells are free text. Wikidata holds no music data, but it is a useful CC0 crosswalk from ISU ID to EN/JA/RU article titles. skatingscores.com is off-limits: robots.txt blocks every bot, and it shows no music on the page checked. The Fandom wiki is CC BY-SA, but its ToU bans scrapers and it covers only 9 seasons. Forum threads and blogs (GoldenSkate, Anything GOEs) are unlicensed, cite no sources, and cover the current season only. Most Wikipedia rows cite archived **ISU bio pages** themselves, so ISU bio snapshots are the real upstream for much of the data (possible follow-up, out of scope here).

## Sources compared

| Source | Music per Program? | Coverage | Structure / access | Licence / ToS | Verdict |
|---|---|---|---|---|---|
| EN Wikipedia skater/team articles | Yes, SP/FS/EX (OD/SD/RD/FD for dance), often with composer, performer, choreographer | Seniors ~100%, junior top-12 high, mid-pack junior patchy (see spot checks) | Wikitext via `action=raw` / API, Parsoid HTML via REST, full dumps | Text CC BY-SA 4.0 + GFDL; facts reusable without attribution; bots OK under the User-Agent policy and API etiquette | **Use, as the primary source** |
| JA Wikipedia | Yes, `プログラム使用曲` / `プログラム` tables | Strong for Japanese skaters and stars; fills some EN gaps | Same as EN | Same as EN | **Use** for JA names and gap filling |
| RU Wikipedia | Yes on star pages (`Программы`) | Stars only: Hanyu has a table, Savchenko and Pavlov (UA junior) have none | Same as EN | Same as EN | **Use** for RU names where present |
| Wikidata | **No.** Program articles have no Wikidata item | 4,964 items carry an ISU skater ID (P2694); of these 2,443 have EN, 2,401 JA and 1,126 RU articles | SPARQL, API, dumps | CC0 | **Use as a crosswalk** (ISU ID → EN/JA/RU titles, multilingual labels) |
| skatingscores.com | No music shown on the archived 2025 Worlds men's FS page | n/a | Returns 403 to non-browser clients | robots.txt `User-agent: *` / `Disallow: /`, and names ClaudeBot, GPTBot etc. | **Do not use** |
| figure-skating.fandom.com | Yes. Season pages plus per-Piece pages listing every skater who used it | Only 9 season pages found (2000–01, 2011–12, 2014–15, 2016–17 to 2021–22); 2021–22 is a stub; 2 active users | MediaWiki API answers; `?action=raw` returns 403 | Text CC BY-SA, but Fandom ToU bans "any robot, spider, scraper or other automated means … without our express written permission" | **Don't scrape.** Worth borrowing its Piece-page model |
| GoldenSkate forum "Programs by Discipline" threads | Yes, one thread per season | Announcements for the current season, mostly seniors | Unstructured forum posts | Each poster keeps copyright; the site licence covers only running the site | **Lead-finding only** |
| Anything GOEs blog (`programmusic2526`) | Yes, a per-season table | About 115 senior entries per season; no sources cited | One HTML table | No content licence; ad-supported blog | **Lead-finding only** |
| JA retail and press (Tower Records, Billboard JP compilation CDs) | Partial, Japanese and star skaters | Per season, selected skaters | Articles | Copyrighted | Cross-check only |

The ISU itself (shown for context, not a candidate here): `isu-skating.com` skater profiles show only the **current** Season's music, for example "Short Program: Bring Me To Life by Katherine Jenkins", "Free Skating / Free Dance: Boléro by Maurice Ravel" ([Mako Yamashita](https://isu-skating.com/figure-skating/skaters/mako-yamashita/)). Past Seasons survive only as archived `isufs.org/bios/…` / `isuresults.com/bios/…` snapshots. Those are exactly what Wikipedia rows cite, e.g. `<ref name="ISU-0405">{{cite web |url=http://www.isufs.org/bios/isufs00007498.htm |title=Aliona SAVCHENKO / Robin SZOLKOWY: 2004/2005 …` ([Aljona Savchenko](https://en.wikipedia.org/wiki/Aljona_Savchenko)).

## Coverage spot checks

The method: for each event below, I took the EN Wikipedia results table, followed each ranked skater's link, and checked for a `Programs` section and the Seasons it lists. Script: `coverage.py` (one-off, not committed). Ranks are the official placings.

| Event (level, Discipline, era) | Ranks checked | Has EN article with a program table | No article / redlink |
|---|---|---|---|
| [2005 Worlds](https://en.wikipedia.org/wiki/2005_World_Figure_Skating_Championships) Ladies (senior, women, 2004–05) | 1–24 | **24 / 24** | 0 |
| [2006 Junior Worlds](https://en.wikipedia.org/wiki/2006_World_Junior_Figure_Skating_Championships) Men (junior, early era) | 1–20 | 18 / 20 | Geoffry Varner (9th), Moris Pfeifhofer (14th) |
| [2015 Junior Worlds](https://en.wikipedia.org/wiki/2015_World_Junior_Figure_Skating_Championships) Men (junior, mid era) | 1–24 | 21 / 24 | Zhang He (13th), Niko Ulanovsky (17th), Kevin Shum (20th) |
| [2024 Junior Worlds](https://en.wikipedia.org/wiki/2024_World_Junior_Figure_Skating_Championships) Men (junior, current) | 1–20 | 15 / 20 | 4 redlinks (14th, 15th, 18th, 20th); Tamir Kuperman (19th) has an article but no table |
| 2015 Junior Worlds Pairs | 1–12 teams (24 people) | 16 / 24 people; both partners covered for 7 of 12 teams | Ranks 4 and 5 have no article; rank 9 is fully redlinked; ranks 6 and 11 have one partner redlinked |
| 2006 Junior Worlds Ice dance | 1–15 teams | 11 / 15 teams | Rank 12 has articles but no tables; rank 13 has one article without a table; ranks 14 and 15 have no article |
| 2024 Junior Worlds Ice dance | 1–15 teams | 7 / 15 teams, plus one partner at rank 9 | Ranks 5, 6, 8, 10, 12, 13 and 15 are fully redlinked |

**Caveat.** Junior Worlds entrants are the best juniors. A mid-pack Junior Grand Prix entrant will be covered less, so read these as an **upper bound** for juniors. Junior pairs and junior dance are the weakest, especially for recent Seasons, because articles get written once a team turns senior or medals.

### The four requested spot checks

**Top senior: Yuzuru Hanyu (men, 2004–05 to 2021–22)**
- EN main article: a shortlist only, through the template with `shortlist=yes`. Details live in a separate list article, [List of figure skating programs of Yuzuru Hanyu](https://en.wikipedia.org/wiki/List_of_figure_skating_programs_of_Yuzuru_Hanyu).
- Raw EN: `|SP12="[[Let Me Entertain You (Robbie Williams song)|Let Me Entertain You]]"|FS12=''[[Taiga drama|Heaven and Earth]]'' ({{lang|ja|天と地と}})` ([source](https://en.wikipedia.org/wiki/Yuzuru_Hanyu)).
- JA ([羽生結弦](https://ja.wikipedia.org/wiki/羽生結弦)): `'''「天と地と」- Heaven and Earth'''<br /><small>[[天と地と (NHK大河ドラマ)|天と地と]]<br />[[新・平家物語 (NHK大河ドラマ)|新・平家物語]]<br />（サウンドトラック）<br />作曲：[[冨田勲]]<br />振付：[[シェイ＝リーン・ボーン]]</small>`. It names both source dramas and the composer, which EN omits.
- RU ([Ханю, Юдзуру](https://ru.wikipedia.org/wiki/Ханю,_Юдзуру)): starts at **2004—2005 (novice)**, e.g. `Музыка из фильма «[[Спартак (фильм, 1960)|Спартак]]»<br>{{Small|[[Алекс Норт]]<br>хореография: Сёитиро Цудзуки}}`.

**Current senior: Ilia Malinin.** He uses the structured template with `{{FS program}}` and named fields ([source](https://en.wikipedia.org/wiki/Ilia_Malinin)):
```
|SP5={{FS program|"[[Malagueña (song)|Malagueña]]"|composer=[[Ernesto Lecuona]]|performer=[[Roni Benise|Benise]]|choreographer=[[Shae-Lynn Bourne]]}}
|FS5= {{FS program|''[[Succession (TV series)|Succession]]'':|music1="Andante Agitato - End Credits - "The Raid""|music2="Andante Con Moto - String Orchestra Version"|composer2=[[Nicholas Britell]]|music3= Succession Main Title|…}}
```

**Mid-ranked junior: Hiroaki Sato (JPN, 15th at 2015 Junior Worlds)**
- EN ([source](https://en.wikipedia.org/wiki/Hiroaki_Sato_(figure_skater))): lists 2014–15 and 2017–18 to 2019–20 only, e.g. `* Ghali Alay <br>{{small| by [[Carole Samaha]] }}` and `* Mibugishiden  <br>{{small| by [[Joe Hisaishi]] }}`.
- JA ([佐藤洸彬](https://ja.wikipedia.org/wiki/佐藤洸彬)): also has **2015–16**, `歌劇『[[カルメン (オペラ)|カルメン]]』より` (FS) and `[[ボレロ (ラヴェル)|ボレロ]]` (EX), plus a 2016–17 row. Merging languages adds Seasons.
- A second example, Ivan Pavlov (UKR, 16th) ([source](https://en.wikipedia.org/wiki/Ivan_Pavlov_(figure_skater))): EN covers 2012–13 to 2017–18 in singles but **not** his 2018–19 pairs season. His RU page has no program table.

**Pair: Savchenko / Szolkowy (GER, 2004–05 to 2013–14).** The tables sit on the individual partner's article, under `==== With Szolkowy ====` ([Aljona Savchenko](https://en.wikipedia.org/wiki/Aljona_Savchenko)). They are complete back to 2004–05:
```
! 2004–2005 <br /><ref name=ST050227/><ref name="ISU-0405"/>
* Isolde <br />{{small| by Maurice Luttikkus <br /> performed by Rondo Veneziano <br /> choreo. by Ingo Steuer }}
* [[Casablanca (film)|Casablanca]] <br />{{small| by [[Max Steiner]] <br /> choreo. by Ingo Steuer }}
```
RU [Савченко, Алёна Валентиновна](https://ru.wikipedia.org/wiki/Савченко,_Алёна_Валентиновна) has **no** program table.

**Dance team: Virtue / Moir (CAN, 2003–04 to 2017–18).**
- EN has a **team article**, [Tessa Virtue and Scott Moir](https://en.wikipedia.org/wiki/Tessa_Virtue_and_Scott_Moir). The individual pages pull its table in with `{{Excerpt|Tessa Virtue and Scott Moir|section=Programs|…}}`. Davis/White has the same setup.
- The Wikidata team item [Q134527807](https://www.wikidata.org/wiki/Q134527807) has an EN sitelink only.
- Raw EN, with dance sub-patterns labelled inline:
```
* {{small|Foxtrot:}} [[Dream a Little Dream of Me]] <br>{{small| by [[Ella Fitzgerald]], [[Louis Armstrong]] }}
* [[The Seasons (ballet)|The Seasons]] {{small|<br> Autumn - Adagio <br> by [[Alexander Glazunov]] }}
```
- JA [テッサ・ヴァーチュ](https://ja.wikipedia.org/wiki/テッサ・ヴァーチュ) transliterates titles rather than keeping the original, e.g. `ロング・タイム・ランニング<br /><small>曲：トラジカリー・ヒップ</small>` ("Long Time Running" by The Tragically Hip).

## Structure and scrapeability (Wikipedia)

- **Access.** Raw wikitext via `https://<lang>.wikipedia.org/w/index.php?title=…&action=raw` or the Action API. Rendered tables via the REST/Parsoid HTML endpoint. Bulk via [dumps.wikimedia.org](https://dumps.wikimedia.org/). The [Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) §12 require following the [User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy) and [API:Etiquette](https://www.mediawiki.org/wiki/API:Etiquette). That means a descriptive UA with a project contact address, serial requests, and no "undue burden" (§4).
- **Three table formats coexist on EN.**
  1. `{{Figure skating program list}}` + `{{FS program}}`, with named fields `composer=`, `performer=`, `choreographer=`, `from=`, `music1..n=`. This is the easiest to parse, but only **47 mainspace articles** use it ([embeddedin query](https://en.wikipedia.org/w/api.php?action=query&list=embeddedin&eititle=Template:Figure_skating_program_list&eilimit=max&einamespace=0)); see the [template doc](https://en.wikipedia.org/wiki/Template:Figure_skating_program_list/doc).
  2. A legacy `wikitable` with `! 2004–2005` season header cells, `* Title <br>{{small| by X <br> choreo. by Y}}` bullets and `----` separators between EX programs. This is the large majority.
  3. An accessible `wikitable` with `! scope="row" | 2019–20` (e.g. [Adam Hagara](https://en.wikipedia.org/wiki/Adam_Hagara)).
- **Where tables live.** On the individual article; on a **team article** (EN only, transcluded via `{{Excerpt}}`); on a **separate list article** (Hanyu, "Nathan Chen programs"); or under per-partner subsections (`==== With Szolkowy ====`).
- **Rowspans.** A Program kept for two Seasons is one cell with `rowspan=2`, and the next row's cells shift left. In JA Sato, the 2014–15 row's first cell is the **FS**, because the SP cell spans down from 2015–16. A naive row reader assigns music to the wrong Segment. Parse the rendered HTML with a rowspan-aware table reader instead of splitting wikitext rows.
- **Free text inside cells.** Separators vary by language: EN `by` / `choreo. by` / `arranged by` / `performed by`; JA `曲：`, `作曲：`, `編曲`, `振付：`; RU `хореография:`. Dance cells prefix rhythm labels such as `Samba:`, `Foxtrot:` or `サンバ：`. Medleys appear as several bullets or `music1..n`. Mid-season changes appear as two rows, e.g. "Initial SP:" on Fandom or `span10=2` in the template.
- **Provenance.** Season rows carry `<ref>`s, mostly ISU bio snapshots, otherwise press (NTV, Sanspo, IceNetwork). Each extracted fact can keep its source language, article revision ID and cited ref.

### How raw strings map to the glossary

- `Symphony No. 5 by Ludwig van Beethoven, arranged by David Garrett` ([Pavlov](https://en.wikipedia.org/wiki/Ivan_Pavlov_(figure_skater))) → a **Piece** plus an **Arrangement**.
- `El Tango de Roxanne (from Moulin Rouge!)` → a **Piece** "Roxanne" (itself an arrangement) with the **Source** *Moulin Rouge!*.
- `Malagueña | composer=Ernesto Lecuona | performer=Benise` → a **Piece** plus a recording/performer.
- `Succession: music1 … music6` → one **Program** containing several **Pieces**.
- `Heaven and Earth (天と地と)` → one Piece with EN and JA names, and JA also names a second **Source** (新・平家物語).
- Wikilinks inside cells (`[[Ballade No. 1 (Chopin)|…]]`) give a free, mostly language-independent Piece identity through the linked article's Wikidata item. This is the most useful hook for deduplicating Pieces.

## Licences and ToS, quoted

- **Wikipedia (all languages):** "Creative Commons Attribution-ShareAlike 4.0 International License … and GNU Free Documentation License". Attribution "Through hyperlink (where possible) or URL to the page or pages that you are reusing". "Where you own Sui Generis Database Rights covered by CC BY-SA 4.0, you waive these rights. As an example, this means facts you contribute to the projects may be reused freely without attribution." ([ToU §7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use))
  - **Implication:** music facts (title, composer, Season, Segment) can be extracted into our own database. Linking back to the article is good practice and matches the project's attribution goal. Copied prose, such as program-background text, would be share-alike.
- **Wikidata:** "All structured data … is released into the public domain under Creative Commons Zero" ([Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)).
- **Fandom:** the community's text is CC BY-SA ([siteinfo rightsinfo](https://figure-skating.fandom.com/api.php?action=query&meta=siteinfo&siprop=rightsinfo)), but the [Terms of Use](https://www.fandom.com/terms-of-use) say: "not use any robot, spider, scraper or other automated means to access the Services for any purpose without our express written permission".
- **skatingscores.com:** [robots.txt](https://skatingscores.com/robots.txt) (read via the Wayback Machine because the site returns 403) has `User-agent: *` / `Disallow: /` and lists AI crawlers by name. I checked only the archived [2025 Worlds men's FS page](https://skatingscores.com/2425/wc/sr/men/long/), which shows protocols and judges' marks but no music field. Do not try to work around the block, e.g. through the Wayback Machine.
- **GoldenSkate:** "You retain ownership and copyright of your Content". The site licence is "in connection with operating … the Service" ([terms](https://www.goldenskate.com/forum/help/terms/)). There is no reuse grant for third parties.
- **Anything GOEs:** no licence for the tables; CC BY-SA 3.0 applies only to its photos ([2025/26 list](https://anythinggoe.com/programmusic2526/)).

## Gaps and open points

- I did not measure Junior Grand Prix mid-pack entrants, and did not check senior pairs or dance outside Worlds. Juniors who never turned senior or medalled (e.g. Zhang He, Niko Ulanovsky, the Peal siblings) have no article in any language I checked. Only an ISU source can cover them.
- I did not check fskate.ru or other Russian fan sites, nor Japanese fan wikis, beyond one web search that found no per-skater database.
- Seasons from 2004–05 are covered for skaters active then, but how reliable they are depends on ISU bio snapshots and press of the time.
