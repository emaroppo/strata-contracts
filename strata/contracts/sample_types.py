"""What a sample is, and what has to be known about one before a catalog takes it.

A type decides three things: which media it is, which files it admits, and
what metadata a sample of it must arrive with. Types are plugins under the
``strata.sample_types`` entry point group, and they inherit:
``Satellite(Image)`` adds a segment and a required key and keeps the rest.
In queries a subtype is a path matched by prefix, the rule collections use.

How a type's bytes are stored is not decided here: canonical form belongs
to the catalog that stores them. See ``docs/adr/0010`` and ``docs/adr/0040``.
"""

from importlib.metadata import entry_points
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError

from strata.common import plugins

#: Where a distribution advertises the sample types it provides.
ENTRY_POINT_GROUP = "strata.sample_types"

#: What the unspecialised case of a media is stored as. Every media has one,
#: and it is what a sample was before anyone thought about subtypes.
PLAIN = "plain"


class SampleTypeError(Exception):
    """A type that cannot be defined, found, or satisfied by the data at hand."""


class SampleType:
    """A kind of sample, and what a catalog requires of one.

    Subclass to specialise. A subclass declares a ``segment`` naming what it
    adds, and inherits everything it does not override.
    """

    #: Which media this is. May not change in a subclass. docs/adr/0010
    media: ClassVar[str] = ""

    #: What this adds below its parent. Empty for the unspecialised case of
    #: a media, which stores as ``plain``.
    segment: ClassVar[str] = ""

    #: Extensions this type admits, lowercase and without the dot. Checked
    #: rather than used to discover. docs/adr/0010
    extensions: ClassVar[frozenset[str]] = frozenset()

    class Metadata(BaseModel):
        """What a sample of this type must arrive with.

        Keys nobody declared are kept: a preparer records what it knows, and
        a key becomes required only when a type says so. A subtype's model
        extends its parent's, so it can add a requirement and never drop
        one. See ``docs/adr/0040``.
        """

        model_config = ConfigDict(extra="allow")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        parent = cls.__mro__[1]
        inherited = getattr(parent, "media", "")
        if inherited and cls.media != inherited:
            raise SampleTypeError(
                f"{cls.__name__} declares media {cls.media!r} but inherits from "
                f"{parent.__name__}, which is {inherited!r}. A subtype cannot "
                f"change its media: a query for {inherited!r} would silently "
                f"stop returning it."
            )
        if "/" in cls.segment:
            raise SampleTypeError(
                f"{cls.__name__} segment {cls.segment!r} contains a '/'. Depth "
                f"comes from inheriting, so the path and the class chain "
                f"cannot disagree."
            )
        declared = cls.__dict__.get("Metadata")
        required = getattr(parent, "Metadata", None)
        if declared is not None and required is not None and not issubclass(declared, required):
            raise SampleTypeError(
                f"{cls.__name__}.Metadata does not extend {parent.__name__}.Metadata. "
                f"Where a {parent.__name__} is accepted a {cls.__name__} is too, so "
                f"it has to arrive with at least what its parent requires."
            )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @classmethod
    def subtype(cls) -> str:
        """The stored path: every segment from the media's base down to here.

        Built from the class chain rather than declared. See
        ``docs/adr/0010``.
        """
        segments = [
            klass.segment
            for klass in reversed(cls.__mro__)
            if isinstance(klass, type)
            and issubclass(klass, SampleType)
            and klass.__dict__.get("segment")
        ]
        return "/".join(segments) or PLAIN

    # ------------------------------------------------------------------
    # What a catalog asks
    # ------------------------------------------------------------------

    def allows(self, path: Path | str) -> bool:
        """Whether this type admits a file, by extension."""
        suffix = Path(path).suffix.lower().lstrip(".")
        return bool(suffix) and suffix in self.extensions

    def check_metadata(self, metadata: dict) -> dict:
        """``metadata`` as this type requires it, or the reason it falls short.

        What comes back is what gets recorded: validated, as plain JSON, with
        every undeclared key kept. See ``docs/adr/0040``.
        """
        try:
            model = self.Metadata.model_validate(metadata)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in err['loc']) or 'metadata'}: {err['msg'].lower()}"
                for err in e.errors()
            )
            raise SampleTypeError(problems) from None
        return model.model_dump(mode="json")


# ----------------------------------------------------------------------
# The registry
# ----------------------------------------------------------------------


def entries():
    """What is installed, as entry points. The seam a test stubs to pretend otherwise."""
    return list(entry_points(group=ENTRY_POINT_GROUP))


def _builtin_names() -> set[str]:
    """Names this package itself provides, which a plugin may not take."""
    return {
        entry.name
        for entry in entries()
        if getattr(getattr(entry, "dist", None), "name", None) == "strata-contracts"
    }


def available() -> dict[str, str]:
    """Registered type names, and what each resolves to."""
    return plugins.available(entries())


def resolve(name: str) -> type[SampleType]:
    """The class a type name refers to. Built-in names are reserved."""
    entry = plugins.find(
        entries(), name, what="sample type", error=SampleTypeError, reserved=_builtin_names()
    )
    return plugins.load(entry, SampleType, error=SampleTypeError)


__all__ = [
    "ENTRY_POINT_GROUP",
    "PLAIN",
    "SampleType",
    "SampleTypeError",
    "available",
    "entries",
    "resolve",
]
