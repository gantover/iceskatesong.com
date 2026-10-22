# How much music data do ISU results carry, 2004–05 to today?

Research for [issue #2](https://github.com/gantover/iceskatesong.com/issues/2). Measured 2026-10-22 against the live ISU result sites and the Internet Archive.

## Answer

- **ISU result documents carry no music at all.** That covers entries, starting orders, results and judges'-details PDFs. In 20 sampled events (4 seasons × 5 event types), 0 have a music-title sheet or any other music document. The only "music" strings in them are scoring labels.
- **The only ISU music source is the Skater/Team bio page** (`/bios/isufsNNNNNNNN.htm`). It holds exactly **one Short Program/Rhythm Dance music field and one Free Skating/Free Dance music field**, labelled "as of season X", and **each new season overwrites them**. ISU keeps no music history.
- **Live bios cover few past Performances.** We sampled 1,939 entries. 93% have a bio listing *some* music, but only **15%** list music for the season they skated. By season: 2004/05 17%, 2011/12 19%, 2017/18 21%, 2023/24 5%. Those hits are mostly skaters whose bio stopped being updated that season, typically because they retired.
- **The Internet Archive (Wayback Machine) recovers past seasons from 2011/12 onwards, as far as we measured.** In a random sample, it returned a bio snapshot with music for the right season for **20/20 entries in each of 2011/12, 2017/18 and 2023/24** (each 20/20 means a true rate of ≥ about 83% at 95% confidence, not 100%). It returned **0/20 for 2004/05**, where no in-season snapshots exist at all. We did not measure 2005/06 to 2010/11. The earliest snapshot we saw was from 2009-07, on one bio, which is a hint only.
- **Implication for phase order:** ISU data alone cannot be the main music source. Archived bio snapshots can seed a per-Skater, per-Season music list from 2011/12 on, at Program granularity, not per Performance. 2004/05 and any mid-season music changes need Submissions or other sources. 2005/06 to 2010/11 is untested and should be assumed to need them too.
- **Terms:** ISU gives no explicit permission to reuse this data. The scraping ban we found sits in ISU's Terms of Service, and those are scoped to its B2B "Business Applications". Pages carry "© ISU. All Rights Reserved", and bios contain personal data. Get written consent from ISU before bulk reuse (see [Terms and scraping](#terms-and-scraping)).

## Method

- **Sample.** We took 4 seasons × 5 event types. "Junior" covers both Junior Worlds and one Junior Grand Prix (JGP) event per season. Each season also has one senior Grand Prix event, Worlds, and Europeans or Four Continents. All four disciplines are included in every event where they were held: men, women/ladies, pairs and ice dance.

  | Season | GP | Worlds | Euros / 4CC | Junior Worlds | JGP |
  |---|---|---|---|---|---|
  | 2004/05 | [GP Final 04/05](http://www.isuresults.com/results/gpf0405/index.htm) | [wc2005](http://www.isuresults.com/results/wc2005/index.htm) | [ec2005](http://www.isuresults.com/results/ec2005/index.htm) | [wjc2005](http://www.isuresults.com/results/wjc2005/index.htm) | [JGP Courchevel 2004](http://www.isuresults.com/results/jgpfra2004/index.htm) |
  | 2011/12 | [Skate America 2011](http://www.isuresults.com/results/gpusa2011/index.htm) | [wc2012](http://www.isuresults.com/results/wc2012/index.htm) | [4CC fc2012](http://www.isuresults.com/results/fc2012/index.htm) | [wjc2012](http://www.isuresults.com/results/wjc2012/index.htm) | [JGP Riga 2011](http://www.isuresults.com/results/jgplat2011/index.htm) |
  | 2017/18 | [Skate America 2017](http://www.isuresults.com/results/season1718/gpusa2017/index.htm) | [wc2018](http://www.isuresults.com/results/season1718/wc2018/index.htm) | [ec2018](http://www.isuresults.com/results/season1718/ec2018/index.htm) | [wjc2018](http://www.isuresults.com/results/season1718/wjc2018/index.htm) | [JGP Riga 2017](http://www.isuresults.com/results/season1718/jgplat2017/index.htm) |
  | 2023/24 | [Skate America 2023](https://results.isu.org/results/season2324/gpusa2023/index.htm) | [wc2024](https://results.isu.org/results/season2324/wc2024/index.htm) | [ec2024](https://results.isu.org/results/season2324/ec2024/index.htm) | [wjc2024](https://results.isu.org/results/season2324/wjc2024/index.htm) | [JGP Gdansk 2023](https://results.isu.org/results/season2324/jgppol2023/index.htm) |

- **Steps.** A Python script did four things:
  1. Fetched every `CATxxxEN.htm` (Entries) page of each event, with a 0.3 s delay between requests.
  2. Took each entry's bio link and fetched all 1,288 unique bios.
  3. Parsed the two music fields and their "as of season" labels.
  4. Deduplicated qualifying-group entry pages. 2004/05 Junior Worlds, for example, lists skaters again under "Qualifying Group A/B".
- **Result:** 1,939 entries (Skater or Team at one event in one discipline).
- **"Music is for this season"** means the bio's SP or FS "as of season" label equals the season of the event.
- **Wayback check.** We drew 20 random entries per season. For each, we queried the [CDX API](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server) for status-200 snapshots of the bio. The query covered both hosts, from August of the season's first year to July of its second. We then fetched up to the 3 latest snapshots and checked for music labelled with the event's season.
- **Documents check.** For every sampled event we did three things:
  - listed the index-page links that are not Entries/Result/Segment pages or score PDFs;
  - grepped the first segment page;
  - grepped one judges'-scores PDF (via `pdftotext`).

## ISU result sources and their structure

**Hosts.** The live hosts are `www.isuresults.com` (http) and `results.isu.org` (https), and they serve the same files. For example, [`isuresults.com/bios/isufs00108049.htm`](http://www.isuresults.com/bios/isufs00108049.htm) and [`results.isu.org/bios/isufs00108049.htm`](https://results.isu.org/bios/isufs00108049.htm) are byte-identical, 23,312 bytes each. Neither host has an index page (`/results/` returns 404) or a `robots.txt` (404 on both).

**Event URLs.**
- up to 2016/17: `/results/<code>/index.htm`, e.g. `gpf0405`, `wc2012`, `jgplat2011`;
- from 2017/18: `/results/season<YYYY>/<code>/index.htm`, e.g. `season1718/wc2018`, `season2324/wc2024`.

Event codes are guessable (`wc`, `ec`, `fc`, `wjc`, `gp<nat><year>`, `jgp<nat><year>`, `gpf`), but nothing lists them. Results were produced by WIGE-DATA in 2004/05 and by Swiss Timing in the 2011/12 and later samples. The page footers say so.

**Event page layout.** Every event index has the same layout. Per Category (discipline × level) it links:

| File | Content | Music? |
|---|---|---|
| `CATnnnEN.htm` | **Entries**: No., Name (linked to bio), Nation | no |
| `CATnnnRS.htm` | Overall result | no |
| `SEGnnn.htm` | Starting order / detailed classification per Segment: rank, name, nation, TSS, TES, PCS components, deductions, start number | no |
| `SEGnnnOF.htm` | Panel of judges | no |
| Judges' scores PDF | Per Skater: executed elements, base value, GOE per judge, PCS per judge, deductions. Named `GPF0405_Men_SP_Scores.pdf` in old events, `FSKMSINGLES-----------FNL-000100--_JudgesDetailsperSkater.pdf` in 2023/24 and later | no |

[Example 2024 Entries page](https://results.isu.org/results/season2425/gpf2024/CAT001EN.htm), [example 2004 Entries page](http://www.isuresults.com/results/gpf0405/CAT001EN.HTM).

**Measured "music" occurrences in result documents.** No sampled event had a link outside the standard set; the only extra was a `/events` back-link at JGP Courchevel 2004.

| Season | Score PDFs: what "music" matches | Segment pages |
|---|---|---|
| 2004/05 | `Music Violation 0.00` deduction label only, e.g. [GPF0405 Men SP](http://www.isuresults.com/results/gpf0405/GPF0405_Men_SP_Scores.pdf) | 0 hits |
| 2011/12 | 0 hits in the sampled PDFs | 0 hits |
| 2017/18 | `Interpretation of the Music/Timing` (a PCS component name) and `Music requirements violation` (a dance deduction), e.g. [wc2018 FD](http://www.isuresults.com/results/season1718/wc2018/wc2018_IceDance_FD_Scores.pdf) | 1 hit each: the legend "Interpretation of the Music" |
| 2023/24 | 0 hits | 0 hits |

None of these hits names a piece of music.

## Where the music is: bio pages

Each Skater (singles) or Team (pairs/dance) has one bio, `https://results.isu.org/bios/isufs<8-digit id>.htm`. Its music block looks like this ([Malinin](https://results.isu.org/bios/isufs00108049.htm), fetched 2026-10-22):

```
Music Short Program as of season 2025/2026
Dies Irae by Náttúra featuring Vila
The Lost Crown by 2WEI, Josnez and Kataem
Music Free Skating / Free Dance as of season 2025/2026
The Ball by Asaf Avidan
The Smell of the Sea by Alan Mayer
Code Duello by Power-Haus, Sergiu-Dan Muresan
```

Retired skaters keep their last season ([Buttle](http://www.isuresults.com/bios/isufs00003253.htm) still shows 2007/2008: "Adios Nonino by Astor Piazzolla" / "Ararat (soundtrack) by Michael Danna").

**Two page layouts.**
- **New (1,160 of the 1,287 live bios):** an HTML table.
- **Old (127):** absolutely positioned `<DIV style="left:..PX;top:..PX">` blocks. In these, source order ≠ visual order: the FS title can appear in the HTML *before* the FS heading. A parser must sort by `top`/`left`. Our first parser did not, and it misassigned SP and FS.

**Coverage per entry.** "Any music" means the bio lists music for some season. "This season" means the music is labelled with the season the entry skated.

| Season | Entries | Bio link | Bio lists any music | **Music for this season** |
|---|---:|---:|---:|---:|
| 2004/05 | 392 | 391 (100%) | 389 (99%) | **67 (17%)** |
| 2011/12 | 508 | 508 (100%) | 483 (95%) | **97 (19%)** |
| 2017/18 | 521 | 521 (100%) | 458 (88%) | **108 (21%)** |
| 2023/24 | 518 | 518 (100%) | 472 (91%) | **28 (5%)** |
| **All** | **1,939** | 1,938 (100%) | 1,802 (93%) | **300 (15%)** |

"Music for this season" by level, discipline and event type:

| Season | Senior | Junior | Men | Women | Pairs | Dance | GP | Worlds | Euros/4CC | JWorlds | JGP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2004/05 | 15% | 21% | 14% | 18% | 17% | 21% | 0% (0/24) | 13% | 22% | 21% | n/a* |
| 2011/12 | 20% | 18% | 17% | 18% | 27% | 18% | 17% | 16% | 30% | 15% | 23% |
| 2017/18 | 25% | 15% | 16% | 20% | 24% | 26% | 28% | 23% | 26% | 9% | 24% |
| 2023/24 | 2% | 9% | 6% | 6% | 5% | 5% | 0% (0/41) | 4% | 2% | 5% | 16% |

\*JGP Courchevel 2004's [Entries pages](http://www.isuresults.com/results/jgpfra2004/CAT001EN.HTM) list 65 entries across 4 disciplines with **no bio links at all**: names are bare `<A>` tags. So there is no ISU ID and no music, and these 65 are excluded from the 1,939. 2004/05 junior figures come from Junior Worlds alone.

**What season the bio's music actually belongs to**, per entry season (top buckets):

- 2004/05 entries → 2005/06 (74), **2004/05 (67)**, 2006/07 (64), 2009/10 (58), 2013/14 (33), …
- 2011/12 entries → 2013/14 (106), **2011/12 (97)**, 2012/13 (69), 2014/15 (51), 2017/18 (48), …
- 2023/24 entries → 2025/26 (206), 2026/27 (194), none (46), 2024/25 (44), **2023/24 (28)**

**Reading.**
- A bio's music matches an event only when the skater's last updated season is that season.
- The GP samples score 0% in 2004/05 (0/24) and 2023/24 (0/41), because those active elite skaters' bios have moved on. The pattern is not uniform: 2017/18 GP scores 28%.
- The music field is per Skater/Team per Season. It is the Program's music, not the Performance's: a mid-season music change is invisible.
- The 2026/27 season is under way (GP started in October). 140 of 1,287 bios already show 2026/27 music, while Malinin's still shows 2025/26. Bio updates lag.

Where the bio lists none: in pairs and ice dance, 19–37% of 2017/18 and 2023/24 entries list no music at all, versus about 0% in men and women.

### Raw strings (as published)

The format is free text, one line per piece. It is mostly `Title by Composer` or `Title performed by Artist`, sometimes `(soundtrack)` or `(from "Film")`. Dance rhythm prefixes look like `Paso Doble: …` and `Rhumba: …`. Composers are misspelled or inconsistent ("A. R. Rhaman", "Petr I. Tchaikovski", "Tomasini Albinoni"). The pieces of a medley are separate lines with no time ranges.

- 2004/05, women ([isufs00004358](http://www.isuresults.com/bios/isufs00004358.htm)): SP `Fire Dance` | FS `Harem by Sarah Brightman`
- 2004/05, ice dance, Keller/Keller ([isufs00004772](http://www.isuresults.com/bios/isufs00004772.htm)): OD `Charleston Foxtrot Quickstep` (rhythms, not pieces) | FD `Bolero (from the Moulin Rouge soundtrack)`
- 2004/05, men, Plushenko ([isufs00000124](https://results.isu.org/bios/isufs00000124.htm), frozen at 2013/14): FS `The Best of Plushenko arranged by Edvin Marton:` / `Criminal St. Petersburg by Igor Korniliuk` / `Godfather by Nino Rota` / `Sheherazade by Nikolai Rimski-Korsakov` / `Tango Amore` / `Tosca by Giacomo Puccini` / `Adagio by Tomasini Albinoni`
- 2011/12, junior men ([isufs00009410](http://www.isuresults.com/bios/isufs00009410.htm)): SP `Zoom by Safri Duo` | FS `Slumdog Millionaire (soundtrack)`
- 2011/12, ice dance (Wayback [20120609112054](http://web.archive.org/web/20120609112054/http://www.isuresults.com/bios/isufs00009177.htm)): SD `Rhumba: Desperados (from "Once Upon a Time in Mexico") / Mambo` | FD `Romeo and Juliet (soundtrack)`
- 2017/18, pairs, Yu/Zhang ([isufs00055106](http://www.isuresults.com/bios/isufs00055106.htm)): SP `Swan Lake by Petr I. Tchaikovski` | FS `Jyn Erso & Hope Suite (from "Rogue One: A Star Wars Story") by Michael Giacchino` / `Princess Leia (from "Star Wars: A New Hope") by John Williams`
- 2017/18, women (Wayback [20180709155528](http://web.archive.org/web/20180709155528/http://www.isuresults.com:80/bios/isufs00034742.htm)): SP `Corazon Espinado (cover) performed by Tania Blanco` / `I Like It Like That performed by The …` | FS `Anna Karenina (soundtrack) by Dario Marianelli`
- 2023/24, men, Uno ([isufs00012455](http://www.isuresults.com/bios/isufs00012455.htm)): SP `I Love You Kung Fu by Son Lux, Ryan Lott, Ian Chang` / `Clair de Lune (Pied: au Piano) by Son Lux, Ryan Lott, Ian Chang` / `I Love You Kung Fu by Son Lux, …` | FS `Timelapse by Mari Samuelsen, Trondheim Soloists, Uno Helmersson` / `Spiegel im Spiegel (Version for Violin and Piano) by Vladimir Spivakov, Sergej Bezrodny, Arvo Pärt`
- 2023/24, junior dance ([isufs00117977](http://www.isuresults.com/bios/isufs00117977.htm)): RD *(empty)* | FD `It's Always Been You by Phil Wickham` / `Your Dazzling Light by Karl Hugo`

Recent strings name recordings and performers, as in Uno's. Older ones name the work, or just the film. Either way, mapping a string to a Piece, Arrangement or Source needs human or fuzzy matching.

## Recovering past seasons: Wayback Machine snapshots of bios

| Entry season | Sampled | Had ≥1 snapshot in season | Snapshot with that season's music | Median snapshots in season |
|---|---:|---:|---:|---:|
| 2004/05 | 20 | 0 | **0 (0%)** | 0 |
| 2011/12 | 20 | 20 | **20 (100%)** | 7 |
| 2017/18 | 20 | 20 | **20 (100%)** | 27 |
| 2023/24 | 20 | 20 | **20 (100%)** | 37.5 |

Each sample of 20 included 7–9 junior entries.

**Where Wayback coverage starts.** The earliest snapshot of Buttle's bio is [2009-07-29](http://web.archive.org/web/20090729090409/http://www.isuresults.com:80/bios/isufs00003253.htm). We did not measure 2005/06 to 2010/11. Wayback coverage of bios likely starts around 2009, but that is unverified for other skaters.

**Limits.**
- A snapshot shows what the bio said on one day, which still does not reveal mid-season music changes.
- Archived pages are copies of ISU content, so the same rights question applies.
- Our sampler leaned on the CDX API. It returns 504 errors on broad prefix queries, so use per-URL queries with a low request rate.

## Skater and Team identity data

- **ISU ID.** Nearly every entry links its bio, which carries a stable 8-digit ID: 1,938 of 1,939 entries link one, and 1,287 of 1,288 unique bios are still live. The exception is JGP Courchevel 2004, where none of 65 entries are linked. Early-era JGP events may need name matching. The same ID is used from 2004 to today, e.g. Buttle `isufs00003253` is linked from the [2004/05 GPF entries](http://www.isuresults.com/results/gpf0405/CAT001EN.HTM) and still resolves.
- **Teams.** A pair or dance couple has **one Team ID**, e.g. [Golubeva/Giotopoulos Moore `isufs00111143`](https://results.isu.org/bios/isufs00111143.htm). Its bio inlines both partners' personal data. It does **not** link to separate individual Skater IDs. So the ISU gives no machine link from a Team to a solo Skater, or across a Skater's successive partnerships. Only 10% of bios fill "Former Partners", and that field is free text.
- **Bio fields** (share of the 1,287 live bios that fill each):
  - Date of birth 100%, place of birth 99%, height 99%;
  - Coach 90%, Choreographer 87%;
  - home town, club, hobbies and profession appear too; we did not count them;
  - some carry free-text biography notes.
- **Per-skater pages.** About 90% of bios (all new-layout ones) link a per-skater competition-results page [`isufs_cr_<id>.htm`](https://results.isu.org/bios/isufs_cr_00108049.htm) and a personal-bests page `isufs_pb_<id>.htm`. These give a cross-event index per Skater/Team.
- **Name spellings drift.** The same Team appears as "Anastasia GOLUBEVA" in the [2024 Worlds entries](https://results.isu.org/results/season2324/wc2024/CAT003EN.htm) and as "Anastasiia GOLUBEVA" in its bio. In 2004/05, 35 Team entries use "SURNAME Given - SURNAME Given", e.g. "SPASSOVA Rumiana - TODOROV Stanimir". Match on ISU ID, never on name.

## Terms and scraping

**Terms of Service.**
- The [ISU Terms of Service](https://www.isu.org/en/terms-service) are linked from the footer of isu.org and of every bio. They prohibit: "Use of ISU Business Applications to conduct any systematic or automated data collection activities (including without limitation scraping, data mining, data extraction and data harvesting) without ISU's express prior written [consent]".
- They also prohibit copying, storing or redistributing Content without ISU's prior approval.
- **Scope:** the same document defines "ISU Business Applications" as resources made available "to constituents (e.g. National Federations, Organizing Committees), its commercial partners and other authorized third parties through its Extranet or other 'Business-to-Business' website(s)". Whether the public result sites fall under it is not stated.
- We found no separate terms page for results.isu.org or isuresults.com. Guessed paths `/en/terms-of-use`, `/en/legal-notice` and `/en/imprint` return the site's generic shell.

**Other signals.**
- `robots.txt` returns 404 on both result hosts, and [isu.org/robots.txt](https://www.isu.org/robots.txt) says `User-agent: * Allow: /`. That is not a licence.
- Result pages carry "© 2024 International Skating Union. All Rights Reserved." Bios carry "© copyright by: International Skating Union".

**ISU Constitution 2024** ([copy hosted by the Dutch federation KNSB](https://knsb.nl/documents/556/2024_Constitution_.pdf)):
- Rule 100 §3a: "The ISU owns all rights to the names, program format, scoring Rules, computer programs, organization, marketing, advertising, broadcasting and reproduction of the ISU Events."
- Rule 105: all TV and "other media exhibition" rights, including the internet, are the ISU's. This matters for Performance videos: link or embed official uploads rather than re-hosting video.

**Personal data.** Bios contain personal data (date and place of birth, height). The ISU processes these under GDPR and the Swiss revDSG, per the ToS. Republishing them is a separate data-protection question from republishing music titles.

**Conclusion:** we found no explicit permission, and an explicit anti-scraping clause whose scope is ambiguous. Ask ISU for written consent before bulk collection or republication. Meanwhile, keep any fetching light: per-URL requests with delays. This is not legal advice.
