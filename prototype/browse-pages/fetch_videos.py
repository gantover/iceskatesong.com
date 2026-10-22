"""PROTOTYPE, throwaway. Pull the newest official ISU upload titles (YouTube Data API, ~80 quota units)."""
import json, pathlib, sys, urllib.request, urllib.parse

ENV = pathlib.Path(sys.argv[1])  # path to the repo's .env
KEY = next(l.split("=", 1)[1].strip().strip("\"'") for l in open(ENV) if l.startswith("YOUTUBE_API_KEY="))
CHANNELS = {"skating_isu": ("UCVZpqbnDjHyScSYGFPMUtYA", 60), "jgp": ("UCbv3gsBXzIwotCt2JGySfJA", 20)}
OUT = pathlib.Path(__file__).parent / "cache"; OUT.mkdir(exist_ok=True)

for name, (cid, pages) in CHANNELS.items():
    items, token = [], None
    for _ in range(pages):
        q = dict(part="snippet,contentDetails", playlistId="UU" + cid[2:], maxResults=50, key=KEY, **({"pageToken": token} if token else {}))
        r = json.load(urllib.request.urlopen("https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode(q)))
        items += [{"id": i["contentDetails"]["videoId"], "title": i["snippet"]["title"], "published": i["contentDetails"].get("videoPublishedAt") or i["snippet"]["publishedAt"]} for i in r["items"]]
        token = r.get("nextPageToken")
        if not token: break
    (OUT / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False))
    print(name, len(items), items[-1]["published"])
