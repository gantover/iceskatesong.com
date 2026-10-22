# iceskatesong.com: product requirements

A website to find the music of ISU figure skating Programs and watch the Performances. A visitor searches a piece of music and finds every Skater and Team who skated to it, or searches a Skater and walks their career Season by Season, with a video of each Performance where one exists.

This PRD is the build-ready spec. Every decision in it was made on the [wayfinder map][map]; the linked tickets hold the reasoning and evidence. Domain terms are defined in [`GLOSSARY.md`](GLOSSARY.md). Hard-to-reverse choices are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Goals

1. **Video coverage is the top value.** Most Performances should have a watchable video. Music on a Performance is nice; a clickable video is much better. When trade-offs arise, video wins over music completeness. Any YouTube video of a Performance qualifies (official ISU, TV broadcasters, fan uploads); the Competition itself must be ISU.
2. **Music search that finds every Performance.** Searching a Piece finds every Program that used it, even where the music data is messy, and says honestly how sure each link is (the **match grade**).
3. **No duplicates.** The same Skater, Team or Piece must not appear twice. This is the project's hardest requirement and shapes the data model.
4. **Cheap and simple to run.** About €0/month on the owner's homeserver, one Admin, least code, proven tools, no speculative flexibility.

## Users

- **Visitors**: fans, skaters and choreographers. Anonymous; no accounts. From R2 they can submit videos and flag mistakes; from R3 they can suggest music.
- **The Admin**: one person (the owner). Starts Imports, fixes data, and (from R2) works the Review Queue. Every Admin change is logged and reversible.

## Scope

**In scope**
- ISU Competitions only, senior and junior, all four Disciplines.
- History from 2004–05 (the IJS era) to today. Pre-2004 only if a usable data source appears (it would also reopen ADR 0001).
- Multiple names per Skater, Team and Piece from day one (EN display name plus JA/RU aliases), so search finds 羽生結弦 and Плющенко.

**Out of scope**
- Hosting or downloading video files. YouTube embeds only.
- Non-ISU competitions.
- Individual recordings. Arrangement is the finest music grain.
- Translating the UI (the data is multilingual-ready).
- User accounts and moderator roles.
- Automatic audio recognition of videos: sending YouTube URLs to a recognition service breaks YouTube's terms ([Can an external service name a Performance's music from its YouTube URL, once per video?][t15]).
- Asking the ISU for consent ([Ask the ISU for written consent to reuse results data][t12]). The site is non-commercial, republishes facts only, crawls politely and attributes fully. An ISU objection reopens ADR 0001.

## Releases

Built and shipped in this order ([In what order do we build data, submissions and browsing?][t8]). Each release is public when done.

| Release | What visitors get | What the Admin gets |
|---|---|---|
| **R1** | Read-only site: every ISU Performance 2004–05 on, official ISU videos, Wikipedia music with match grades, Skater and Piece search | "Import now" button, Import status and problems, fixes via the repo-kept corrections file |
| **R2** | "Submit a video" on a Performance, Flags ("Wrong video?", "Wrong music?") | Review Queue, edit screens (reassign, hide, merge, split, edit music), reversible audit log, Block |
| **R3** | "Suggest music" on a Performance's Program | Music Submissions in the Review Queue, grouped by Program |
| **R4** | Submit a bare YouTube URL, matched automatically, auto-published above a threshold | (not specified: needs its own wayfinding effort before build) |

Public launch is R1. It does not wait for anything from the ISU.

## Data

### Data sources

ISU results are the **only** data source that creates records ([ADR 0001](docs/adr/0001-isu-results-are-the-only-record-creator.md)). Everything else attaches to existing records ([Which data sources feed the import, and in what precedence?][t7]).

| What | Data source | Notes |
|---|---|---|
| Competitions | A repo-kept list of ISU event URLs | The result hosts have no index. Seeded once from 2004–05, ~25 events added per Season. City and dates come from each event's index page. |
| Segments, Performances, results, Skaters, Teams | ISU result pages (`isuresults.com` = `results.isu.org`) | The 8-digit ISU ID is the Skater/Team key. ISU results carry **no music** ([How much music data do ISU results carry, 2004–05 to today?][t2]). |
| JA/RU names, ISU ID → Wikipedia article crosswalk | Wikidata (CC0), property P2694 | Display name stays the ISU (Latin) name; JA/RU names become aliases. |
| Music per Program | English Wikipedia program tables, reached only through the Wikidata crosswalk | Near-complete for seniors back to 2004–05, partial for juniors ([Which non-ISU sources list music per Program, and can we use them?][t3]). No name matching to Skaters. |
| Official videos | The uploads playlists of the two ISU YouTube channels (Skating ISU, ISU Junior Grand Prix), via the YouTube Data API | Per-skater clips from ~2011–12 (junior) and ~2019–20 (senior); 2016–17 to 2018–19 senior only as full-segment streams ([What can we get from YouTube: official ISU videos and bare-URL metadata?][t4]). |
| Music from visitors | Music Submissions (R3) | |
| Videos from visitors | Video Submissions (R2) | |

A Wikipedia row for a Season and Segment type with no ISU-derived Program creates nothing: it is logged as an Import problem.

Not used: live ISU bios (season-correct for ~15% of entries), skatingscores.com (robots.txt bans bots), Fandom wiki (ToU bans scrapers), GoldenSkate and Anything GOEs (unlicensed). MusicBrainz and Wikidata are optional cross-references on Pieces, never their identity ([Can MusicBrainz or Wikidata anchor Piece and Source identity?][t5]).

**Music precedence** (highest first): Admin > corrections file > approved Music Submission > Wikipedia > ISU. Each claim is its own row, so a lower one never overwrites a higher one, and an Import rewrites only its own rows.

### Data model

Fully specified in [ADR 0002](docs/adr/0002-data-model-identities-and-correction-survival.md) ([What are the data model's entities, identities and dedup keys?][t9]). The essentials:

- Every record has our own ID plus **keys** in one shared key table, unique on `(system, value)`: ISU Skater/Team IDs, Wikidata QIDs, MusicBrainz work IDs, and a never-changing **slug**.
- **Corrections survive re-imports** by four rules: a merge moves keys and aliases to the survivor; Skater/Team and Program links on a Performance are set on insert only; human facts are their own origin-tagged rows; an Import never resets a status (except its own Performance `gone` flag).
- Music is **flat**: a Piece is the most specific work the data names; Pieces never nest; each has at most one Source, 0..n credited Artists and Genre tags. A Program's music is an ordered list of Arrangements (Piece, Style, optional performer). The raw music string is always kept.
- A **Performance video** is (YouTube ID, optional start seconds, Performance), origin `official`/`admin`/`submitted`, status `active`/`hidden`. One stream can serve many Performances; a Performance can have many videos. YouTube metadata lives only in a cache refreshed within 30 days (YouTube ToS).
- The Review Queue is a query over pending Submissions and open Flags, not a table.

### Import

One Import pulls every data source in one job ([How does an Import run end to end?][t13]).

- **Trigger**: only the Admin's "Import now" button. It inserts a `pending` row; the long-running `import` service polls every 30 s and claims it atomically, so a double-click can't start two. On startup the service marks any `running` row `failed` ("interrupted"). No schedule.
- **Fetch phase** (no transaction): validate `corrections.yaml` (invalid → `failed` before crawling); conditional GETs on **every** listed event's index and `SEGxxx` pages (~6k pages; past results do change); Wikidata crosswalk and labels; Wikipedia articles re-downloaded only when their revision changed; the ISU YouTube uploads playlists plus a refresh of cache rows older than 25 days. One request at a time, 1 req/s per host, User-Agent `iceskatesong-import/1.0 (<contact email>)`. Every body is cached gzipped on a volume with a `fetched_pages` row. A fetch that fails 3 times keeps the cached copy and logs a problem.
- **Apply phase** (one Postgres transaction, holding the Import advisory lock): re-parse **all** cached pages, so a parser fix applies without a re-crawl. Order: ISU, names, music, videos, then the corrections file. A page that fails to parse leaves its Segment untouched. After a Segment parses cleanly, its Performances whose key wasn't seen are marked `gone` (hidden, never deleted, cleared if they reappear).
- **Outcome**: `succeeded` with per-entity counts and a problem count, or `failed` (rolled back) only for systemic errors: invalid corrections file, database error, or more than ~20% of fetches failing.
- **`import_problems`** rows (step, kind, URL or key, JSON detail) for: fetch failed, parse failed, Team member created, Wikipedia Skater with no crosswalk, Wikipedia row with no Program, music string with no alias match, official video with no Performance match, corrections line with an unknown key, vanished import key. Problems older than the last 10 Imports are pruned.
- **Parser variants**: 2004–05 events use a different results vendor (uppercase filenames, no `seasonXXYY/` folder). Team members are matched to Skaters by normalised name + nationality (ISU Team IDs don't link to Skaters); a miss creates a Skater and logs a problem.

### Official video matching

Each Import links official clips to Performances after the ISU apply ([How does the Import match official ISU videos to Performances?][t17]). Measured 99% recall with no wrong links seen.

1. Skip what isn't one Performance: other sports, highlights, interviews, galas, `LIVE`, `#Shorts`, "Winner(s)", and clips under ~100 s.
2. **The title must name the event**: the event's city (from the ISU index) or a code-kept event-type alias (`wc` → "World Champs", `gpchn` → "Cup of China", …), with the year matching the event's start or end calendar year. Only a title without a year falls back to the `publishedAt` window (start − 2 days to end + 10 days). A match found by the window alone is logged, not linked.
3. Pick the Segment from title words (junior channel = junior; Ladies = Women; Short Dance = Rhythm Dance; "Free" in dance = Free Dance).
4. Pick the entry: every ISU surname of the entry appears in the title, diacritic-insensitive, one-edit fuzzy fallback; ties broken by given names and nation.
5. Anything else, including titles with no Segment type, goes to `import_problems`.
6. **Full-segment streams** (over 30 min, not practice, ceremony or medals) link to every Performance of their Segment with an empty start time; a "Skaters N–M" stream links only that start-number range. Untimed streams play last.
7. Titles are a transient signal: we store only the YouTube ID and our own link.

**Play order** on a Performance: clips and timed streams first, untimed streams last, each in origin order (`official`, `admin`, `submitted`), skipping any video blocked in the viewer's `CF-IPCountry`.

### Music and match grades

Raw Wikipedia music text becomes Pieces, Arrangements, Artists and Sources through a normaliser: rules → Wikidata → fuzzy alias match → LLM on the leftovers ([Can raw music strings become Pieces and Arrangements without duplicates?][t10]). Text-only normalising missed the owner's 95% bar (errors in composer, Source and Style, never the Piece), so every Program → Piece link carries a **match grade** shown to visitors:

- **identified**: anchored to an external ID (today the Wikidata QID of Wikipedia's own title link). ~34% of occurrences.
- **credited**: the composer or Source appears in the entry's own text. ~41%.
- **title only**: a bare title. ~13%.

Rules:
1. For imported music the grade comes from **that entry's own text**, not the Piece: a bare "Tango" merged into an anchored Piece stays title only.
2. For an identified Piece, composers come from Wikidata, not from parsing "X by Y".
3. **No facts from LLM memory.** Only fields found in the text or in Wikidata are kept.
4. **A bare title never merges on title alone.** It stays its own Piece until a stronger signal joins it.
5. For human-picked music (Admin, corrections file, approved Music Submission) the grade comes from the picked Piece: external key → identified; Artist or Source → credited; else title only.
6. Entries where nothing parsed go to `import_problems`; wrong merges and credits are fixed in the corrections file (R1) or the Admin screens (R2).
7. The LLM result is cached by raw string, so later Imports pay only for new strings. Expected cost ~$7 one-off for the full corpus; a hard spend cap must allow that first run.

### Corrections file (R1 only)

`corrections.yaml` in the repo, referencing records only by keys, with four sections: `piece_aliases` (raw string → Piece slug, new Pieces defined inline), `program_music` (Program key → ordered Arrangements), `skater_merges` (duplicate slug → survivor slug), `video_hides` (YouTube ID + Performance key). Every Import replays the whole file and replaces all corrections-file rows, so deleting a line undoes the fix. Git history is the audit trail. At R2 it moves into the database and the file is deleted.

## Public site

### Search

Postgres alone: `pg_trgm` + `unaccent` on a generated `search_key` column per searched table (Pieces, aliases, Sources, Artists, Skaters, Teams), and `english` full-text search over the raw Wikipedia music text ([Can Postgres alone power the site search?][t20]).

- Substring search from 3 characters; anchored prefix match below that. Typos and missing accents match (`plushchenko` → Plushenko, `kevin aym` → Kévin Aymoz).
- JA/RU names are aliases of the same Skater; no engine links Hanyu to 羽生結弦 by itself.
- **The database must never be created with the `C` locale** (pg_trgm would silently index nothing for Japanese or Cyrillic). Keep the image default (`en_US.utf8`).
- Escape hatch if short kanji queries become a problem: the PGroonga image.

### Pages

Layout A: one page per record, single column, works on mobile ([What do the public browse pages look like?][t19]).

- **Home**: one search box with example chips. As-you-type dropdown grouped into Skaters, Music, and "In music text, not matched to a Piece". The search box is in the top bar on every page.
- **Skater page** (and a **Team page** built the same way): Season tabs, newest first. Each Season lists Competition cards with one row per Segment: rank, score, music with grade badges, video marker. A Skater page also lists the Performances of their Teams.
- **Piece page**: title, composers, Source, Wikidata link, Skater and Program counts; one collapsible block per Skater (open when ≤4 Skaters) with their Programs (Season, Segment, grade, raw text) and each Program's Performances.
- **Performance page**: breadcrumb to the Skater's Season; video first (beside the result and music on desktop, stacked on mobile); result card with the ISU result link; music card with grade badges, raw Wikipedia text and article link; "Same Program, other Competitions".
- **Video slot**: a click-to-load placeholder served by us (YouTube logo, video title, one-line privacy notice; no `i.ytimg.com` thumbnail before the click). The click loads the `youtube-nocookie` player. Alternatives listed under the player, the untimed stream labelled "untimed, plays last". Geo-blocked videos are skipped, or the slot says "Not available in your country". No video: "No video yet".
- **Grades**: a badge after each Piece on every music line; music search hits show the grade mix ("15 Programs: 2 identified, 13 credited").
- **R2/R3 entry points** are laid out in R1 and disabled: "Wrong video?" and "Submit another video" under the player; "Wrong music?" and "Suggest music" under the music card; "Wrong music?" on the Piece page.
- Performances marked `gone` are hidden everywhere.
- **Visual style**: simple and elegant; Tailwind v4 + shadcn-svelte with a dark/light toggle (follows the OS, manual override). The theme (palette, fonts, radius) is picked by the owner from examples once the skeleton exists; reference: [OpenUI F1 dashboard](https://www.openui.com/demo/f1-dashboard).

### Legal and attribution

([What legal pages and attribution must the R1 launch carry?][t21]; research, not legal advice; assumes the owner lives in Belgium.)

- **Footer pages** with a contact email: **Privacy** (who runs the site; "uses YouTube API Services" with Google's Privacy Policy link; Cloudflare, logs, the Admin's Cloudflare Access login, YouTube after a click; legal bases, retention, rights, the Belgian DPA; a section for the Skaters listed with a contact for objections), **Terms** (YouTube ToS link binding users, no warranty, not affiliated with ISU, YouTube or Wikimedia), **Sources** (ISU results, English Wikipedia CC BY-SA 4.0 "modified", Wikidata CC0, YouTube).
- **Per page**: the exact ISU result link on Performance and Competition views; the Wikipedia article link and "CC BY-SA 4.0, modified" next to Wikipedia-sourced music (one line per page on the Skater page).
- **No cookie banner**: no analytics, no third-party CDN or Google Fonts; every asset self-hosted.
- No date of birth or height from ISU bios (junior events include minors).
- The Import reads each video's "made for kids" flag.
- Ops: Docker log rotation; don't log visitor IPs, or keep them 14 days at most; check Cloudflare Bot Fight Mode.

## Admin

### R1

Under `/admin` in the same web app. Auth by **Cloudflare Access** (owner's email only) plus a fail-closed check of the `Cf-Access-Jwt-Assertion` JWT on every `/admin` request ([Which web framework runs the public site and the Admin panel?][t18]).

- "Import now" button, current and last Import status with counts.
- The latest Import's problems grouped by kind.
- A warning when the oldest YouTube cache row is older than 25 days (the Admin should run an Import; the YouTube ToS requires refresh within 30 days).

### R2: Review Queue, edit screens, audit log

Layout A, "Inbox": three tabs, **Review Queue**, **Records**, **Audit log** ([What do the R2 Admin screens look like?][t14]). Every record is chosen with a **search picker**; editors never create records inline (a separate **New record** page does). Every action is one audit change with an optional note.

- **Video Submission** item: embed, hints, hashed IP, a warning when the YouTube ID is already linked. **Approve** (Performance picker prefilled with the target; start time `h:mm:ss`) creates a `submitted` Performance video. **Reject**. **Block submitter**.
- **Flag** item: reason, hashed IP, and the target's editor embedded. Fixing the data does **not** close the Flag; the Admin clicks **Resolve** or **Dismiss**. **Block submitter**.
- **Block**: adds the HMAC-hashed IP to a block list (audited, reversible) and, in the same change, rejects that hash's pending Submissions and dismisses its open Flags. New ones from the hash are refused.
- **Performance editor**: **Move to Program** (reassigns the Skater/Team), videos table with editable start time, **Hide/Unhide** per link, **Add video** (`admin` origin).
- **Program editor**: raw text and claims by origin with the shown one marked; **Edit music** (ordered Arrangements, pick-only); optional "add raw text as alias"; **Split** (mid-season music change → new Program `seq + 1`); **Merge** a duplicate Program.
- **Skater / Team / Piece / Artist / Source record**: **Rename** (old name kept as alias), **Add alias**, **Add key** (Wikidata QID or MusicBrainz work ID only), where used, **Merge a duplicate into this record** with a preview (Skater/Team merges also merge colliding Programs). **Skater split**, refused when a Program has Performances on both sides.
- **New record** page: Piece (title, composer Artists, Source, Genres), Artist or Source, with a near-match warning (`pg_trgm` over titles and aliases) that never blocks.
- **Audit log**: changes with expandable before/after rows and **Revert**. A generic Postgres trigger writes audit rows when `app.audit_change` is set (Admin transactions set it, Imports don't). Revert is a new change and refuses, naming the later changes, if a row no longer equals its after-image.
- Admin edits take the Import advisory lock and show "Import is applying, try again in a few minutes" while it's held.
- **Corrections file migration**: a one-off step relabels its rows as Admin rows with one audit change each ("migrated from corrections file") and deletes the file.

## Submissions and Flags

### R2: Video Submissions and Flags

- **Video Submission**: "Submit a video" / "Submit another video" on a Performance. A YouTube URL plus optional hints, pre-targeted at that Performance. No bare-URL matching, no title parsing, no LLM. **Every one goes to the Review Queue**; nothing auto-publishes.
- **Flag**: "Wrong video?" (a Performance video), "Wrong music?" (a Program's music), or a wrong Performance assignment, with a reason.
- **Anti-abuse**: anonymous, Cloudflare Turnstile loaded only on these forms, rate limits, IPs stored only as an HMAC keyed by a secret (IPv6 by its /64), blocked hashes refused.
- **Legal additions**: a Contributions clause in the Terms, a "you agree" line on the forms, and Submissions, Turnstile and IP-hashing sections on the Privacy page.

### R3: Music Submissions

([What does a Music Submission carry, and when may an approved one re-link a Program?][t22])

- **Form** ("Suggest music" under a Performance's music card): free music text (required) plus one optional link (MusicBrainz, Spotify, Apple Music, Shazam, a YouTube upload of the original). Targets the Performance's **Program**.
- **Review Queue groups pending Music Submissions by Program.** Approval opens the pick-only music editor prefilled with the music shown now, plus the alias matcher's hits on the submitted text. Saving writes the full ordered Arrangement list as a `submission` claim and rejects the other pending suggestions for that Program in the same change.
- **Re-linking to a different Piece is always allowed**: the Admin is the guard. The approval screen shows a before/after ("replaces *X* with *Y*"). A mid-season change is handled by **Split** first.
- Links never become keys automatically; recording links stay on the Submission. The Admin adds Wikidata/MusicBrainz work keys by hand with **Add key**.
- A later Wikipedia change never outranks an approved Music Submission; the Program editor shows the disagreement.

### R4: bare-URL Video Submissions (later effort)

A visitor pastes any YouTube URL plus hints; the site finds the Performance itself (reusing the official-video matcher, ISU results and LLM validation) and publishes above a confidence threshold. **Not specified**: the matching, the confidence score and the threshold need their own wayfinding effort before any R4 build. Known constraints: titles are a secondary signal only (YouTube ToS), metadata refresh ≤ 30 days, geo-blocked official videos may need a fallback. Owner idea: the same matcher could discover unofficial videos for videoless Performances (YouTube `search.list` costs 100 units and allows ~100 calls/day, so it must be targeted).

## Stack, hosting and operations

([Where does it run: hosting, database and deployment?][t11], [Which web framework runs the public site and the Admin panel?][t18], [What do the hosting options cost, and how do they scale?][t6])

- **Repo layout**: `compose.yml`, `web/`, `import/`, `db/` at the root.
- **Host**: the owner's Radxa Rock 5 ITX (ARM64, 24 GB) behind the existing Cloudflare Tunnel; Docker volumes on NVMe/SATA. Secrets in `.env` on the box, never in git.
- **Compose services**: `migrate` (one-shot), `web`, `import`, `postgres`, `backup`, `cloudflared`. `web` and `import` start only after `migrate` succeeds.
- **Database**: Postgres (pinned current major) with `pg_trgm` and `unaccent` (plus the 3-line `IMMUTABLE` `unaccent` wrapper for generated columns); never the `C` locale.
- **Schema**: plain-SQL Alembic migrations in `db/` (`op.execute("""…""")`, no models, no autogenerate), run by the `migrate` service.
- **`web`**: SvelteKit 3 with `adapter-node`, server-rendered on every request, Node 24 LTS (`node:24-slim`), pnpm 12 with a 7-day minimum release age, frozen lockfile. Queries with Kysely + `kysely-codegen` on `pg` (trigram operators as `sql` fragments). Tailwind v4 + shadcn-svelte (its Combobox is the Admin search picker). `Cache-Control` headers on public pages.
- **`import`**: Python managed with `uv`, long-running, polls for `pending` Imports. The normaliser's LLM is a small Claude model (the prototype used Haiku) behind an API key in `.env`.
- **Deploy**: a script on the box, `git pull && docker compose up -d --build`, with a read-only deploy key.
- **Backups**: nightly `pg_dump` → gzip → Cloudflare R2, 30-day retention, by the `backup` sidecar; one restore drill onto the owner's laptop at setup, restore command kept in the repo.
- **Monitoring**: Healthchecks.io ping from each backup; a free external uptime check on the public site; email alerts. Logs via `docker compose logs` with rotation.
- **Path to grow** (nothing built until a trigger fires): home downtime hurts → restore onto a Hetzner/OVH VPS (~€5–7/mo) and repoint the Tunnel; the box gets busy → Cloudflare Cache Rules on public pages; DB off the box → managed Postgres.

### Testing

Vitest for non-trivial logic in `web` (JWT check, search queries, Admin actions); query tests run against a throwaway database in the Compose Postgres, migrated by Alembic. pytest for the `import` parsers and matchers, against cached real pages. No browser test suite in R1.

### AI harness

([Which AI harness tools get installed before implementation?][t23]) The first R1 issue writes a checked-in, project-scoped `.mcp.json` (Playwright MCP, official Svelte MCP) and `.claude/settings.json` allowlist (`pnpm`, `uv run`, local `docker compose`, `psql`, `gh issue`; ssh and the deploy script always prompt). No Postgres, docs, GitHub or Cloudflare MCPs. The homeserver is `ssh rock5itx` (needs the owner's Tailscale login): read-only commands freely, deploys only when the owner asks.

## Open questions

- **R4**: bare-URL matching, confidence score, auto-publish threshold (see above). Needs its own wayfinding effort.
- **Wayback ISU-bio enrichment**: archived ISU bio snapshots could fill junior music from 2011–12 on (two page layouts, Program granularity). Unscheduled; decide at R3 kick-off whether it's worth building alongside Music Submissions, and its precedence against Wikipedia.
- **Pre-2004 data**: only if a usable data source appears.

## Changes from the first draft of this PRD

- Video Submissions **never create** Skaters, Programs or Performances: they only attach to records the ISU results created (ADR 0001). The first draft's "create a new one if there is none" is dropped.
- Imports run only when the Admin presses "Import now", and re-check every listed event, not a weekly current-season job.
- Music comes mainly from Wikipedia, not from Submissions. Submissions matter most for video.

[map]: https://github.com/gantover/iceskatesong.com/issues/1
[t2]: https://github.com/gantover/iceskatesong.com/issues/2
[t3]: https://github.com/gantover/iceskatesong.com/issues/3
[t4]: https://github.com/gantover/iceskatesong.com/issues/4
[t5]: https://github.com/gantover/iceskatesong.com/issues/5
[t6]: https://github.com/gantover/iceskatesong.com/issues/6
[t7]: https://github.com/gantover/iceskatesong.com/issues/7
[t8]: https://github.com/gantover/iceskatesong.com/issues/8
[t9]: https://github.com/gantover/iceskatesong.com/issues/9
[t10]: https://github.com/gantover/iceskatesong.com/issues/10
[t11]: https://github.com/gantover/iceskatesong.com/issues/11
[t12]: https://github.com/gantover/iceskatesong.com/issues/12
[t13]: https://github.com/gantover/iceskatesong.com/issues/13
[t14]: https://github.com/gantover/iceskatesong.com/issues/14
[t15]: https://github.com/gantover/iceskatesong.com/issues/15
[t17]: https://github.com/gantover/iceskatesong.com/issues/17
[t18]: https://github.com/gantover/iceskatesong.com/issues/18
[t19]: https://github.com/gantover/iceskatesong.com/issues/19
[t20]: https://github.com/gantover/iceskatesong.com/issues/20
[t21]: https://github.com/gantover/iceskatesong.com/issues/21
[t22]: https://github.com/gantover/iceskatesong.com/issues/22
[t23]: https://github.com/gantover/iceskatesong.com/issues/23
