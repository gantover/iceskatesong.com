# What legal pages and attribution must the R1 launch carry?

Research for [#21](https://github.com/gantover/iceskatesong.com/issues/21), checked 2026-10-22. **This is research, not legal advice.** The owner is assumed to be an individual in Belgium, running a non-commercial site with no ads, served from a homeserver behind Cloudflare Tunnel ([#11](https://github.com/gantover/iceskatesong.com/issues/11)). Where the country changes the answer, the text says so.

## Answer in one screen

R1 needs **three pages, linked in the footer of every page**, plus **notices on specific pages**:

| Page | Why it's required | Must contain |
|---|---|---|
| **Privacy** (`/privacy`) | GDPR Art 13/14; YouTube API Terms §7 and Developer Policies III.A.2 | Who runs the site (name + contact email). States that the site uses YouTube API Services. Link to the [Google Privacy Policy](https://policies.google.com/privacy). What is collected about **visitors** (server/Cloudflare logs, the Admin session cookie, YouTube after a click) and about **Skaters** (names, nationality, ISU IDs, results). Legal bases, retention, rights including the right to object, and a complaint route to the Belgian APD/GBA. Third parties: Google/YouTube, and Cloudflare as processor |
| **Terms** (`/terms`) | Developer Policies III.A.1 | A link to the [YouTube Terms of Service](https://www.youtube.com/t/terms), with: "By playing videos on this site you agree to be bound by the YouTube Terms of Service." No warranty on data accuracy. Not affiliated with the ISU, YouTube or Wikimedia |
| **Sources & credits** (`/sources`) | CC BY-SA 4.0 §3(a); ISU attribution policy ([#12](https://github.com/gantover/iceskatesong.com/issues/12)) | ISU results as the data source, with a link. Wikipedia (CC BY-SA 4.0, a "modified" note, a licence link). Wikidata (CC0, credit as a courtesy). YouTube as the video source. How to ask for a correction or removal |

**Per-page notices:**
- **Every Performance/Competition page:** "Results: International Skating Union", linking to the specific ISU result page.
- **Every Program or Piece shown with music data from Wikipedia:** "Music: Wikipedia, *<article title>*", linking to the article, with "CC BY-SA 4.0, modified".
- **Every video slot:** a **click-to-load** placeholder. It must not contact Google before the click, and it must carry YouTube branding and the line "Plays from YouTube (Google). Google gets your IP address and may store data on your device. [Privacy]".
- **Footer:** links to Privacy · Terms · Sources, plus a contact email.

**What R1 does not need:**
- **A cookie banner:** none, provided the site itself sets only the Admin session cookie and loads no analytics, Google Fonts or other third-party resources before a click.
- **A separate imprint page:** none in Belgium for a non-commercial site, provided the privacy page names the owner and gives a contact. Germany and Austria differ; see [Imprint](#imprint--contact).

**R2 adds** (anonymous Submissions/Flags, Turnstile, hashed IPs for Blocks):
- **Privacy page:** three new sections: Submissions/Flags (what is stored, retention), Turnstile (Cloudflare), and the keyed-hash IP used for Blocks (legal basis Art 6(1)(f), retention).
- **Terms page:** a Contributions clause, for example "you dedicate your Submission to CC0 / grant us a licence; don't submit personal data in hints".
- **Submission and Flag forms:** a one-line notice beside the button, and **Turnstile loaded only on those forms**.
- **DSA:** if the site ever earns money, DSA hosting duties may appear; see [R2](#r2-additions).

## Data sources: attribution

### ISU results

- **No attribution duty.** The [ISU Terms of Service](https://www.isu.org/en/terms-service) contain no attribution clause and no permission to reuse. §2.2 forbids copying, storing or redistributing Content and automated data collection "without ISU's prior approval". §3.1 forbids removing "any copyright or other proprietary notices". Swiss law, Lausanne courts (§13).
- **Scope is unclear.** The terms are scoped to "ISU Business Applications" (the B2B extranet). Whether they cover the public results sites is not stated ([isu-music-coverage research, Terms and scraping](https://github.com/gantover/iceskatesong.com/blob/research/isu-music-coverage/research/isu-music-coverage.md#terms-and-scraping)).
- **Attribution stands in for consent.** The owner decided not to ask the ISU ([#12](https://github.com/gantover/iceskatesong.com/issues/12), [ADR 0001](../docs/adr/0001-isu-results-are-the-only-record-creator.md)), so attribution is the mitigation the site has chosen, not a legal requirement. To keep that promise:
  - Credit "International Skating Union" with a link to the exact ISU result page on every Performance/Competition page, and on `/sources`.
  - Say "Not affiliated with or endorsed by the ISU."
  - Don't reproduce ISU pages, logos or PDFs, so there are no ISU notices to strip (§3.1).
  - Republishing the facts themselves is the accepted risk from #12.
- **Uncertainty:** the EU sui generis database right (Directive 96/9/EC) may protect ISU results as a database. Attribution does not cure a substantial extraction. This is the accepted risk recorded in #12.

### English Wikipedia (program music tables)

- **Licence and attribution rule.** Text is CC BY-SA 4.0. [Wikimedia Terms of Use §7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) (in force since 7 June 2023) says to attribute "through hyperlink (where possible) or URL to the page or pages that you are reusing", and to "clearly indicate that the original work has been modified".
- **Facts vs text.** Music titles per Program are **facts**. [CC BY-SA 4.0 §8(a)](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en) says the licence does not restrict uses that need no permission, and §2(a)(2) says it doesn't apply where an exception covers the use. Copying facts alone needs no licence, under copyright.
- **The catch: the database right.** [CC BY-SA 4.0 §4](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en) licenses EU sui generis database rights too.
  - If you put "all or a substantial portion" of a protected database into your own database, **your database (not its individual contents) becomes Adapted Material**, so ShareAlike (§3(b)) attaches to it.
  - Whether Wikipedia's program tables carry a database right at all is **unresolved**: the right needs a "maker" with substantial investment, which is doubtful for crowd-written pages.
  - Treat the Wikipedia-derived part of the data as CC BY-SA 4.0. It costs nothing unless the site ever publishes a data dump under other terms.
- **Per-record or site-wide?** CC BY-SA §3(a)(1)(A)(v) wants a link to the material "to the extent reasonably practicable". §3(a)(2) allows "any reasonable manner". Since the site knows which article each record came from, a **per-record link is reasonably practicable**, and a credits page alone is the weaker position. So do both: a per-record link and a `/sources` page with the licence link.
  - **Data model consequence:** store the source article title (or revision ID) on each Wikipedia-derived fact.
- **Wikipedia prose.** Don't display it at R1. If prose is ever shown (for example, a Piece intro), per-page credit is mandatory and the excerpt is BY-SA.

### Wikidata

- **No attribution required.** Structured data (main, Property, Lexeme, EntitySchema namespaces) is "released into the public domain under Creative Commons Zero" ([Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)).
- **Courtesy credit:** one line on `/sources`.
- **Text in other namespaces is CC BY-SA 4.0.** We don't use it.

### YouTube

- **Developer Policies apply to the embed too.** Google: "Developer Policies apply to the access and use of the YouTube embedded player", "even if you embed YouTube videos with the Privacy Enhanced Mode player" ([YouTube Help 171780](https://support.google.com/youtube/answer/171780)). The import also calls the Data API ([#4](https://github.com/gantover/iceskatesong.com/issues/4)), so the site is an API Client both ways.
- **Required items, from [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) and [API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) (last updated 2026-09-14):**
  - **III.A.1:** display a link to the YouTube ToS, and state in **your own terms** that users are bound by it. **This means a Terms page.**
  - **III.A.2:** a privacy policy that users agree to before using the client's features, "prominently displayed and easily accessible to users at all times". It must:
    - **(b)** say the client uses YouTube API Services;
    - **(c)** reference and link to the Google Privacy Policy;
    - **(d, e)** say what user info is collected and how it's used and shared;
    - **(f)** say whether third parties serve content (yes, YouTube);
    - **(g)** say whether the client stores or accesses info on devices "directly or indirectly through third parties" (yes, through the YouTube player after a click);
    - **(h)** only applies to Authorized Data (OAuth), which we don't use.
  - **API ToS §7:** publish and follow a privacy policy that describes what you access and collect and how it is shared, "with us and other third parties". Comply with privacy law.
  - **API ToS §9.2:** comply with [Google's EU User Consent Policy](https://www.google.com/about/company/user-consent-policy/). It requires consent to "the use of cookies or other local storage where legally required". You must "clearly identify each party that may collect, receive, or use end users' personal data", keep consent records, and explain how to withdraw consent.
  - **III.F.2.a:** "make clear to the viewer that YouTube is the source"; **III.F.2.c:** don't obscure YouTube's attribution. The real player brands itself, but **the click-to-load placeholder must show YouTube branding** too.
  - **III.E.4.j (Made for Kids):** look up the Made For Kids status of every embedded video, and "turn off tracking" for those flagged. Read `status.madeForKids` in `videos.list` during the Import. Click-to-load plus nocookie is the most we can do client-side.
  - **[Required Minimum Functionality](https://developers.google.com/youtube/terms/required-minimum-functionality):** the player must be at least 200×200 px (480×270 recommended for 16:9). Send an HTTP `Referer` (`Referrer-Policy: strict-origin-when-cross-origin`). Don't use `noreferrer`.
- **Uncertain:** III.A.2 says users must "agree" to the privacy policy before using features. Clickwrap makes no sense for an anonymous read-only site. Best effort: a footer link on every page, and a privacy link inside each click-to-load notice (the click is the moment the YouTube features start).

## Privacy and GDPR

### Does GDPR apply to a hobby site?

- **Yes.** The household exemption (GDPR [Art 2(2)(c)](https://eur-lex.europa.eu/eli/reg/2016/679/oj)) does not cover publishing personal data to an indefinite audience on the internet. This is CJEU *Lindqvist* C-101/01 (ECLI:EU:C:2003:596) and *Ryneš* C-212/13. The owner is the **controller**.
- **The owner must be identifiable.** Art 13(1)(a) requires "the identity and the contact details of the controller" in the privacy notice, whatever the imprint rules say. A contact email is the usual minimum, and a postal address is not strictly required by GDPR.
- **Cookie consent rules sit separately**, in ePrivacy Directive Art 5(3) ([ELI](https://eur-lex.europa.eu/eli/dir/2002/58/oj)). Belgium now implements it in **Art 10/2 of the loi-cadre of 30 July 2018** (cited by the APD's [cookie checklist](https://www.autoriteprotectiondonnees.be/publications/checklist-cookies.pdf), footnote 11).

### Skaters are data subjects too (often forgotten)

Republishing names, nationality, ISU IDs and results is processing of personal data. Junior events include **minors**.

- **Legal basis.** Art 6(1)(f), legitimate interest: a public-interest sports and music reference built from already-public results. Document the balancing test in one paragraph in the repo.
- **Information duty.** The data is not collected from the Skaters themselves, so Art 14 applies. Art 14(5)(b) waives individual notice where it would take "disproportionate effort", but the controller must then "make the information publicly available". The privacy page does that. It needs a section headed something like "If you are a skater listed here".
- **Right to object.** Art 21 gives Skaters a right to object, so publish a contact address and say how quickly hides happen. The Admin "video hide" / correction tools already fit this.
- **Data minimisation (Art 5(1)(c)).** Do **not** republish ISU bio fields such as date and place of birth or height. They aren't needed for music search.
- **Possible derogation (uncertain).** Art 85 lets member states exempt journalistic, academic, artistic or literary expression. Belgium does this in the loi-cadre of 30 July 2018 (Art 24; not fetched). Whether a fan reference site counts as "journalistic" is doubtful, so don't rely on it.

### Visitors at R1

| Processing | Who | Consent? | Notice on Privacy page |
|---|---|---|---|
| Every request passes through Cloudflare (TLS terminates there) | Cloudflare = **processor**. [Customer DPA v6.4](https://www.cloudflare.com/cloudflare-customer-dpa/) (effective 3 April 2026) is part of the Self-Serve agreement; transfers rely on the EU-US Data Privacy Framework, with SCCs as fallback | No. Art 6(1)(f), delivering and securing the site | Name Cloudflare, the purpose, and the US transfer under DPF |
| Cloudflare cookies (`__cf_bm` if Bot Fight Mode is on; `cf_clearance` after a challenge) | Cloudflare | Cloudflare classes them as "strictly necessary" ([cookie list](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/cloudflare-cookies/)), and they fall under the Art 5(3) security/necessity exception | List them. **Owner: check whether Bot Fight Mode is on.** `__cf_bm` needs (Super) Bot Fight Mode enabled, `cf_clearance` is set only after a challenge, and the Always Online cookies only if that feature is on. The page doesn't say which are on by default |
| Origin logs (web app, `docker compose logs`) | Owner | No. Art 6(1)(f) | State the retention. **Don't log visitor IPs at R1**, or keep them ≤ 14 days. Docker's default `json-file` driver never rotates, so set `max-size`/`max-file` |
| Admin session cookie | Owner | No: "strictly necessary in order for the provider of an information society service explicitly requested by the subscriber or user to provide the service" (Art 5(3), as quoted in [EDPB Guidelines 2/2023](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-22023-technical-scope-art-53-eprivacy-directive_en) fn 4) | One line |
| Analytics | n/a | **Belgium: consent.** The APD checklist footnote 12 says visitor counting is not "strictly necessary" | **Don't add analytics at R1.** If you want numbers, count from server logs, without cookies or client JS |
| Fonts, CSS, JS from CDNs | Third party | Avoid | **Self-host everything.** German *LG München I*, 3 O 17493/20 (20 January 2022), awarded damages for hotlinking Google Fonts because it sent the IP to Google. That is a regional court and only persuasive in Belgium, but the logic matches EDPB 2/2023 |

### YouTube embeds: why click-to-load, and why nocookie is not enough

- **What privacy-enhanced mode (`youtube-nocookie.com`) does.** According to Google ([Help 171780](https://support.google.com/youtube/answer/171780)), views don't personalise the viewer's YouTube experience or ads outside your site, and ads on those embeds are non-personalised. Google **does not document** whether it sets cookies or local storage, or when. Independent observations report device storage, but we have no primary source for the specifics, so this doc doesn't claim any.
- **Why that's not enough.** Loading any Google iframe makes the browser send the IP address, User-Agent and Referer to Google and run Google's JS on the device.
  - EDPB Guidelines 2/2023 (adopted 7 October 2024): passing on IP addresses and identifiers through instructed protocols "can lead to the application of Article 5(3)" (§§42–43). Instructed client-side JS and cached resources also count (§§50–51). "Tracking based on IP only" can also fall under Art 5(3) (§54).
  - CJEU *Fashion ID*, C-40/17, ECLI:EU:C:2019:629: a site that embeds a third-party plugin which causes the browser to transmit visitors' personal data is a **joint controller for that collection and transmission**. Where consent is needed, the site must obtain it before the transmission. *EUR-Lex/Curia didn't return the text to our tools, so this holding is taken from secondary summaries (e.g. [Inside Privacy](https://www.insideprivacy.com/international/european-union/cjeu-rules-that-facebook-and-website-operators-are-joint-controllers-if-the-website-embeds-facebooks-like-button/)). Verify the operative part before relying on its exact wording.*
  - Google's EU User Consent Policy (binding through API ToS §9.2) asks for consent to local storage "where legally required" and for each party to be named.
- **Pattern: the two-click / facade.**
  1. Before the click, render a **neutral placeholder** from our own server: Skater, Segment, Competition, a YouTube logo and the notice text. **Don't hotlink the thumbnail from `i.ytimg.com`**, because that sends the IP to Google before consent.
     - If thumbnails are wanted, fetch and cache them server-side ≤ 30 days. That fits the API Data storage limit in Developer Policies III.E.4.d. Whether a thumbnail fetched via oEmbed counts as "API Data" is unclear.
  2. On click, swap in the `youtube-nocookie.com` iframe. That click is the specific, informed consent for that embed.
  3. Optionally, offer a "Always load YouTube videos" toggle stored in `localStorage`. That storage is itself at the user's request, so it is strictly necessary. Make it withdrawable from the Privacy page (consent policy: "clear instructions for withdrawing").
- **Result:** no site-wide cookie banner. The per-embed click is the consent mechanism.
- **Consent records.** Google's policy asks for them. With per-click consent and no server state, the "record" is the click itself. This is **uncertain** for strict compliance; it's the common practice for two-click embeds.

## Imprint / contact

- **EU baseline.** E-Commerce Directive 2000/31/EC Art 5 (identity, geographic address, email) applies only to "information society services". Those are services "normally provided for remuneration" (Directive (EU) 2015/1535 Art 1(1)(b)). Recital 18 of 2000/31 extends that to free services funded by **advertising**.
- **Belgium.**
  - **Imprint:** Code de droit économique Book XII uses the same definition (Art I.18: "presté normalement contre rémunération"; see the [Book XII bill, doc 53K2963001](https://www.dekamer.be/FLWB/PDF/53/2963/53K2963001.pdf)). A non-commercial, ad-free site is **probably not** an ISS, so **Art XII.6 imprint duties probably don't apply**. We did not fetch the consolidated XII.6 text. We found **no general Belgian media-law imprint for websites**.
  - **Privacy-page minimum:** name + contact email (GDPR Art 13).
- **Germany (if the owner lives there).**
  - [§ 5 DDG](https://www.gesetze-im-internet.de/ddg/__5.html) covers only "geschäftsmäßige, in der Regel gegen Entgelt angebotene digitale Dienste", which is probably not this site.
  - But [§ 18(1) MStV](https://www.gesetze-bayern.de/Content/Document/MStV-18) requires **name and postal address** from any telemedia provider whose service is "nicht ausschließlich persönlichen oder familiären Zwecken" (not purely personal or family). A public reference site is not purely personal, and media authorities read the exemption narrowly. **So in Germany: an imprint with name + ladungsfähige postal address (no P.O. box).**
- **Austria (if the owner lives there).** Mediengesetz §25 requires a short "Offenlegung" even for small websites (name, place of residence). Not checked against the source.
- **The trigger to watch.** Adding ads, donations, affiliate links or sponsorship likely makes the site an ISS. That brings in ECD Art 5 / CDE XII.6 imprint duties, and also DSA duties at R2.

## R2 additions

- **Turnstile** ([privacy addendum](https://www.cloudflare.com/turnstile-privacy-policy/), updated 18 June 2025).
  - **What Cloudflare processes:** "client IP address, TLS Fingerprint, User-Agent Header and Sitekey and associated origin". Cloudflare is the **processor** for bot detection and a **controller** for improving Turnstile. The site operator is the controller and picks the legal basis. Signals are "strictly necessary for the purpose of detecting and blocking bots".
  - **Consent:** none needed, provided Turnstile **loads only on the Submission/Flag form** the user chose to use. That is the "user-centric security" case WP29 Opinion 04/2012 ([WP194](https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2012/wp194_en.pdf)) treats as exempt.
  - **Privacy page:** add a Turnstile section naming Cloudflare in both roles, with a link to the addendum.
- **Hashed IPs for Blocks.**
  - **Still personal data.** A hash of an IP is pseudonymised, not anonymous (GDPR Recital 26). Dynamic IPs are personal data (CJEU *Breyer*, C-582/14).
  - **Use a keyed hash.** A plain SHA-256 of an IPv4 address can be reversed by trying all 2³² addresses, so use HMAC with a secret key kept in `.env`. Hash the IPv6 /64 prefix, not the full address. Behind the Tunnel, the visitor IP comes from `CF-Connecting-IP`.
  - **Legal basis and retention.** Art 6(1)(f), abuse prevention. Store the hash only alongside Submissions/Flags and Blocks, and state retention, e.g. "hash deleted N days after the Submission is resolved; Blocks kept until lifted".
  - **Privacy page:** add a section on this.
- **Submission content.**
  - **Terms page:** a Contributions clause: the submitter dedicates the hint to CC0 or grants a licence, and promises not to include personal data or third-party content.
  - **Form:** a one-line notice beside the submit button, "By submitting you agree to the Terms and Privacy Policy", which also helps with YouTube III.A.2's "agree before using".
  - **Data minimisation:** free-text hints may contain personal data; mention it and minimise.
- **DSA ([Regulation (EU) 2022/2065](https://eur-lex.europa.eu/eli/reg/2022/2065/oj)).** Storing visitors' Submissions is "hosting". But DSA duties attach to *intermediary services*, which are a subset of information society services. So the same "remuneration" test applies: **likely out of scope while non-commercial.** If it flips, the minimum is:
  - a single point of contact (Art 11–12);
  - Terms covering content moderation (Art 14);
  - a notice-and-action mechanism (Art 16), which the Flag feature nearly is;
  - statements of reasons for removals (Art 17).

## Open questions and uncertainties

1. **Owner's country.** Belgium is assumed. Germany adds a full imprint with postal address (MStV §18).
2. **YouTube III.A.2 "agree before using".** Footer link plus a link in the click notice is best effort. Google may read it more strictly.
3. **The EU database right** over ISU results and Wikipedia tables is unresolved. ISU is the accepted risk (#12). For Wikipedia, treat the derived data as BY-SA.
4. **What youtube-nocookie stores** is undocumented by Google. Our conclusion doesn't depend on it.
5. **Not re-fetched from the primary text** (EUR-Lex/Curia/Justel unreachable or not tried): *Fashion ID* wording (secondary sources), CDE XII.6, Belgian loi-cadre Art 24, Austrian MedienG §25. GDPR articles, *Lindqvist*, *Ryneš*, *Breyer* and *LG München I* are cited from their well-known holdings, not re-read for this note.
6. **Whether a click on a facade counts as valid consent with records**, under Google's EU User Consent Policy. It's common practice, but not confirmed by Google.

## Sources

- YouTube: [API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) · [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) · [Required Minimum Functionality](https://developers.google.com/youtube/terms/required-minimum-functionality) · [Privacy-enhanced mode](https://support.google.com/youtube/answer/171780) · [EU User Consent Policy](https://www.google.com/about/company/user-consent-policy/) · [YouTube ToS](https://www.youtube.com/t/terms) · [Google Privacy Policy](https://policies.google.com/privacy)
- Wikimedia: [Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) · [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en) · [Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)
- ISU: [Terms of Service](https://www.isu.org/en/terms-service) · [isu-music-coverage research](https://github.com/gantover/iceskatesong.com/blob/research/isu-music-coverage/research/isu-music-coverage.md#terms-and-scraping)
- EU law: [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj) · [ePrivacy Directive](https://eur-lex.europa.eu/eli/dir/2002/58/oj) · [EDPB Guidelines 2/2023 v2](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-22023-technical-scope-art-53-eprivacy-directive_en) · [WP29 Opinion 04/2012](https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2012/wp194_en.pdf) · [E-Commerce Directive](https://eur-lex.europa.eu/eli/dir/2000/31/oj) · [DSA](https://eur-lex.europa.eu/eli/reg/2022/2065/oj)
- Belgium: [APD/GBA cookie checklist](https://www.autoriteprotectiondonnees.be/publications/checklist-cookies.pdf) · [CDE Book XII bill](https://www.dekamer.be/FLWB/PDF/53/2963/53K2963001.pdf)
- Germany: [§ 5 DDG](https://www.gesetze-im-internet.de/ddg/__5.html) · [§ 18 MStV](https://www.gesetze-bayern.de/Content/Document/MStV-18)
- Cloudflare: [Customer DPA](https://www.cloudflare.com/cloudflare-customer-dpa/) · [Cookies](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/cloudflare-cookies/) · [Turnstile privacy addendum](https://www.cloudflare.com/turnstile-privacy-policy/)
