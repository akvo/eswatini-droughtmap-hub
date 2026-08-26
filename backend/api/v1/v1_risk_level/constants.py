from api.v1.v1_publication.constants import DroughtCategory

# Validated DroughtCategory -> the D-class label published to the frontend.
# `normal` (wet conditions) is a decision and must stay distinct from a
# missing one; anything absent from this map — including `none` (-9999, raster
# no-signal) — is published as null, which the UI renders as "No Data".
DCLASS_BY_CATEGORY = {
    DroughtCategory.normal: "Normal",
    DroughtCategory.d0: "D0",
    DroughtCategory.d1: "D1",
    DroughtCategory.d2: "D2",
    DroughtCategory.d3: "D3",
    DroughtCategory.d4: "D4",
}

BAND_MAP = {
    "Very High": "urgent",
    "High": "watch",
    "Moderate": "watch",
    "Low": "monitor",
}

VALID_BANDS = {"urgent", "watch", "monitor"}

# Exposure rows on the build-up accordion — the four scored sub-indicators,
# and only those (redesign D-8).
#
# `under_five` and `rainfed_cropland` used to ride along as `scored: false`
# context rows. They are eligibility filters, not exposure: keeping them under
# the exposure heading invited the reader to treat six numbers as the build-up
# of a score that four of them produce, and the CONTEXT chip was doing all the
# work of saying otherwise. Removed 2026-08-21 — see
# track-3/risk-level-detail-buildup-api.md D-9.
EXPOSURE_UNITS = {
    "land_use_dvi_agri": None,
    "population": "people",
    "cattle": "head",
    # RL-2 D-8: assumed unit, declared here so the frontend never converts.
    "water_demand": "m3",
}

# Empty-state reasons, same idiom as v1_weather ("no_station_data_for_period").
# NO_WATER_POINTS_REASON went with the water-access row (D-10) — it had no
# other caller.
NO_CONFIDENCE_REASON = "no_station_baseline"
WATER_DEMAND_UNIT_STATUS = "assumed_pending_dwa"

# Drought trend (RL-2 D-6). Six cycles is more than the copy ever needs
# ("N months worsening") and keeps the publication JSON scan bounded.
TREND_HISTORY_LIMIT = 6

WORSENING = "worsening"
RECOVERING = "recovering"
STABLE = "stable"

# Direction -> the word used in trend_desc. "stable" reads as "unchanged"
# when counted in months.
TREND_DESC = {
    WORSENING: "worsening",
    RECOVERING: "recovering",
    STABLE: "unchanged",
}
