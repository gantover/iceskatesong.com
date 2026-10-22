# Grades: claude-haiku-5-5-aggressive

PROTOTYPE. The 40 items `render.py` samples (Random(42)), graded by the agent at the owner's request, 2026-10-22.
Bar set by the owner before grading: ≥95% right, ≤1 missed duplicate in 30.

## Entries: 16/20 right (fail)

| id | raw | verdict | reason |
|---|---|---|---|
| e5238 | Sorry by Rick Wakeman | right | |
| e912 | Tosca by Giacomo Puccini | right | QID Q192941 |
| e204 | Spartacus by Aram Khachaturian | right | Source = itself, harmless |
| e6074 | "Lamentations" By Marimuz | **wrong** | composer filed as performer ("X by Y" ambiguity) |
| e2253 | Dibby Dibby Sound by Avera | **wrong** | cover act filed as composer; QID right |
| e2006 | Rain, In Your Black Eyes by Ezio Bosso | right | |
| e1828 | Swing: Crazy Little Thing Called Love by Queen | right | album as Source is allowed by GLOSSARY |
| e1143 | Paya d'Ora by Orquesta del Tango… | right | nothing more in the text |
| e6033 | Do You Love Me… by The Contours | right | |
| e839 | The Impossible Dream (Man of La Mancha) by Mitch Leigh | right | |
| e5543 | "Awakening" · From Limelight Soundtrack | right | Chaplin added from memory, correct |
| e6067 | Le discours d'Arthur (Le meilleur reste à venir) by Rebotier | right | |
| e7308 | March: Clock Scene | right? | Prokofiev / Cinderella from memory, plausible, unverified |
| e4467 | Another Level by Tyrone Wells, Dustin Burnett performed by Oh the Larceny | **wrong** | Style "vocal cover" on the original |
| e712 | Jessica's Theme from Who Framed Roger Rabbit by Alan Silvestri | right | |
| e4837 | The Immigrant | right | bare title, nothing to parse |
| e3456 | Tango: Vuelvo al Sur by Medialuna Tango Project | **wrong** | memory facts wrong: Source is film *Sur*, lyricist Solanas, not *María de Buenos Aires* / Ferrer |
| e260 | The Phantom of the Opera by Andrew Lloyd Webber | right | |
| e244 | Another Brick in the Wall by Pink Floyd performed by the LPO | right | |
| e767 | Nostradamus | right | bare title |

No entry has the wrong Piece; every error is in composer / Source / Style.
Same 20 entries in the default (rules-first) run: about 12/20, mostly performers filed as composers (Queen, Pink Floyd, The Contours, Medialuna).

## Merged Pieces: 8/10 one Piece (fail)

| id | variants | verdict |
|---|---|---|
| m758 | Cha Cha (bare) + Cha Cha / Santa Esmeralda, 7 uses | **false merge**: generic rhythm name |
| m814 | Paxi Ni Ngongo / Bonga | one Piece |
| m2325 | What Love Can Be / Kingdom Come | one Piece |
| m2907 | Spectres in the Fog / Zimmer | one Piece |
| m59 | Umbrellas of Cherbourg (EN/FR) / Legrand | one Piece |
| m2637 | Entr'acte (bare) + Entr'acte / Lloyd Webber | **false merge**: generic title |
| m625 | Korobushka spellings | one Piece |
| m3843 | Rhapsody on a Theme of Paganini, Var. 8 + Var. 11 | one Piece (variations not split) |
| m3245 | Human / Rory Graham, two credit lists | one Piece |
| m3768 | Drink Up Me Hearties | one Piece |

287 of 789 merged Pieces contain a bare-title member (Flamenco, Overture, Tango, Maria…): the false-merge risk class.

## Missed duplicates: 0/10 (pass)

None of the 10 sampled Pieces had a duplicate among its 3 closest titles. Caveat: closest-title sampling can't see cross-language duplicates.
