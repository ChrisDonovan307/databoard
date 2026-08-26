import pandas as pd
from services.metadata import _split_at_watermark


def test_split_at_watermark_stops_at_older_item():
    items = [
        {"published_at": "2026-08-24T00:00:00Z"},
        {"published_at": "2026-08-22T00:00:00Z"},
        {"published_at": "2026-08-19T00:00:00Z"},  # older than watermark
        {"published_at": "2026-08-01T00:00:00Z"},
    ]
    kept, hit = _split_at_watermark(items, since="2026-08-20T00:00:00Z")
    assert hit is True
    assert len(kept) == 2


def test_split_at_watermark_no_hit_returns_all():
    items = [{"published_at": "2026-08-24T00:00:00Z"}]
    kept, hit = _split_at_watermark(items, since="2026-01-01T00:00:00Z")
    assert hit is False
    assert kept == items


def test_dedupe_keeps_latest_published():
    df = pd.DataFrame(
        [
            {
                "identifier": "abc",
                "installation_url": "https://x",
                "published_at": "2026-08-01T00:00:00Z",
                "global_id": None,
            },
            {
                "identifier": "abc",
                "installation_url": "https://x",
                "published_at": "2026-08-20T00:00:00Z",
                "global_id": None,
            },
        ]
    )
    key = df["global_id"].fillna(df["identifier"]).astype(str) + "|" + df[
        "installation_url"
    ].astype(str)
    df["_k"] = key
    result = df.sort_values("published_at").drop_duplicates("_k", keep="last")
    assert len(result) == 1
    assert result.iloc[0]["published_at"] == "2026-08-20T00:00:00Z"
