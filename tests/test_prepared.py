"""The prepared index: what it reads, how it combines, and what it refuses.

A corpus is taken whole or not at all, so every shortfall a check can see
is reported together, and each names the file it concerns.
"""

import json

import pytest

from strata.contracts import (
    PREPARED_FORMAT,
    PREPARED_NAME,
    Choices,
    Frames,
    Image,
    PreparedError,
    PreparedFormatError,
    PreparedIndex,
    PreparedSample,
    check,
)


def index(type_name="frames", **samples) -> PreparedIndex:
    return PreparedIndex(
        version=PREPARED_FORMAT,
        type=type_name,
        samples={key: PreparedSample(metadata=meta) for key, meta in samples.items()},
    )


# ----------------------------------------------------------------------
# Reading and writing
# ----------------------------------------------------------------------


def test_an_index_survives_the_round_trip():
    original = PreparedIndex(
        version=PREPARED_FORMAT,
        type="image",
        produced_by="leaves",
        samples={"a/1.jpg": PreparedSample(metadata={"leaf": "7"}, value=Choices(values=["x"]))},
    )
    assert PreparedIndex.from_json(original.to_json()) == original


def test_the_text_is_stable_for_a_diff():
    text = index(**{"b/2.jpg": {"video": "b"}, "a/1.jpg": {"video": "a"}}).to_json()
    assert text.endswith("\n")
    assert text.index('"a/1.jpg"') < text.index('"b/2.jpg"')


def test_an_index_from_before_it_named_its_type_is_refused_as_stale():
    # The first layout: no type, and metadata read by whichever type ingested
    old = {"version": 1, "produced_by": "x", "samples": {}}
    with pytest.raises(PreparedFormatError, match="Prepare the corpus again"):
        PreparedIndex.from_json(json.dumps(old))


def test_an_index_that_does_not_say_its_version_is_refused_as_stale():
    with pytest.raises(PreparedFormatError, match="does not say"):
        PreparedIndex.from_json(json.dumps({"type": "image", "samples": {}}))


# ----------------------------------------------------------------------
# Combining runs
# ----------------------------------------------------------------------


def test_a_second_run_adds_to_the_first():
    first = index(**{"a/1.jpg": {"video": "a"}})
    second = index(**{"b/1.jpg": {"video": "b"}})
    assert set(first.merge(second).samples) == {"a/1.jpg", "b/1.jpg"}


def test_a_later_run_wins_for_a_file_both_name():
    first = index(**{"a/1.jpg": {"video": "old"}})
    second = index(**{"a/1.jpg": {"video": "new"}})
    assert first.merge(second).samples["a/1.jpg"].metadata == {"video": "new"}


def test_one_corpus_is_one_type():
    with pytest.raises(PreparedError, match="One corpus is one type"):
        index("frames").merge(index("image"))


# ----------------------------------------------------------------------
# Checking a corpus against its type
# ----------------------------------------------------------------------


def test_a_corpus_that_meets_its_type_passes_with_its_metadata():
    corpus = index(**{"clip/000001.jpg": {"video": "clip", "frame_index": 1}})
    checked = check(corpus, Frames(), "frames", {"clip/000001.jpg"})
    assert checked.ok
    assert checked.entries == {"clip/000001.jpg": {"video": "clip", "frame_index": 1}}


def test_a_corpus_of_another_type_is_refused_before_its_files_are_read():
    checked = check(index("image", **{"a.jpg": {}}), Frames(), "frames", {"a.jpg"})
    assert not checked.ok
    assert not checked.entries
    assert "prepared as 'image'" in str(checked.violations[0])


def test_every_shortfall_is_reported_and_names_its_file():
    corpus = index(
        **{
            "clip/1.jpg": {"video": "clip"},  # fine
            "clip/2.jpg": {},  # no video
            "clip/3.jpg": {"video": "clip"},  # not on disk
            "clip/4.gif.txt": {"video": "clip"},  # not an image
        }
    )
    present = {"clip/1.jpg", "clip/2.jpg", "clip/4.gif.txt"}
    checked = check(corpus, Frames(), "frames", present)

    found = {v.key: v.problem for v in checked.violations}
    assert set(found) == {"clip/2.jpg", "clip/3.jpg", "clip/4.gif.txt"}
    assert "video" in found["clip/2.jpg"]
    assert "not there" in found["clip/3.jpg"]
    assert ".txt" in found["clip/4.gif.txt"]
    assert set(checked.entries) == {"clip/1.jpg"}


@pytest.mark.parametrize(
    "key",
    ["../outside.jpg", "/abs/a.jpg", "a/../../b.jpg", "a\\b.jpg", "./a.jpg", "a//b.jpg", ""],
)
def test_a_file_named_outside_the_root_or_ambiguously_is_refused(key):
    checked = check(index("image", **{key: {}}), Image(), "image", {key})
    assert [v.key for v in checked.violations] == [key]


def test_the_index_cannot_name_itself():
    checked = check(index("image", **{PREPARED_NAME: {}}), Image(), "image", {PREPARED_NAME})
    assert not checked.ok
