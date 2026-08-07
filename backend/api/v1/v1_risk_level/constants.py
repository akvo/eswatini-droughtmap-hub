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

# Exposure rows on the build-up accordion. The first four are the scored
# sub-indicators (redesign D-8); the rest are eligibility counts shown for
# context only — they never move the score.
EXPOSURE_UNITS = {
    "land_use_dvi_agri": None,
    "population": "people",
    "cattle": "head",
    # RL-2 D-8: assumed unit, declared here so the frontend never converts.
    "water_demand": "m3",
    "under_five": "children",
    "rainfed_cropland": "ha",
}

# Shown under the exposure accordion for context. Eligibility filters
# (redesign D-8), never inputs to the score.
ELIGIBILITY_EXPOSURE_FIELDS = ["under_five", "rainfed_cropland"]

# Empty-state reasons, same idiom as v1_weather ("no_station_data_for_period").
NO_CONFIDENCE_REASON = "no_station_baseline"
NO_WATER_POINTS_REASON = "no_water_points_recorded"
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
