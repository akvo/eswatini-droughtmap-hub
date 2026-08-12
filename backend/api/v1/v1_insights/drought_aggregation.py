"""Rolling the per-Inkhundla D-class up to a coarser grouping.

Its own module so `services` (the Breakdown-by-zones card) and `map_layers`
(the Regions and Agro-eco map tabs) can both import it at module level without
importing each other. The two surfaces sit on the same screen, so a second
definition of "the modal class" would let the map contradict the card directly
above it.
"""
from collections import Counter

from api.v1.v1_publication.constants import (
    DroughtCategory,
    PublicationStatus,
    is_validated,
)
from api.v1.v1_publication.models import Publication


def validated_categories(year_month=None):
    """({administration_id: category}, publication) for one published month.

    `year_month` is 'YYYY-MM'; without it, the latest published map. Taking
    the month is what lets the Regions and Agro-eco tabs follow the date
    selector — they paint the D-class, which changes every month.

    Only real, admin-assigned D-classes land here. An Inkhundla with no
    published category is simply absent — never defaulted to 0, which the
    frontend paints as a genuine "Wet/normal conditions" verdict.
    """
    queryset = Publication.objects.filter(
        status=PublicationStatus.published, published_at__isnull=False
    )
    if year_month:
        year, month = year_month.split("-")
        queryset = queryset.filter(
            year_month__year=int(year), year_month__month=int(month)
        )
    publication = queryset.order_by("-year_month", "-id").first()
    if not publication or not publication.validated_values:
        return {}, publication
    return {
        v["administration_id"]: v["category"]
        for v in publication.validated_values
        if is_validated(v.get("category"))
    }, publication


def modal_category(cat_counts, total_count):
    """(modal D-class, confidence %) for one group of Tinkhundla.

    Confidence is a share of the WHOLE group, not of the Tinkhundla that
    happen to have data, so missing months read as low confidence rather than
    as silent agreement.
    """
    if not cat_counts:
        return DroughtCategory.none, 0
    modal_cat, modal_count = cat_counts.most_common(1)[0]
    return modal_cat, round((modal_count / (total_count or 1)) * 100)


def grouped_drought(groups, year_month=None):
    """({group_key: (modal D-class, confidence %)}, publication).

    `groups` maps a group key to the administration ids it contains.
    """
    categories, publication = validated_categories(year_month)
    if not categories:
        return {}, publication
    return {
        key: modal_category(
            Counter(
                categories[aid] for aid in ids if aid in categories
            ),
            len(ids),
        )
        for key, ids in groups.items()
    }, publication
