# Hosting options: cost and scaling

Research for issue #6. All pages were fetched on **2026-10-22**. Prices are in each vendor's own currency and are not converted. Hetzner prices exclude VAT. Where OVH states tax or commitment terms, this file says so. This file records facts only. The decision belongs to a later ticket.

## Traffic baseline used for "now" and "10×"

There is no traffic data yet, so the figures below are assumptions. Redo the arithmetic once real numbers exist.

| | Now | 10× |
|---|---|---|
| Pageviews / month | 10,000 | 100,000 |
| Dynamic requests / month (HTML + search/API, about 3 per pageview) | 30,000 (~1,000/day) | 300,000 (~10,000/day) |
| Searches / month (about 1 per pageview) | 10,000 (~330/day) | 100,000 (~3,300/day) |
| Transfer / month (~500 KB per pageview incl. assets, video is YouTube-embedded) | ~5 GB | ~50 GB |
| Dataset | 100k–500k rows, well under 1 GB | same |
| Weekly import | rewrites up to the whole dataset once a week | same |

At these volumes, bandwidth and request counts move almost no bill. **What decides the cost is the free-tier caps (D1 rows read and written, Neon compute hours) and backups.**

---

## 1. Homeserver + Cloudflare Tunnel

### What Cloudflare gives on the Free plan

| Item | Fact | Source |
|---|---|---|
| Tunnel | "Available on all plans." You can run several `cloudflared` replicas for HA. Each tunnel holds 4 connections to 2 data centres. | https://developers.cloudflare.com/tunnel/ |
| CDN, SSL, DDoS | Free plan "provides free SSL, CDN, DDoS protection". DDoS is "Standard, unmetered DDoS protection (layers 3-7)" and is "Available on all plans". | https://www.cloudflare.com/plans/free/ , https://developers.cloudflare.com/ddos-protection/ |
| Cache | "The Cloudflare CDN does not cache HTML or JSON by default." Static extensions (JS, CSS, images, fonts…) are cached. | https://developers.cloudflare.com/cache/concepts/default-cache-behavior/ |
| Rate limiting | Free gets **1 rule**, counting by **IP**, over a **10 s** period, with a 10 s mitigation timeout. | https://developers.cloudflare.com/waf/rate-limiting-rules/ |
| Turnstile | Free, up to 20 widgets per account, "Unlimited challenges". | https://developers.cloudflare.com/turnstile/plans/ |
| CDN terms | Free, Pro and Business may not serve video or a "disproportionate percentage of … large files" through the CDN. This does not apply here, because video is embedded from YouTube. | https://www.cloudflare.com/service-specific-terms-application-services/ |

### Cost
- **Now and at 10×: $0 to Cloudflare.** The marginal cost is electricity, which is box watts × 730 h / 1000 × your tariff per kWh. A 15 W box uses about 11 kWh a month. No tariff is cited here.
- Off-site backup target: Cloudflare R2's free tier has 10 GB-month of storage, 1M Class A and 10M Class B operations, and free egress. Beyond that it costs $0.015/GB-month. https://developers.cloudflare.com/r2/pricing/

### Scaling and risks
- HTML and search JSON are not cached by default, so **every dynamic page and search crosses the tunnel to the home box and the home uplink**, unless you add cache rules. Static assets are served from the edge. 50 GB/month at 10× is small for most uplinks, and most of it is cacheable assets.
- Uptime depends on home power, the ISP and the hardware. Nothing gives a failover unless you add a second `cloudflared` replica on another machine.
- **Not verified, owner to check:** whether your residential ISP's terms allow running a public server.
- Backups are entirely DIY: DB dump plus off-site copy (R2, a second machine, etc.).

**Ops burden:** highest. You own the OS, patches, hardware, DB and backups. **Lock-in:** none, apart from the Cloudflare DNS needed for the Tunnel. **Weekly Python job:** cron on the box.

---

## 2. Cheap VPS (Hetzner, OVH), optionally behind the Cloudflare Free plan

### Hetzner Cloud (excl. VAT)
https://www.hetzner.com/cloud/cost-optimized/ , https://www.hetzner.com/cloud/regular-performance/

| Plan | vCPU / RAM / NVMe | €/month | Traffic incl. |
|---|---|---|---|
| CX23 (Cost-Optimized) | 2 / 4 GB / 40 GB | 5.99 | 20 TB (EU) |
| CAX11 (Arm, Cost-Optimized) | 2 / 4 GB / 40 GB | 6.49 | 20 TB |
| CX33 | 4 / 8 GB / 80 GB | 8.99 | 20 TB |
| CPX02 (Regular Performance) | 1 / 1 GB / 20 GB | 6.49 | 20 TB |
| CPX12 | 2 / 2 GB / 40 GB | 11.99 | 20 TB |

- **Availability (2026-10-22):** every Cost-Optimized plan showed "This product is currently unavailable. Please check back later", and the page says the number of servers is limited. Some Regular Performance plans also showed "currently unavailable". This research did not confirm which plan could actually be bought that day. Check the Hetzner Console.
- Prices include IPv4. Traffic overage in the EU costs €1.00/TB.
- **Backups:** "starting at €1.1980/month related to instance", which is 20 % of CX23's €5.99 (my arithmetic). Hetzner takes one backup a day and keeps 7 slots. https://docs.hetzner.com/cloud/servers/backups-snapshots/overview/
- Snapshots cost €0.0143/GB-month.

### OVHcloud VPS
https://www.ovhcloud.com/en/vps/

| Plan | vCores / RAM / NVMe | From |
|---|---|---|
| VPS-1 | 2 / 4 GB / 40 GB | $4.54/month |
| VPS-2 | 4 / 8 GB / 75 GB | $8.50/month |

- Traffic is "Unlimited". VPS-1 runs at 500 Mbps.
- A daily backup with 24 h retention is included. Premium 7-day backup costs from $1.40/month, and snapshots from $0.40/month.
- These are USD prices from the /en/ site, and the page doesn't say whether tax is included. **Unverified:** the Configure links carry `pricing=upfront12`, so the "from" price probably assumes 12 months paid upfront.

### Cost
- **Now:** about €6–7.2/month for Hetzner CX23 with backups, excl. VAT, or about $4.54–5.94/month for OVH VPS-1 with or without premium backup.
- **At 10×:** the same. 300k dynamic requests a month and 50 GB of transfer fit easily on the smallest plan and in 20 TB or unlimited traffic. Growing means resizing to the next plan, for example CX33 at €8.99.

**Ops burden:** high. You own the OS, patches, DB and app process, but not the hardware, power or uplink. **Lock-in:** none, because it is a plain Linux VM. **Backups:** provider snapshots or backups of the whole VM, plus DB dumps you take yourself to an off-site store such as R2. **Weekly Python job:** cron on the VPS.

---

## 3. Serverless / edge + managed DB

### 3a. Cloudflare Workers (or Pages) + D1

Pricing: https://developers.cloudflare.com/workers/platform/pricing/ , limits: https://developers.cloudflare.com/workers/platform/limits/ , https://developers.cloudflare.com/d1/platform/limits/ , https://developers.cloudflare.com/d1/platform/pricing/

| | Free | Workers Paid ($5/month minimum) |
|---|---|---|
| Requests | 100,000/day | 10M/month incl., then $0.30/M |
| CPU | 10 ms per invocation | 30M CPU-ms/month incl., then $0.02/M CPU-ms. Up to 5 min per request, 15 min per Cron Trigger |
| Subrequests per invocation | 50 | 10,000 |
| Cron Triggers | 5 | 250 |
| D1 rows read | 5M/day | 25B/month incl., then $0.001/M |
| D1 rows written | 100k/day | 50M/month incl., then $1.00/M |
| D1 storage | 5 GB total, 500 MB per DB | 5 GB incl., then $0.75/GB-month, 10 GB per DB |
| D1 Time Travel (PITR) | 7 days | 30 days |

Static asset requests on Pages are "free and unlimited". Functions are billed as Workers requests. https://developers.cloudflare.com/pages/functions/pricing/

**D1 rows-read arithmetic.** D1 counts rows *scanned*, not rows returned: "a `SELECT * FROM table` as a full table scan" of 5,000 rows "would count as 5,000 rows read". On the Free plan, hitting the daily limit means "you will not be able to run queries against D1" until 00:00 UTC. That is a **hard stop, not a bill**.

| Search style (200k-row table) | Rows read per search | Free, now (330/day) | Free, 10× (3,300/day) | Paid, now | Paid, 10× |
|---|---|---|---|---|---|
| Full scan (`LIKE '%x%'`, unindexed) | ~200,000 | **fails after ~25 searches/day** | fails | 2B/month, incl. → $5 | 20B/month, incl. → $5 |
| Indexed / FTS5, ~1,000 rows touched | ~1,000 | 0.33M/day, OK | 3.3M/day, OK (66 % of cap) | $5 | $5 |
| Indexed, ~100 rows touched | ~100 | OK | OK | $5 | $5 |

**D1 rows-written arithmetic.** A weekly full re-import of 100k+ rows passes the Free plan's **100k rows/day write cap in one run**, and every index on a written column adds one more written row. Free only works with incremental upserts of changed rows. On Paid, a full rewrite of 500k rows × 4 weeks × (1 + indexes) stays well under the 50M/month included.

**Cost:** Free covers now and 10× only if search is indexed and the import is incremental. Otherwise it is **$5/month on Workers Paid, now and at 10×**.

**Backups:** Time Travel is automatic and free, with 7 or 30 days of history. Restore is destructive, overwriting in place. https://developers.cloudflare.com/d1/reference/time-travel/ For long-term copies you have `wrangler d1 export` to a SQL file, or Workflows to R2. **However, "Export is not supported for virtual tables"**, which includes FTS5. If search uses FTS5 you must drop, export and recreate it, or rebuild the index from the base tables after a restore. https://developers.cloudflare.com/d1/best-practices/import-export-data/

**Lock-in:** medium. The data is SQLite, exportable as SQL apart from virtual tables, but the app code targets the Workers runtime and D1 bindings. **Ops burden:** lowest. There is no server or OS to run.

**Weekly Python job:**
- Not on Workers Free (50 subrequests, 10 ms CPU).
- Workers Paid gives a cron with 15 min CPU and 10k subrequests. Python Workers exist and need the `python_workers` flag. The docs list FastAPI, Langchain and Pydantic packages, but this research **did not verify** HTTP-client or scraping support. https://developers.cloudflare.com/workers/languages/python/
- The simplest path is to run it elsewhere (GitHub Actions, the homeserver) and write to D1 via `wrangler` or the D1 HTTP API.

### 3b. Neon (serverless Postgres)
https://neon.com/pricing , https://neon.com/docs/introduction/plans

| | Free | Launch (pay-as-you-go, no minimum) |
|---|---|---|
| Compute | 100 CU-hours per project per month (~400 h at 0.25 CU). Suspends after 5 min idle | $0.106/CU-hour. Scale-to-zero can be disabled |
| Storage | 1 GB per project, 20 GB total | $0.35/GB-month |
| Restore window | 6 h (1 GB-month of changes) | up to 7 days, with instant restore at $0.20/GB-month |
| Egress | 5 GB per project | 500 GB, then $0.10/GB |
| Overage | Compute suspended until the next period, writes blocked over storage cap. No data deleted | billed, no hard stop |

- **Compute-hours arithmetic:** a month has 730 h, and Free gives about 400 h at 0.25 CU. Anything that keeps compute awake more than about 55 % of the time **suspends the DB until next month**. A crawler or uptime pinger hitting it every few minutes would do that.
- **Launch, always-on at 0.25 CU:** 0.25 × 730 × $0.106 ≈ **$19.3/month**, plus about $0.35 for 1 GB of storage.
- **Launch with scale-to-zero:** you pay only for awake hours, for example 200 h × 0.25 CU ≈ $5.3.
- **Cost:** now, $0 if idle enough, otherwise about $5–20/month. At 10×, traffic is likelier to keep compute awake, so expect toward about $19–20/month at 0.25 CU.
- Still needs a host for the TypeScript app: Workers, Fly, a VPS, etc.

**Lock-in:** low, because it is standard Postgres (`pg_dump`). **Ops burden:** low. **Backups:** the built-in restore window, which is short on Free, plus your own `pg_dump` to R2 for anything longer.

### 3c. Supabase
https://supabase.com/pricing , https://supabase.com/docs/guides/platform/compute-and-disk

| | Free | Pro |
|---|---|---|
| Fee | $0 | from $25/month, including $10 compute credit that "covers one Micro instance" |
| DB size | 500 MB per project | 8 GB disk, then $0.125/GB |
| Compute | Nano (shared, up to 0.5 GB) | Micro, about $10 (1 GB); Small about $15; Medium about $60 |
| Egress | 5 GB | 250 GB, then $0.09/GB |
| Pausing | "Free projects are paused after 1 week of inactivity" | not paused |
| Backups | none, no PITR | daily, kept 7 days. PITR is an add-on at $100/month per 7 days |

- **Cost:** now, $0 if the data fits in 500 MB and you accept no backups. Otherwise $25/month. At 10×, still $25/month, since 50 GB is within 250 GB of egress.
- The spend cap is on by default.

**Lock-in:** low to medium. The DB is plain Postgres, but Auth, Storage and RLS-based APIs tie you in if you use them. **Ops burden:** low. **Weekly Python job:** Supabase doesn't host it, so run it elsewhere.

### 3d. Fly.io
https://docs.fly.io/about/pricing , https://docs.fly.io/flyctl/machine-run

- **There is no free tier for new organisations.** "No, new organizations don't have a free tier or a monthly free usage allowance". New accounts get a trial of up to 2 h of Machine runtime or 7 days. A card is required.
- Always-on shared-cpu-1x prices (iad/ewr): 256 MB at $2.19/month, 512 MB at $3.69/month, 1 GB at $6.70/month. Billing is per second. A stopped Machine costs $0.15/GB-month of rootfs.
- Volumes cost $0.15/GB-month. Volume snapshots cost $0.08/GB-month, with the first 10 GB free. Outbound bandwidth in NA/EU is $0.02/GB. Dedicated IPv4 is $2/month, and shared IPv4 is free.
- Managed Postgres starts at **$38/month** (Basic), with storage at $0.28/GB-month.
- **Cost:** with the app plus SQLite on a 1 GB volume (512 MB Machine), about $3.69 + $0.15 + 5 GB × $0.02 ≈ **$3.9/month now** and about **$4.8/month at 10×** (50 GB egress). With Managed Postgres it is about $42+/month.
- **Weekly Python job:** `fly machine run --schedule weekly` ("hourly, daily, weekly and monthly intervals"), billed per second only while running.

**Lock-in:** low, because it runs OCI images. **Ops burden:** low to medium. You own the app image and the DB-on-volume backups, but not the hosts. **Backups:** volume snapshots, plus your own dumps.

---

## 4. Where the weekly Python job can run (all options)

| Runner | Works with | Cost | Notes |
|---|---|---|---|
| cron on homeserver | everything | $0 | needs the box to be up |
| cron on VPS | everything | included | |
| GitHub Actions (schedule) | everything | This repo is **private** (checked 2026-10-22), so it uses the GitHub Free plan's 2,000 min/month. A weekly 30 min job uses about 120 min | 6 h max per job. `schedule` "can be delayed during periods of high loads" and "some queued jobs may be dropped". Public repos auto-disable schedules after 60 days without activity. https://docs.github.com/en/billing/concepts/product-billing/github-actions , https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows , https://docs.github.com/en/actions/reference/limits |
| Fly scheduled Machine | everything | per-second, cents a month | |
| Workers Cron (Paid) | D1 | in the $5 | Python package support not verified |
| Workers Cron (Free) | — | — | 50 subrequests and 10 ms CPU, so not usable for a scraper |

Any LLM API cost for the import is the same whichever host you pick, and is not covered here.

---

## Summary table (monthly, at the assumed baseline)

| Option | Now | 10× | Ops burden | Lock-in | Built-in backups |
|---|---|---|---|---|---|
| Homeserver + CF Tunnel/Free | $0 + electricity | same | highest | none | none, DIY (R2 has 10 GB free) |
| Hetzner CX23 (+backups) | €5.99 (€7.19) excl. VAT, if in stock | same | high | none | daily ×7 at +20 % |
| OVH VPS-1 | from $4.54 (probably 12-month upfront) | same | high | none | daily 24 h incl., 7-day from $1.40 |
| CF Workers + D1 Free | $0 | $0 *only if* indexed search + incremental import | lowest | medium | Time Travel 7 d |
| CF Workers Paid + D1 | $5 | $5 | lowest | medium | Time Travel 30 d (FTS5 not exportable) |
| Neon Free / Launch (+ app host) | $0 / ~$5–20 | ~$19–20 at 0.25 CU always-on | low | low | 6 h / up to 7 d |
| Supabase Free / Pro (+ app host) | $0 (pauses, no backups) / $25 | $25 | low | low–medium | none / daily ×7 |
| Fly.io app + SQLite volume | ~$3.9 | ~$4.8 | low–medium | low | volume snapshots (10 GB free) |
| Fly.io + Managed Postgres | ~$42+ | ~$43+ | low | low | managed |
