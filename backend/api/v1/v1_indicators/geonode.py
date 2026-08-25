"""Read the GeoNode catalogue for provider-published dataset files (PA-6 D-1).

GeoNode is the providers' inbox: DWA, JRBA and CSO hold the data and will
never hold platform accounts, so they publish into a per-dataset category and
this module fetches what lands there. Django admin stays the review desk —
nothing here writes to `Indicator`.

Read-only. Nothing in this module creates or modifies a GeoNode resource.
"""

import logging
from typing import Dict, List, Optional

import requests
from django.conf import settings

from api.v1.v1_indicators.datasets import DATASETS
from api.v1.v1_publication.constants import (
    GEONODE_REQUEST_TIMEOUT,
    GEONODE_SSL_VERIFY,
)
from api.v1.v1_publication.utils import geonode_auth

logger = logging.getLogger(__name__)

__all__ = [
    "GeoNodeError",
    "list_documents",
    "download",
    "existing_categories",
    "category_map",
    "resource_source_label",
    "resource_as_of",
    "resource_owner_email",
]

# A tabular CSV has no geometry, so it cannot be a GeoNode *dataset* — it
# lands as a document.
#
# Filter on `resource_type`, NOT on `subtype`. For a dataset the two agree
# (subtype is "raster"/"vector", which is why v1_publication filters on it),
# but for a document `subtype` is the FILE kind — a CSV reports
# subtype="other" — while `resource_type` is "document". Verified against
# resource 708 on cdie-geonode-prod: filter{subtype}=document returns 0,
# filter{resource_type}=document returns it.
DOCUMENT_RESOURCE_TYPE = "document"

MAX_PAGES = 20  # a category holding more than this is a misconfiguration


class GeoNodeError(Exception):
    """The catalogue could not be read. Never raised for 'nothing found'."""


def _get(path: str) -> dict:
    url = f"{settings.GEONODE_BASE_URL}{path}"
    try:
        response = requests.get(
            url,
            auth=geonode_auth(),
            verify=GEONODE_SSL_VERIFY,
            timeout=GEONODE_REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        # The catalogue and the file host fail independently (v1_publication
        # D-7, and the 2026-08-11 incident). A timeout here says nothing
        # about the other categories, so this raises rather than aborting the
        # whole run — the caller decides.
        raise GeoNodeError(f"{url}: {type(error).__name__}: {error}")
    if response.status_code != 200:
        raise GeoNodeError(f"{url}: HTTP {response.status_code}")
    return response.json()


def existing_categories() -> set:
    """Category identifiers the GeoNode instance actually has.

    Routing is by category (D-1), so a dataset whose category is absent is
    silently unreachable — the poller would report "nothing new" forever.
    Checked explicitly instead.
    """
    payload = _get("/api/v2/categories?page_size=200")
    items = payload.get("categories") or payload.get("TopicCategories") or []
    return {c.get("identifier") for c in items if c.get("identifier")}


def list_documents(category: str) -> List[dict]:
    """Every document resource in one category, newest first."""
    resources: List[dict] = []
    page = 1
    while page <= MAX_PAGES:
        payload = _get(
            "/api/v2/resources"
            f"?filter{{category.identifier}}={category}"
            f"&filter{{resource_type}}={DOCUMENT_RESOURCE_TYPE}"
            f"&sort[]=-date&page={page}"
        )
        found = payload.get("resources", [])
        resources.extend(found)
        total = payload.get("total", 0)
        page_size = payload.get("page_size", len(found) or 1)
        if not found or page * page_size >= total:
            break
        page += 1
    return resources


def download(resource: dict) -> bytes:
    """The document's bytes.

    Prefers the catalogue's own `download_url`; falls back to the documented
    document download path, because GeoNode omits the field on some resource
    serializations.
    """
    url = resource.get("download_url") or (
        f"{settings.GEONODE_BASE_URL}/documents/{resource.get('pk')}/download"
    )
    try:
        response = requests.get(
            url,
            auth=geonode_auth(),
            verify=GEONODE_SSL_VERIFY,
            timeout=GEONODE_REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        raise GeoNodeError(f"{url}: {type(error).__name__}: {error}")
    if response.status_code != 200:
        raise GeoNodeError(f"{url}: HTTP {response.status_code}")
    return response.content


def resource_source_label(resource: dict) -> str:
    """Provenance text for a fetched file.

    The operator sees this on the confirmation page before it is stamped
    onto `Indicator.source`, which is the check on GeoNode metadata being
    whatever the provider happened to type.
    """
    title = (resource.get("title") or "").strip()
    owner = resource.get("owner") or {}
    org = (owner.get("organization") or "").strip()
    pk = resource.get("pk")
    parts = [p for p in (title, org) if p]
    label = " — ".join(parts) if parts else "GeoNode document"
    return f"{label} (GeoNode #{pk})"


def resource_as_of(resource: dict) -> Optional[str]:
    """The date the resource claims, as YYYY-MM-DD.

    Unlike the admin path (D-4), nobody typed this — it is whatever metadata
    the provider set. Returned as-is for the operator to check on the
    confirmation page; None means the resource carries no usable date, which
    the caller treats as a rejection rather than guessing.
    """
    for key in ("date", "temporal_extent_start", "last_updated", "created"):
        value = resource.get(key)
        if value:
            return str(value)[:10]
    return None


def resource_owner_email(resource: dict) -> str:
    """Who published it — recorded so a human can follow up (OQ-14).

    Deliberately not used to send anything: mailing an external partner
    automatically is an outward-facing action nobody has signed off.
    """
    owner = resource.get("owner") or {}
    return (owner.get("email") or "").strip()


def category_map() -> Dict[str, str]:
    """{geonode_category: dataset slug} for every registered dataset."""
    return {d.geonode_category: slug for slug, d in DATASETS.items()}
