# Music normaliser acceptance — issue #35

Re-graded on 2026-10-26 against the original `claude-haiku-5-5-aggressive`
prototype's 20 entries and ten merge groups. The live Haiku responses and
Wikidata composer evidence are retained in `import/tests/pages/music/`;
`import/tests/test_normalise.py` repeats the checks without paid requests.

## Result

- **Entry precision: 19/20 (95%). Pass** against the owner's ≥95% bar.
- **False merges in the ten groups: zero.** The generic Cha Cha and Entr'acte
  merges in the prototype are prevented.
- **Missed duplicates: one of the ten groups still has a split. Pass** against
  the owner's ≤1 missed duplicate across the 20 entry and ten merge checks.
  This sample cannot establish corpus-wide recall or find every cross-language
  duplicate.

The one entry error is **e6067**: Jérôme Rebotier is classified as a performer
instead of the composer of *Le discours d'Arthur*. His name is in the text;
the error is the role. No composer or Source absent from the entry or Wikidata
is retained. The model's omission of the bare title *The Immigrant* is handled
by the rules tier. Named variations retain the parent work's title and their
numbers, including when the entry says “Variations 11 & 8”.

The 20 entry IDs are e5238, e912, e204, e6074, e2253, e2006, e1828, e1143,
e6033, e839, e5543, e6067, e7308, e4467, e712, e4837, e3456, e260, e244, e767.
Expected facts are independently recorded alongside the captured responses.
Unstated credits or styles are omitted, rather than being filled from memory.

| Original merge group | Result under the adopted evidence rules |
| --- | --- |
| m758 Cha Cha | Separate; no shared work identity beyond the generic title. |
| m814 Paxi Ni Ngongo | Missed duplicate: performer-only credit versus a Source credit. |
| m2325 What Love Can Be | Joined by the title-link QID. |
| m2907 Spectres in the Fog | The actual nested HTML is extracted once, preserving its shared credit; all five named cues remain distinct. |
| m59 Umbrellas of Cherbourg | QID-linked occurrences join; the differently credited version joins after a positive model pair verdict. |
| m2637 Entr'acte | Bare title stays separate from the credited occurrence. |
| m625 Korobushka | The shared performer and a positive pair verdict join the spelling variant to the QID-linked Piece. |
| m3843 Paganini variations | Repeated occurrences of each variation join; Variation 11 and Variation 8 stay distinct. |
| m3245 Human | The same credited Artist matches across the differing composer/performer classifications; no role is inferred from the merge. |
| m3768 Drink Up Me Hearties | The track template preserves its actual shared heading and Hans Zimmer credit; the title variants join after a positive pair verdict. |

The initial six-split result lost HTML scope and ignored performer evidence.
The corrected benchmark retains the original cells for m2907 and m3768 in
`context-cells.json` and runs them through the production Wikipedia extractor.
The prototype incorrectly counted the nested *Spectres in the Fog* twice;
the track template had dropped credits that apply to each listed track.
These are recovered source facts, not credits supplied from model memory.

Shared performers now support identity matching without becoming composers or
raising an occurrence's grade. Differently credited entries require an explicit
model pair verdict. Bare titles, conflicting composers/QIDs, and distinct
numbered works remain guarded. The one remaining split, *Paxi Ni Ngongo*, has
a performer credit on one side and a Don Juan musical credit on the other;
the recorded model verdict is false. Raw text remains available for #37 and
corrections in #36.

The original prototype grade treated the two Paganini variations as one Piece.
Code review exposed that the same fuzzy rule also merged distinct numbered
concertos. The final matcher preserves the most specific named work from
`GLOSSARY.md`: conflicting work/movement/variation numbers cannot merge by
fuzzy title or a model pair verdict. The two distinct variations are therefore
not counted as a missed duplicate in the final assessment.

The first production Import failed in its apply transaction: a Wikipedia music
title linked to Sergei Rachmaninoff's article, so the Piece took his QID, which
was already his artist key. A title-link QID that is a composer of another
fetched work now names the person, not the work: the occurrence keeps its text
credits and is not identified, and Pieces linked that way no longer join by it.

## Runtime checks

The integration tests cover ordered graded occurrences, independent grades,
Wikidata-only composers for identified Pieces, existing key/alias reuse,
unchanged-string and pair-verdict caching, cap exhaustion, ambiguous API
failures, Wikidata API error envelopes, preservation of human claims, and
refusal of unsupported or numerically conflicting merges.
The merge benchmark enforces the recall threshold, checks false merges, and
repeats the Import with zero model calls. A regression also starts with an
existing split occurrence and verifies that re-import relinks it to the
canonical Piece while preserving bare-title identity and human claims.
This includes existing title variants that need their first model pair
verdict: matching their own old aliases does not suppress reconciliation
against another active Piece. Once reconciled, subsequent Imports make no
new model calls. Unreferenced historical rows retain their keys and aliases;
the Import relinks its music occurrences rather than deleting records.

`ANTHROPIC_API_KEY` enables aggressive parsing with `claude-haiku-5-5`.
Issue #35 explicitly selects the prototype's aggressive mode: every new raw
string is parsed by the model, even though the PRD's general pipeline shorthand
describes a leftovers-only mode. Cached strings do not incur another request;
rules still handle missing keys and named-title abstentions.
`MUSIC_SPEND_CAP_USD` defaults to **$10 per Import**, above the prototype's
rough $7 projection. Parse and pair requests share the budget. Requests
reserve their maximum charge before sending, then refund known unused tokens;
ambiguous failures keep their reservation and SDK retries are disabled.
Uncached strings left at the cap remain ungraded and log Import problems.
Cached results remain usable at a zero budget. Without a key, the rules tier
runs without paid requests. All network work precedes the apply transaction.

Pricing and limits were checked against the official
[Haiku 5.5 documentation](https://platform.claude.com/docs/en/models/haiku-5-5/overview).
The implementation uses short-context standard pricing ($0.10 input / $0.50
output per million tokens), bounds request size below that tier, and reserves
the full short-context input allowance plus maximum output. The two live
original grading runs each had a $1 cap; the recall re-grade reused those
cached parses and had a $0.25 cap for new parses and pair verdicts.

This is a sample acceptance record. A full production corpus Import, ARM64
container build, and deployed-site checks were not performed for this change.
