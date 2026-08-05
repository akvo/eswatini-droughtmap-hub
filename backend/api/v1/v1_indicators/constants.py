class IndicatorSource:
    placeholder = "placeholder"
    PLACEHOLDER_LABEL = "Placeholder (uncurated)"
    PROTOTYPE = "prototype-illustrative"
    HANDOVER_2026_07 = "DIH Risk Dataset Handover 2026-07"


# Hazard D-class rescale mapping [0, 1]
# Validated D-class -> Hazard value (H)
HAZARD_RESCALE = {
    "None": 0.0,
    "D0": 0.2,
    "D1": 0.4,
    "D2": 0.6,
    "D3": 0.8,
    "D4": 1.0,
}

# IPC food-security phase rescale mapping [0, 1]
# Phase (1..5) -> Vulnerability value (V)
IPC_RESCALE = {
    1: 0.10,
    2: 0.30,
    3: 0.60,
    4: 0.85,
    5: 1.00,
}

# Risk score classification bands (descending threshold)
# Threshold -> Risk class label
RISK_BANDS = [
    (0.50, "Very High"),
    (0.30, "High"),
    (0.15, "Moderate"),
    (0.0, "Low"),
]

# Exposure sub-indicators used for min-max normalisation
# and exposure mean score
EXPOSURE_SUBINDICATORS = [
    "land_use_dvi_agri",
    "population",
    "cattle",
    "water_demand",
]

# Raw sub-indicator -> the normalised key score_all() emits for it. Only
# land_use_dvi_agri is shortened; spelled out so consumers read the mapping
# instead of re-deriving the exception.
EXPOSURE_NORM_KEYS = {
    "land_use_dvi_agri": "land_use_norm",
    "population": "population_norm",
    "cattle": "cattle_norm",
    "water_demand": "water_demand_norm",
}
