"""Shared constants for the v1_iks views.

Centralised so the repeated literals (region list, image extensions,
Section-D indicator names) and the synthetic placeholder figures live in one
place instead of being scattered across the view methods.

The trend/heatmap week axis is NOT here any more: it is computed per request
by `utils.rolling_weeks`, because a fixed "May 01".."Jul 24" list described a
quarter that had nothing to do with when the data was collected.
"""

# Region names — match Administration.region; used across the aggregations.
REGIONS = ["Hhohho", "Manzini", "Lubombo", "Shiselweni"]

# Image attachment extensions served through the photo proxy.
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# Section D single-select indicators (stored under these fixed names by the
# Kobo extractor). Handled separately from the numeric B/C indicators.
SOIL_MOISTURE_INDICATOR = "soil_moisture"
VEGETATION_GREENNESS_INDICATOR = "vegetation_greenness"
SECTION_D_INDICATOR_NAMES = [
    SOIL_MOISTURE_INDICATOR,
    VEGETATION_GREENNESS_INDICATOR,
]

# Kobo survey field carrying the chiefdom/community name (question A3).
CHIEFDOM_FIELD = "A3_Name_of_chiefdom_odzi_lokubikwa_ngaso"

# --- Synthetic placeholders (NOT real measurements) -------------------------
# Prototype stand-ins flagged inline in the views; named here so every fake
# figure is visible in one place until a real source lands.
MOCK_VALIDATION_TIME_PER_REPORT_DAYS = 1.5   # stats: avg validation time
MOCK_FORM_COMPLETION_PCT = 95.0              # stats: form completion
IKS_SCORE_PER_REPORT = 12.5                  # agreement: invented iks scaling
MOCK_SAT_SCORE = 66.7                        # agreement: fixed fake sat score
