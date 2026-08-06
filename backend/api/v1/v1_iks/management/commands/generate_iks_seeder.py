"""Offline stand-in for `download_iks_data` (DEMO-1 D-13/D-14).

Builds Kobo submissions with the REAL question keys and the REAL indicator
choice vocabulary (./source/iks_kobo_catalogue.csv), then hands each payload to
`download_iks_data._map_iks_values` — the same extractor the live sync uses. So
IKSIndicator/IKSValue rows are produced by one code path, and a question the
extractor learns later reaches seeded submissions too.

Submissions are spread across the FULL window rather than the May-Jul band the
IKS aggregations are hardcoded around (D-13). That is deliberate: `sat=66.7`,
the week-invariant heatmap counts and the fixed week axis are known synthetic
remnants, and seeding only into May-Jul would make them look computed.
"""
import csv
import logging
import os
import random
import shutil
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.v1.v1_iks.constants import CHIEFDOM_FIELD
from api.v1.v1_iks.models import KoboData, KoboForm
from api.v1.v1_publication.models import Administration

logger = logging.getLogger(__name__)

CATALOGUE_PATHS = ["./source/iks_kobo_catalogue.csv"]
IMAGE_DIR = "./source/images"

DEMO_FORM_UUID = "demo-iks-form"
DEMO_FORM_NAME = "IKS Observation (seeded)"

# Kobo ids far above any real submission id so `--clean` can find them and a
# later real sync cannot collide.
DEMO_KOBO_ID_BASE = 900_000_000

# The real Kobo question keys. These must match download_iks_data's extractor
# exactly — a typo here yields submissions that store fine and produce zero
# IKSValue rows, which looks like an empty explorer rather than a bad seed.
FIELD_B1 = "group_tn4ao32/B1_Which_of_the_fol_vile_endzaweni_yakho"
FIELD_C1 = "group_mq8ds86/C1_Which_of_the_fol_lotivile_kulendzawo"
FIELD_D1 = "group_bx6rt12/D1_How_is_the_soil_atsi_endzaweni_yakho"
FIELD_D2 = "group_bx6rt12/D2_How_is_the_veget_ato_endzaweni_yakho"

# Section D choice values. Substrings here are what utils.label_soil_moisture
# and utils.label_vegetation key off; changing them silently produces None
# labels and empty Section D cards.
SOIL_CHOICES = ["dry_womile", "moist_ubutsile", "wet_umanti"]
VEGETATION_CHOICES = [
    "generally_green_luhlata",
    "some_green_lokuncane",
    "brown_bushile",
]

# Share of Tinkhundla submitting in any given month. Not everyone reports
# every month — full coverage would hide the "no reports" empty state.
SUBMISSION_RATE = 0.4


class Command(BaseCommand):
    help = (
        "Seeds IKS Kobo submissions offline, using the real question keys, "
        "choice vocabulary and value extractor."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--months", type=int, default=24,
            help="Months of submissions, ending this month.",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="RNG seed; the same seed reproduces the same submissions.",
        )
        parser.add_argument(
            "--no-photos", action="store_true",
            help="Skip attachments (and the image copy into STORAGE_PATH).",
        )
        parser.add_argument(
            "--clean", action="store_true",
            help="Delete the seeded form and its submissions, then exit.",
        )

    def handle(self, *args, **options):
        if options["clean"]:
            deleted, _ = KoboForm.objects.filter(
                uuid=DEMO_FORM_UUID
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(f"Removed {deleted} seeded IKS row(s).")
            )
            return

        rng = random.Random(options["seed"])
        catalogue = self._catalogue()
        if not catalogue:
            self.stderr.write(
                self.style.ERROR(
                    f"IKS catalogue not found in {CATALOGUE_PATHS}."
                )
            )
            return

        administrations = list(Administration.objects.order_by("id"))
        if not administrations:
            self.stderr.write(
                self.style.ERROR(
                    "No administrations; run generate_administrations_seeder."
                )
            )
            return

        form = self._form()
        images = (
            [] if options["no_photos"] else self._stage_images()
        )
        created = self._submissions(
            form, administrations, catalogue, images, options["months"], rng
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{created} IKS submission(s) across "
                f"{len(administrations)} Tinkhundla, "
                f"{len(catalogue['B']) + len(catalogue['C'])} indicators, "
                f"{len(images)} photo(s) available."
            )
        )

    # --- inputs -----------------------------------------------------------

    def _catalogue(self):
        """{'B': [...], 'C': [...]} of real Kobo choice names.

        `group` in the CSV is the questionnaire section: rainfall predictors
        are B1, seasonal/extreme weather are C1.
        """
        path = next(
            (
                candidate
                for candidate in (
                    os.path.join(settings.BASE_DIR, p) for p in CATALOGUE_PATHS
                )
                if os.path.exists(candidate)
            ),
            None,
        ) or next(
            (p for p in CATALOGUE_PATHS if os.path.exists(p)), None
        )
        if not path:
            return None

        sections = {"B": [], "C": []}
        with open(path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                choice = (row.get("kobo_choice_name") or "").strip()
                if not choice:
                    continue
                section = "B" if row.get("group") == "rainfall" else "C"
                sections[section].append(choice)
        return sections if any(sections.values()) else None

    def _form(self):
        """The seeded form, active.

        Any OTHER active form is deactivated: there is no single-active
        constraint, and the public IKS API merges every active form's data, so
        leaving two active silently blends seeded and real submissions into
        one set of aggregations.
        """
        others = KoboForm.objects.filter(active=True).exclude(
            uuid=DEMO_FORM_UUID
        )
        for other in others:
            self.stdout.write(
                self.style.WARNING(
                    f"Deactivating already-active form '{other.name}' "
                    f"({other.uuid}) so its data does not merge with the "
                    f"seeded form in the public IKS aggregations."
                )
            )
        others.update(active=False)

        form, _ = KoboForm.objects.update_or_create(
            uuid=DEMO_FORM_UUID,
            defaults={
                "name": DEMO_FORM_NAME,
                "description": "Seeded by generate_iks_seeder (DEMO-1).",
                "active": True,
                "last_sync_timestamp": timezone.now(),
            },
        )
        return form

    def _stage_images(self):
        """Copy the committed sample photos into STORAGE_PATH.

        IKSPhotoFileView serves attachments by basename out of STORAGE_PATH,
        so the seeder only has to put the files where that view already looks
        — no view change (D-14).
        """
        source_dir = IMAGE_DIR
        if not os.path.isdir(source_dir):
            source_dir = os.path.join(settings.BASE_DIR, IMAGE_DIR)
        if not os.path.isdir(source_dir):
            self.stdout.write(
                self.style.WARNING(
                    f"No {IMAGE_DIR}; seeding submissions without photos."
                )
            )
            return []

        os.makedirs(settings.STORAGE_PATH, exist_ok=True)
        staged = []
        for name in sorted(os.listdir(source_dir)):
            if not name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            target = os.path.join(settings.STORAGE_PATH, name)
            if not os.path.exists(target):
                shutil.copy2(os.path.join(source_dir, name), target)
            staged.append(name)
        return staged

    # --- submissions ------------------------------------------------------

    def _submissions(
        self, form, administrations, catalogue, images, months, rng
    ):
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        periods = []
        cursor = first_of_month
        for _ in range(months):
            periods.append(cursor)
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        periods.reverse()

        kobo_id = DEMO_KOBO_ID_BASE
        created = 0
        for period in periods:
            reporters = [
                administration
                for administration in administrations
                if rng.random() < SUBMISSION_RATE
            ]
            for administration in reporters:
                kobo_id += 1
                if self._submission(
                    form, administration, catalogue, images, period,
                    kobo_id, rng,
                ):
                    created += 1
        return created

    def _submission(
        self, form, administration, catalogue, images, period, kobo_id, rng
    ):
        submitted = timezone.make_aware(
            timezone.datetime(
                period.year, period.month, rng.randint(1, 28),
                rng.randint(6, 18), rng.randint(0, 59),
            )
        )
        raw = {
            "_id": kobo_id,
            "_submitted_by": f"observer_{administration.id}",
            "meta/instanceID": f"uuid:demo-{kobo_id}",
            CHIEFDOM_FIELD: administration.name,
            # Space-separated multi-select, exactly as Kobo stores it.
            FIELD_B1: " ".join(
                rng.sample(
                    catalogue["B"], rng.randint(1, min(4, len(catalogue["B"])))
                )
            ),
            FIELD_C1: " ".join(
                rng.sample(
                    catalogue["C"], rng.randint(1, min(3, len(catalogue["C"])))
                )
            ),
            FIELD_D1: rng.choice(SOIL_CHOICES),
            FIELD_D2: rng.choice(VEGETATION_CHOICES),
        }
        if images:
            name = images[kobo_id % len(images)]
            raw["_attachments"] = [
                {
                    "filename": f"attachments/{name}",
                    "mimetype": "image/jpeg",
                }
            ]

        KoboData.objects.update_or_create(
            kobo_id=kobo_id,
            defaults={
                "form": form,
                "geo": None,
                "submission_time": submitted,
                "submitted_by": raw["_submitted_by"],
                "instance_name": raw["meta/instanceID"],
                "raw_data": raw,
            },
        )

        # Reuse the live extractor rather than duplicating the field mapping.
        # It takes no instance state, so a bare instance is enough.
        from api.v1.v1_iks.management.commands.download_iks_data import (
            Command as IksSyncCommand,
        )

        IksSyncCommand()._map_iks_values(
            form, raw, kobo_id, administration.id
        )
        return True
