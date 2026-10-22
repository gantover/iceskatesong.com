# Can an external service name a Performance's music from its YouTube URL?

Research for [issue #15](https://github.com/gantover/iceskatesong.com/issues/15). Sources were checked on 2026-10-22.

## Answer in brief

**No. Sending a YouTube URL to AudD or ACRCloud breaks YouTube's terms, and fingerprinting is weakest on exactly the music we are missing.**

- **Services exist.** AudD's enterprise endpoint and ACRCloud File Scanning both take a YouTube URL, fetch the audio on their own servers, and return every recognised track with timestamps (§1).
- **Terms block it.** The service downloads the audio for us, which counts the same as downloading it ourselves.
  - The YouTube API Developer Policies ban us from enabling "others to … download … YouTube audiovisual content" and from isolating its audio (§5).
  - Both vendors make the customer warrant that it holds the rights to what it submits.
  - Embeds-only rules this out, whatever it costs or however accurate it is.
- **Weak where we need it.** Fingerprinting matches one exact released recording. Our 14% bare-title gap is likely mostly film cues, re-orchestrated edits and commissioned music, and fingerprinting has the least to match there (§3).
- **No path to a Piece ID.** Neither service returns a MusicBrainz *work* ID. You get at most a MusicBrainz recording ID or an ISRC, and in MusicBrainz as a whole fewer than about 20% of recordings link to a work (§2).
- **Cheap, if it were allowed.** AudD costs about $0.05–0.10 per program, or roughly $150–300 one-off for 3,000 videos. ACRCloud prices are visible only after login (§4).
- **No YouTube Content ID route.** The "Music in this video" panel is not in the Data API. The Content ID API is for content owners only, and scraping the panel is forbidden (§6).

## Method and evidence quality

- **Read, not tested.** Everything comes from vendor docs, pricing pages, terms, SDK source and YouTube's policies. **No live recognition calls were made**:
  - Both vendors need a signup.
  - A YouTube-URL test would itself be the act the YouTube terms forbid (§5).
- **Hit rate has no direct data.** No vendor publishes accuracy for user-uploaded broadcast audio, and nothing published covers skating. §3 uses the published Shazam algorithm paper as a baseline for how fingerprinting behaves; it is not AudD or ACRCloud accuracy.
- **Not legal advice.** The terms reading is a plain reading of each document.

---

## 1. Services: YouTube URL input, offsets, medleys

| | AudD enterprise endpoint | ACRCloud File Scanning | Others |
|---|---|---|---|
| YouTube URL input | Yes. "You can also send a URL of a web page that contains audio or video instead of the URL of the actual audio file" ([docs](https://docs.audd.io/enterprise.md)). AudD's own [`youtube-recognizer`](https://github.com/AudDMusic/youtube-recognizer) tool passes a YouTube watch URL straight to this endpoint. | Yes. `data_type=platforms`: "Currently, supported platforms are Youtube, Twitter, Tiktok, Vimeo, Brightcove…", e.g. `https://www.youtube.com/watch?v=…` ([FsFiles API](https://docs.acrcloud.com/reference/console-api/file-scanning/file-scanning.md)). The console also takes channel and playlist URLs ([tutorial](https://docs.acrcloud.com/llms-full.txt)). | **AcoustID**: no snippets ("designed for identifying full audio files", [FAQ](https://acoustid.org/faq)), and we would have to fingerprint audio we downloaded. **ShazamKit**: an app SDK that matches audio the app holds ([Apple](https://developer.apple.com/shazamkit/)), with no URL input. Gracenote and Audible Magic are sales-only and not checked further. |
| Start offset | `skip_first_seconds`, or `use_timecode=true` to read the URL's `t=` / `start=` parameter. | **None.** The upload takes only `file`, `data_type`, `url`, `name` and `isrc`. | |
| End offset | No end parameter, but `limit` caps the number of 12-second chunks scanned, so start + `limit` bounds a window. | None. Scan the whole video and slice the results by `offset`. | |
| Medleys | Yes. The whole file is cut into 12 s chunks, each chunk returns its own `songs[]` with an `offset` into our file, and `accurate_offsets=true` refines start and end. `skip`/`every` scan only some chunks. | Yes. With the "Traverse" policy, `results.music[]` holds one entry per match with `offset` and `played_duration`, plus `sample_*`/`db_*` offsets. | |
| Covers / re-recordings | Fingerprint only. A humming method exists but is hidden in the docs, with "no accuracy" guaranteed. | **Cover Song Identification** engine (container `engine` 2 or 3) matches "by melody" across "key, tempo, structure, instrumentation" ([product page](https://www.acrcloud.com/cover-song-identification/)). "Derivative Works Detection" for sped-up or pitch-shifted tracks is limited to "up to 10 files for testing", then sales. | |

**Full-segment streams.** One 3–6 h stream holds many Performances (see the [YouTube research](https://github.com/gantover/iceskatesong.com/blob/research/youtube-metadata/research/youtube-metadata.md)):
- **AudD** can scan one window per Performance with `skip_first_seconds` + `limit`.
- **ACRCloud** scans the whole stream once, and the results are split per Performance by `offset`.

## 2. Identifiers per match, and the path to a MusicBrainz work

| Field | AudD standard (`api.audd.io`) | AudD enterprise (the endpoint that takes YouTube URLs) | ACRCloud |
|---|---|---|---|
| Artist, title, album, label, release date | Yes | Yes | Yes |
| ISRC / UPC | Only inside the Apple/Spotify blocks | "you need an enterprise account to get ISRCs and UPCs" ([docs](https://docs.audd.io/enterprise.md)) | `external_ids.isrc`, `upc` |
| Spotify / Apple / Deezer IDs | Via `return=spotify,apple_music,deezer` ([docs](https://docs.audd.io/.md)) | **Not offered.** The docs send you to the standard endpoint for "the detailed composition data Spotify, Apple Music, Musicbrainz and other hold (and not just links)". | `external_metadata.spotify/deezer/youtube`, behind the "3rd Party ID Integration" option |
| MusicBrainz | `return=musicbrainz` gives a list of `{id, score, title, length}` ([SDK model](https://github.com/AudDMusic/audd-python/blob/HEAD/src/audd/models.py)). A `length` field means a **recording**, not a work (our inference). | Not offered | `external_metadata.musicbrainz.track.id`, a recording or track ID |
| Composer | Apple's `composerName` string, when Apple has one | No | `contributors.composers`, plus `works[]` with ISWC and IPI-coded creators. Both are "+fields", "visible upon request" ([metadata reference](https://docs.acrcloud.com/reference/identification-api/metadata/music.md)). |

The standard endpoint takes an audio-file URL and reads only "the first 12 seconds", so it cannot read a YouTube page. The rich identifiers and the YouTube input are therefore on **different AudD endpoints**.

**From a match to a Piece (MB work):** neither service returns an MB **work** ID. You must hop recording → work in MusicBrainz, or go through ISWC. Coverage, from [MusicBrainz statistics](https://musicbrainz.org/statistics) for 2026-10-21:
- 40,646,500 recordings.
- 7,973,292 recording–work relationships ([relationship stats](https://musicbrainz.org/statistics/relationships)). So **at most about 20% of recordings link to a work**, and fewer if some recordings link to several works.
- 15.5% of recordings carry an ISRC.
- 17.3% of the 2.88M works carry an ISWC.

These are averages over all of MusicBrainz, not weighted toward skating music. The [registries research](https://github.com/gantover/iceskatesong.com/blob/research/music-registries/research/music-registries.md) already showed that the skating long tail (Seimei, film cues, remixes) is where MB and Wikidata lack works.

**Conclusion:** a match tells you *which recording*, and sometimes the composer. It reaches the Piece grain only through our own local alias matching, the same normaliser that Wikipedia strings already go through.

## 3. Hit rate on skating audio

**No published data covers this audio type.** AudD and ACRCloud publish no accuracy figures for UGC or broadcast audio, and a search found nothing on figure skating. The closest primary source is the published algorithm behind Shazam-style fingerprinting ([Wang 2003, "An Industrial-Strength Audio Search Algorithm", ISMIR](https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf)). AudD and ACRCloud run their own engines, so this is a baseline, not their numbers.

- **Noise and commentary are not the problem.**
  - In Wang's tests, recognition with pub noise fell to 50% only at about −9, −6 and −3 dB SNR, for 15, 10 and 5 s samples.
  - "It can correctly identify music in the presence of voices, traffic noise, dropout, and even other music."
  - Crowd noise and a commentator over a broadcast are well within this.
- **Cut edits are mostly fine.** Each 10–12 s chunk is matched on its own, and "discontinuities are irrelevant". A program cut together from a released recording should match chunk by chunk.
- **Other versions fail.** "The algorithm is … very sensitive to which particular version of a track has been sampled."
  - A re-orchestrated, re-recorded or commissioned arrangement is a different recording, so there is nothing in the catalogue to match it against.
  - Wang's matching also assumes the sample plays at the original speed (a "slope of the diagonal line" of 1.0), so tempo-changed edits are at risk. ACRCloud selling sped-up and pitch-shifted detection as a separate product points the same way.
- **ACRCloud Cover Song Identification** is the one feature aimed at other versions. It publishes no accuracy figures.

**What this means for the 14% gap.** Bare-title entries are likely concentrated in obscure film cues, skating-specific edits and commissioned music: the long tail. This is not measured; the normaliser prototype did not classify them.
- When a program uses a commercially released soundtrack recording, a fingerprint can name it. For *Seimei*, MB holds Japanese-titled recordings from the *Onmyōji* OST.
- When it doesn't, fingerprinting returns nothing, or a wrong near match.
- Expect hits mostly on Programs whose music Wikipedia already names well (pop, classical warhorses on commercial recordings), and misses on the long tail.

**Hands-on test: not done, and it needs a signup.**
- **AudD:**
  - The pricing page says the 300-request free trial (14 days, no card) covers the standard endpoint, and that the enterprise endpoint is for "any paid plan" ([pricing](https://audd.io/pricing/)).
  - The enterprise doc says "The first 300 requests are free".
  - So a YouTube-URL test probably needs the $5 Indie plan, and therefore a card.
- **ACRCloud:** a 14-day trial with no card, but it needs a signup.
- **The terms problem applies to the test too.** Either test means having a third party download YouTube audio (§5). It is a follow-up only if the owner accepts that.

## 4. Cost at our scale

**AudD** ([pricing](https://audd.io/pricing/)):
- Indie is $5/month with 1,000 requests included, then $5.00 per 1,000.
- Startup is $450/month with 100,000 included.
- The enterprise endpoint counts **one request per 12 s scanned**.

| Scan of one Performance | Requests | Cost at $5/1,000 |
|---|---|---|
| 4-min program, every chunk | 20 | $0.10 |
| Same with `skip=1, every=1` (12 s of every 24 s) | 10 | $0.05 |
| 3,000 videos (R1 order of magnitude), every chunk | 60,000 | ≈ $300 one-off (Indie: $5 + 59 × $5) |
| 3,000 videos, half the chunks | 30,000 | ≈ $150 |
| Each later Submission | 10–20 | $0.05–0.10 |

- **One-off, not per Import.** Recognition runs once per video, so only new Submissions add cost after that.
- **Minimum to read results.** Results may be cached and stored (§5), so after the backfill month a $5/month minimum would cover about 100 Submissions a month.
- **Free access is possible.** AudD's terms mention free access for "educational, non-profit, open-source, or other socially beneficial purposes" under branding rules, but you have to ask for it.
- **ACRCloud:** "You will have 14 days for the free trial after registration." Prices are "on this page (login required)", both for recognition and for File Scanning ([docs](https://docs.acrcloud.com/llms-full.txt)). No public per-hour or per-1,000 price could be verified.

## 5. Terms

### YouTube

- **[YouTube Terms of Service](https://www.youtube.com/t/terms), Permissions and Restrictions:**
  - You may not "access, reproduce, download … or otherwise use any part of the Service or any Content except: (a) as specifically permitted by the Service; (b) with prior written permission from YouTube and, if applicable, the respective rights holders; or (c) as permitted by applicable law".
  - You may not "access the Service using any automated means (such as robots, botnets or scrapers)" except for search engines, with permission, or as the law allows.
  - What the Terms do allow is to "show YouTube videos through the embeddable YouTube player".
- **[YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies).** These bind us because the pipeline uses the Data API.
  - **III.E, Audiovisual Content:** "You and your API Clients must not, and must not encourage, enable, or require others to: download, import, backup, cache, or store copies of YouTube audiovisual content without YouTube's prior written approval".
  - **III.I, Additional Prohibitions:** "separate, isolate, or modify the audio or video components of any YouTube audiovisual content made available as part of, or in connection with, YouTube API Services".
  - **III.I also bans** using "any technology other than YouTube API Services to access or retrieve API Data, including to access any portion of any YouTube audiovisual content".

Sending a video ID we know from the API to a service that downloads the audio and fingerprints it is "enabling others to download" and "isolating the audio component". It is not a gray zone like the derived-data clause in the YouTube research. **It conflicts with the embeds-only rule.**

### AudD ([API Terms of Service](https://audd.io/terms/), version 2026-07-07)

- **Rights warranty.** The customer "represents and warrants that it has and will maintain all rights, licenses, permissions … necessary to provide Customer Content to AudD".
- **Banned content.** The customer will not submit content "collected through unlawful recording, interception, scraping, surveillance, or monitoring".
- **Indemnity.** The customer indemnifies AudD for claims arising from Customer Content.
- **Results are usable.** The customer may use Results "within the customer's own products and services, including displaying Results to the customer's users", and "may cache and store Results".
- **No resale.** Results may not be resold "as a standalone data product". This matters only if we ever publish a bulk data export.
- **Non-profit access.** Free access for "educational, non-profit, open-source" use comes with branding rules.

### ACRCloud ([Terms of Use](https://www.acrcloud.com/terms/), effective 2026-10-13)

- **URLs count as content.** "Customer Content" explicitly includes "URLs".
- **Rights warranty.** "You represent and warrant that you have all rights, notices, permissions and lawful bases required to submit Customer Content", and "You remain responsible for clearing copyrights, licenses, permissions".
- **Customer-facing use needs a plan.** The Services are for "lawful internal business purposes". Use "as part of a customer-facing product is permitted only where expressly allowed by the applicable plan, order or documentation".
- **No raw media kept.** Raw audio and video are processed transiently and not retained (§5 of their terms).

**Net:** both vendors push the YouTube-rights question back onto us, and we cannot honestly give their rights warranty for third-party YouTube uploads.

## 6. YouTube's own Content ID ("Music in this video")

- **What the panel is.** It appears when "Videos are claimed by one of YouTube's copyright management tools, like Content ID" or use Audio Library music. It shows at most "the first ten songs", and is missing when the copyright owner gave too little data or the video is "made for kids" ([YouTube Help](https://support.google.com/youtube/answer/7680188)).
- **Not in the Data API.** The `videos` resource has no music field. See the [YouTube research](https://github.com/gantover/iceskatesong.com/blob/research/youtube-metadata/research/youtube-metadata.md). `contentDetails.licensedContent` only says whether a partner claimed its own upload.
- **The Content ID API is partner-only.**
  - It is "for YouTube content partners, not all developers or users", and "Access requires a YouTube Content Manager account" ([Content ID API](https://developers.google.com/youtube/partner)).
  - `claims.list` returns only "claims administered by the content owner associated with the currently authenticated user" ([claims](https://developers.google.com/youtube/partner/reference/rest/v1/claims)).
  - The ISU itself could see claims on its own channel's videos, but we cannot.
- **Scraping is forbidden.** Reading the panel from watch pages is scraping, which Developer Policies III.E bans (see the YouTube research).

**No official route exists for a third party.**

## Implications for the project

- **Drop audio recognition of YouTube videos** while embeds-only stands. Reopen it only if the owner gets written permission from YouTube, or if a Submission includes an audio file the submitter has rights to (unlikely).
- **Fill the 14% gap with what we already have.** That means Music Submissions (R3, always reviewed), the Wayback ISU bio lead, and local alias matching. Submitter hints remain the music signal for a video.
- **If the question ever reopens:**
  - Use the AudD enterprise endpoint with `use_timecode`/`skip_first_seconds` + `limit` for cheap scoped scans.
  - Use ACRCloud with Cover Song Identification for re-recordings.
  - Store results as one more data source, below Admin and Music Submission in precedence.
  - Feed the artist and title strings through the same normaliser; never store them as a Piece identity.

## Sources

- AudD API docs: https://docs.audd.io/.md ; enterprise endpoint: https://docs.audd.io/enterprise.md ; pricing: https://audd.io/pricing/ ; API Terms of Service: https://audd.io/terms/ (text served from `https://dashboard.audd.io/api/html.php?url=https://audd.io/terms/`)
- AudD SDK model: https://github.com/AudDMusic/audd-python/blob/HEAD/src/audd/models.py ; youtube-recognizer: https://github.com/AudDMusic/youtube-recognizer
- ACRCloud FsFiles API: https://docs.acrcloud.com/reference/console-api/file-scanning/file-scanning.md ; metadata fields: https://docs.acrcloud.com/reference/identification-api/metadata/music.md and https://docs.acrcloud.com/reference/console-api/file-scanning/metadata/music.md ; Metadata API: https://docs.acrcloud.com/reference/metadata-api.md ; tutorials, trials and pricing pointers: https://docs.acrcloud.com/llms-full.txt ; Cover Song Identification: https://www.acrcloud.com/cover-song-identification/ ; Terms of Use: https://www.acrcloud.com/terms/
- AcoustID FAQ: https://acoustid.org/faq ; web service: https://acoustid.org/webservice
- ShazamKit: https://developer.apple.com/shazamkit/
- Wang 2003, An Industrial-Strength Audio Search Algorithm: https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf
- MusicBrainz statistics: https://musicbrainz.org/statistics ; relationships: https://musicbrainz.org/statistics/relationships
- YouTube Terms of Service: https://www.youtube.com/t/terms ; API Developer Policies: https://developers.google.com/youtube/terms/developer-policies ; Content ID API: https://developers.google.com/youtube/partner ; claims resource: https://developers.google.com/youtube/partner/reference/rest/v1/claims ; Music in this video: https://support.google.com/youtube/answer/7680188
