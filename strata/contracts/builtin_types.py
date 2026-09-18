"""The sample types every strata install has.

Deliberately few, and registered through the same entry point group as any
plugin. See ``docs/adr/0033``.
"""

from typing import ClassVar

from pydantic import Field

from .sample_types import SampleType


class Image(SampleType):
    """A picture, standing on its own."""

    media: ClassVar[str] = "image"
    extensions: ClassVar[frozenset[str]] = frozenset(
        {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "gif"}
    )


class Frames(Image):
    """Video frames, each recording which video it came from under ``video``.

    A project freezing its versions with ``group_by = "video"`` keeps a
    video's frames on one side of the split; one that does not treats each
    frame as its own sample. Which video is a fact the preparer knows, and a
    frame that arrives without it is refused rather than made a group of one.
    See ``docs/adr/0023`` and ``docs/adr/0040``.
    """

    segment: ClassVar[str] = "frames"

    #: The metadata key a frame's video is recorded under.
    VIDEO: ClassVar[str] = "video"

    class Metadata(Image.Metadata):
        video: str = Field(min_length=1)


class Text(SampleType):
    """A document, read as characters rather than pixels.

    A span is a pair of character offsets, so the characters have to be
    the ones the catalog stores. Its canonical form is the catalog's; a
    preparer that ships spans writes text in that form. See
    ``docs/adr/0010`` and ``docs/adr/0040``.
    """

    media: ClassVar[str] = "text"
    extensions: ClassVar[frozenset[str]] = frozenset({"txt", "md"})


__all__ = ["Frames", "Image", "Text"]
