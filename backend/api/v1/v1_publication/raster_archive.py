"""Discovery for a local pct-rank GeoTIFF archive.

The CDI pipeline writes its output as one directory per index holding one
raster per month:

    GeoTiffs/EVI2/STEP_0303_EVI2_pct_rank_Eswatini_202604.tif

Split out of generate_rasters_seeder so the filename parsing — the part that
silently mislabels data when it is wrong — can be tested without a database.
"""
import os
import re

from api.v1.v1_publication.constants import RasterIndicatorTypes

INDICATORS = list(RasterIndicatorTypes.FieldStr)

# The trailing YYYYMM is the only part of the filename that identifies the
# month. Anchored to the end so the "0303" pipeline-step prefix, which also
# looks like a date, can never be mistaken for one.
MONTH_IN_FILENAME = re.compile(r"(\d{4})(0[1-9]|1[0-2])(?=\D*$)")

RASTER_SUFFIXES = (".tif", ".tiff")


def indicator_from_path(dirpath: str, filename: str):
    """Infer the indicator from the directory name or the filename.

    Longest-first, with token boundaries: "sm" also occurs inside longer
    words, so a bare substring test would label an ESI or SPI file as SM.
    """
    haystack = f"{os.path.basename(dirpath)}/{filename}".casefold()
    for candidate in sorted(INDICATORS, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){candidate}(?![a-z0-9])", haystack):
            return candidate
    return None


def scan_raster_archive(root: str, indicator: str = None) -> dict:
    """{(indicator, 'YYYY-MM'): filepath} for a GeoTIFF archive.

    Accepts either a single-indicator directory (pass `indicator`) or a parent
    holding per-indicator subdirectories (CDI/ESI/EVI2/SM/SPI).

    An EXPLICIT `indicator` is taken as the caller's assertion and is not
    checked against INDICATORS — that list holds the four *components*, so
    requiring membership would silently return nothing for the CDI composite,
    which lives in the same archive and is what the publication seeder reads.
    Only INFERRED indicators are validated, since inference is a guess.

    Walk and filenames are both sorted, and the first match for a key wins, so
    an archive with duplicate months resolves identically on every run rather
    than depending on filesystem order.
    """
    found = {}
    for dirpath, _, filenames in sorted(os.walk(root)):
        for filename in sorted(filenames):
            if not filename.lower().endswith(RASTER_SUFFIXES):
                continue
            match = MONTH_IN_FILENAME.search(os.path.splitext(filename)[0])
            if not match:
                continue
            if indicator:
                resolved = indicator
                # A single-indicator scan of a multi-indicator tree must not
                # sweep in its siblings' rasters.
                inferred = indicator_from_path(dirpath, filename)
                if inferred and inferred != indicator:
                    continue
            else:
                resolved = indicator_from_path(dirpath, filename)
                if resolved not in INDICATORS:
                    continue
            period = f"{match.group(1)}-{match.group(2)}"
            found.setdefault(
                (resolved, period), os.path.join(dirpath, filename)
            )
    return found
