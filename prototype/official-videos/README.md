# PROTOTYPE, throwaway: official ISU video → Performance matcher

Answers [How does the Import match official ISU videos to Performances?](https://github.com/gantover/iceskatesong.com/issues/17). Never merged.

    python3 fetch_youtube.py   # needs YOUTUBE_API_KEY in ../../.env; ~620 quota units, both uploads playlists
    python3 fetch_isu.py       # 19 sample events, index + SEGnnn pages, 1 req/s, cached
    python3 match.py           # writes out/results.json, prints summary.txt

Method: candidate events = publishedAt in [start-2d, end+10d] (fallback: title year + city);
the title must name the event (ISU index city, or a per-event-type alias list keyed by ISU code prefix);
Segment from Discipline/level/Segment type words; entry = all ISU surnames present in the title
(one-edit fuzzy fallback), ties broken by given names and nation. Results in summary.txt.
