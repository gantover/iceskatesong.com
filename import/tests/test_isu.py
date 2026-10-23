import datetime as dt
import pathlib
from decimal import Decimal

import pytest

import isu

PAGES = pathlib.Path(__file__).parent / "pages" / "results"


def page(path):
    return isu.decode((PAGES / path).read_bytes())


def test_index_gives_name_city_dates_and_segment_pages_only():
    event = isu.parse_index(page("season2526/gpf2025/index.htm"))
    assert event.name == "ISU Grand Prix Final 2025"
    assert event.city == "Aichi, Nagoya"
    assert (event.start, event.end) == (dt.date(2025, 12, 4), dt.date(2025, 12, 7))
    assert event.segment_pages == [f"SEG{n:03}.htm" for n in range(1, 17)]


def test_older_index_is_latin1_with_uppercase_links():
    event = isu.parse_index(page("wc2008/index.htm"))
    assert event.city == "Göteborg"
    assert event.start == dt.date(2008, 3, 16)
    assert event.segment_pages[0] == "SEG001.HTM"
    assert len(event.segment_pages) == 9


def test_segment_page_gives_its_segment_and_entries_as_printed():
    seg = isu.parse_segment(page("season2526/gpf2025/SEG007.htm"))
    assert (seg.discipline, seg.level, seg.segment_type, seg.round) == ("ice dance", "senior", "rhythm dance", "")
    assert len(seg.entries) == 6
    assert seg.entries[0] == isu.Entry(
        rank=1, rank_label=None, name="Madison CHOCK / Evan BATES", nation="USA", isu_id="00013665",
        tss=Decimal("88.74"), tes=Decimal("50.93"), pcs=Decimal("37.81"), deductions=Decimal("0.00"), start_number=6,
    )


def test_older_segment_page_with_uppercase_tags_and_five_components():
    seg = isu.parse_segment(page("wc2008/SEG001.HTM"))
    assert (seg.discipline, seg.level, seg.segment_type) == ("men", "senior", "short program")
    assert seg.entries[5] == isu.Entry(
        rank=6, rank_label=None, name="Brian JOUBERT", nation="FRA", isu_id="00004708",
        tss=Decimal("77.75"), tes=Decimal("41.14"), pcs=Decimal("38.61"), deductions=Decimal("2.00"), start_number=43,
    )


def test_qualifying_group_is_its_own_round_of_the_free_skating():
    seg = isu.parse_segment(page("wc2006/SEG001.HTM"))
    assert (seg.discipline, seg.segment_type, seg.round) == ("men", "free skating", "qualifying group a")
    assert seg.entries[0].name == "Stephane LAMBIEL"


def test_city_printed_with_a_comma_nation():
    assert isu.parse_index(page("season1516/ec2016/index.htm")).city == "Bratislava"


def test_dates_printed_month_first_with_slashes():
    event = isu.parse_index(page("wjc2010/index.htm"))
    assert (event.city, event.start, event.end) == ("The Hague", dt.date(2010, 3, 9), dt.date(2010, 3, 13))


def test_index_of_the_other_vendor_fails_to_parse():
    with pytest.raises(isu.ParseError, match="no SEGnnn pages"):
        isu.parse_index(page("season2324/gpjpn2023/index.htm"))


def test_dates_printed_day_first_with_slashes():
    event = isu.parse_index(page("gpcan06/index.htm"))
    assert (event.start, event.end) == (dt.date(2006, 11, 2), dt.date(2006, 11, 5))


def test_a_typo_in_the_end_year_is_ignored():
    event = isu.parse_index(page("jgpcze2010/index.htm"))  # printed "10/13/2010 - 10/16/2020"
    assert (event.start, event.end) == (dt.date(2010, 10, 13), dt.date(2010, 10, 16))


def test_dates_printed_with_two_digit_years():
    event = isu.parse_index(page("season1819/gpfin2018/index.htm"))  # "02/11/18 - 04/11/18"
    assert (event.city, event.start, event.end) == ("Helsinki", dt.date(2018, 11, 2), dt.date(2018, 11, 4))


@pytest.mark.parametrize("path, segment", [
    ("owg2014/SEG009.HTM", ("men", "senior", "short program", "team")),  # "Team Men - Short Program"
    ("season2122/owg2022/SEG009.htm", ("men", "senior", "short program", "team")),  # "Team Event - Men Single Skating - …"
    ("season1920/wyog2020/SEG009.htm", ("men", "senior", "free skating", "team")),  # "Mixed NOC Team - Men Single Skating - …"
    ("ec2011/SEG003.HTM", ("ice dance", "senior", "free dance", "preliminary round")),
    ("gpf0809/SEG009.HTM", ("men", "senior", "short program", "")),  # "Senior Men"
    ("season1718/owg2018/SEG005.HTM", ("pairs", "senior", "short program", "")),  # "Pair Skating"
    ("season1718/owg2018/SEG001.HTM", ("men", "senior", "short program", "")),  # "Men Single Skating"
    ("season1920/jgprus2019/SEG005.htm", ("pairs", "junior", "short program", "")),  # "Junior Pair"
])
def test_caption_variants(path, segment):
    seg = isu.parse_segment(page(path))
    assert (seg.discipline, seg.level, seg.segment_type, seg.round) == segment


def test_withdrawn_and_disqualified_entries_keep_their_label_instead_of_a_rank_or_scores():
    withdrawn = next(e for e in isu.parse_segment(page("season2122/jgpaut2021/SEG003.htm")).entries if e.isu_id == "00107901")
    assert (withdrawn.name, withdrawn.rank, withdrawn.rank_label, withdrawn.tss, withdrawn.start_number) == (
        "Zara HUSEDZINOVIC", None, "WD", None, 20)
    disqualified = next(e for e in isu.parse_segment(page("season2122/ec2022/SEG003.htm")).entries if e.isu_id == "00107871")
    assert (disqualified.rank, disqualified.rank_label, disqualified.tss, disqualified.start_number) == (None, "DSQ", None, 35)


def test_2004_index_prints_name_city_and_dates_as_headings():
    event = isu.parse_index(page("jgpchn2004/index.htm"))
    assert (event.name, event.city) == ("ISU Junior Grand Prix Harbin", "Harbin")
    assert (event.start, event.end) == (dt.date(2004, 9, 16), dt.date(2004, 9, 19))
    assert event.segment_pages == [f"SEG{n:03}.HTM" for n in range(1, 10)]  # as linked, though the host serves seg001.htm


def test_2004_segment_page_prints_its_caption_as_a_heading_and_entries_without_isu_id():
    seg = isu.parse_segment(page("jgpchn2004/seg001.htm"))
    assert (seg.discipline, seg.segment_type, seg.round) == ("men", "short program", "")
    assert seg.entries[4] == isu.Entry(
        rank=5, rank_label=None, name="Jinlin GUAN", nation="CHN", isu_id=None,
        tss=Decimal("51.06"), tes=Decimal("25.24"), pcs=Decimal("25.82"), deductions=Decimal("0.00"), start_number=8,
    )
    assert seg.entries[4].key == "Jinlin GUAN (CHN)"


def test_surname_first_names_are_turned_given_name_first():
    seg = isu.parse_segment(page("ec2005/SEG005.HTM"))  # "TOTMIANINA Tatiana - MARININ Maxim"
    assert (seg.discipline, seg.segment_type) == ("pairs", "short program")
    assert seg.entries[0].name == "Tatiana TOTMIANINA / Maxim MARININ"


def test_qualifying_group_printed_in_the_category():
    seg = isu.parse_segment(page("wjc2005/SEG001.HTM"))  # "Men Qualifying Group A - Free Skating"
    assert (seg.discipline, seg.segment_type, seg.round) == ("men", "free skating", "qualifying group a")


def test_synchronized_skating_is_skipped():
    with pytest.raises(isu.Skipped):
        isu.parse_segment(page("season1516/gpf1516/SEG017.HTM"))
