# What can we get from YouTube? Official ISU videos and bare-URL metadata

Research for issue #4. Checked on 2026-10-22.

## Answer in brief

- **Official videos.** Two ISU channels carry Performance videos: **Skating ISU** (all events) and **ISU Junior Grand Prix** (JGP, from 2011). Coverage per skater:
  - Junior events: good from about 2011.
  - Senior events: good from about 2019. 2017–18 senior events exist only as full-segment streams, and anything earlier only as highlights.
- **Titles can be parsed. Descriptions cannot.** Titles follow a mostly regular `Skater (NAT) | Segment | Competition` pattern. Descriptions are pure boilerplate.
- **Embedding and geo-blocking.** Every sampled video is embeddable. Geo-blocking varies by event: junior events block only BY/RU, while senior Grand Prix Final 2025 blocks about 30 territories, including the US, JP, KR and much of Europe.
- **oEmbed** returns only title, channel name, channel URL and thumbnail. No key and no quota needed.
- **Data API v3 `videos.list`** returns everything we need: description, `publishedAt`, ISO 8601 duration, `regionRestriction`, `embeddable`, tags and localized titles. It costs 1 unit per call, batched by ID, out of 10,000 free units a day.
- **There is no chapters field.** Chapters exist only as timestamps typed into the description.
- **ToS.** Non-authorized API data may be stored for at most 30 days, then it must be refreshed or deleted. Scraping is forbidden. There is a "derived data" clause to keep in mind for auto-matching (see §3).

## Method and evidence quality

- **Channel data was sampled once, by hand.** It came from public watch, playlist and search pages (`ytInitialPlayerResponse` / `ytInitialData`) and the channel RSS feed. This was a manual research sample only: production code must not do this, because the Developer Policies forbid scraping (§3).
- **API fields come from Google's docs, not live calls.** No API key was available.
- **oEmbed was called live.**
- **Coverage claims are sampled, not exhaustive.** They come from about 15 channel searches across seasons.
- **How blocked countries were counted.** A video's `availableCountries` list was compared with a reference video available in 249 countries (`gqfhPl5HYfQ`).

---

## 1. Official ISU videos

### Channels

| Channel | ID | Handle | What it carries |
|---|---|---|---|
| Skating ISU | `UCVZpqbnDjHyScSYGFPMUtYA` | [@SkatingISU](https://www.youtube.com/@SkatingISU) | All ISU disciplines, including speed skating and short track. Figure skating: senior and junior championships, Grand Prix, and the JGP since about 2024. |
| ISU Junior Grand Prix | `UCbv3gsBXzIwotCt2JGySfJA` | [@isujuniorgrandprix](https://www.youtube.com/@isujuniorgrandprix) (legacy `/user/ISUJGP2011`) | JGP from 2011 ([launch article, Sept 2011](https://www.ice-dance.com/site/isu-launches-youtubecom-channel-for-jgp)) to at least 2023 |

The ISU's own "where to watch" pages describe the YouTube channel as the live outlet for the "rest of the world", meaning territories without a broadcast partner. For the JGP 2026/27, those partners are SBS (KR), TV Asahi (JP) and OKKO (RU/BY/KZ) ([ISU](https://isu-skating.com/news/where-to-watch-isu-figure-skating-junior-grand-prix-series-202627/), [ISU Europeans](https://isu-skating.com/figure-skating/news/where-to-watch-isu-figure-skating-european-championships-broadcast-partners/)). This explains the geo-blocking pattern below.

### Coverage by season (sampled)

| Era | Junior (JGP, Jr Worlds) | Senior (GP, Euros, 4CC, Worlds, WTT) |
|---|---|---|
| 2004–05 to 2010–11 | Not found | Not found (a few later "ISU Archives" or retrospective clips) |
| 2011–12 to 2016–17 | **Per-skater clips** (JGP channel). For 2015–16 there are also full-segment streams. | Highlights and "Relive" recaps only, e.g. `Ladies Highlights - ISU Grand Prix Final Marseille 2016` |
| 2016–17 to 2018–19 | Per-skater clips plus full-segment streams | **Full-segment streams (3–6 h)**, e.g. `Men Short Program \| 2017 ISU World Figure Skating Championships Helsinki FIN`. Per-skater clips are rare and some were re-uploaded years later, e.g. Hanyu at 2017 Worlds was published on 2022-07-19. |
| 2019–20 onward | Per-skater clips plus full-segment streams | **Per-skater clips** plus full-segment streams |
| Current (2026–27) | One playlist per segment per event, e.g. `Men Short Program \| Gdańsk 2026` | Same pattern, e.g. GP Final 2025 |

The playlists on the current channel are organised as one playlist per (event, segment). That is a cheap way to enumerate the videos (see §2 on quota).

**Implication:** for 2004–05 to about 2010–11, every Performance video will come from Submissions. Fan uploads of TV broadcasts are plentiful; for example, a search for "Yuna Kim 2009 World Championships free skate" returns dozens of NBC, CBC, BBC and SBS rips. For senior events from about 2011 to 2018, it will be mostly Submissions too, plus the full-segment streams, which need a timestamp to point at one Performance.

### Title formats (real examples)

Current, 2019 onward:
```
Jaewook CHUNG (KOR) | Junior Men Short Program | Gdańsk 2026
Ilia MALININ (USA) | Men Free Skating | Grand Prix Final 2025 | #GPFigure
MIURA / KIHARA (JPN) | Pairs Free Skating | Grand Prix Final 2025 | #GPFigure
FOURNIER BEAUDRY / CIZERON (FRA) | Ice Dance Rhythm Dance | Sheffield 2026 | #FigureSkating
Alysa LIU (USA) | Women Free Skating | ISU World Team Trophy | Tokyo 2025 | #WTTFigure
Adeliia PETROSIAN (AIN) | Women Free Skating | #SkateToMilano | 2025 – Beijing
Sofiia DZEPKA (AIN 2) | Junior Women Free Skating | Xi’An 2026
```
2019–2020:
```
Alexandra Trusova (RUS) | 1st place Ladies | Free Skating | Skate Canada 2019 | #GPFigure
Nathan Chen (USA) | Men Free Skating | ISU GP Finals 2019 | Turin | #GPFigure
Yuzuru Hanyu (JPN) | Men Short Program | ISU Four Continents Figure Skating | #4ContsFigure      <- no year
D. Usacheva | Ladies Short Program | ISU World Junior Figure Skating Championships | #WorldJFigure <- initial, no country, no year
```
JGP channel, 2011–2018:
```
3 Risa SHOJI (JPN) - ISU GP and JGP Final 2011 Junior Ladies Short Program
ISU JGP Brisbane 2011 Junior Ladies Short Program - 3 Vanessa LAM (USA)
2015 ISU Jr. Grand Prix - Torun Ladies Free Skate Kaori SAKAMOTO JPN
Alexandra TRUSOVA (RUS) | Ladies Short Program | Vancouver 2018         <- JGP Final, but no "Junior"
LIVE 🔴 | Ladies Short Program | Linz  2018                             <- full-segment stream
```

**Can titles be mapped to Skater + Competition + Segment automatically?** Mostly yes, with rules and a small lookup table, but there are traps:

- **Year means the calendar year of the event, not the season.** "Gdańsk 2026" is season 2026–27, and "Boston 2025" is 2024–25. Resolve the year against the results data (city + year + level → Competition).
- **Competitions are often named only by city and year,** e.g. "Sheffield 2026" or "Gdańsk 2026". The name is sometimes the GP event's brand ("Skate Canada 2019", "Grand Prix De France 2025") and sometimes a hashtag only. Matching needs a city/alias → Competition lookup.
- **Some titles have no year** (2020 4CC and Jr Worlds). Fall back to `publishedAt`, but re-uploads break this: the 2017 Worlds Hanyu clip was published in 2022.
- **Level is sometimes only implied by the channel.** The 2018 JGP Final clips say "Ladies", not "Junior Ladies". A video on the JGP channel is always junior.
- **Name variants:**
  - casing: `Ilia MALININ` vs `Nathan Chen`
  - an initial only (`D. Usacheva`)
  - surname-only teams (`MIURA / KIHARA`)
  - neutral athletes: `AIN`, `AIN 2`, `AIN2`
  - prefixes: `1st place`, and leading numbers in 2011 titles (probably start order or placement, not confirmed)
  - no separators at all (2015)
- **Segment vocabulary changed:**
  - Ladies → Women from 2021–22.
  - Short Dance up to 2017–18, Rhythm Dance afterwards.
  - "Free Skate" / "Free Skating" / "Free".
  - Pre-2010–11 ice dance had Compulsory and Original Dance. None were found on the official channels, so Submissions will need those Segments too.
- **Full-segment streams** have a title with no skater (`Women Free Skating | Grand Prix Final 2025 | #GPFigure`, 1:40:51). One video covers many Performances.

### Descriptions

Descriptions are **pure boilerplate**: licensing link, subscribe link and social links. Example from `Ocr7hn304pQ`, 2026:
```
To license ISU footage: https://bit.ly/3M7bcaF
SUBSCRIBE to our channel: https://www.youtube.com/SkatingISU?sub_confirmation=1
LIKE us on Facebook: ...
```
The 2019 GP clips add the season's GP calendar (event / city / dates), which is still not per-Performance. **No timestamps or chapters were found,** including on the multi-hour segment streams. Tags are channel-generic (`Figure Skating, Speed Skating, ...`). **All the useful information is in the title.**

### Embeddability and geo-blocking

Every sampled official video had `playableInEmbed: true` and was public. Geo-blocking differs by event, presumably following the broadcast rights:

| Video | Blocked territories (vs 249-country reference) |
|---|---|
| JGP Gdańsk 2026, `Ocr7hn304pQ` | BY, RU |
| World Team Trophy Tokyo 2025, `fJXdrsK78LE` | CZ DK FI HU IT JP KR NO RU SE TW (11) |
| Grand Prix Final 2025, `AV1r_pNSI1s` (and its full stream) | AS AU BZ CR CZ DE DK DO FI GT GU HN HU IT JP KR MP MX NI NO PA PR RU SE SK SV TH TW US VI (30) |
| 2017 Worlds, 2019 GP clips | none |

**Implication:** the site needs a per-video blocked-country list, from `contentDetails.regionRestriction`. It can then hide or flag the video for visitors in those countries, or offer an alternative video. Without that, a US or Japanese visitor would see "video unavailable" on current senior Performances.

---

## 2. Bare-URL metadata

### oEmbed (`https://www.youtube.com/oembed?url=<video url>&format=json`)

YouTube's oEmbed endpoint is listed in the [oEmbed provider registry](https://oembed.com/providers.json). It accepts `watch`, `youtu.be`, `shorts`, `embed`, `live` and playlist URLs ([spec](https://oembed.com/)). It needs no key and has no documented quota. A live response for `AV1r_pNSI1s`:
```json
{"title":"Ilia MALININ (USA) | Men Free Skating | Grand Prix Final 2025 | #GPFigure",
 "author_name":"Skating ISU","author_url":"https://www.youtube.com/@SkatingISU",
 "type":"video","provider_name":"YouTube","thumbnail_url":"https://i.ytimg.com/vi/AV1r_pNSI1s/hqdefault.jpg",
 "thumbnail_width":480,"thumbnail_height":360,"html":"<iframe ...>", "width":200,"height":113,"version":"1.0"}
```
- **Returns:** title, channel name, channel URL (as an `@handle`, not a `UC…` ID), thumbnail and embed HTML.
- **Does not return:** description, publish date, duration, region restriction, channel ID or chapters.
- **Bad ID:** a malformed or unknown ID returned HTTP 400 in testing. That non-embeddable videos return 401 is commonly reported but was **not verified**.
- **Good use:** a cheap first check at submission time ("is this a real video, and what is its title?"). Too thin for matching on its own.

### Data API v3 `videos.list` ([resource](https://developers.google.com/youtube/v3/docs/videos), [method](https://developers.google.com/youtube/v3/docs/videos/list))

Relevant parts:
- **`snippet`**
  - `title` (≤100 chars)
  - `description` (≤5000 bytes)
  - `publishedAt` ("might be different than the time that the video was uploaded")
  - `channelId`, `channelTitle`
  - `tags`
  - `defaultLanguage`, `defaultAudioLanguage`
  - `localized` (with `hl`)
  - `liveBroadcastContent`
- **`contentDetails`**
  - `duration`, ISO 8601, e.g. `PT7M48S`
  - `regionRestriction.allowed` / `.blocked`: country lists, where an allow-list blocks everything not listed
  - `licensedContent`
- **`status`**
  - `embeddable` ("whether the video can be embedded on another website")
  - `privacyStatus`
  - `madeForKids`
- **`recordingDetails.recordingDate`**: uploaders rarely set it.
- **`liveStreamingDetails.actualStartTime`**: useful for the full-segment streams, since it gives the stream's real start time.

Not available:
- **Chapters.** There is no field; chapters exist only as `00:00`-style timestamps inside the description, which we would parse ourselves.
- **Music.** The watch page's "Music in this video" panel is not in the API (no such field in the resource).

**Localized titles:** the same video can show a different title per language. For example, `YJN1OspT6WA` showed an English title in search results and a Korean one on its watch page. Request `snippet` with `hl=en` and also keep the default-language title for matching.

### Quota ([quota costs](https://developers.google.com/youtube/v3/determine_quota_cost))

Verbatim from the page: "Projects that enable the YouTube Data API have a default quota allocation of 100 search.list calls, 100 videos.insert calls, and 10,000 units per day combined for all other endpoints." Quotas reset at midnight Pacific Time, and invalid requests cost at least 1.

| Call | Cost |
|---|---|
| `videos.list` | 1 unit, whatever `part` is set to |
| `playlistItems.list`, `playlists.list`, `channels.list` | 1 unit each |
| `search.list` | 1 per call, but a **separate cap of 100 calls/day** |
| `captions.list` | 50 |

- `videos.list` takes a comma-separated `id` list. The **50-ID-per-call limit is not stated** in the docs we fetched; it is the commonly observed limit and needs checking with a key.
- More quota requires the audit and quota-extension process ([Developer Policies, Usage and Quotas](https://developers.google.com/youtube/terms/developer-policies)).

**Design implications:**
- **Enumerate official videos without `search.list`.** Use `channels.list` (uploads playlist ID) → `playlistItems.list`, 50 per page, 1 unit per page. Then call `videos.list` in batches.
- **Back-catalogue size is an estimate.** The two channels hold an estimated tens of thousands of uploads (not counted). That is roughly hundreds to low thousands of units for a full crawl, well within 10k/day.
- **A 30-day refresh of every stored video** (see ToS) costs about N/50 units. 100k videos is about 2,000 units.
- **Submissions** cost 1 unit each, or less when batched.

---

## 3. ToS constraints ([YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies), [Policies guide](https://developers.google.com/youtube/terms/developer-policies-guide))

Verbatim excerpts from the raw page:

- **Storage (III.E.4.d):** "API Clients may temporarily store limited amounts of Non-Authorized Data for as long as is necessary for the purposes of the API Client but not longer than 30 calendar days. … after 30 calendar days, the API Client must either delete or refresh the stored data." Data about public videos that we fetch with an API key is "Non-Authorized Data", because no user granted consent.
- **Derived data (III.E.4.h):** "Your API Clients must not (i) replace API Data with similar, independently calculated data, or (ii) access or use API Data to create new or derived data or metrics. To the extent your API Clients display any information, data or metrics not based on API Data alongside API Data, your API Clients must include a clear and prominent disclosure that such information … are not from YouTube."
- **Scraping (III.E.6):** "You and your API Clients must not … directly or indirectly, scrape YouTube Applications … or obtain scraped YouTube data or content."
- **Embedding (I.6, I.21):** the player must not be modified or blocked, and must not be nested in iframes to get around the policies.
- **Video and channel IDs:** the policies **do not mention them**, so they give no explicit permission to keep IDs indefinitely. In practice an ID is how a video is embedded at all, and the storage rules target "API Data" such as metadata and statistics.

What this means for us (interpretation, not legal advice):

1. **Store the video ID and our own Performance link indefinitely.** The link comes from ISU results plus the submitter's hints.
2. **Treat everything fetched from the API as a 30-day cache:**
   - title
   - description
   - duration
   - `regionRestriction`
   - `embeddable`

   Refresh it on a schedule, which is cheap (§2), or delete it. A refresh also catches deleted, private or newly blocked videos.
3. **Open risk: the derived-data clause.** Parsing a YouTube title to create a Performance match could be read as "using API Data to create new or derived data". The Policies guide places that rule, and "Merge or combine YouTube API data with any other data", in a list about **metrics and analytics**, such as estimating views or revenue. It is not framed as a ban on linking a video to an external record, but the clause is broad. Ways to lower the risk:
   - Rely mainly on the submitter's hints and ISU results data.
   - Use the title only as a transient matching signal.
   - Label our match data as ours, not YouTube's.
4. **No scraping in production.** That includes watch pages, `ytInitialData`, and probably yt-dlp. Use the Data API and oEmbed only. The public channel RSS feed (`/feeds/videos.xml?channel_id=…`, latest 15 videos with full descriptions) is a gray area; the API does the same job for 1 unit.

## Sources

- YouTube Data API v3, Videos resource: https://developers.google.com/youtube/v3/docs/videos
- YouTube Data API v3, videos.list: https://developers.google.com/youtube/v3/docs/videos/list
- Quota costs: https://developers.google.com/youtube/v3/determine_quota_cost
- YouTube API Services Developer Policies: https://developers.google.com/youtube/terms/developer-policies
- Developer Policies guide: https://developers.google.com/youtube/terms/developer-policies-guide
- oEmbed spec and provider registry: https://oembed.com/ , https://oembed.com/providers.json
- Skating ISU channel: https://www.youtube.com/@SkatingISU ; ISU Junior Grand Prix channel: https://www.youtube.com/@isujuniorgrandprix
- ISU "where to watch" (JGP 2026/27): https://isu-skating.com/news/where-to-watch-isu-figure-skating-junior-grand-prix-series-202627/
- ISU JGP channel launch (2011): https://www.ice-dance.com/site/isu-launches-youtubecom-channel-for-jgp
