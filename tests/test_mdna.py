from src.mdna import Table, blocks_to_text, parse_table, relevant_excerpt, split_blocks

HTML = (
    "<table><tr><td></td><td></td></tr>"
    "<tr><td colspan='3'></td><td><span>2023</span></td><td></td><td><span>Change</span></td><td><span>2022</span></td></tr>"
    "<tr><td><span>Americas</span></td><td>$</td><td>162,560 </td><td></td><td>(4</td><td>)%</td><td>$</td><td>169,658</td></tr>"
    "</table>"
)
TEXT = "Intro paragraph about the year.   Total net sales decreased 3% during 2023.   " + HTML + "   Unrelated closing remarks."


def test_parse_table_merges_currency_and_percent_cells():
    table = parse_table(HTML)
    assert table.rows[0] == ["", "2023", "Change", "2022"]
    assert table.rows[1] == ["Americas", "$162,560", "(4)%", "$169,658"]


def test_split_blocks_separates_paragraphs_and_tables():
    blocks = split_blocks(TEXT)
    assert [type(b).__name__ for b in blocks] == ["str", "str", "Table", "str"]
    assert "<" not in blocks_to_text(blocks)


def test_relevant_excerpt_includes_following_table():
    picked = relevant_excerpt(TEXT, ["net sales"])
    assert picked[0].startswith("Total net sales") and isinstance(picked[1], Table)
    assert all("Unrelated" not in (b if isinstance(b, str) else b.text) for b in picked)


def test_relevant_excerpt_respects_budget():
    long = "   ".join(f"net sales paragraph {i} " + "x" * 200 for i in range(50))
    assert len(blocks_to_text(relevant_excerpt(long, ["net sales"], max_chars=1000))) <= 1100
