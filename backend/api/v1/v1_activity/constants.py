from api.v1.v1_publication.constants import DroughtCategory


class ActivityStatus:
    draft = 1
    active = 2
    archived = 3

    FieldStr = {draft: "Draft", active: "Active", archived: "Archived"}


# draft can activate (guarded) or be discarded; active can only be archived.
ACTIVITY_TRANSITIONS = {
    ActivityStatus.draft: [ActivityStatus.active, ActivityStatus.archived],
    ActivityStatus.active: [ActivityStatus.archived],
    ActivityStatus.archived: [],
}


class ActivitySector:
    food = 1
    health = 2
    wash = 3
    edu = 4
    env = 5
    coord = 6
    social = 7
    trans = 8

    FieldStr = {
        food: "Food & Agriculture",
        health: "Health & Nutrition",
        wash: "Water & Sanitation",
        edu: "Education",
        env: "Environment & Energy",
        coord: "Coordination",
        social: "Social Protection",
        trans: "Transport & Logistics",
    }
    # Used to build the Protocol ID `code`.
    Code = {
        food: "FOOD",
        health: "HEALTH",
        wash: "WASH",
        edu: "EDU",
        env: "ENV",
        coord: "COORD",
        social: "SOCIAL",
        trans: "TRANS",
    }


class ActivityResponseType:
    public = 1
    institutional = 2

    FieldStr = {public: "Public", institutional: "Institutional"}


class TriggerOperator:
    gte = 1
    lte = 2

    FieldStr = {gte: ">=", lte: "<="}


# Exposure indicators the wizard authors.
# Constrains triggers["exp"][*]["indicator"].
# population = people exposed; cropland = ha rain-fed cropland;
# water = litres water demand; cattle = amount of cattle.
EXPOSURE_INDICATORS = [
    "population",
    "cropland",
    "water",
    "cattle",
    "land_use_dvi_agri",
    "water_demand",
]

# class int -> wizard segment label, for trigger_summary.
DCLASS_SEGMENT = {
    DroughtCategory.d0: "D0",
    DroughtCategory.d1: "D1",
    DroughtCategory.d2: "D2",
    DroughtCategory.d3: "D3",
    DroughtCategory.d4: "D4",
}

# Valid drought-class gate values: D0..D4 only (never normal/none).
VALID_DCLASS = set(DCLASS_SEGMENT)

# Vulnerability = IPC food-security phase threshold (Phase 1..5).
VULN_PHASE_MIN, VULN_PHASE_MAX = 1, 5


# --- Trigger evaluation (SOP-2) -----------------------------------------
# Dimensions with no honest per-administration source yet. Conditions on
# these are treated as satisfied (never block firing) and reported in
# `matched_on` with source "unavailable".
UNAVAILABLE = {"months"}


ALLOWED_EXTENSIONS = {
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".csv",
}

ALLOWED_MIMES = {
    # Images
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    # Documents
    "application/pdf",
    "text/plain",
    "text/csv",
    # Microsoft Office (Legacy and Modern)
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # noqa
}
