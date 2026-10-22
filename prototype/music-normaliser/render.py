# /// script
# dependencies = ["rapidfuzz"]
# ///
"""PROTOTYPE, throwaway. results.json -> results.html, a page to label the normaliser's output.

Run: uv run render.py out/claude-haiku-5-5
"""
import json, random, sys, html
from pathlib import Path
from rapidfuzz import fuzz, process

d = Path(sys.argv[1])
R = json.loads((d / "results.json").read_text())
rng = random.Random(42)
P = {p["id"]: p for p in R["pieces"]}
esc = html.escape


def piece_str(x):
    bits = [f"<b>{esc(x['title'])}</b>"]
    if x["composers"]: bits.append("by " + esc(", ".join(x["composers"])))
    if x["source"]: bits.append("from <i>" + esc(x["source"]) + "</i>")
    if x["performer"]: bits.append("perf. " + esc(x["performer"]))
    bits.append(f"<span class=tag>{esc(x['style'])}</span>")
    bits.append(f"<span class=meta>Piece #{x['piece']} ({esc(x['how'])}{', ' + x['qid'] if x['qid'] else ''}),"
                f" Arr. #{x['arrangement']}</span>")
    return " · ".join(bits)


def radios(name, opts):  # first option pre-checked: only the wrong ones need a click
    return "".join(f"<label><input type=radio name='{name}' value='{v}'{' checked' if i == 0 else ''}> {v}</label>"
                   for i, v in enumerate(opts)) + \
        f"<input class=note name='{name}:note' placeholder='note'>"


def variants(pid):
    return "<br>".join(esc(" | ".join(v)) for v in P[pid]["variants"][:8]) + \
        (f"<br><span class=meta>+{len(P[pid]['variants']) - 8} more</span>" if len(P[pid]["variants"]) > 8 else "")


# 1. random entries
sample = rng.sample(R["rows"], 20)
s1 = "".join(
    f"<tr><td class=meta>{esc(r['article'])}<br>{esc(r['season'])} {esc(r['segment'])}<br>tier: {esc(r['tier'] or '')}"
    f"{' (unsure)' if r['unsure'] else ''}</td><td class=raw>{esc(r['raw'])}</td>"
    f"<td>{'<br>'.join(piece_str(x) for x in r['pieces']) or '<i>nothing</i>'}</td>"
    f"<td>{radios('e' + str(r['id']), ['right', 'wrong'])}</td></tr>" for r in sample)

# 2. merged Pieces (several distinct raw variants) -> false merges?
merged = [p for p in R["pieces"] if len(p["variants"]) > 1]
s2 = "".join(f"<tr><td class=meta>#{p['id']}<br>{p['uses']} uses<br>{esc(', '.join(p['hows']))}</td>"
             f"<td>{variants(p['id'])}</td><td>{radios('m' + str(p['id']), ['one Piece', 'false merge'])}</td></tr>"
             for p in rng.sample(merged, min(10, len(merged))))

# 4. missed duplicates: random Pieces with their closest other Pieces by title
titles = [p["variants"][0][0] for p in R["pieces"]]
ids = [p["id"] for p in R["pieces"]]
s4 = ""
for p in rng.sample(R["pieces"], 10):
    near = [ids[i] for _, sc, i in process.extract(p["variants"][0][0], titles, scorer=fuzz.token_set_ratio, limit=4)
            if ids[i] != p["id"]][:3]
    s4 += (f"<tr><td>{variants(p['id'])}</td><td>" +
           "<hr>".join(f"<span class=meta>#{n}</span> {variants(n)}" for n in near) +
           f"</td><td>{radios('d' + str(p['id']), ['no duplicate', 'duplicate missed'])}</td></tr>")

S = R["summary"]
review_reasons = {}
for r in R["review"]:
    for w in r["why"]:
        review_reasons[w] = review_reasons.get(w, 0) + 1
page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Music normaliser check</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mute:#6b6a65;--line:#dedbd2;--acc:#2f5d8a;--tag:#ece8dc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16171a;--fg:#e8e6e1;--mute:#9a988f;--line:#33343a;--acc:#86b2df;--tag:#2a2b30}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1300px;padding:16px}}
table{{border-collapse:collapse;width:100%;margin-bottom:2em}} td,th{{border-top:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}}
.meta{{color:var(--mute);font-size:12px}} .raw{{font-family:ui-monospace,monospace;font-size:12px;max-width:340px}}
.tag{{background:var(--tag);border-radius:3px;padding:0 4px;font-size:12px}} label{{display:block;white-space:nowrap}}
.note{{width:110px;font-size:12px;background:transparent;color:var(--fg);border:1px solid var(--line)}}
h2{{margin-top:2em}} pre{{background:var(--tag);padding:8px;overflow:auto}} button{{font-size:15px;padding:6px 14px}}
#bar{{position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line)}}
</style>
<div id=bar><button onclick=exportLabels()>Copy labels</button> <span id=count class=meta></span></div>
<h1>Can raw music strings become Pieces and Arrangements without duplicates?</h1>
<p class=meta>PROTOTYPE, throwaway. Model {esc(str(S['model']))}. Every row starts as right; flip only the wrong ones, then press "Copy labels" and paste the result back to Claude.</p>
<h2>Numbers</h2><pre>{esc(json.dumps(S, indent=1))}
review reasons: {esc(json.dumps(review_reasons))}</pre>
<h2>1. Random entries (20): is the parse right?</h2>
<p class=meta>Right = every Piece is correctly identified (title, composer vs performer, Source, Style) and split correctly.</p>
<table>{s1}</table>
<h2>2. Merged Pieces (10): did unlike things get merged?</h2><table>{s2}</table>
<h2>3. Missed duplicates (10 random Pieces vs their closest titles)</h2>
<p class=meta>"duplicate missed" if any Piece on the right is the same Piece as the left one.</p><table>{s4}</table>
<script>
const K='normaliser-labels-'+{json.dumps(d.name)};
function all(){{const o={{}};document.querySelectorAll('input').forEach(i=>{{if(i.type==='radio'&&i.checked)o[i.name]=i.value;if(i.type!=='radio'&&i.value)o[i.name]=i.value}});return o}}
function save(){{const o=all();document.getElementById('count').textContent=Object.keys(o).filter(k=>!k.includes(':')).length+' labelled';try{{localStorage.setItem(K,JSON.stringify(o))}}catch(e){{}}}}
function exportLabels(){{const t=JSON.stringify(all());navigator.clipboard.writeText(t).then(()=>alert('Copied '+t.length+' chars'),()=>prompt('Copy this:',t))}}
try{{const o=JSON.parse(localStorage.getItem(K)||'{{}}');for(const[k,v]of Object.entries(o)){{const r=document.querySelector(`input[name="${{k}}"][value="${{v}}"]`);if(r)r.checked=true;else{{const n=document.querySelector(`input[name="${{k}}"]:not([type=radio])`);if(n)n.value=v}}}}}}catch(e){{}}
document.addEventListener('input',save);save();
</script>"""
(d / "results.html").write_text(page)
print(d / "results.html")
