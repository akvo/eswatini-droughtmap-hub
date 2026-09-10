"""Print the Risk Level arithmetic for one Inkhundla, from live data.

A teaching/verification aid for the platform walkthrough: it shows the
Hazard x Exposure x Vulnerability build-up, a sensitivity table that varies
only the drought class, and how much of the risk range is actually reachable
if the whole country hit D4.

It calls `score_all()` — the same service the API serves — so the numbers
printed here are the numbers the platform shows. Nothing is written.

    ./manage.py risk_level_demo
    ./manage.py risk_level_demo --inkhundla Nkilongo --dclass D3
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError

from api.v1.v1_indicators.constants import (
    EXPOSURE_NORM_KEYS,
    HAZARD_RESCALE,
    RISK_BANDS,
)
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.services import score_all, _apply_band
from api.v1.v1_publication.constants import DroughtCategory, PublicationStatus
from api.v1.v1_publication.models import Publication

logger = logging.getLogger(__name__)

RULE = "-" * 68


def _pick(rows: List[Dict[str, Any]], name: Optional[str]) -> Dict[str, Any]:
    """Return the subject Inkhundla: the named one, else the highest-risk one.

    Only Tinkhundla with all four exposure sub-indicators present are eligible
    — a build-up with a missing term teaches the wrong lesson.

    Raises:
        CommandError: When no eligible Inkhundla matches `name`.
    """
    complete = [
        r for r in rows if not r["unavailable"] and r["risk_score"] is not None
    ]
    if not complete:
        raise CommandError(
            "No Inkhundla has all four exposure sub-indicators. "
            "Run generate_indicators_seeder and generate_water_demand_seeder."
        )
    complete.sort(key=lambda r: -r["risk_score"])

    if not name:
        return complete[0]

    want = name.strip().lower()
    match = [r for r in complete if want in r["administration_name"].lower()]
    if not match:
        available = ", ".join(
            sorted(r["administration_name"] for r in complete)
        )
        raise CommandError(
            f"No Inkhundla matching {name!r} with all four sub-indicators.\n"
            f"Available: {available}"
        )
    return match[0]


class Command(BaseCommand):
    help = "Prints the Risk Level build-up for one Inkhundla from live data."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--inkhundla",
            help="Name (or part of one). Defaults to the highest-risk one.",
        )
        parser.add_argument(
            "--dclass",
            choices=list(HAZARD_RESCALE),
            help="Recompute the subject at this drought class instead.",
        )

    def handle(self, *args, **options) -> None:
        rows = score_all()
        pub = (
            Publication.objects.filter(
                status=PublicationStatus.published, published_at__isnull=False
            )
            .order_by("-year_month", "-id")
            .first()
        )
        if pub is None:
            raise CommandError("No published publication to take hazard from.")

        row = _pick(rows, options.get("inkhundla"))
        out = self.stdout.write

        out("=" * 68)
        out("RISK LEVEL — worked example from live data")
        out("=" * 68)
        out(f"Hazard source: published publication {pub.year_month:%Y-%m}\n")

        category = DroughtCategory.FieldStr[row["category"]]
        out(f"Inkhundla : {row['administration_name']} ({row['region']})")
        out(f"D-class   : {category}\n")

        # Both columns, because the Risk Level page shows the raw measurement
        # while the mean is taken over the normalised one. Printing only one
        # of them is what makes the slide and the screen look contradictory.
        indicator = Indicator.objects.get(
            administration_id=row["administration"]
        )
        out("EXPOSURE — mean of 4 sub-indicators "
            "(each log1p then min-max over all 59)")
        out(f"   {'sub-indicator':<22}{'raw (on screen)':>18}"
            f"{'normalised':>13}")
        for raw_key, norm_key in EXPOSURE_NORM_KEYS.items():
            raw = getattr(indicator, raw_key, None)
            norm = row["components"].get(norm_key)
            raw_shown = (
                "-" if raw is None
                else f"{raw:,.4f}".rstrip("0").rstrip(".")
            )
            norm_shown = "-" if norm is None else f"{norm:.4f}"
            out(f"   {raw_key:<22}{raw_shown:>18}{norm_shown:>13}")
        out(f"   {'mean = exposure':<22}{'':>18}"
            f"{row['exposure']:>13.4f}\n")

        ipc = indicator.ipc_phase
        out(f"VULNERABILITY — IPC phase {ipc} rescaled "
            f"-> {row['vulnerability']}")
        out(f"HAZARD        — {category} rescaled -> {row['hazard']}\n")

        out("RISK = H x E x V")
        out(f"     = {row['hazard']} x {row['exposure']:.4f} "
            f"x {row['vulnerability']}")
        out(f"     = {row['risk_score']:.4f}   ->  {row['risk_class']}")
        # The API is canonical on 0-1; the Risk Level page multiplies by 10
        # for the headline and by 100 for exposure. Same number, and the band
        # is decided on the 0-1 scale either way.
        out(f"   as the Risk Level page shows it: "
            f"{row['risk_score']:.4f} x 10 = "
            f"{row['risk_score'] * 10:.1f} on a 0-10 axis  ·  exposure "
            f"{row['exposure'] * 100:.0f}%\n")

        # "What if this Inkhundla were D3?" — answered without touching the DB.
        what_if = options.get("dclass")
        if what_if:
            hazard = HAZARD_RESCALE[what_if]
            score = round(
                hazard * row["exposure"] * row["vulnerability"], 4
            )
            out(f"WHAT IF the D-class were {what_if} instead?")
            out(f"     = {hazard} x {row['exposure']:.4f} "
                f"x {row['vulnerability']}")
            out(f"     = {score:.4f}   ->  {_apply_band(score) or 'Low'}\n")

        out(RULE)
        out("SENSITIVITY — same Inkhundla, same E and V, "
            "varying only the D-class")
        out(RULE)
        out(f"{'D-class':<10}{'H':>6}{'risk = H x E x V':>22}{'band':>14}")
        for label, hazard in HAZARD_RESCALE.items():
            score = round(hazard * row["exposure"] * row["vulnerability"], 4)
            band = _apply_band(score) or "-"
            out(f"{label:<10}{hazard:>6}{score:>22.4f}{band:>14}")

        bands = " · ".join(f"{b} >= {t}" for t, b in RISK_BANDS if t > 0)
        out(f"\nBands: {bands} · else Low")

        spread = Counter(r["risk_class"] for r in rows if r["risk_class"])
        out(f"\nAll 59 Tinkhundla this cycle: {dict(spread)}")
        missing = Counter(u for r in rows for u in r["unavailable"])
        out("Sub-indicators unavailable  : "
            f"{dict(missing) or 'none — all four present'}")

        # Reachability: what each Inkhundla would score at the worst drought
        # class, holding its real E and V. Shows how much of the risk range is
        # decided by who lives there rather than by the drought.
        out(f"\n{RULE}")
        out("REACHABILITY — every Inkhundla at D4 (H = 1.0), real E and V")
        out(RULE)
        usable = [
            r for r in rows
            if r["exposure"] is not None and r["vulnerability"] is not None
        ]
        worst = sorted(
            (
                (
                    r["administration_name"],
                    r["exposure"],
                    r["vulnerability"],
                    round(1.0 * r["exposure"] * r["vulnerability"], 4),
                )
                for r in usable
            ),
            key=lambda t: -t[3],
        )
        out(f"{'Inkhundla':<22}{'E':>8}{'V':>6}{'risk':>9}  band")
        for name, exposure, vulnerability, score in worst[:3]:
            out(f"{name:<22}{exposure:>8.3f}{vulnerability:>6.2f}"
                f"{score:>9.4f}  {_apply_band(score)}")
        out("...")
        for name, exposure, vulnerability, score in worst[-2:]:
            out(f"{name:<22}{exposure:>8.3f}{vulnerability:>6.2f}"
                f"{score:>9.4f}  {_apply_band(score)}")
        reachable = Counter(_apply_band(sc) for *_, sc in worst)
        out(f"\nBand spread if the whole country hit D4: {dict(reachable)}")
        out(
            self.style.SUCCESS(
                "A drought class alone does not create high risk — that is "
                "the point of the multiplicative form."
            )
        )
