"""Non-view helpers for the v1_iks app.

Query scoping (the ``active_*`` readers), the published-CDI lookup, the
Section-D label mappers and the X-API-Key permission live here so the views
module holds request handling only.
"""
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue


# Every IKS endpoint reads through these three helpers so that the KoboForm
# `active` flag set in the admin panel is the single switch deciding which
# form's data is public. Data from a deactivated form stays in the DB (for
# re-activation and audit) but must never reach an API response.
def active_indicators():
    return IKSIndicator.objects.filter(kobo_form__active=True)


def active_values():
    return IKSValue.objects.filter(iks_indicator__kobo_form__active=True)


def active_kobo_data():
    return KoboData.objects.filter(form__active=True)


def latest_validated_d_class(administration_id):
    """Return the validated CDI category for an administration.

    Reads the most recent *published* publication and looks up this
    administration's entry in its validated_values. Returns None when no
    published publication covers this administration yet (e.g. only
    in-review/in-validation publications exist, or IKS data exists but no
    CDI publication does). The caller renders None as a "No data" badge.
    """
    pub = (
        Publication.objects.filter(
            status=PublicationStatus.published,
            deleted_at__isnull=True,
            validated_values__isnull=False,
        )
        .order_by("-year_month")
        .first()
    )
    if not pub or not pub.validated_values:
        return None
    return next(
        (
            item.get("category")
            for item in pub.validated_values
            if str(item.get("administration_id")) == str(administration_id)
        ),
        None,
    )


# Section D single-select answers are stored as raw Kobo choice slugs
# (e.g. "1__dry__womile"); the numbering is NOT in severity order, so match
# on the siSwati term (or the English word), never the numeric prefix — same
# rule the soil-trend aggregation uses. These labels ARE the observer's data,
# not UI config, so they are resolved on the backend.
def label_soil_moisture(raw):
    v = (raw or "").lower()
    if "womile" in v or ("dry" in v and "moist" not in v):
        return "Dry"
    if "ubutsile" in v or "moist" in v:
        return "Moist"
    if "umanti" in v or "wet" in v:
        return "Wet"
    return None


def label_vegetation(raw):
    v = (raw or "").lower()
    if "generally_green" in v or "almost_green" in v:
        return "Generally green"
    if "some" in v or "few" in v:
        return "Some/few green"
    if "brown" in v or "bushile" in v:
        return "Brown"
    return None
