import gzip

from neurofly.proprioception_polarity_reviewed_match_discovery import inspect


def test_reviewed_match_discovery_reports_schema_and_keyword_hits_without_classifying():
    text = (
        "query_id,match_id,match_cell_type,validation\n"
        "1,101,hook_flx,TRUE\n"
        "2,102,other,FALSE\n"
    )
    payload = gzip.compress(text.encode("utf-8"))
    report = inspect(payload)
    assert report["csv_columns"] == ["query_id", "match_id", "match_cell_type", "validation"]
    assert report["row_count"] == 2
    assert report["keyword_hit_count"] == 1
    assert report["keyword_hits"][0]["match_cell_type"] == "hook_flx"
    assert report["md5_matches"] is False
