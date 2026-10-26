# Data model: identities, dedup keys, and how corrections survive re-imports

Every record has our own ID plus one or more stable **keys** in a shared key table, unique on `(system, value)`: ISU Skater/Team IDs, Wikidata QIDs, MusicBrainz work IDs, and a readable **slug** given at creation that never changes. One exception: an English Wikipedia article title (`enwiki`) sits in the key table for lookup but is not stable; the Import owns it, keeps it on the record its Wikidata item resolves to, and replaces it when the article is renamed. Imports find records by key and refresh only the fields they own; human fixes live in separate rows tagged with their origin, and the highest-precedence origin wins. We chose this over "Admin edits a column, Import skips edited columns" because merges, splits, reassignments and hides all have to survive an Import that sees the original ISU data again. Moving keys and aliases to the survivor, and setting links only when a row is created, handles every one of those cases with the same few rules.

## Entities and keys

| Entity | Key(s) | Notes |
|---|---|---|
| Competition | ISU event URL path (from the repo-kept event list), slug | Level (senior/junior); names and city (city and dates read from the ISU event index page). Video titles are matched against these plus a code-kept alias list per event type (e.g. `wc` → "World Champs"), not a per-Competition alias table. |
| Segment | (Competition, Discipline, level, Segment type, round) | Mirrors an ISU Category's segment page. A qualifying group is its own Segment. No Category entity. |
| Season | plain value (start year) | Not a table. |
| Skater | ISU ID (0..n), Wikidata QID, `enwiki` title (Import-owned, not stable), slug | Pairs/dance-only Skaters have no ISU ID. Names: display (ISU Latin) + JA/RU (Wikidata) + every name an Import matched on, kept as aliases. |
| Team | ISU Team ID (0..n), Wikidata QID and `enwiki` title only when one item names both partners, slug | Two Skater links (attributes, not identity). The same pair under two IDs is fixed by a merge. Wikidata puts most ISU Team IDs on each partner's own person item, so the Import resolves a Team ID to the partner whose names match the item, and to the Team only when the item names both partners; no match is an Import problem. Wikipedia steps reach a Team's Programs through its partners' keys. |
| Program | (Skater or Team, Season, Segment type, seq) | Exactly one of Skater/Team (check constraint). `seq` > 1 only from a split for a mid-season music change. The Admin can merge two Programs with the same owner, Season and Segment type. Raw music string always kept. |
| Performance | import key = (Segment, entry key as printed: ISU ID, or name + nation) | Rank, scores, name as printed, **nation as printed** (Skaters switch federations). Skater/Team and Program links are set on insert only. `gone` flag, Import-owned: set when a cleanly parsed Segment no longer lists the key (hidden, never deleted), cleared if it reappears. |
| Piece | slug, Wikidata QID (0..1), MusicBrainz work IDs (0..n) | Flat: Pieces never nest. At most one Source; credited Artists (0..n; a bare title from an Import may have none); Genre tags. Names + aliases (match keys). |
| Arrangement | (Piece, Style, performing Artist or none) | Fully ours. A Program's music is an ordered list of Arrangements. |
| Style, Genre | slug | Small lookup tables. |
| Source | slug, Wikidata QID (0..1) | Film, musical, ballet, opera, album, franchise. |
| Artist | slug, Wikidata QID (0..1) | Composer/songwriter of a Piece or performer of an Arrangement; multilingual names + aliases. |
| YouTube video | YouTube ID | API cache only: title, channel, `publishedAt`, duration, blocked (or allowed) regions, embeddable, made for kids, `refreshed_at` (each Import refreshes rows older than 25 days and drops rows older than 30, the API terms' limit, even without a fetch). |
| Performance video | (YouTube ID, start seconds, Performance) | Origin `official`/`admin`/`submitted`, status `active`/`hidden`. One stream serves many Performances via start times; many videos per Performance. A per-skater clip starts at 0. A full-segment stream with no known start time is linked to every Performance of its Segment with empty start seconds (key declared `NULLS NOT DISTINCT`, so re-Imports upsert rather than duplicate); the Admin or a Submission (R2) adds the start time (stream descriptions carry none). The page plays the first video not blocked in the viewer's `CF-IPCountry`: Performance clips and timed streams first, untimed streams last, each in origin order. |
| Submission | own ID | Kind video/music; target Performance (video) or Program (music), empty for R4 bare URLs; YouTube ID and hints (video), or music text and an optional link (music; recording links such as Spotify stay here and never become keys), status `pending`/`approved`/`rejected`, hashed IP, resolving audit change. |
| Flag | own ID | Target Performance, performance video, or Program music; reason, status `open`/`resolved`/`dismissed`, hashed IP, resolving audit change. That change is the Admin's explicit Resolve or Dismiss, never the fix itself: fixing the data does not close the Flag. |
| Blocked submitter | hashed IP | Set by the Admin's Block (an audited, revertable change). That one change also rejects the hash's pending Submissions and dismisses its open Flags; new ones from the hash are refused. |
| Import | own ID | Job row (status pending/running/succeeded/failed, per-entity counts `{created, updated}`, plus `deleted` from a step that removes its own stale rows; the Admin page renders this shape) plus `import_problems` rows (step, kind, URL or key, detail) for items that matched nothing or failed. |
| Audit change / audit row | own ID | One Admin action (who, when, label, note, `reverted_by`) with rows (table, primary key, before JSON, after JSON). |

The Review Queue is a query over pending Submissions and open Flags, not a table.

## How corrections survive re-imports

1. **Merge moves keys and aliases.** Merging two Skaters (or Teams, Pieces, …) moves the loser's keys (ISU IDs, slug) and aliases to the survivor. The next Import resolves either ISU ID, an old URL, or the old misspelling to the survivor. When merged Skaters or Teams both have a Program with the same key, those Programs are merged in the same change (Performances and music claims move to the survivor's Program).
2. **Links are set on insert only.** An Import finds a Performance by its import key and refreshes rank, scores and printed name. It never touches the Skater/Team or Program link afterwards, so reassignments and Program splits stick.
3. **Human facts are their own rows.** Music claims and names are one row per claim, tagged with origin; a Wikipedia row also keeps its article and revision, which the page links for CC BY-SA attribution. Precedence: Admin > corrections file > approved Music Submission > Wikipedia > ISU. An approved Music Submission's claim is the full ordered Arrangement list the Admin picked, linked to its Submission; a later Wikipedia change never outranks it. An Import rewrites only rows of its own origin.
4. **Statuses are never reset.** An Import upserts a performance video and leaves its status alone, so a hidden link stays hidden. The Performance `gone` flag is the exception: it is the Import's own field, not a human status.

## Corrections file (R1)

`corrections.yaml` in the repo, referencing records only by the keys above, with four sections: `piece_aliases` (raw string → Piece slug; new Pieces defined inline with title, Artists, Source, Genres), `program_music` (Program key → ordered Arrangements), `skater_merges` (duplicate Skater slug → survivor slug), `video_hides` (YouTube ID + Performance key). Every Import applies the whole file and replaces all corrections-file rows, so deleting a line undoes the fix. Git history is its audit trail.

Not every fix can be a separate origin-tagged row: a merge moves keys, aliases and Programs, a hide sets a video's status, and a new Piece is a record of its own. For those the R1 replay keeps an undo journal (`corrections_undo`). The next Import first drops the origin-tagged rows, then runs the journal backwards, which also deletes the records the file created. So a Piece the file defines is recreated under a new ID on every Import; its slug stays while the line does, and once an Import creates that Piece itself, the slug passes to the imported Piece and the line only aliases it. The journal goes away when the corrections move into the database ([#44](https://github.com/gantover/iceskatesong.com/issues/44)).

A Piece alias is not an edit of Wikipedia's music: a bare title never re-matches across Programs, so an edited entry could not be restored when its line is deleted. Instead each affected Program gets its own `corrections` claim that copies Wikipedia's text, article and revision with the aliased entries repointed. That claim is written only for Programs with no Admin, corrections or Music Submission claim: an alias is Wikipedia's music with one fix, so it never outranks human-picked music, even though the corrections origin normally ranks above Music Submissions. How the file behaves in detail: [Corrections file: how it works](../corrections-file.md).

At R2 it **moves into the DB**: a one-off step relabels its rows as Admin rows, writes one audit change per entry ("migrated from corrections file"), and deletes the file. After that there is one path for human fixes. Later bulk fixes are scripts that write audit changes.

## Audit log (R2)

A generic Postgres trigger on human-editable tables writes audit rows whenever the `app.audit_change` session variable is set; Admin transactions set it, Imports do not (the Import row is their record). Revert is a new change that applies the before-images in reverse order and refuses if a row no longer equals its after-image, so later edits are never silently overwritten. A merge or split is one change with many rows.

## Consequences

- Polymorphic key and name tables can't carry real foreign keys; the code that writes them must keep `(entity type, entity ID)` valid, and merges must move them in the same transaction.
- How raw music strings become Pieces, Arrangements and aliases is left to [Can raw music strings become Pieces and Arrangements without duplicates?](https://github.com/gantover/iceskatesong.com/issues/10). This ADR fixes only the shape they land in.
