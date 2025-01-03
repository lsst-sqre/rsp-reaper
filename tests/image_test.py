"""Tests for image comparison and sorting."""

from rsp_reaper.storage.gar import GARClient


def test_image_sort(gar_client: GARClient) -> None:
    """Test image comparison and sorting."""
    gar_client.categorize()
    cat = gar_client.categorized_images
    rels = list(cat.rsp["release"].values())
    assert rels == sorted(rels, reverse=True)


def test_image_counts(gar_client: GARClient) -> None:
    """Test whether categorization gets the right item counts."""
    gar_client.categorize()
    cat = gar_client.categorized_images
    counts = {
        "release": 19,
        "weekly": 144,
        "daily": 398,
        "release_candidate": 46,
        "experimental": 80,
        "unknown": 0,
    }
    for category, count in counts.items():
        assert len(cat.rsp[category]) == count
    assert len(cat.untagged) == 136
