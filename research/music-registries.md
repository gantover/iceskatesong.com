# Can MusicBrainz or Wikidata anchor Piece and Source identity?

Research for [issue #5](https://github.com/gantover/iceskatesong.com/issues/5). The live API checks were run on 2026-10-22.

## Answer

**Neither registry can be the identity of a Piece or a Source. Use them as optional cross-references on our own records.**

- **Wikidata QID: the main external reference.** Wikidata has one item for each major work. It has EN/JA/RU labels, composer, part-of hierarchy (movement → work, aria → opera), and links out to MusicBrainz. It has no items for film cues, remixes or skating-specific edits.
- **MusicBrainz work MBID: a second reference.** One of our Pieces can match several MB works, because MB has duplicates and some arrangements or remixes are entered as separate works. MB is strong on recordings and ISWCs. It is weak for multilingual lookup.
- **Fuzzy matching: neither helps with raw skating strings.** Normalise locally first. Then match against a local alias index built from a Wikidata extract, and keep our own aliases on top of it.
- **Sources (films, ballets, musicals): use the Wikidata film or stage-work item.** Don't use the soundtrack album item. MB has no film entity, only soundtrack release groups.

## Coverage spot-check

Key: MB = MusicBrainz work search (`/ws/2/work`). WD = Wikidata search plus `wbgetentities`. "dupes" = several MB works for the same Piece.

| Piece | MusicBrainz work | Wikidata item | EN/JA/RU labels (WD) |
|---|---|---|---|
| Swan Lake (Tchaikovsky) | `11f48c5e…` "Swan Lake, op. 20" (Ballet), plus a Drigo-revision work. Aliases EN/FR/DE only. | [Q199786](https://www.wikidata.org/wiki/Q199786), P435 → `11f48c5e…` | 白鳥の湖 / Лебединое озеро |
| Rachmaninoff PC2 | `aca4167a…` (ISWC T-003.007.883-1). A second top-level dupe `b1c5d53d…`, plus movement works. | [Q210224](https://www.wikidata.org/wiki/Q210224), P435 → `aca4167a…`. The movement Q101424811 is P361 part of it. | ピアノ協奏曲第2番 / Концерт … № 2 (Рахманинов) |
| Chopin Ballade No. 1 | `f94364c5…` has many aliases, including JA. 2 more dupes. | [Q2038498](https://www.wikidata.org/wiki/Q2038498), P435 → `f94364c5…` | バラード第1番 / Баллада № 1 (Шопен) |
| He's a Pirate (Badelt/Zimmer) | `8bce4766…`. The remix names sit as **aliases** of this work, but 3 remixes are also **separate works** with their own ISWCs. | **No work item.** [Q3128955](https://www.wikidata.org/wiki/Q3128955) is the 2006 Tiësto remix *album*. No WD item carries P435 `8bce4766…`. | n/a |
| Phantom of the Opera (song) | 5 works titled "The Phantom of the Opera" (Song ×2, Musical, untyped ×2). | [Q1157267](https://www.wikidata.org/wiki/Q1157267) (song), P361 → musical | オペラ座の怪人 / (no RU) |
| Bad Romance | `45c75efc…` (ISWC) plus one dupe. Credited as writer, not composer. | [Q153064](https://www.wikidata.org/wiki/Q153064), P435 → `45c75efc…` | バッド・ロマンス / Bad Romance |
| Libertango (Piazzolla) | 4 works titled "Libertango". One credits arranger Lev Zhurbin, one credits Éric Sammut as composer. | [Q1073405](https://www.wikidata.org/wiki/Q1073405), P435 → `e039120f…`. Separate cover-recording and single items also exist. | リベルタンゴ / Либертанго |
| El Tango de Roxanne (Moulin Rouge) | `882eff51…`, credited to Sting and Mariano Mores | **None.** The base song Roxanne is [Q1631268](https://www.wikidata.org/wiki/Q1631268). | n/a |
| Seimei (Umebayashi, *Onmyōji*) | **No work.** Only soundtrack recordings with Japanese titles (e.g. 晴明の涙 on the 陰陽師 OST). "SEIMEI" in MB is an unrelated J-pop song. | **None.** The film is [Q4184393](https://www.wikidata.org/wiki/Q4184393) (陰陽師 / Колдун). | film only |
| Carmen / Habanera (Bizet) | Opera `45efd8f4…`, plus per-language works and 345 hits for Carmen-related works. Habanera has ≥2 works (`eef9a258…`, `c339a112…`, …). | Opera [Q185968](https://www.wikidata.org/wiki/Q185968). Aria [Q692648](https://www.wikidata.org/wiki/Q692648) is P361 part of the opera. Its P435 is `05ad4550…`, a **third** MB Habanera work, not the top search hit. | カルメン / Кармен; ハバネラ / Хабанера |

**Pattern:**
- Classical, opera, ballet, musical numbers and big pop singles are covered well by both registries.
- Film cues, remixes, tango arrangements and skating edits (Seimei, He's a Pirate as a composition, El Tango de Roxanne) are where coverage fails. That long tail is a large share of skating music.
- Where Wikidata has an item, it **chooses one MB work among MB's duplicates** (Habanera, Libertango, PC2). That is useful for merging MB duplicates.

**Source ambiguity.** "Moulin Rouge!" alone has three QIDs:
- the 2001 film, [Q193573](https://www.wikidata.org/wiki/Q193573);
- the soundtrack album, [Q2690177](https://www.wikidata.org/wiki/Q2690177);
- the stage musical, [Q51879470](https://www.wikidata.org/wiki/Q51879470).

The Pirates search only surfaced the soundtrack album, [Q1935773](https://www.wikidata.org/wiki/Q1935773). Our glossary's Source matches the film or stage work, so anchor on that and ignore album items.

## Works vs recordings modelling

### MusicBrainz

- **Work vs recording.** A Work is "a distinct intellectual or artistic creation" that "can be expressed in the form of one or more audio recordings". Recordings link to works. ([Work](https://musicbrainz.org/doc/Work))
- **What counts as a separate work.** Medleys, mashups, lyric additions and translations are separate works. Arranger is only a credit role. ([Work](https://musicbrainz.org/doc/Work))
- **No arrangement rule.** The style guide gives no rule on whether an arrangement or remix is a new work ([Style/Work](https://musicbrainz.org/doc/Style/Work)). In practice editors do both (see He's a Pirate and Libertango above).
- **Mapping to our model:** Piece → 1..N MB works, and Arrangement stays our own entity.
- **Structure.** Parts link to the parent through "part-of-work" relationships, for example movement → concerto and aria → opera.
- **Aliases.** Aliases cover other names and languages. The canonical name is "in the language it was originally written". ([Work](https://musicbrainz.org/doc/Work))
- **Sources.** MB has no film or musical entity. Soundtracks are release groups with secondary type "Soundtrack". ([Style/Work](https://musicbrainz.org/doc/Style/Work))
- **Composer names are stored in the native script.** Tchaikovsky is "Пётр Ильич Чайковский" and Rachmaninoff is "Сергей Васильевич Рахманинов". In our tests, `artist:Tchaikovsky` and `artist:Rachmaninoff` returned **0** hits, so the `artist` search field does not seem to match artist aliases. This was observed, not confirmed: query by `arid:` to be safe.

### Wikidata

- **Work items.** Musical works are items, typically P31 = musical work/composition (Q105543609).
- **Properties that matter:** P86 (composer), P361 (part of), P435 (MusicBrainz work ID), and P1441 (present in work).
- **Labels and aliases** exist per language. Sitelinks show notability. Swan Lake has 64 sitelinks, Carmen 75.
- **Cross-reference size.** 58,862 items carry a MusicBrainz work ID (P435), counted by SPARQL on 2026-10-22. That is small next to MB's work count, so the crosswalk only covers the notable repertoire.

## Multilingual names

- **Wikidata:** EN/JA/RU labels were present on every major item checked. RU was missing only on the Phantom song.
- **MusicBrainz:** multilingual coverage is uneven, alias by alias.
  - The Chopin Ballade has a JA alias, but Swan Lake has none in JA or RU.
  - Searching 白鳥の湖 or Лебединое озеро did **not** find Swan Lake. It returned 白鳥の詩 and a Noize MC song instead.
- **Conclusion:** Wikidata is the practical source for EN/JA/RU display names. Keep local overrides for skating-community names (e.g. "SEIMEI", "Rach 2").

## Fuzzy matching of messy strings

- **MB search** takes full Lucene syntax, and its work search fields include `alias`, `work`, `artist`, `arid`, `iswc`, `lang` and `type`. Results are capped at 100 per request. ([Search](https://musicbrainz.org/doc/MusicBrainz_API/Search))
- **MB free-text tests:**
  - "Rachmaninoff Piano Concerto 2" ranked a Uri Caine track "RachmanINoff" first and never returned the real work.
  - "Ballade 1 Chopin" ranked a Melanie Doane song first.
  - "Bad Romance piano ver" did find Bad Romance.
  - `Libretango~`, a Lucene fuzzy term, found Libertango. That fixes single-word typos, not structure.
- **Wikidata full-text search** (`list=search`) did better on "Piano Concerto No. 2 Rachmaninoff" and "Ballade No. 1 Chopin". It still found nothing for "El Tango de Roxanne" or "Seimei Umebayashi", and "He's a Pirate" returned the remix album.
- **Recommended pipeline** (outside both services):
  1. Split on `/` and `–`.
  2. Strip the Style and arranger markers, for example `(piano ver.)` and `arr. X`.
  3. Match the remainder against a **local** alias index, seeded from a Wikidata SPARQL extract (labels and aliases in en/ja/ru, plus composer) and our own aliases.
  4. Keep MBIDs only as attached references.
- Don't call a live API once per raw string. The rate limits below rule it out for bulk import anyway.

## API limits

- **MusicBrainz web service** ([Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)):
  - About 1 request per second per source IP. Over that, every request gets a 503.
  - The service as a whole handles about 300 requests per second.
  - Requests need a User-Agent with contact information.
  - Anonymous User-Agents are throttled further.
  - Clients that query at fixed times may be blocked.
- **Wikidata Query Service, SPARQL** ([User Manual](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual#Query_limits)):
  - 60-second timeout per query.
  - 60 seconds of processing time per minute for each User-Agent plus IP.
  - 30 error queries per minute.
  - 5 parallel queries per IP.
  - Over the limits you get HTTP 429 with Retry-After. Clients that ignore it may be banned.
- **Wikidata Action API** ([API:Etiquette](https://www.mediawiki.org/wiki/API:Etiquette)):
  - No hard speed limit on reads.
  - Send requests one at a time, not in parallel.
  - Use `maxlag` for batch jobs.
  - A meaningful User-Agent is required.
  - Pipe-batch IDs; `wbgetentities` takes several IDs per call.

## Licences

| Registry | Data and licence |
|---|---|
| MusicBrainz | **Core data is CC0.** That includes works, recordings, artists, releases, aliases and relationships, URLs included. ([Data License](https://musicbrainz.org/doc/About/Data_License), [Database](https://musicbrainz.org/doc/MusicBrainz_Database)) |
| MusicBrainz | **Supplementary data is CC BY-NC-SA 3.0** (non-commercial). That includes tags, **genre associations**, ratings and annotations. Don't build our Style field from MB tags or genres if the site may ever be commercial. |
| MusicBrainz | **Live Data Feed replication packets are CC BY-NC-SA 3.0.** |
| Wikidata | **Structured data is CC0**: the main, Property, Lexeme and EntitySchema namespaces. Other text is CC BY-SA. ([Database download](https://www.wikidata.org/wiki/Wikidata:Database_download)) |

## Offline dumps vs API

- **MusicBrainz dumps.** There are two kinds:
  - Postgres dumps (`mbdump.tar.bz2`, core CC0), loaded through a local MusicBrainz Server or `mbslave` ([Download](https://musicbrainz.org/doc/MusicBrainz_Database/Download)).
  - Per-entity **JSON dumps**, one file per entity type (works included), with one JSON entity per line in web-service format ([JSON Data Dumps](https://musicbrainz.org/doc/Development/JSON_Data_Dumps)).
- **Wikidata dumps.**
  - A weekly full JSON dump, about 130 GiB gzipped. That figure is the 2024-01-01 size from the docs, so it is dated.
  - Truthy N-Triples and full RDF dumps, plus incremental daily XML.
  - Third-party filtered dumps via WDumper. ([Database download](https://www.wikidata.org/wiki/Wikidata:Database_download))
- **Recommendation.**
  - Skip the full Wikidata dump. Take a SPARQL or WDumper extract of musical works, compositions, films, ballets, operas and musicals, with en/ja/ru labels and aliases plus P86/P361/P435/P1441.
  - Optionally add the MB **work** JSON dump for ISWCs and extra aliases. That is the CC0 part, and it is small next to recordings.
  - Use the live APIs only for one-off curator lookups.

## Implications for our model

- **Piece:**
  - Our own ID is the identity.
  - Optional `wikidata_qid`, at most one.
  - Optional `musicbrainz_work_ids`, a list, because MB has duplicates and splits remixes into separate works.
- **Source:** our own ID, with an optional QID that points at the film or stage work, never a soundtrack album.
- **Arrangement:** stays fully ours. Neither registry models a Style-tagged arrangement independently of recordings.
- **Composers and artists:** a Wikidata QID, and optionally an MB artist MBID. These are well covered, including Umebayashi.
- **Long tail:** expect a large share of film cues and skating edits to have no external ID. The model must work without one.
