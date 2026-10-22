"""PROTOTYPE, throwaway. Pull every upload title from the two official ISU channels via the Data API."""
import json, os, pathlib, urllib.request, urllib.parse

KEY = next(l.split("=", 1)[1].strip().strip("\"'") for l in open(pathlib.Path(__file__).parents[2] / ".env") if l.startswith("YOUTUBE_API_KEY="))
CHANNELS = {"skating_isu": "UCVZpqbnDjHyScSYGFPMUtYA", "jgp": "UCbv3gsBXzIwotCt2JGySfJA"}
OUT = pathlib.Path(__file__).parent / "cache"; OUT.mkdir(exist_ok=True)

def get(path, **q):
    q["key"] = KEY
    return json.load(urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?{urllib.parse.urlencode(q)}"))

units = 0
for name, cid in CHANNELS.items():
    items, token = [], None
    while True:
        r = get("playlistItems", part="snippet,contentDetails", playlistId="UU" + cid[2:], maxResults=50, **({"pageToken": token} if token else {}))
        units += 1
        items += [{"id": i["contentDetails"]["videoId"], "title": i["snippet"]["title"], "published": i["contentDetails"].get("videoPublishedAt") or i["snippet"]["publishedAt"]} for i in r["items"]]
        token = r.get("nextPageToken")
        if not token: break
    (OUT / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=0))
    print(name, len(items))
print("quota units", units)
