"""One command to fill every model the demo pages read (DEMO-1 D-1/D-3).

A thin orchestrator over the per-app seeders, not a re-implementation: most of
the model families already had a working command, and duplicating them here
would drift from the originals immediately.

What it adds over a shell script is the ORDER, which is a hard dependency chain
rather than a preference (D-3). Two links that fail silently when wrong:
  - insights/response-activities evaluates activity triggers against Indicator
    AND the latest published Publication; seeded out of order it reports 0
    triggered Tinkhundla, which reads as a UI bug rather than a seeding one.
  - generate_weather_seeder draws its values from AdministrationNormal, so
    extract_weather_normals has to run BEFORE it (D-16).

Lives in v1_publication because that app owns Administration, the root every
other seeder joins to.
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_publication.constants import (
    SEEDED_PUBLICATION_GEONODE_BASE,
    SEEDED_RASTER_GEONODE_BASE,
    PublicationStatus,
)
from api.v1.v1_publication.models import (
    Publication,
    PublicationGeonode,
    PublicationRaster,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
    CitizenScienceReading,
    StationDailyAggregate,
)

DEFAULT_MONTHS = 24
DEFAULT_WEATHER_MONTHS = 24

# Months before which --to is far enough in the past that the CDI-E strip —
# anchored on the CURRENT month, never on the latest published one — renders
# visibly empty cells on its right (D-15 Trap 3).
CDI_STRIP_MONTHS = 12


def _clean_publications():
    """Publication + everything CASCADEd off it, plus the GeoNode cache.

    hard=True is mandatory: Publication is SoftDeletes, so a plain delete only
    stamps deleted_at, leaves Review/ValidationDecision/PublicationRaster
    orphaned, AND leaves the unique cdi_geonode_id in place — which then blocks
    re-seeding that same month (D-9).
    """
    queryset = Publication.objects.filter(
        cdi_geonode_id__gte=SEEDED_PUBLICATION_GEONODE_BASE
    )
    count = queryset.count()
    queryset.delete(hard=True)
    PublicationGeonode.objects.filter(
        geonode_id__gte=SEEDED_PUBLICATION_GEONODE_BASE
    ).delete()
    return count


def _clean_rasters():
    queryset = PublicationRaster.objects.filter(
        geonode_id__gte=SEEDED_RASTER_GEONODE_BASE
    )
    count = queryset.count()
    queryset.delete()
    return count


def _clean_weather():
    count = StationDailyAggregate.objects.filter(
        station__metadata_status="demo"
    ).count()
    call_command("generate_weather_seeder", "--clean", verbosity=0)
    return count


def _clean_iks():
    from api.v1.v1_iks.models import KoboData

    count = KoboData.objects.filter(form__uuid="demo-iks-form").count()
    call_command("generate_iks_seeder", "--clean", verbosity=0)
    return count


def _clean_citizen_science():
    # No marker on this model — every row is seeded data by construction.
    count = CitizenScienceReading.objects.count()
    CitizenScienceReading.objects.all().delete()
    return count


def _clean_activities():
    # ResponseActivity is SoftDeletes too — same hard-delete rule as above.
    count = ResponseActivity.objects.count()
    ResponseActivity.objects.all().delete(hard=True)
    return count


def _clean_indicators():
    # is_placeholder is the marker the CSV seeders already set, so a
    # hand-curated NDMA row would survive this.
    queryset = Indicator.objects.filter(is_placeholder=True)
    count = queryset.count()
    queryset.delete()
    return count


def _clean_normals():
    count = AdministrationNormal.objects.count()
    AdministrationNormal.objects.all().delete()
    return count


CLEAN_FAMILIES = {
    "publications": _clean_publications,
    "rasters": _clean_rasters,
    "weather": _clean_weather,
    "iks": _clean_iks,
    "citizen-science": _clean_citizen_science,
    "activities": _clean_activities,
    "indicators": _clean_indicators,
    "normals": _clean_normals,
}

# Never in any family: Administration, SystemUser, roles/abilities and the
# KoboAdapter credentials. Re-seeding those is the slow part, and deleting
# users is the one irreversible thing here.


class Command(BaseCommand):
    help = (
        "Seeds every model the National overview and Detailed Insights pages "
        "read, in dependency order."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--months", type=int, default=DEFAULT_MONTHS,
            help=(
                f"Months of publications (default {DEFAULT_MONTHS}), matched "
                f"to --weather-months so no tab shows data on one chart and a "
                f"wall on another (D-15)."
            ),
        )
        parser.add_argument(
            "--weather-months", type=int, default=DEFAULT_WEATHER_MONTHS,
            help=(
                "Months of daily observations. Always ends TODAY regardless "
                "of --months: station health is computed against the wall "
                "clock, so a historical end date reads as 0 of 8 online."
            ),
        )
        parser.add_argument(
            "--publish-through", default=None,
            help=(
                "YYYY-MM. Later months stay in_review with values populated, "
                "so review -> validate -> publish can be walked by hand. "
                "Default: every seeded month is published."
            ),
        )
        parser.add_argument(
            "--path", default=None,
            help=(
                "Local pct-rank GeoTIFF archive for REAL publication and "
                "component values, e.g. ./storage/geotiffs. Without it the "
                "seeders fall back to the cached GeoNode resource list, then "
                "to live GeoNode, then to synthetic values."
            ),
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="RNG seed; the same seed reproduces the same database.",
        )
        parser.add_argument(
            "--skip-users", action="store_true",
            help="Leave accounts alone (roles, admin, reviewers, observers).",
        )
        parser.add_argument(
            "--clean", nargs="?", const="all", default=None,
            help=(
                "Delete seeded data and exit. Optionally a comma-separated "
                f"subset of: {', '.join(sorted(CLEAN_FAMILIES))}. "
                "'--clean=weather,iks,citizen-science' is the "
                "answers/history-only case."
            ),
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Required to run when DEBUG is False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to run with DEBUG=False. This writes fabricated "
                "drought classifications; pass --force if that is genuinely "
                "what you intend."
            )

        if options["clean"] is not None:
            self.clean(options["clean"])
            return

        self.seed(options)

    # --- seeding ----------------------------------------------------------

    def stage(self, label, command, *args, **kwargs):
        """Run one seeder, reporting rather than swallowing a failure.

        An optional stage failing (usually extract_weather_normals without
        rasterio) must not abort the rest, but it must be loud: a silently
        skipped stage surfaces much later as an empty chart.
        """
        self.stdout.write(self.style.MIGRATE_HEADING(f"-> {label}"))
        try:
            call_command(command, *args, **kwargs)
            return True
        except Exception as exc:  # noqa: BLE001 — reported, not hidden
            self.stderr.write(self.style.ERROR(f"   {label} FAILED: {exc}"))
            self.failures.append(label)
            return False

    def seed(self, options):
        self.failures = []
        seed = options["seed"]
        months = options["months"]
        path = options["path"]

        self._warn_about_stale_window(options)
        self._report_publication_source(path)

        # 1-3: reference data every later stage joins to.
        self.stage("Administrations", "generate_administrations_seeder")
        if not options["skip_users"]:
            self.stage(
                "Roles and abilities", "generate_roles_n_abilities_seeder"
            )
            self.stage("Admin account", "generate_admin_seeder")
            self.stage("Reviewer accounts", "fake_users_seeder")

        # 4-6: risk inputs and the activity library, all from ./source CSVs.
        self.stage("Risk indicators", "generate_indicators_seeder")
        self.stage("Eligibility counts", "generate_eligibility_seeder")
        # --demo activates the ACT-DEMO-* rows. Without them only one of the
        # real library's four activities can ever fire (the rest gate on
        # cattle/water_demand, which are null for all 59 Tinkhundla), so three
        # of the four National overview sector cards read 0.
        self.stage(
            "Response activities", "generate_activity_seeder", "--demo"
        )

        # 7: publications. --repeat is doubled by that command, hence half.
        publication_args = [
            "--repeat", max(months // 2, 1),
            "--seed", seed,
            "--with-reviews",
        ]
        if path:
            publication_args += ["--source", "path", "--path", path]
        if options["publish_through"]:
            publication_args += [
                "--publish-through", options["publish_through"]
            ]
        else:
            publication_args += ["--status", str(PublicationStatus.published)]
        self.stage(
            "Publications", "generate_publications_seeder", *publication_args
        )

        # 8: component rasters, layered on the publications from 7.
        raster_args = ["--seed", seed]
        if path:
            raster_args += ["--source", "path", "--path", path]
        self.stage(
            "Component rasters", "generate_rasters_seeder", *raster_args
        )

        # 9 BEFORE 10: the weather seeder draws its values from the normals.
        self.stage("30-year normals", "extract_weather_normals")
        self.stage(
            "Weather stations and observations", "generate_weather_seeder",
            "--months", options["weather_months"], "--seed", seed,
        )
        if not options["skip_users"]:
            self.stage(
                "Citizen-science readings", "fake_citizen_weather_seeder"
            )

        self.stage(
            "IKS submissions", "generate_iks_seeder",
            "--months", months, "--seed", seed,
        )
        self.stage("Frontend config", "generate_config")

        self.summary()

    def _report_publication_source(self, path):
        """Say up front where publication values will come from.

        The seeders resolve this themselves (path -> cache -> geonode ->
        synthetic), but they resolve it several stages in. Printing it here
        turns the two states that look identical on the pages — real values
        extracted, and rows created with initial_values still empty because
        GeoNode never answered — into something you can tell apart without
        opening a shell.
        """
        if path:
            return
        cached = PublicationGeonode.objects.filter(
            geonode_id__lt=SEEDED_PUBLICATION_GEONODE_BASE
        ).count()
        if cached:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Publication source: {cached} cached GeoNode resource(s) "
                    f"(no catalogue request). Values still need a worker and "
                    f"a reachable raster host; re-run './job.sh cdi' if any "
                    f"publication ends up with empty initial_values."
                )
            )
            return
        self.stdout.write(
            self.style.WARNING(
                "Publication source: no cached GeoNode resources. Falling "
                "back to live GeoNode, then to synthetic values. Run "
                "sync_publication_geonodes first to seed from real metadata."
            )
        )

    def _warn_about_stale_window(self, options):
        """`resolve_window` anchors the CDI-E strip on the CURRENT month, not
        the latest published one, so a --publish-through well in the past
        leaves the strip's right-hand cells empty by design (D-15 Trap 3)."""
        boundary = options["publish_through"]
        if not boundary:
            return
        from django.utils import timezone

        now = timezone.now().date()
        try:
            year, month = (int(part) for part in boundary.split("-"))
        except ValueError:
            raise CommandError(
                f"--publish-through must be YYYY-MM, got '{boundary}'."
            )
        behind = (now.year - year) * 12 + (now.month - month)
        if behind > CDI_STRIP_MONTHS:
            self.stdout.write(
                self.style.WARNING(
                    f"--publish-through {boundary} is {behind} months back. "
                    f"The CDI-E strip is anchored on the current month, so "
                    f"its right-hand cells will render empty. That is by "
                    f"design, not a seeding failure."
                )
            )

    def summary(self):
        published = Publication.objects.filter(
            status=PublicationStatus.published
        ).count()
        rows = [
            ("Publications", Publication.objects.count()),
            ("  of which published", published),
            ("Component rasters", PublicationRaster.objects.count()),
            ("Indicators", Indicator.objects.count()),
            ("Response activities", ResponseActivity.objects.count()),
            ("30-year normals", AdministrationNormal.objects.count()),
            ("Weather daily rows", StationDailyAggregate.objects.count()),
        ]
        self.stdout.write("")
        for label, count in rows:
            self.stdout.write(f"  {label:24s} {count}")

        # The one count worth calling out: a publication with no
        # initial_values renders as an empty review queue and an all-No-Data
        # map, neither of which looks like a seeding problem from the page.
        empty = Publication.objects.filter(initial_values=[]).count()
        if empty:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{empty} publication(s) have empty initial_values — "
                    f"their raster download has not completed. Check the "
                    f"worker is running, then './job.sh cdi' to retry."
                )
            )

        if self.failures:
            self.stdout.write(
                self.style.WARNING(
                    f"\nCompleted with {len(self.failures)} failed stage(s): "
                    f"{', '.join(self.failures)}"
                )
            )
            return
        self.stdout.write(self.style.SUCCESS("\nSeeding complete."))

    # --- cleaning ---------------------------------------------------------

    def clean(self, families):
        requested = (
            sorted(CLEAN_FAMILIES)
            if families == "all"
            else [name.strip() for name in families.split(",") if name.strip()]
        )
        unknown = [name for name in requested if name not in CLEAN_FAMILIES]
        if unknown:
            raise CommandError(
                f"Unknown clean family {unknown}. Valid families: "
                f"{', '.join(sorted(CLEAN_FAMILIES))}"
            )

        for name in requested:
            deleted = CLEAN_FAMILIES[name]()
            self.stdout.write(f"  {name:18s} {deleted} row(s)")
        self.stdout.write(self.style.SUCCESS("Clean complete."))
