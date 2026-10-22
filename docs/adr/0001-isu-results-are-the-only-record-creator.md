# ISU results are the only data source that creates records

Competitions, Segments, Performances, Skaters and Teams are created only from ISU result pages (`isuresults.com` / `results.isu.org`). Every other data source — Wikipedia program tables, Wikidata labels, official ISU YouTube videos, Submissions — only attaches to records that already exist and never creates one. Skaters and Teams carry our own IDs, with the 8-digit ISU ID as a unique external key where one exists.

We chose this because avoiding duplicates is the project's hardest requirement, and ISU results are the only complete, authoritative list of who skated where from 2004–05 on. Letting Wikipedia or a YouTube title create a Skater would reintroduce the name-drift duplicates ("Anastasia"/"Anastasiia") that matching on ISU ID avoids.

## Consequences

- Anything the ISU results don't list (pre-2004 events, non-ISU Competitions) can't enter the database. Adding such a data source later means revisiting this ADR.
- ISU's terms give no explicit permission to reuse results, so this rests on ISU data being usable; the owner chose not to ask for written consent ([Ask the ISU for written consent to reuse results data](https://github.com/gantover/iceskatesong.com/issues/12)): the site is non-commercial and republishes facts only, with a polite crawl and full attribution. An objection from the ISU would reopen this ADR.
- Team members are matched to Skaters by normalised name + nationality, because ISU Team IDs don't link to the individual Skaters; the Admin fixes misses.
