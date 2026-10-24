"""What a sample is, and the invariants that keep it honest.

Each failure this guards against is silent: a subtype that changes its
media stops being returned by a query for that media, a stored path that
does not match the class chain makes "is this an image" answerable two
ways, and a subtype that drops a required key is accepted where its parent
would have been refused.
"""

from pathlib import Path
from typing import ClassVar

import pytest

from strata.contracts.builtin_types import (
    Frames,
    GeneratedMedia,
    GeneratedText,
    Image,
    SFTExample,
    SFTTextExample,
    Text,
)
from strata.contracts.sample_types import (
    PLAIN,
    SampleType,
    SampleTypeError,
    available,
    resolve,
)

# ----------------------------------------------------------------------
# The path is the class chain
# ----------------------------------------------------------------------


def test_an_unspecialised_type_is_plain():
    assert Image.subtype() == PLAIN
    assert Text.subtype() == PLAIN


def test_a_subtype_names_what_it_adds():
    assert Frames.subtype() == "frames"


def test_depth_comes_from_inheriting():
    class Satellite(Image):
        segment = "satellite"

    class Multispectral(Satellite):
        segment = "multispectral"

    # Selecting 'satellite' has to match this without knowing it exists,
    # which is the same prefix rule collections use
    assert Satellite.subtype() == "satellite"
    assert Multispectral.subtype() == "satellite/multispectral"
    assert Multispectral.subtype().startswith(Satellite.subtype() + "/")


def test_substitution_holds_in_code():
    class Satellite(Image):
        segment = "satellite"

    # Where an image is expected, a satellite scene does
    assert issubclass(Satellite, Image)
    assert Satellite.media == Image.media


# ----------------------------------------------------------------------
# What is refused, and why
# ----------------------------------------------------------------------


def test_a_subtype_cannot_change_its_media():
    with pytest.raises(SampleTypeError, match="cannot"):

        class Raster(Image):
            media = "raster"
            segment = "raster"


def test_a_segment_cannot_carry_its_own_path():
    # Depth comes from inheriting; a slash here would let the stored path
    # and the class chain disagree
    with pytest.raises(SampleTypeError, match="'/'"):

        class Nested(Image):
            segment = "satellite/multispectral"


def test_a_type_with_no_parent_media_is_free_to_declare_one():
    class Audio(SampleType):
        media = "audio"
        extensions = frozenset({"wav"})

    assert Audio.subtype() == PLAIN


# ----------------------------------------------------------------------
# Extensions are checked, not used to discover
# ----------------------------------------------------------------------


def test_an_allowed_extension_is_admitted():
    assert Image().allows(Path("a/b/photo.JPG"))
    assert Text().allows(Path("notes.md"))


def test_anything_else_is_not():
    # Reported by the caller rather than skipped in silence: a corpus
    # quietly smaller than the directory it came from is the failure this
    # list exists to make visible
    assert not Image().allows(Path("notes.md"))
    assert not Image().allows(Path("no-extension"))


def test_a_subtype_inherits_what_it_admits():
    assert Frames().allows(Path("vid1/frame001.jpg"))


# ----------------------------------------------------------------------
# What a sample must arrive with
# ----------------------------------------------------------------------


def test_a_plain_sample_requires_nothing_and_keeps_what_it_is_given():
    assert Image().check_metadata({}) == {}
    assert Image().check_metadata({"camera": "a", "exposure": 0.5}) == {
        "camera": "a",
        "exposure": 0.5,
    }


def test_a_frame_must_say_which_video_it_came_from():
    # A frame with no video would be a group of one under group_by = "video",
    # a split that leaks a video across sides without saying so
    with pytest.raises(SampleTypeError, match="video"):
        Frames().check_metadata({"frame_index": 3})
    with pytest.raises(SampleTypeError, match="video"):
        Frames().check_metadata({"video": ""})


def test_a_frame_that_says_keeps_the_rest_of_what_it_knows():
    assert Frames().check_metadata({"video": "clip-1", "frame_index": 3}) == {
        "video": "clip-1",
        "frame_index": 3,
    }


def test_a_subtype_inherits_what_its_parent_requires():
    class Thermal(Frames):
        segment = "thermal"

    with pytest.raises(SampleTypeError, match="video"):
        Thermal().check_metadata({})


def test_a_subtype_can_require_more():
    class Satellite(Image):
        segment = "satellite"

        class Metadata(Image.Metadata):
            crs: str

    with pytest.raises(SampleTypeError, match="crs"):
        Satellite().check_metadata({})
    assert Satellite().check_metadata({"crs": "EPSG:4326"})["crs"] == "EPSG:4326"


def test_a_subtype_cannot_require_less():
    # Where a Frames is accepted a subtype of it is too, so its model has to
    # extend the parent's rather than start again without 'video'
    with pytest.raises(SampleTypeError, match="extend"):

        class Loose(Frames):
            segment = "loose"

            class Metadata(Image.Metadata):
                pass


# ----------------------------------------------------------------------
# The registry
# ----------------------------------------------------------------------


def test_the_built_ins_are_registered_like_any_plugin():
    assert {"image", "frames", "text"} <= set(available())


def test_resolving_gives_the_class():
    assert resolve("frames") is Frames


def test_an_unknown_type_says_what_is_installed():
    with pytest.raises(SampleTypeError, match="image"):
        resolve("satellite")


def test_a_type_says_nothing_about_its_bytes_unless_it_computes_something():
    assert Text().facts(b"some words") == {}

    class Counted(Text):
        segment: ClassVar[str] = "counted"

        def facts(self, data: bytes) -> dict:
            return {"word_count": len(data.split())}

    assert Counted().facts(b"some words") == {"word_count": 2}


# ----------------------------------------------------------------------
# What a sample is for: generated media and fine-tuning examples
# ----------------------------------------------------------------------


def test_generated_text_is_text_that_says_a_model_wrote_it():
    """A mixin, so a query for text still returns it (docs/adr/0053)."""
    assert GeneratedText.media == "text"
    assert GeneratedText.subtype() == "generated"
    assert issubclass(GeneratedText, Text) and issubclass(GeneratedText, GeneratedMedia)


def test_a_projects_generated_type_inherits_both():
    class Email(GeneratedText):
        segment: ClassVar[str] = "phishnet-email"

    assert (Email.media, Email.subtype()) == ("text", "generated/phishnet-email")
    assert issubclass(Email, GeneratedMedia)


def test_a_fine_tuning_example_is_the_text_it_should_write():
    assert (SFTTextExample.media, SFTTextExample.subtype()) == ("text", "sft")
    assert issubclass(SFTTextExample, SFTExample)
    assert not issubclass(SFTTextExample, GeneratedMedia)


def test_a_mixin_is_not_a_type_of_its_own():
    """A type with no media would mean nothing, so neither can be registered as one."""
    assert not issubclass(GeneratedMedia, SampleType)
    assert not issubclass(SFTExample, SampleType)


def test_an_examples_input_is_metadata_its_type_requires():
    class Template(SFTTextExample):
        segment: ClassVar[str] = "template"
        inputs: ClassVar[tuple[str, ...]] = ("subject", "urls")

        class Metadata(SFTTextExample.Metadata):
            subject: str
            urls: bool

    assert Template.subtype() == "sft/template"
    assert Template().check_metadata({"subject": "Hi", "urls": False, "corpus": "enron"}) == {
        "subject": "Hi",
        "urls": False,
        "corpus": "enron",
    }
    with pytest.raises(SampleTypeError, match="subject"):
        Template().check_metadata({"urls": False})
    assert Template.input_of({"subject": "Hi", "urls": False, "corpus": "enron"}) == {
        "subject": "Hi",
        "urls": False,
    }


def test_an_input_the_metadata_does_not_require_is_refused():
    """Otherwise an origin could arrive without it, and the example has nothing to train on."""
    with pytest.raises(SampleTypeError, match="subject"):

        class Unrequired(SFTTextExample):
            segment: ClassVar[str] = "unrequired"
            inputs: ClassVar[tuple[str, ...]] = ("subject",)


def test_a_type_can_fold_two_spellings_of_one_input():
    class Folded(SFTTextExample):
        segment: ClassVar[str] = "folded"
        inputs: ClassVar[tuple[str, ...]] = ("subject",)

        class Metadata(SFTTextExample.Metadata):
            subject: str

        @classmethod
        def input_of(cls, metadata: dict) -> dict:
            return {"subject": " ".join(metadata["subject"].split())}

    assert Folded.input_of({"subject": "Re:  lunch\n tomorrow"}) == Folded.input_of(
        {"subject": "Re: lunch tomorrow"}
    )


def test_the_generated_and_fine_tuning_types_are_registered():
    assert resolve("generated-text") is GeneratedText
    assert resolve("sft-text") is SFTTextExample
