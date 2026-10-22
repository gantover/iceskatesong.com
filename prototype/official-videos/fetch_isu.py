"""PROTOTYPE, throwaway. Fetch index + SEGnnn pages for a sample of events (1 req/s, cached)."""
import pathlib, re, time, urllib.request

EVENTS = """season2526/gpf2025 season2526/ec2026 season2526/fc2026 season2526/wjc2026 season2627/jgppol2026
season2627/jgpgeo2026 season2425/wc2025 season2425/wtt2025 season2324/gpusa2023 season1920/gpcan2019
season1920/fc2020 season1920/wjc2020 season1617/wc2017 season2526/gpchn2025 season2122/gpusa2021
season2223/gpf2022 season2425/jgptur2024 season1819/gpf2018 jgpaus2011 season1516/jgppol2015""".split()
CACHE = pathlib.Path(__file__).parent / "cache" / "isu"
UA = "iceskatesong-prototype/0.1 (damian.b.hubert@gmail.com)"

def get(url):
    f = CACHE / re.sub(r"[^\w.]+", "_", url.split("/results/")[1])
    if not f.exists():
        time.sleep(1)
        try:
            body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read()
        except Exception as e:
            print("FAIL", url, e); return None
        f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(body)
    return f.read_text(encoding="utf-8", errors="replace")

for ev in EVENTS:
    base = f"https://results.isu.org/results/{ev}/"
    idx = get(base + "index.htm")
    if idx is None: continue
    segs = sorted(set(re.findall(r"(?i)href=\"?(SEG\d{3})\.htm", idx)))
    ext = re.search(r"(?i)href=\"?SEG\d{3}(\.html?)", idx).group(1) if segs else ".htm"
    for s in segs: get(base + s + ext)
    print(ev, len(segs), "segments")
