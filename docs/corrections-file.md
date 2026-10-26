# Corrections file: how it works

The R1 path for Admin fixes (#36). The why behind the design is in [ADR 0002](adr/0002-data-model-identities-and-correction-survival.md#corrections-file-r1);
this page is how the code in `import/corrections.py` behaves and the decisions taken while building and reviewing it.
The file itself, `corrections.yaml` at the repo root, has a commented example of each section. It moves into the
database at R2 (#44), and the undo journal described here goes with it.

## The Import cycle

1. **Fetch phase, first step: validate.** `corrections.load` reads the file before the Fetcher exists. An invalid file
   fails the Import with `corrections.yaml: <where>: <what>` and nothing is fetched. A missing file fails too (Docker
   mounts a missing path as a directory).
2. **Apply phase, first step: revert.** Right after the Import lock, `corrections.revert` deletes every row with origin
   `corrections` (music claims, which cascade to their occurrences, names, `piece_artists`, `piece_genres`), then runs the
   undo journal backwards. Every later step (ISU, names, Wikidata, Wikipedia, the music normaliser, videos) therefore sees
   the imported state, as if the file were empty.
3. **Apply phase, last step: replay.** `corrections.apply` runs once every imported row exists, in this order: Skater
   merges, Piece aliases and definitions, Program music, alias claims, video hides, then the journal entries for the
   records it created.

So deleting a line undoes its fix on the next Import, and the tests compare whole tables before and after to prove it.

## Two mechanisms: origin-tagged rows and the undo journal

- **Origin-tagged rows** (ADR 0002's default). Aliases, music claims and occurrences, and Piece Artists and Genres are
  written with origin `corrections`, so the revert simply deletes them.
- **The undo journal, `corrections_undo`** (migration 0008), for fixes that cannot be a separate row: a merge moves keys,
  names, Team places, Programs and Performances; a hide sets a video's status; a new Piece, Artist, Source, Genre, Style
  or Arrangement is a record of its own. Each change journals the statement that puts it back. Created records are
  journaled by explicit ID, never as an ID range, so a later non-Import writer (the R2 New record screen) is never
  caught by the revert.
- Why not edit Wikipedia's rows in place and remember the old values: a bare title never re-matches across Programs,
  so the old Piece could not be found again when the line is deleted.

## Sections

### `piece_aliases`: raw string → Piece slug

- A line maps one Wikipedia music entry, exactly as a "music string with no alias match" problem shows it, to a Piece.
- **An alias becomes its own claim, not an edit of Wikipedia's.** For every Program whose winning claim is Wikipedia's
  and which has an entry equal to an alias, the replay writes a `corrections` claim that copies Wikipedia's text, article
  and revision (needed for attribution, see `docs/search.md`), repoints the aliased entries at the alias Piece and copies
  the other occurrences as they are. Wikipedia's rows are untouched, so deleting the line restores them exactly.
- **Deliberate exception to the precedence order:** a Program that already has an Admin, corrections or Music Submission
  claim gets no alias claim. An alias is Wikipedia's music with one fix, so it must not outrank human-picked music,
  even though origin `corrections` normally ranks above Music Submissions. `program_music` for the same Program wins.
- The raw string is also stored as a Piece name with origin `corrections`, after the normaliser has run, so it never
  changes the normaliser's own matching within that Import.
- **Grades come from the picked Piece** (PRD rule 5): identified with an external key, credited with an Artist or Source,
  otherwise title only (`normalise.piece_grade`).
- **A line with `title` defines a new Piece** under that slug, with its Source, composer Artists and Genres.
  - Definitions are processed before alias-only lines. The revert deleted the file's Pieces, so an alias line written
    above its definition would otherwise fail on every Import.
  - **Only new Pieces.** A `title` on a slug that already exists logs `corrections slug taken by another record`, skips
    the definition, and still applies the alias. Retitling an imported Piece in place was tried and removed: it broke
    ADR 0002's "human fixes live in separate rows". Fixing an imported Piece's title or credits waits for the R2 editors.
  - **A defined Piece is recreated on every Import,** under a new ID. Its slug, and so its URL, stays while the line does.
  - **Its slug can pass to an imported Piece.** The revert frees the slug before the music step, so if Wikipedia's text
    later yields the same Piece, the normaliser creates it under that slug and the file's line only aliases it. The
    "slug taken" problem then repeats every Import until the line's `title` is removed.
- Not logged: an alias whose raw string matches no Wikipedia entry.

### `program_music`: Program key → ordered Arrangements

- Program key: `{skater|team: slug, season: start year, segment_type, seq (default 1)}`.
- Writes one `corrections` claim whose raw text is the Piece titles, one per line, with no article (it is the Admin's,
  not Wikipedia's, so it needs no attribution). Each Arrangement defaults to style `original`, optional `performer`.
- **One unknown Piece slug skips the whole line:** a partial ordered list would be wrong.
- Two lines that reach one Program (possible after a merge) log `corrections line repeats a Program`; the first wins.

### `skater_merges`: duplicate slug → survivor slug

- Moves the duplicate's keys (its slug included, so the old URL resolves to the survivor), names, Team places, Programs
  and Performance links.
- **Programs with the same key merge:** Performances move, and so do music claims of an origin the survivor lacks. Where
  both have a claim of the same origin, the survivor keeps its own.
- The emptied duplicate Skater and Program rows are kept, so undoing is plain updates.
- Known gaps, noted on #46: Team merges are not handled (two Teams can end up with the same members), and the web links
  `min(slug)`, so a merged-away misspelling can become the survivor's link when it sorts first.

### `video_hides`: YouTube ID + Performance key

- Performance key: `{competition: slug, discipline, segment_type, entry (as printed), level (default: the Competition's),
  round (default: main round)}`.
- Hides every link between that video and that Performance, whatever its start time.

## Validation (before any fetch)

Shape only: keys that match no record are found at replay and logged, never fatal. The file fails the Import when:

- a section is unknown, a field is unknown or missing, or a value has the wrong type. Unquoted values YAML misreads
  (`00013665` is octal, `yes` is a boolean) get a "quote it" error;
- a mapping repeats a key (PyYAML would silently keep the last one, dropping a fix);
- a raw string or a Program key is listed twice, or a slug is defined twice;
- a merge merges a Skater into itself, or chains (a survivor is also merged away);
- an alias-only line has Artists, a Source or Genres (those need a `title`);
- a YouTube ID is not 11 characters, or a Discipline, Segment type or level is not one of the known values.

## Problems logged at replay

| Kind | When |
| --- | --- |
| `corrections line with an unknown key` | A slug, Program or Performance key matches nothing. The key says where, e.g. `program_music[2].music[1].piece`. |
| `corrections slug taken by another record` | A `title` line names a slug that already exists. |
| `corrections line repeats a Program` | A second `program_music` line reaches the same Program. |

## Side effects worth knowing

- Records the file created are deleted and recreated every Import, so their IDs change; nothing links them by ID.
- The fetch phase runs before the revert, so `normalise.prepare` sees the corrected state. It passes on only strings
  and evidence, never IDs, so no link can leak; at worst it changes which paid normaliser questions are asked.
