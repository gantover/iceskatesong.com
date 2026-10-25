# R1 legal pages: acceptance check

Checked 2026-10-25 for #38, using Playwright Chromium against a local development server and an isolated,
migrated Postgres database. Repeated on the combined #34/#38 production build with Wikipedia music
claims in that disposable database; all seven page checks below passed again. The public operator
details are Damian Hubert and
`damian.b.hubert@gmail.com`, supplied by the owner. `SITE_OPERATOR_NAME` and `SITE_CONTACT_EMAIL` override
those defaults at runtime.

## Browser results

| Page | HTTP status | Third-party requests before a video click | Cookies | Initial iframes |
| --- | --- | --- | --- | --- |
| Home | 200 | 0 | 0 | 0 |
| Skater | 200 | 0 | 0 | 0 |
| Team | 200 | 0 | 0 | 0 |
| Performance with video | 200 | 0 | 0 | 0 |
| Privacy | 200 | 0 | 0 | 0 |
| Terms | 200 | 0 | 0 | 0 |
| Sources | 200 | 0 | 0 | 0 |

Every tested page had Privacy, Terms and Sources footer links plus the correct `mailto:` link.
The Performance linked its exact ISU result URL. Its notice named Google, IP transmission and possible
device storage, and linked Privacy and YouTube Terms. Clicking Privacy in that notice did not load a
player. Clicking the video created one `youtube-nocookie.com` iframe; the browser intercepted that
outgoing request so the check did not depend on YouTube availability. Client navigation through the
Skater page to another Performance restored the unloaded placeholder with zero iframes.

On the combined build, every displayed Wikipedia music entry linked its attributed article revision.
The Skater page showed four linked entries and the Team page two, with one CC BY-SA 4.0, modified
licence line per page. The Performance music card had its article/revision and licence links, and
disabled "Wrong music?" and "Suggest music" actions. The exact ISU result link remained present.

To repeat with any local fixture database:

1. Migrate an isolated database and seed a Skater, Team, their Programs and Performances, including a
   Performance video. Start `DATABASE_URL=<isolated database URL> pnpm dev --host 127.0.0.1 --port 5178`
   from `web/`. Do not point fixture writes at the live database.
2. In a fresh Playwright browser context, attach a `page.on('request')` listener before navigation.
   Visit home, the fixture Skater, Team and Performance, then `/privacy`, `/terms` and `/sources`.
   After `waitForLoadState('networkidle')`, require HTTP 200, no request hostname other than the local
   server, `context.cookies()` equal to `[]`, and no iframe. Check each footer's links and contact.
3. On the Performance, follow the Privacy link in the video notice and check that no YouTube request
   occurred. Return, intercept `https://www.youtube-nocookie.com/**`, click the placeholder and verify
   its iframe URL. Navigate using page links to a different Performance and require a fresh facade.

The PRD excludes a browser test suite in R1; this is a recorded acceptance run, with existing server
tests retained. `pnpm check` passed with zero errors and warnings; the combined web suite passed all
24 tests, and the production build passed.

## Audit and remaining launch checks

- Public components load their assets locally. The only remote asset URL is the YouTube iframe,
  created after a click. External attribution and policy links are ordinary navigation links.
- Application code sets no cookies and has no date-of-birth or height profile fields. The appearance
  toggle uses local storage, disclosed in Privacy. Wikipedia responses are reduced to raw program
  tables, partnership context, follow links and attribution metadata before disk storage; biography
  fields are excluded. Legacy cached articles are validated and reduced on read too.
- Wikipedia music attribution passed the combined-build check described above.
- A Piece page does not exist at this revision, so the Piece browser acceptance item cannot yet run.
  Repeat the same check when that page is implemented.
- Local checks do not verify production Cloudflare settings. Ensure Access protects only `/admin`,
  and that public-page features which set cookies (for example Bot Fight Mode or challenges) are off
  if the site's no-public-cookies promise is to hold. Verify the deployed site's response cookies.
- The owner still reviews the wording before launch. Operational logs are described by their actual
  three-file, 10 MB rotation limit rather than an unimplemented time-based deletion promise.

## Wording references

The ticket's [legal research](https://github.com/gantover/iceskatesong.com/blob/research/legal-pages/research/legal-pages.md)
and PRD define the scope. These primary pages were rechecked while implementing:

- [YouTube Developer Policies](https://developers.google.com/youtube/terms/developer-policies), including
  the accessible policy, API Services notice, Google Privacy Policy link and binding Terms requirement.
- [YouTube privacy-enhanced embeds](https://support.google.com/youtube/answer/171780).
- [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), for attribution, modification and
  licence links.
- [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing), for structured data under CC0.
- [Belgian DPA complaint route](https://www.autoriteprotectiondonnees.be/citoyen/agir/introduire-une-plainte).
- [Cloudflare Privacy Policy](https://www.cloudflare.com/privacypolicy/).
