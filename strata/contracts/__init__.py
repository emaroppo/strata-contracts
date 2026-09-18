"""What crosses a boundary between strata packages, independent of who produces or stores it.

What enters a catalog: the sample types, the metadata each requires, and
the prepared index a corpus declares itself in. What an annotation is:
value types and schema descriptors. What leaves a catalog for a trainer:
the manifest. The one package every other may import, so each has one
description. A change here is a wire-format change.

**May import:** the standard library, pydantic, and ``strata.common`` for
resolving a sample type through its entry point group.

**May not import:** anything doing I/O, any storage layer, any ML
framework, or Label Studio, whose format converts inside ``strata.labeller``.

Every schema answers which classes an annotation asserts (``docs/adr/0039``).
Why the manifest lives here: ``docs/adr/0004``; the sample types and the
prepared index: ``docs/adr/0040``.
"""

from .builtin_types import Frames, Image, Text
from .manifest import (
    FILES_DIR,
    MANIFEST_FORMAT,
    MANIFEST_NAME,
    Manifest,
    ManifestFormatError,
    ManifestSample,
    feature_digest,
    order_digest,
    sides_from_string,
    sides_string,
)
from .prepared import (
    PREPARED_FORMAT,
    PREPARED_NAME,
    Checked,
    PreparedError,
    PreparedFormatError,
    PreparedIndex,
    PreparedSample,
    Violation,
    check,
)
from .sample_types import SampleType, SampleTypeError
from .schema import AnySchema, BBoxSchema, ClassificationSchema, SchemaError, SpanSchema
from .values import (
    AnyPrediction,
    AnyValue,
    Box,
    Boxes,
    BoxesPrediction,
    Choices,
    ChoicesPrediction,
    Prediction,
    Span,
    Spans,
    SpansPrediction,
    Value,
)

#: Modules a sibling may import by path beyond what is exported here: the
#: type registry, whose ``entries`` is the seam tests patch (docs/adr/0015).
PUBLIC_MODULES = frozenset({"sample_types"})

__all__ = [
    "FILES_DIR",
    "MANIFEST_FORMAT",
    "MANIFEST_NAME",
    "PREPARED_FORMAT",
    "PREPARED_NAME",
    "AnyPrediction",
    "AnySchema",
    "AnyValue",
    "BBoxSchema",
    "Box",
    "Boxes",
    "BoxesPrediction",
    "Checked",
    "Choices",
    "ChoicesPrediction",
    "ClassificationSchema",
    "Frames",
    "Image",
    "Manifest",
    "ManifestFormatError",
    "ManifestSample",
    "Prediction",
    "PreparedError",
    "PreparedFormatError",
    "PreparedIndex",
    "PreparedSample",
    "SampleType",
    "SampleTypeError",
    "SchemaError",
    "Span",
    "SpanSchema",
    "Spans",
    "SpansPrediction",
    "Text",
    "Value",
    "Violation",
    "check",
    "feature_digest",
    "order_digest",
    "sides_from_string",
    "sides_string",
]
