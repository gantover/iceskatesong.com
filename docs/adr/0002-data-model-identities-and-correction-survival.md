# Data model: identities, dedup keys, and how corrections survive re-imports

Every record has our own ID plus one or more stable **keys** in a shared key table, unique on `(system, value)`: ISU Skater/Team IDs, Wikidata QIDs, MusicBrainz work IDs, and a readable **slug** given at creation that never changes. Imports find records by key and refresh only the fields they own; human fixes live in separate rows tagged with their origin, and the highest-precedence origin wins. We chose this over "Admin edits a column, Import skips edited columns" because merges, splits, reassignments and hides all have to survive an Import that sees the original ISU data again. Moving keys and aliases to the survivor, and setting links only when a row is created, handles every one of those cases with the same few rules.

## Entities and keys

| Entity | Key(s) | Notes |
|---|---|---|
| Competition | ISU event URL path (from the repo-kept event list), slug | Level (senior/junior); names + city aliases for video-title matching. |
| Segment | (Competition, Discipline, level, Segment type, round) | Mirrors an ISU Category's segment page. A qualifying group is its own Segment. No Category entity. |
| Season | plain value (start year) | Not a table. |
| Skater | ISU ID (0..n), slug | Pairs/dance-only Skaters have no ISU ID. Names: display (ISU Latin) + JA/RU (Wikidata) + every name an Import matched on, kept as aliases. |
| Team | ISU Team ID (0..n), slug | Two Skater links (attributes, not identity). The same pair under two IDs is fixed by a merge. |
| Program | (Skater or Team, Season, Segment type, seq) | Exactly one of Skater/Team (check constraint). `seq` > 1 only from a split for a mid-season music change. The Admin can merge two Programs with the same owner, Season and Segment type. Raw music string always kept. |
| Performance | import key = (Segment, entry key as printed: ISU ID, or name + nation) | Rank, scores, name as printed, **nation as printed** (Skaters switch federations). Skater/Team and Program links are set on insert only. `gone` flag, Import-owned: set when a cleanly parsed Segment no longer lists the key (hidden, never deleted), cleared if it reappears. |
| Piece | slug, Wikidata QID (0..1), MusicBrainz work IDs (0..n) | Flat: Pieces never nest. At most one Source; credited Artists (1..n); Genre tags. Names + aliases (match keys). |
| Arrangement | (Piece, Style, performing Artist or none) | Fully ours. A Program's music is an ordered list of Arrangements. |
| Style, Genre | slug | Small lookup tables. |
| Source | slug, Wikidata QID (0..1) | Film, musical, ballet, opera, album, franchise. |
| Artist | slug, Wikidata QID (0..1) | Composer/songwriter of a Piece or performer of an Arrangement; multilingual names + aliases. |
| YouTube video | YouTube ID | API cache only: title, blocked regions, embeddable, `refreshed_at` (≤ 30 days). |
| Performance video | (YouTube ID, start seconds, Performance) | Origin `official`/`admin`/`submitted`, status `active`/`hidden`. One stream serves many Performances via start times; many videos per Performance. The page plays the first in that origin order not blocked in the viewer's `CF-IPCountry`. |
| Submission | own ID | Kind video/music; target Performance (video) or Program (music), empty for R4 bare URLs; YouTube ID, hints/music text, status `pending`/`approved`/`rejected`, hashed IP, resolving audit change. |
| Flag | own ID | Target Performance, performance video, or Program music; reason, status `open`/`resolved`/`dismissed`, hashed IP, resolving audit change. That change is the Admin's explicit Resolve or Dismiss, never the fix itself: fixing the data does not close the Flag. |
| Blocked submitter | hashed IP | Set by the Admin's Block (an audited, revertable change). That one change also rejects the hash's pending Submissions and dismisses its open Flags; new ones from the hash are refused. |
| Import | own ID | Job row (status pending/running/succeeded/failed, per-entity counts) plus `import_problems` rows (step, kind, URL or key, detail) for items that matched nothing or failed. |
| Audit change / audit row | own ID | One Admin action (who, when, label, note, `reverted_by`) with rows (table, primary key, before JSON, after JSON). |

The Review Queue is a query over pending Submissions and open Flags, not a table.

## How corrections survive re-imports

1. **Merge moves keys and aliases.** Merging two Skaters (or Teams, Pieces, …) moves the loser's keys (ISU IDs, slug) and aliases to the survivor. The next Import resolves either ISU ID, an old URL, or the old misspelling to the survivor. When merged Skaters or Teams both have a Program with the same key, those Programs are merged in the same change (Performances and music claims move to the survivor's Program).
2. **Links are set on insert only.** An Import finds a Performance by its import key and refreshes rank, scores and printed name. It never touches the Skater/Team or Program link afterwards, so reassignments and Program splits stick.
3. **Human facts are their own rows.** Music claims and names are one row per claim, tagged with origin. Precedence: Admin > corrections file > approved Music Submission > Wikipedia > ISU. An Import rewrites only rows of its own origin.
4. **Statuses are never reset.** An Import upserts a performance video and leaves its status alone, so a hidden link stays hidden. The Performance `gone` flag is the exception: it is the Import's own field, not a human status.

## Corrections file (R1)

`corrections.yaml` in the repo, referencing records only by the keys above, with four sections: `piece_aliases` (raw string → Piece slug; new Pieces defined inline with title, Artists, Source, Genres), `program_music` (Program key → ordered Arrangements), `skater_merges` (duplicate Skater slug → survivor slug), `video_hides` (YouTube ID + Performance key). Every Import applies the whole file and replaces all corrections-file rows, so deleting a line undoes the fix. Git history is its audit trail.

At R2 it **moves into the DB**: a one-off step relabels its rows as Admin rows, writes one audit change per entry ("migrated from corrections file"), and deletes the file. After that there is one path for human fixes. Later bulk fixes are scripts that write audit changes.

## Audit log (R2)

A generic Postgres trigger on human-editable tables writes audit rows whenever the `app.audit_change` session variable is set; Admin transactions set it, Imports do not (the Import row is their record). Revert is a new change that applies the before-images in reverse order and refuses if a row no longer equals its after-image, so later edits are never silently overwritten. A merge or split is one change with many rows.

## Consequences

- Polymorphic key and name tables can't carry real foreign keys; the code that writes them must keep `(entity type, entity ID)` valid, and merges must move them in the same transaction.
- How raw music strings become Pieces, Arrangements and aliases is left to [Can raw music strings become Pieces and Arrangements without duplicates?](https://github.com/gantover/iceskatesong.com/issues/10). This ADR fixes only the shape they land in.
