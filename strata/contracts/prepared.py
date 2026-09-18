"""The prepared index: what a corpus declares about itself on its way into a catalog.

One file at the corpus root, ``prepared.json``, naming the sample type and
every file the catalog should take, each with the metadata a preparer
knew and any candidate annotation the corpus arrived with. It is the only
way in: a catalog ingests what the index names, checked against the type
it declares, and nothing else under the root. A preparer writes it and a
catalog reads it, through this definition, and neither needs the other.
See ``docs/adr/0040``.

Like the manifest, it is a model and not a reader: which filesystem the
corpus sits on is the caller's business.
"""

import json
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .sample_types import SampleType, SampleTypeError
from .values import AnyValue

#: The index's filename, at the root of the prepared corpus.
PREPARED_NAME = "prepared.json"
#: The layout this release writes, and the only one it reads.
PREPARED_FORMAT = 2


class PreparedError(Exception):
    """An index that cannot be combined, or a corpus that does not meet its type."""


class PreparedFormatError(PreparedError):
    """An index in a layout this release does not read.

    Not a ``ValueError``, so a caller can tell *stale* from *broken*, the
    distinction ``ManifestFormatError`` draws. See ``docs/adr/0038``.
    """


class PreparedSample(BaseModel):
    """What a preparer knew about one file it wrote."""

    #: Checked against the declared type's ``Metadata`` and recorded on the
    #: sample. A grouping — the video a frame came from, the thread a
    #: message is in — is a key in here, respected by a version frozen with
    #: ``group_by``. docs/adr/0023
    metadata: dict[str, Any] = Field(default_factory=dict)
    #: The annotation the corpus arrived with, where it arrived with one.
    #: **A candidate, never ground truth**, landed under a source of its
    #: own. docs/adr/0028
    value: AnyValue | None = None


class PreparedIndex(BaseModel):
    """Everything a preparer declared about the corpus it wrote."""

    #: Required rather than defaulted, as the manifest's is (docs/adr/0038).
    version: int
    #: The registered sample type every file here is, by name.
    type: str
    #: Which preparer wrote this, for tracing a corpus back to the code
    #: that made it. Not authoritative for anything.
    produced_by: str = ""
    #: Keyed by path relative to the corpus root, posix-style, and never
    #: outside it. docs/adr/0033
    samples: dict[str, PreparedSample] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _readable_by_this_release(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        version = data.get("version")
        if version != PREPARED_FORMAT:
            said = (
                "does not say which layout it is" if version is None else f"is version {version!r}"
            )
            raise PreparedFormatError(
                f"This prepared index {said}, and this release reads version "
                f"{PREPARED_FORMAT}, which names its sample type and nothing but the "
                f"files to take. Prepare the corpus again with this release."
            )
        return data

    # -- as text --------------------------------------------------------

    @classmethod
    def from_json(cls, text: str) -> "PreparedIndex":
        return cls.model_validate_json(text)

    def to_json(self) -> str:
        """Sorted and indented: people read this debugging a corpus, and a
        stable order keeps a re-run's diff to what actually changed."""
        return (
            json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
        )

    # -- combining ------------------------------------------------------

    def merge(self, other: "PreparedIndex") -> "PreparedIndex":
        """This index updated with ``other``'s entries.

        Later wins per file, and files this one knows about are kept, so
        preparing a grown source adds rather than forgets. Two types in one
        corpus are refused: the index declares one. See ``docs/adr/0033``.
        """
        if other.type != self.type:
            raise PreparedError(
                f"The corpus is prepared as {self.type!r} and this run prepares "
                f"{other.type!r}. One corpus is one type; prepare into another "
                f"directory."
            )
        return PreparedIndex(
            version=PREPARED_FORMAT,
            type=self.type,
            produced_by=other.produced_by or self.produced_by,
            samples={**self.samples, **other.samples},
        )


# ----------------------------------------------------------------------
# Checking a corpus against its type
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """One way a corpus falls short of what it declares."""

    #: The file it concerns, as the index names it; None for the whole index.
    key: str | None
    problem: str

    def __str__(self) -> str:
        return f"{self.key}: {self.problem}" if self.key is not None else self.problem


@dataclass
class Checked:
    """What a check found: each file's metadata as its type requires it, and what fell short."""

    #: Keyed as the index keys them. Only entries that passed.
    entries: dict[str, dict] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def check(
    index: PreparedIndex,
    sample_type: SampleType,
    type_name: str,
    present: Collection[str],
) -> Checked:
    """Whether ``index`` is a corpus of ``type_name`` that a catalog can take whole.

    ``present`` is every file under the root, keyed as the index keys them;
    the caller lists them, since reading a directory is not this package's
    to do. Every shortfall is collected rather than the first raised, so a
    corpus is fixed in one pass. See ``docs/adr/0036`` and ``docs/adr/0040``.
    """
    checked = Checked()
    if index.type != type_name:
        checked.violations.append(
            Violation(
                None,
                f"prepared as {index.type!r}, and {type_name!r} was expected. Prepare it "
                f"with a preparer producing {type_name!r}, or name that type.",
            )
        )
        return checked

    present = set(present)
    for key, entry in sorted(index.samples.items()):
        problem = _key_problem(key)
        if problem is None and key not in present:
            problem = "named by the index but not there"
        if problem is None and not sample_type.allows(key):
            suffix = PurePosixPath(key).suffix or "no extension"
            problem = (
                f"{type_name!r} does not admit {suffix} "
                f"(it admits: {', '.join('.' + e for e in sorted(sample_type.extensions))})"
            )
        if problem is None:
            try:
                checked.entries[key] = sample_type.check_metadata(entry.metadata)
            except SampleTypeError as e:
                problem = f"metadata falls short of {type_name!r}: {e}"
        if problem is not None:
            checked.violations.append(Violation(key, problem))
    return checked


def _key_problem(key: str) -> str | None:
    """Why ``key`` cannot name a file inside the corpus, if it cannot."""
    path = PurePosixPath(key)
    if not key or "\\" in key:
        return "not a posix path relative to the corpus root"
    if path.is_absolute() or ".." in path.parts:
        return "outside the corpus root; a prepared file is written inside it"
    if path.as_posix() != key:
        return f"not in normal form (as {path.as_posix()!r})"
    if key == PREPARED_NAME:
        return "the index itself"
    return None


__all__ = [
    "PREPARED_FORMAT",
    "PREPARED_NAME",
    "Checked",
    "PreparedError",
    "PreparedFormatError",
    "PreparedIndex",
    "PreparedSample",
    "Violation",
    "check",
]
