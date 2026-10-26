# Search, Piece pages and music lines: how they work

Built for #37 on the PRD's [Search](../PRD.md#search) and [Pages](../PRD.md#pages) sections. The queries are in
`web/src/lib/server/browse.ts` (`search`, `piecePage`, `musicOf`); this page records the decisions taken while building
and reviewing them.

## One rule for every music reader: the winning claim

A Program's music is its highest-precedence claim: Admin > corrections file > Music Submission > Wikipedia > ISU
(ADR 0002, `topClaim`). Search hits, the grade mix, the Piece page and the music lines all read only that claim's
occurrences. A Program can hold occurrences under two origins at once (Wikipedia, plus a corrections claim from an alias
or `program_music`; see `docs/corrections-file.md`), so a reader that skips this rule shows an overridden Program under
the wrong Piece or counts it twice.

Programs whose Performances are all marked gone count nowhere: not in the grade mix, the Piece page or the text hits.

## Search

One `search()` serves the home dropdown (`/api/search`) and the `/search` page. Each group shows at most 8 hits, as the
Skater and Team groups already did.

**Matching** (pg_trgm, accents and case ignored): from 3 characters a substring or a close spelling, below that the start
of a word. The length is counted on the query as typed; the old SQL counted it after removing accents, so the two differ
only for characters that expand (ß, æ, œ) right at the boundary.

### Music

- **Hits are always Pieces.** A Piece is found by its title, a Piece alias, a composer Artist, a performing Artist
  (the performer of an Arrangement counts as an Artist, per ADR 0002) or its Source. An Artist or Source match turns into
  its Pieces, because Artists and Sources have no page of their own.
- Ranked by substring match first, then closeness of spelling, then how many Programs use the Piece, then title.
- Each hit's subtitle is its Source, else its composers.
- **Grade mix:** each Program counts once per Piece, with its best grade, e.g. "15 Programs: 2 identified, 13 credited".

### In music text, not matched to a Piece

The recall guarantee: music text that names what was searched, on Programs the music search would miss.

- `english` full-text search (`websearch_to_tsquery`) over each Program's winning claim's raw text, served by the GIN
  index of migration 0007. Whole words only: while someone types "pira", only the Music group fills.
- A Program shows here when its text matches and none of its Pieces matches the query. That covers both a Program whose
  text never became a Piece and one linked to the wrong Piece.
- A hit shows the Skater or Team, Season and Segment type, and links to their Season page (Programs have no page). It
  shows no raw text, so the dropdown needs no licence line.

### Speed

The bar is "well under 100 ms on the full data". The dev database stays empty until the first production Import (#41),
so it was measured on a throwaway database seeded at corpus scale (48k Programs, 40k claims, 15k Pieces, 96k
Performances) after `vacuum analyze`. Medians: 5 to 30 ms for ordinary queries; 57 ms for "film" (5,000 matching
Pieces); 64 ms for "medley" (10,000 matching claims). Recheck on real data after #41.

What made it fast, and why it is written this way:

- **The music query ranks first, then looks up.** It aggregates the Programs per Piece once, takes the top 8, and only
  then fetches slugs and credits. The first version recounted every Program once per matching Piece: 1.8 s for "film".
- **The match predicate is chosen in TypeScript by query length**, not in a SQL `case`, so Postgres plans only the branch
  that applies.
- **The three queries (text, music, Skaters and Teams) run concurrently**, using three pool connections per search.
- Tried and rejected: building the predicate from constants so the planner would pick the trigram indexes (slower: the
  planner still chose sequential scans, with worse row estimates); `enable_seqscan`, `random_page_cost` or a function
  `COST` change (a planner hack, and an `ALTER FUNCTION` on an extension member is lost on a backup restore).
- If real data misses the bar, the remaining cost is the sequential `word_similarity` scan in the Piece-matching step,
  which the music and text queries both run. Compute it once, or narrow the text query's anti-join to its candidates.

## Piece page: `/piece/[slug]`

- Keyed by the Piece's slug, which the normaliser already writes (ADR 0002); an unknown slug is a 404.
- Header: title, composers (`piece_artists`), Source, Wikidata link, and counts. The count reads "N Skaters and Teams"
  when a Team uses the Piece, else "N Skaters".
- One collapsible block per Skater or Team, all open when there are 4 or fewer. Each Program: Season and Segment type
  (linked to the Season page) with its grade badge, the raw text of the entries naming this Piece, and its Performances
  with rank and a video marker.
- "Wrong music?" is laid out disabled until Flags (#49).

## Music lines and grade badges

- On the Skater, Team and Performance pages, each music line shows its Pieces in order, each followed by a grade badge
  whose tooltip explains the grade. The raw text stays beside them.
- Every Piece carries a badge. Text with no linked Piece shows only the raw text, with no "unmatched" marker.

## Wikipedia attribution follows the article, not the origin

Raw text is linked to its Wikipedia article revision, with one "CC BY-SA 4.0, modified" line per page, whenever its claim
carries an `article_title` and `revision`, whatever the claim's origin. A corrections alias claim copies Wikipedia's text,
so it must be attributed too. Gating on `origin = 'wikipedia'` once left that text unattributed. The browser check is in
`docs/legal-acceptance.md`.

## Pitfall: SQL fragments embedded in other queries

`topClaim` is spliced into other queries. Its subquery once aliased `music_claims` as `m`, the same alias as the caller's
table, so inside the text query `m.program_id` named its own row: one corrections claim anywhere hid every "In music text"
hit. Fragments like it use an alias no caller uses, and tests of origin precedence mix origins in the fixture.
