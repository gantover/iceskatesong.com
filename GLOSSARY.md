# Glossary

**Skater**: One individual person who competes. Always a single human, never a pair.

**Team**: A pair (pairs) or couple (ice dance) of two Skaters competing together. A Skater can belong to several Teams over a career. A Team's Performances count as Performances of each of its Skaters.

**Discipline**: Men's singles, women's singles, pairs, or ice dance.

**Season**: An ISU competitive season (e.g. 2024–25), running roughly July to June.

**Segment**: One scored part of one Discipline at one level of one Competition (e.g. Men's Free Skating at the 2025 World Championships). A qualifying group is its own Segment.

**Segment type**: The kind of Segment: short program, free skating, short dance, rhythm dance, free dance, original dance, or compulsory dance, named as the ISU named it in that era.

**Competition**: An ISU-sanctioned event (e.g. 2025 World Championships), senior or junior level.

**Program**: A choreographed routine for one Season and one Segment type, skated by one Skater or Team. Music belongs to the Program. A mid-season music change makes a new Program.

**Performance**: One skating of a Program at one Competition. It has a result and may have a video.

**Piece**: A musical work regardless of recording or arrangement, at the most specific grain the data names: an aria, song or film cue, else the whole work (e.g. *He's a Pirate*; *Swan Lake* when only the ballet is named). The unit users search and pick. A Program uses one or more Pieces. Pieces never contain other Pieces.

**Arrangement**: One Piece played in one Style, optionally by one performing Artist (e.g. *Bad Romance*, piano ballad). Programs use Arrangements, and the original version is an Arrangement too. Not tied to a specific recording.

**Style**: How a Piece is played in an Arrangement: original, orchestral, piano, ballad, string-quartet cover, remix, vocal cover, etc.

**Source**: The film, musical, ballet, opera, album, or franchise a Piece comes from (e.g. *Pirates of the Caribbean*; *Swan Lake* for *Black Swan pas de deux*). Not itself a Piece. A Piece has at most one Source.

**Artist**: A person or group credited on music: the composer or songwriter of a Piece, or the performer of an Arrangement.

**Genre**: A descriptive tag on a Piece (e.g. classical, pop, tango).

**Submission**: A contribution from a visitor. Either a **Video Submission** (a YouTube URL plus optional hints: "this video is this Performance") or a **Music Submission** (free music text plus an optional link: "this Program uses this music"). An approved Music Submission becomes the Program's music unless the Admin has set it directly.

**Match grade**: How well the evidence behind a Program's link to a Piece backs it: **identified** (an external ID), **credited** (a composer or Source), or **title only**. For imported music the evidence is that entry's own text, so a bare title stays title only even on a well-known Piece. For music the Admin picked, the evidence is the Piece itself, so a confirmed pick still shows title only until the Piece gains an Artist, Source or external ID.

**Flag**: A visitor's report that a Performance, video, or music is wrongly assigned. It stays open until the Admin resolves or dismisses it.

**Block**: The Admin barring an anonymous visitor from sending Submissions and Flags, and discarding their pending ones.

**Review Queue**: Submissions not confident enough to publish automatically, plus all Music Submissions and Flags, awaiting the Admin.

**Admin**: The person who resolves the Review Queue and corrects data (reassign, merge, split, edit). Every Admin change is logged and reversible.

**Corrections file**: The repo-kept list of Admin fixes (Piece aliases, Program music, Skater merges, video hides) applied on every Import until the Admin edit screens replace it.

**Import**: One run that pulls new and changed records from the data sources. Started only by the Admin, as a **quick** Import (re-checks the ISU results of the two newest Seasons listed, older events from the cache) or a **full** one (every ISU page); each Import has a status (pending, running, succeeded, failed).

_Avoid_: "song" for Piece (many Pieces aren't songs); "routine" for Program; "skate" for Performance; bare "source" for where data comes from (say "data source": Source is the film, musical or ballet a Piece comes from).
