"""The sample types every strata install has.

Deliberately few, and registered through the same entry point group as any
plugin. See ``docs/adr/0033``.
"""

from typing import Any, ClassVar

from pydantic import Field

from .sample_types import SampleType, SampleTypeError


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


# ----------------------------------------------------------------------
# What a sample is for, beside what it is made of
# ----------------------------------------------------------------------


class GeneratedMedia:
    """A model's output, whatever its media.

    A mixin, not a type: combined with a media's type, as
    ``GeneratedText(Text, GeneratedMedia)``, so every tool for that media
    still reads it. A sample of such a type arrives only through a
    generate run, which records what made it. See ``docs/adr/0053``.
    """


class SFTExample:
    """A supervised fine-tuning example: the bytes are its target, its metadata its input.

    A mixin, like :class:`GeneratedMedia`. A type names its input fields
    in ``inputs``, and its ``Metadata`` must require each one, so every
    origin carries the input. See ``docs/adr/0053``.
    """

    #: The metadata keys that are the example's input, in the order a
    #: prompt names them.
    inputs: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        metadata = getattr(cls, "Metadata", None)
        declared = set(getattr(metadata, "model_fields", {}))
        missing = [name for name in cls.inputs if name not in declared]
        if missing:
            raise SampleTypeError(
                f"{cls.__name__} names {', '.join(missing)} as input, which its "
                f"Metadata does not declare. An example without its input cannot "
                f"be trained on, so the type has to require it."
            )

    @classmethod
    def input_of(cls, metadata: dict) -> dict[str, Any]:
        """The input one origin recorded, in the form two origins are compared in.

        A freeze leaves out a sample whose origins disagree on it, so a
        type that counts two spellings as one input folds them here. As
        recorded, by default. See ``docs/adr/0053``.
        """
        return {name: metadata.get(name) for name in cls.inputs}


class GeneratedText(Text, GeneratedMedia):
    """Text a model wrote."""

    segment: ClassVar[str] = "generated"


class SFTTextExample(Text, SFTExample):
    """A fine-tuning example whose target is text: the bytes are the document it should write."""

    segment: ClassVar[str] = "sft"


__all__ = [
    "Frames",
    "GeneratedMedia",
    "GeneratedText",
    "Image",
    "SFTExample",
    "SFTTextExample",
    "Text",
]
