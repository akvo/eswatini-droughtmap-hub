from enum import Enum


class UserRoleTypes:
    admin = 1
    reviewer = 2
    observer = 3

    FieldStr = {
        admin: "Admin",
        reviewer: "Reviewer",
        observer: "Observer",
    }


# Citizen-science magic link (WX-6 D-3): purpose-salted signed pk, framework
# signing only — no token table. 7-day validity per the product brief.
CS_LINK_SALT = "cs-magic-link"
CS_LINK_MAX_AGE = 7 * 24 * 3600


# Technical Working Group list
# https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT?node-id=3-2#1050735747
class TechnicalWorkingGroup:
    ndma = 1
    moag = 2
    met = 3
    dwa = 4
    uneswa = 5

    FieldStr = {
        ndma: "NDMA (National Disaster Management Agency)",
        moag: "MoAg (Ministry of Agriculture)",
        met: "MET (Meteorological Office)",
        dwa: "DWA (Department of Water Affairs)",
        uneswa: "UNESWA (University of Eswatini)",
    }


class ActionEnum(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.capitalize()) for tag in cls]
