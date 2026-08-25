"""Parse and validate an operator-submitted CSV (PA-6 D-15).

Reads which datasets a file carries from its header, and produces one report
per recognised value column. Writes nothing — applying is a separate step
with a human in it (D-3).
"""

import csv
import hashlib
import io
import logging
import unicodedata
from typing import Dict, List, Tuple

from api.v1.v1_indicators.datasets import (
    DatasetDef,
    GENERIC_VALUE_COLUMN,
    KEY_COLUMNS,
    lookup,
    normalise_header,
)

logger = logging.getLogger(__name__)

__all__ = ["ParseError", "checksum_of", "parse", "MAX_ROWS", "MAX_ERRORS"]

# 59 Tinkhundla plus slack. Checked before parsing so a large file is
# rejected on its shape rather than read into memory.
MAX_ROWS = 200

# A mis-shaped column produces one error per row otherwise.
MAX_ERRORS = 50

ALLOWED_EXTENSIONS = {".csv", ".txt"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # generous for 59 rows


class ParseError(Exception):
    """The file cannot be read at all — no per-dataset report is possible."""


def checksum_of(handle) -> str:
    """sha256 of the uploaded bytes. Groups the siblings of one file."""
    digest = hashlib.sha256()
    handle.seek(0)
    for chunk in iter(lambda: handle.read(8192), b""):
        digest.update(chunk if isinstance(chunk, bytes) else chunk.encode())
    handle.seek(0)
    return digest.hexdigest()


def _norm_name(name: str) -> str:
    """Inkhundla-name normalisation, matching generate_indicators_seeder."""
    return unicodedata.normalize("NFKD", name or "").strip().casefold()


def _decode(handle) -> str:
    handle.seek(0)
    raw = handle.read()
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ParseError("File is not readable as text.")


def _coerce(raw, definition: DatasetDef):
    """Return (value, error). A blank cell is (None, None) — skip, not zero."""
    if raw is None:
        return None, None
    text = str(raw).strip().replace(",", "")
    if text == "":
        return None, None
    try:
        number = float(text)
    except ValueError:
        return None, f"{raw!r} is not a number."
    if definition.dtype is int and number != int(number):
        return None, f"{raw!r} must be a whole number ({definition.unit})."
    if definition.minimum is not None and number < definition.minimum:
        return None, (
            f"{raw!r} is below the minimum {definition.minimum:g} "
            f"for {definition.label} ({definition.unit})."
        )
    if definition.maximum is not None and number > definition.maximum:
        return None, (
            f"{raw!r} is above the maximum {definition.maximum:g} "
            f"for {definition.label} ({definition.unit})."
        )
    return (int(number) if definition.dtype is int else number), None


def _resolve_header(fieldnames) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Split the header into keys, value columns and unrecognised columns.

    Returns (keys, value_headers, ignored). `keys` maps a canonical key name
    to the raw header that supplied it, because the raw name is what
    csv.DictReader keys its rows by.
    """
    keys: Dict[str, str] = {}
    value_headers: List[str] = []
    ignored: List[str] = []
    generic: List[str] = []

    for raw in fieldnames or []:
        canonical = normalise_header(raw)
        if canonical in KEY_COLUMNS:
            keys[canonical] = raw
        elif lookup(raw) is not None:
            value_headers.append(raw)
        elif canonical == GENERIC_VALUE_COLUMN:
            generic.append(raw)
        elif canonical:
            ignored.append(raw)

    # `value` is accepted only when it is unambiguous: with a named column
    # present there is no way to say which dataset it means.
    if generic and not value_headers:
        value_headers.extend(generic)
    elif generic:
        ignored.extend(generic)

    return keys, value_headers, ignored


def _match_administration(
    row, keys, administrations_by_id, administrations_by_name
):
    """(administration, error). Prefers the id; disagreement is an error."""
    raw_id = (row.get(keys.get("administration_id"), "") or "").strip()
    raw_name = (row.get(keys.get("inkhundla_name"), "") or "").strip()

    by_id = None
    if raw_id:
        try:
            by_id = administrations_by_id.get(int(float(raw_id)))
        except ValueError:
            return None, f"administration_id {raw_id!r} is not a number."
        if by_id is None:
            return None, f"administration_id {raw_id!r} is not an Inkhundla."

    by_name = administrations_by_name.get(_norm_name(raw_name)) if raw_name \
        else None

    if by_id and by_name and by_id.id != by_name.id:
        # The realistic accident: the sheet was sorted and the ids no longer
        # line up with the names they were typed against.
        return None, (
            f"administration_id {raw_id} is {by_id.name}, but the name "
            f"column says {raw_name!r}. The rows may have been sorted."
        )
    resolved = by_id or by_name
    if resolved is None:
        if raw_name:
            return None, f"{raw_name!r} does not match any Inkhundla."
        return None, "Row has neither an administration_id nor a name."
    return resolved, None


def parse(handle, administrations) -> Dict[str, dict]:
    """Validate one file against every dataset its header declares.

    Returns {field_name: report}. An empty result means no recognised value
    column was found, which the caller surfaces as a rejection listing the
    valid names — also how an operator discovers what the platform accepts.
    """
    text = _decode(handle)
    reader = csv.DictReader(io.StringIO(text))
    keys, value_headers, ignored = _resolve_header(reader.fieldnames)

    if not keys.get("administration_id") and not keys.get("inkhundla_name"):
        raise ParseError(
            "No key column found. The file needs 'administration_id' or "
            "'inkhundla_name'. Found: "
            + ", ".join(reader.fieldnames or ["(nothing)"])
        )

    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ParseError(
            f"{len(rows)} rows is more than the {MAX_ROWS} allowed — there "
            "are only 59 Tinkhundla."
        )
    if not value_headers:
        return {}

    by_id = {a.id: a for a in administrations}
    by_name = {_norm_name(a.name): a for a in administrations}

    reports: Dict[str, dict] = {}
    for header in value_headers:
        definition = lookup(header)
        reports[definition.field] = _build_report(
            rows,
            header,
            definition,
            keys,
            by_id,
            by_name,
            ignored,
            _current_values(definition.field),
        )
    return reports


def _current_values(field: str) -> Dict[int, object]:
    """{administration_id: current value} for one Indicator column.

    Read here rather than returned to the caller so `before` in the diff is
    the real stored value — the diff is both what the operator confirms and
    the snapshot a revert replays (D-10).
    """
    from api.v1.v1_indicators.models import Indicator

    return dict(
        Indicator.objects.values_list("administration_id", field)
    )


def _build_report(
    rows, header, definition, keys, by_id, by_name, ignored, current
) -> dict:
    diff = []
    errors: List[dict] = []
    error_total = 0
    blank = 0
    seen = set()

    for offset, row in enumerate(rows):
        line = offset + 2  # 1-indexed, and the header occupies line 1

        administration, problem = _match_administration(
            row, keys, by_id, by_name
        )
        if problem:
            error_total += 1
            if len(errors) < MAX_ERRORS:
                errors.append({
                    "row": line,
                    "column": definition.field,
                    "code": "unknown_administration",
                    "detail": problem,
                })
            continue

        if administration.id in seen:
            error_total += 1
            if len(errors) < MAX_ERRORS:
                errors.append({
                    "row": line,
                    "column": definition.field,
                    "code": "duplicate_administration",
                    "detail": f"{administration.name} appears more than once.",
                })
            continue
        seen.add(administration.id)

        value, problem = _coerce(row.get(header), definition)
        if problem:
            error_total += 1
            if len(errors) < MAX_ERRORS:
                errors.append({
                    "row": line,
                    "column": definition.field,
                    "code": "out_of_range",
                    "detail": problem,
                })
            continue

        if value is None:
            # D-7: blank leaves the existing value alone. Never 0.
            blank += 1
            continue

        diff.append({
            "administration_id": administration.id,
            "name": administration.name,
            "before": current.get(administration.id),
            "after": value,
        })

    warnings = []
    if blank:
        warnings.append({
            "code": "blank_value",
            "count": blank,
            "detail": (
                f"{blank} Tinkhundla have no value and will keep their "
                "current one."
            ),
        })
    if ignored:
        # D-16: loud, because a typo fails exactly like a genuinely new field.
        warnings.append({
            "code": "ignored_columns",
            "columns": ignored,
            "detail": (
                f"{len(ignored)} column(s) were NOT imported: "
                f"{', '.join(ignored)}. Check for a typo, or ask for the "
                "field to be added."
            ),
        })

    return {
        "dataset": definition.slug,
        "field": definition.field,
        "unit": definition.unit,
        "rows_read": len(rows),
        "matched": len(seen),
        "blank": blank,
        "error_total": error_total,
        "errors": errors,
        "warnings": warnings,
        "diff": diff,
    }
