# Can Postgres alone power the site search?

Research for issue #20. Sources were fetched on **2026-10-22**. Hosting constraints come from #11: Rock 5 ITX (ARM64), one `compose.yml`, Postgres from day one with `pg_trgm` and `unaccent`.

The tests ran in the official `postgres:18` (Debian, 18.6) and `postgres:18-alpine` (musl, 18.6) images, against synthetic data: about 50k person names (Latin with diacritics, plus Cyrillic and ~1,050 Japanese rows) and 30k Pieces carrying ~1.75 KB of English text each. **The timings come from a fast x86 desktop (Ryzen AI Max+ 395), not the RK3588.** Expect the Rock 5 to be several times slower per query. Re-time on the box once it is set up. The test script is [`postgres-search.sql`](postgres-search.sql).

## Answer

**Yes. Postgres covers every search on the list, and no dedicated engine earns a slot in the Compose file.** The setup costs nothing beyond what #11 already plans: two trusted contrib extensions, one 3-line SQL function, a generated column, and a GIN index per searched table. At our scale every query ran in under 30 ms. The slowest were seq-scan worst cases.

There is one setup rule, and it is fixed when the database is first created (initdb): **never initialise the database with the `C` locale.** See [Locale](#1-locale-decide-before-day-one).

Cross-script matching is a **data problem, not an engine problem.** Matching "Hanyu" to 羽生結弦, or "Plushenko" to Плющенко, needs a stored alias or romanisation. Meilisearch and Typesense do not transliterate kanji to romaji or Cyrillic to Latin either. ISU results are already romanised, so the Latin form always exists. JA/RU names go in as extra alias rows that point to the same Skater, which is the same alias mechanism Pieces already use.

## What each need maps to

| Need | Postgres feature | Result in test |
|---|---|---|
| Skater, Team, Artist and Source names; Piece titles and aliases | `pg_trgm` GIN index on `f_unaccent(lower(name))` | substring `'%aymo%'`: **0.08 ms** |
| Diacritics (Kévin, Ribič, Søren, Weiß, Łukasz, Ё) | `unaccent` in a generated column | `kevin aym` → Kévin Aymoz. `Ёлкин` → `Елкин` |
| Typos | `word_similarity` / `<%` (threshold 0.6) | `plushchenko` → Evgeni Plushenko (0.69); `cizeronn` → Cizeron (0.78); `hanyu yuzru` → Yuzuru Hanyu (0.67); `плющенка` → Плющенко (0.78). **0.16 ms** |
| As-you-type (partial words) | `LIKE '%…%'` on the trigram index, ranked by `word_similarity` | 3 letters `'%kar%'` (782 hits, top 10): **2.5 ms**. 2 letters `'%ka%'` (12k hits, seq scan): **18–26 ms** |
| Japanese names (no word boundaries) | the same trigram index; trigrams work on characters, not words | `'%羽生結%'`: **1.1 ms**. `'宇野%'`: **0.8 ms**. 1–2 kanji `'%羽生%'`: **3.5–4.8 ms** (full scan, see below) |
| Russian names | the same trigram index | `'%плющ%'` → Евгений Плющенко |
| Raw Wikipedia music text | built-in full-text search: `tsvector` generated column + GIN, `websearch_to_tsquery('english', …)`, `ts_rank` | rare terms: **0.1–0.5 ms**. Prefix `zimm:*`: **15 ms**. Common words matching 98% of rows, ranked: **25 ms** |
| Admin record pickers (R2) | the same queries | transactional: a record the Admin just created is searchable at once |

### Why Japanese works without a word segmenter

- The default FTS parser cuts only at whitespace and punctuation. `to_tsvector('simple','羽生結弦のフリー')` returns **one token**, `'羽生結弦のフリー':1`. Full-text search is therefore the wrong tool for JA names. Use it only for the long English music text.
- `pg_trgm` uses the same notion of "word" ("ignores non-word characters (non-alphanumerics)… Each word is considered to have two spaces prefixed and one space suffixed", [pg_trgm docs][trgm]). A JA name is therefore one long "word", but substring matching works on its character trigrams anyway, so `LIKE '%生結弦%'` hits the index.
- **The weak spot is a 1–2 character query** (two-kanji surnames like 羽生 or 宇野 are common). The docs say: "a pattern with no extractable trigrams will degenerate to a full-index scan" ([pg_trgm docs][trgm]). The test confirmed it: the index returned all 50,061 rows for a recheck, or the planner picked a seq scan, and both took 3.5–4.8 ms. That is fine at tens of thousands of rows, and only becomes a concern somewhere past millions.
- Anchored prefixes (`'宇野%'`) do extract a trigram (the padded word start) and stay fast.
- Two normalisations `unaccent` does not do. Both are one-liners if they are ever needed (tested, not built):
  - half-width to full-width kana: `normalize(s, NFKC)` turns `ﾊﾆｭｳ` into `ハニュウ` and `ＨＡＮＹＵ` into `HANYU`;
  - hiragana to katakana: `translate()` over U+3041–U+3096 shifted by +0x60. Tested: `はにゅう ゆづる` folds to `ハニュウ ユヅル`.

### Typos and as-you-type: limits to know

- `word_similarity` is trigram overlap, not edit distance. Very short words (≤3 letters) with a typo rarely reach 0.6. Meilisearch has the same blind spot: by default it "accepts one typo for query terms containing five or more characters, and up to two typos if the term is at least nine characters long" ([Meilisearch typo tolerance][meili-typo]).
- A 2-letter Latin query can't use the index and scans everything: 18–26 ms here with 12k matching rows. Cheap fix in the UI: start substring search at 3 characters, and before that do an anchored prefix (`LIKE 'ka%'`), which can use the padded word-start trigram.
- GIN vs GiST: GIN was 7–60× faster here for `LIKE` and `<%`. GiST adds KNN ordering (`<->`, "not by GIN indexes", [pg_trgm docs][trgm]), but at this scale sorting the GIN matches is cheap. **Use GIN only.**

## 1. Locale: decide before day one

`pg_trgm` and the FTS parser decide which characters are letters from the database's `lc_ctype` ("The parser's notion of a 'letter' is determined by the database's locale setting, specifically `lc_ctype`", [FTS parsers][parsers]). Tested on `show_trgm`:

| Database locale | `羽生結弦` | `Плющенко` | `Ribič` |
|---|---|---|---|
| image default `en_US.utf8` (libc), Debian and Alpine | 5 trigrams | 9 trigrams | full |
| `C` | **`{}` (nothing indexed)** | **`{}`** | `č` dropped, word split |
| builtin provider `C.UTF-8` (PG17+) | 5 trigrams | 9 trigrams | full |

Both official images initialise with `en_US.utf8` by default, so **doing nothing is correct**. The trap is setting `POSTGRES_INITDB_ARGS=--locale=C` (or `LANG=C`) for speed, or copying a tutorial that does. JA/RU search then silently returns nothing. The locale can't be changed after initdb without a dump and restore. Debian and Alpine behaved the same in every test.

## 2. `unaccent` needs a wrapper to be indexed

`unaccent()` is `STABLE`. Tested: `pg_proc.provolatile = 's'` for both signatures. Index expressions and generated columns need `IMMUTABLE`. The standard wrapper pins the dictionary schema-qualified:

```sql
create extension pg_trgm;   -- trusted: no superuser needed (docs)
create extension unaccent;  -- trusted

create function f_unaccent(text) returns text
  language sql immutable parallel safe strict
  return public.unaccent('public.unaccent'::regdictionary, $1);
```

Coverage: the shipped `unaccent.rules` "translates characters with accents to the same characters without accents, and it also expands ligatures" ([unaccent docs][unaccent]). Tested: `Ribič Ñandú Søren Weiß Æon Łukasz Kévin` → `Ribic Nandu Soren Weiss AEon Lukasz Kevin`, and `Ёлкин` → `Елкин`. `lower()` folds Cyrillic and accented Latin correctly in both images.

## 3. Minimal schema shape

```sql
-- one per searched table (Skater, Team, Artist, Source, Piece, plus alias tables)
alter table skater add column search_key text
  generated always as (f_unaccent(lower(name))) stored;
create index on skater using gin (search_key gin_trgm_ops);

-- music text only
alter table piece add column body_tsv tsvector
  generated always as (to_tsvector('english', f_unaccent(coalesce(wiki_text,'')))) stored;
create index on piece using gin (body_tsv);

-- query: substring OR fuzzy, ranked; :q is already f_unaccent(lower(input))
select id, name from skater
where search_key like '%' || :q || '%' or :q <% search_key
order by word_similarity(:q, search_key) desc
limit 20;
```

Sizes at test scale: a 50k-name trigram GIN index takes 2.2 MB, and the FTS GIN over 30k × 1.75 KB of text takes 6.9 MB. Both are negligible on 24 GB.

Searching one box across Pieces, Skaters, Artists and so on means a `UNION ALL` of these per-table queries, or a single `search_entry(kind, ref_id, text)` table maintained by the Import. Pick one at build time. Neither needs a new service.

## 4. The alternatives

| | PGroonga | pg_bigm | Meilisearch | Typesense |
|---|---|---|---|---|
| What it is | Postgres extension (Groonga engine) with N-gram / JA tokenising | Postgres extension: 2-gram GIN index, fixes the 1–2 char case | separate search server | separate search server |
| ARM64 Docker image | **yes**: `groonga/pgroonga:4.1.0-debian-18` / `-alpine-18`, amd64 + arm64, updated 2026-10-09 ([Docker Hub][pgroonga-hub]) | **no image**. Source + Makefile only ([repo][bigm]), so it needs a custom Dockerfile build | **yes**: `getmeili/meilisearch:v1.55.0`, amd64 + arm64, released 2026-10-12 ([Docker Hub][meili-hub], [release][meili-rel]) | **yes**: `typesense/typesense:30.2` stable (2026-04-19), amd64 + arm64 ([Docker Hub][ts-hub], [release][ts-rel]) |
| Japanese | yes | bigrams, good for short JA | lindera IPA dictionary segmentation ([languages][meili-lang]) | `locale: "ja"`: "Mixed kanji-kana text segmentation" ([locale][ts-locale]) |
| Typos | yes | similarity only | built-in, edit distance, defaults above | built-in |
| Transliteration (Hanyu ↔ 羽生) | no | no | no | no |
| Setup cost | swap the `postgres` image. Stays one database, transactional | maintain a custom image | new service + volume + API key + **sync job** from Postgres + reindex on every Import and Admin edit | same as Meilisearch |
| Consistency | same transaction | same transaction | async indexing: a record the Admin just created may be missing from the R2 picker for a moment | async |
| Backups | covered by `pg_dump` | covered | separate, or rebuild from Postgres | separate, or rebuild |

What a dedicated engine buys that Postgres doesn't: tuned relevance out of the box (typo-count ranking, word proximity, attribute weights), facets, and highlighting without SQL. None of these is in the ticket. What it costs: a second source of truth, a sync path that every Admin correction must also go through (and the corrections must survive per ADR 0002), and one more service to back up and upgrade on the box.

## Recommendation

1. **Postgres only.** Use `pg_trgm` (GIN) + `unaccent` (immutable wrapper) on a generated `search_key` per searched table, and built-in FTS (`english`) for the Wikipedia music text only. Leave the image default locale alone (`en_US.utf8`), and write "never `C` locale" next to the `postgres` service in `compose.yml`.
2. Store JA/RU names as **aliases** of the Skater/Piece, the same as other aliases. Do not expect any engine to match across scripts.
3. UI: substring search starts at 3 Latin characters (before that, prefix only). JA input searches from 1 character, which costs a few ms at our size.
4. **Path to grow (nothing built until a trigger fires):**

| Trigger | Move |
|---|---|
| JA users complain about 1–2 kanji queries (slow or badly ranked), or rows reach millions | Swap the `postgres` image for `groonga/pgroonga:*-debian-18` (still one service, same `pg_dump`) |
| Relevance tuning, facets or instant-search UX become a product feature | Add Meilisearch as a derived index rebuilt from Postgres after each Import |
| Half-width kana or hiragana/katakana mismatches show up | Add `normalize(…, NFKC)` and the kana `translate()` to `f_unaccent` (one line each) |

## Not checked

- Timings on the actual RK3588. Re-run the appendix there. On the slow side, the 25 ms worst cases could become ~100 ms. That is acceptable for a search box, but the 3-character rule matters more there.
- Ranking quality on real names and real Wikipedia text: the test data was synthetic (a 60-word vocabulary, which overstates "common word" matches).
- PGroonga and pg_bigm were not run, only their packaging checked.

## Sources

- https://www.postgresql.org/docs/18/pgtrgm.html (PostgreSQL 18.6 docs: trigram extraction, operators and defaults, GIN/GiST support, "full-index scan" note, trusted)
- https://www.postgresql.org/docs/18/unaccent.html (rules file coverage, signature, trusted, FTS config example)
- https://www.postgresql.org/docs/18/textsearch-parsers.html ("letter" determined by `lc_ctype`)
- https://www.postgresql.org/docs/18/textsearch-controls.html (`websearch_to_tsquery`, `:*` prefix, `ts_rank`, `ts_headline`)
- https://hub.docker.com/_/postgres (tags `18`, `18.6`, `18-alpine`: arm64/v8 present, updated 2026-10-21/22)
- https://hub.docker.com/r/groonga/pgroonga/tags
- https://github.com/pgbigm/pg_bigm
- https://hub.docker.com/r/getmeili/meilisearch/tags · https://github.com/meilisearch/meilisearch/releases/tag/v1.55.0
- https://www.meilisearch.com/docs/learn/relevancy/typo_tolerance_settings
- https://www.meilisearch.com/docs/learn/resources/language
- https://hub.docker.com/r/typesense/typesense/tags · https://github.com/typesense/typesense/releases/tag/v30.2
- https://typesense.org/docs/guide/locale.html

[trgm]: https://www.postgresql.org/docs/18/pgtrgm.html
[unaccent]: https://www.postgresql.org/docs/18/unaccent.html
[parsers]: https://www.postgresql.org/docs/18/textsearch-parsers.html
[pgroonga-hub]: https://hub.docker.com/r/groonga/pgroonga/tags
[bigm]: https://github.com/pgbigm/pg_bigm
[meili-hub]: https://hub.docker.com/r/getmeili/meilisearch/tags
[meili-rel]: https://github.com/meilisearch/meilisearch/releases/tag/v1.55.0
[meili-typo]: https://www.meilisearch.com/docs/learn/relevancy/typo_tolerance_settings
[meili-lang]: https://www.meilisearch.com/docs/learn/resources/language
[ts-hub]: https://hub.docker.com/r/typesense/typesense/tags
[ts-rel]: https://github.com/typesense/typesense/releases/tag/v30.2
[ts-locale]: https://typesense.org/docs/guide/locale.html

## Appendix: reproduce

```sh
docker run -d --rm --name pgt -e POSTGRES_PASSWORD=x postgres:18
docker exec -i pgt psql -U postgres < research/postgres-search.sql   # data generation + EXPLAIN ANALYZE runs (~1 min)
```

Locale check, in each database: `select show_trgm('羽生結弦'), show_trgm('Плющенко'), show_trgm('Ribič');` after `create database tc locale 'C' template template0;` and `create database tb locale_provider builtin builtin_locale 'C.UTF-8' template template0;`.

Data: 49,000 names built from random syllables (including `zé`, `ić`, `ña`, `ø`), plus real names (Yuzuru Hanyu / 羽生結弦 / はにゅう ゆづる, Evgeni Plushenko / Евгений Плющенко, Shoma Uno / 宇野昌磨, Kévin Aymoz, Guillaume Cizeron, Kaori Sakamoto / 坂本花織), 50 names starting with `羽生`, and 1,000 random 4-kanji names. 30,000 Pieces each get 250 random words from a 60-word music vocabulary, plus one real "He's a Pirate" paragraph. Each test is `EXPLAIN (ANALYZE)`, with `Execution Time` reported above.
