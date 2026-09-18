# strata-contracts

What crosses a boundary between strata packages, independent of who
produces it or where it is stored: what an annotation is, what enters a
catalog, and what a trainer is handed. The one package every other strata
package imports, so each has one description rather than three that drift.

Not on PyPI: it installs from its repository at a release tag. uv takes a
git source only for a package named directly, so the strata packages
beneath it are named beside it.

```bash
g=git+https://github.com/emaroppo
uv add "strata-contracts @ $g/strata-contracts@v0.1.0" \
       "strata-common @ $g/strata-common@v0.1.0"
```

Depends on pydantic and `strata-common`, whose entry-point resolver finds
the sample types. May not import anything that does I/O, any storage
layer, any ML framework, or Label Studio.

## What it holds

**Values** are the payload of an annotation, one per task type,
discriminated on `kind` so a value round-trips out of JSON as the right
type without the reader knowing which task it came from:

| kind | value | prediction |
|---|---|---|
| `choices` | `Choices` — classes asserted about a whole sample | `ChoicesPrediction` |
| `spans` | `Spans` — labelled character ranges in a document | `SpansPrediction` |
| `boxes` | `Boxes` — labelled rectangles over an image | `BoxesPrediction` |

`AnyValue` and `AnyPrediction` are the unions. A prediction is the same
value plus a confidence per thing asserted, positional against `values`.
An empty value is an answer: a reviewer looked and found none of the
classes present. Values are frozen and forbid unknown fields, because a
typo that produced an empty value would land in a catalog as that answer.

**Schemas** describe a label set: the task, its classes, and the rules
over them. `ClassificationSchema`, `SpanSchema` and `BBoxSchema`, with
`AnySchema` as the union. Each validates a value against its class list
and answers the indexing contract, *which classes does this value assert*,
which is what lets a catalog index annotations it does not otherwise
understand. A span schema also declares its shape, `multi_label` and
`overlapping`, so a model can refuse before a round.

**The manifest** is what a trainer is handed: `Manifest` and
`ManifestSample`, written by the catalog beside a materialised dataset and
read by modelling, complete enough that nothing needs a database to train
from it. It states `MANIFEST_FORMAT`, and a reader refuses a format it
does not know. `feature_digest` is the digest of a sample's features that
keys the prediction cache.

**Sample types** say what a sample is and what it must arrive with.
`Image`, `Frames` and `Text` are built in, registered under the
`strata.sample_types` entry point group like any plugin, and a type
inherits: a subtype adds a `segment`, may narrow the extensions, and
extends its parent's `Metadata` model, never loosening it. `Frames`
requires `video`. `check_metadata` validates a sample's metadata against
its type and keeps every key the type does not declare. How a type's bytes
are stored is not decided here: canonical form is the catalog's.

**The prepared index** is what a corpus declares itself in on its way into a
catalog: `PreparedIndex`, at `prepared.json`, naming the type and every file
with its metadata and any candidate annotation. `check` compares one with
the files present and the type it names and returns every shortfall, so a
preparer's tests and a catalog refuse the same things. It states
`PREPARED_FORMAT`, and a reader refuses one it does not know. A model, not
a reader: loading and saving it is its callers'.

**Examples.** `strata.contracts.examples` holds a sample of every type. Each
consuming package tests its own layer against all of them, so a type added
here fails in each package until that package handles it.

## Decisions

Recorded in the strata umbrella repository's `docs/adr/` (https://github.com/emaroppo/strata/tree/main/docs/adr): the manifest as the
contract between catalog and modelling (0004), the prediction cache's third
input (0006), sample types as plugins (0010), features as plain JSON (0011),
a label set declaring its shape (0014), and what enters a catalog being
declared outside it (0040).

## Tests

```bash
.github/sibling-wheels.sh common   # the strata packages this one needs, from their repositories
uv sync --find-links dist --group dev
uv run pytest
```

Inside the strata workspace: `uv run pytest packages/contracts` from its root.
