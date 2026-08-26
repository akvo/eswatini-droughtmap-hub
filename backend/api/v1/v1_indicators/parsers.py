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

from api.v1.v1_indicators.models import Indicator
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


# Excel writes the LOCALE list separator, not a comma. On a machine set to a
# European/Indonesian locale, re-saving our comma template produces
# semicolons — and, in the same breath, decimal commas.
DELIMITERS = (",", ";", "\t")


def sniff_delimiter(header_line: str) -> str:
    """The delimiter that actually separates this file's columns.

    Decided from the header alone: it is the one line guaranteed to contain
    only separators and field names, so a decimal comma in the data cannot
    outvote a semicolon separator.
    """
    counts = {d: header_line.count(d) for d in DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] else ","


def _to_number(text: str, decimal_comma: bool):
    """Parse a numeric cell under this file's locale convention.

    THE DANGEROUS CASE: with a semicolon delimiter, "12202861,56" is
    12,202,861.56. Stripping the comma as a thousands separator would read it
    as 1220286156 — a hundred times too large, and `water_demand` has no
    maximum to catch it. Wrong by 100x and silently accepted is far worse
    than rejected.
    """
    if decimal_comma:
        # `;`-separated: comma is the decimal point, dot groups thousands.
        return float(text.replace(".", "").replace(",", "."))
    # `,`-separated: an unquoted comma cannot appear inside a number, so any
    # comma that survived the reader groups thousands.
    return float(text.replace(",", ""))


def _coerce(raw, definition: DatasetDef, decimal_comma: bool = False):
    """Return (value, error, rounded).

    A blank cell is (None, None, False) — skip, not zero (D-7).
    """
    if raw is None:
        return None, None, False
    text = str(raw).strip()
    if text == "":
        return None, None, False
    try:
        number = _to_number(text, decimal_comma)
    except ValueError:
        return None, f"{raw!r} is not a number.", False
    rounded = False
    if definition.dtype is int and number != int(number):
        # WorldPop and similar models emit fractional counts — the handover
        # CSV carries 13992.45154882247 for population, and
        # generate_indicators_seeder has always done int(float(raw)).
        # Rejecting would make the platform's own reference data unloadable.
        # Rounded rather than truncated, and counted in a warning so the
        # operator sees it happened.
        number = round(number)
        rounded = True
    if definition.minimum is not None and number < definition.minimum:
        return None, (
            f"{raw!r} is below the minimum {definition.minimum:g} "
            f"for {definition.label} ({definition.unit})."
        ), False
    if definition.maximum is not None and number > definition.maximum:
        return None, (
            f"{raw!r} is above the maximum {definition.maximum:g} "
            f"for {definition.label} ({definition.unit})."
        ), False
    value = int(number) if definition.dtype is int else number
    return value, None, rounded


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
    delimiter = sniff_delimiter(text.splitlines()[0] if text else "")
    # `;` and decimal comma travel together: both come from the same Excel
    # locale setting, so one sniff decides both.
    decimal_comma = delimiter == ";"
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
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
            delimiter,
            decimal_comma,
        )
    return reports


def _current_values(field: str) -> Dict[int, object]:
    """{administration_id: current value} for one Indicator column.

    Read here rather than returned to the caller so `before` in the diff is
    the real stored value — the diff is both what the operator confirms and
    the snapshot a revert replays (D-10).
    """
    return dict(
        Indicator.objects.values_list("administration_id", field)
    )


def _build_report(
    rows, header, definition, keys, by_id, by_name, ignored, current,
    delimiter=",", decimal_comma=False,
) -> dict:
    diff = []
    errors: List[dict] = []
    error_total = 0
    blank = 0
    rounded_count = 0
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

        value, problem, was_rounded = _coerce(
            row.get(header), definition, decimal_comma
        )
        if was_rounded:
            rounded_count += 1
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

    if rounded_count:
        warnings.append({
            "code": "rounded_to_whole",
            "count": rounded_count,
            "detail": (
                f"{rounded_count} {definition.label} value(s) had decimals "
                f"and were rounded to whole {definition.unit}."
            ),
        })

    if decimal_comma:
        warnings.append({
            "code": "locale_format",
            "detail": (
                "Read as a semicolon-separated file with decimal commas "
                "(e.g. 1234,56 = 1234.56). Check a value or two in the "
                "before/after list below."
            ),
        })

    return {
        "dataset": definition.slug,
        "field": definition.field,
        "unit": definition.unit,
        "delimiter": delimiter,
        "rows_read": len(rows),
        "matched": len(seen),
        "blank": blank,
        "error_total": error_total,
        "errors": errors,
        "warnings": warnings,
        "diff": diff,
    }
