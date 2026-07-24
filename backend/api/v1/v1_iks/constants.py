"""Shared constants for the v1_iks views.

Centralised so the repeated literals (region list, the fixed week axis, image
extensions, Section-D indicator names) and the synthetic placeholder figures
live in one place instead of being scattered across the view methods.
"""

# Region names — match Administration.region; used across the aggregations.
REGIONS = ["Hhohho", "Manzini", "Lubombo", "Shiselweni"]

# Fixed 13-week axis used by the prototype aggregations (net-signal, heatmap).
# NOTE: this is a hardcoded May–Jul window — see the heatmap/soil-trend caveats
# about submissions outside that range.
HEATMAP_WEEKS = [
    "May 01", "May 08", "May 15", "May 22", "May 29",
    "Jun 05", "Jun 12", "Jun 19", "Jun 26",
    "Jul 03", "Jul 10", "Jul 17", "Jul 24",
]

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
