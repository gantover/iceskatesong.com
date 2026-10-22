"""PROTOTYPE, throwaway. Do full-segment streams carry per-skater timestamps in their descriptions?"""
import json, re, urllib.request, urllib.parse, random
KEY = next(l.split("=", 1)[1].strip().strip("\"'") for l in open("../../.env") if l.startswith("YOUTUBE_API_KEY="))
o = json.load(open("out/results.json"))
seg = [x for x in o if x["status"].startswith("segment-level") and not re.search(r"practice", x["title"], re.I)]
random.seed(11)
items = []
for k in range(0, 150, 50):
    s = random.sample(seg, 150)[k:k + 50] if k == 0 else seg[k * 2:k * 2 + 50]
    r = json.load(urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(
        {"part": "snippet,contentDetails", "id": ",".join(x["id"] for x in s), "key": KEY})))
    items += r["items"]
ts = re.compile(r"(?m)^\s*\(?\d{1,2}:\d{2}(?::\d{2})?\)?\s")
def sec(p):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", p)
    return int(m.group(1) or 0) * 86400 + int(m.group(2) or 0) * 3600 + int(m.group(3) or 0) * 60 + int(m.group(4) or 0)
long = {i["id"]: i for i in items if sec(i["contentDetails"]["duration"]) > 1800}.values()
withts = [i for i in long if len(ts.findall(i["snippet"]["description"])) >= 3]
print("sampled", len(items), "| longer than 30 min:", len(long), "| with >=3 timestamp lines:", len(withts))
for i in sorted(long, key=lambda i: i["snippet"]["publishedAt"]):
    print(f'  {sec(i["contentDetails"]["duration"])//60:4}min ts={len(ts.findall(i["snippet"]["description"])):3} {i["snippet"]["publishedAt"][:10]} {i["snippet"]["title"][:70]}')
if withts:
    print("\nEXAMPLE description:\n", withts[0]["snippet"]["description"][:1200])
