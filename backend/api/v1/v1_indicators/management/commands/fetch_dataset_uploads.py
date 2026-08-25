"""Fetch provider-published dataset files from GeoNode (PA-6 D-1, phase 2).

GeoNode is the inbox for DWA, JRBA and CSO, who hold the data and will never
hold platform accounts. This walks each dataset's category, downloads
anything it has not seen, and validates it.

It stops at `validated`. Publishing to GeoNode does NOT update the platform:
an external organisation must not write into the national risk score
unreviewed, so the operator still confirms the diff in Django admin (D-3).

Run it on a schedule — daily is generous for datasets that refresh a few
times a year. How long a published file may sit unnoticed is bounded by the
notification, not by the polling interval.
"""

import logging

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from rest_framework.exceptions import ValidationError

from api.v1.v1_indicators import geonode, uploads
from api.v1.v1_indicators.constants import UploadOrigin, UploadStatus
from api.v1.v1_indicators.datasets import DATASETS
from api.v1.v1_indicators.models import DatasetUpload
from api.v1.v1_indicators.notifications import notify_pending_uploads
from api.v1.v1_indicators.parsers import checksum_of

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch dataset files providers published to GeoNode categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            help="Limit to one registry slug (default: all).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help=(
                "Report which dataset categories exist on GeoNode and exit. "
                "A missing category is silently unreachable otherwise."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be fetched without downloading or storing.",
        )
        parser.add_argument(
            "--no-email",
            action="store_true",
            help="Skip the operator notification.",
        )

    def handle(self, *args, **options):
        # Dry run creates no rows, so the summary needs its own tally or
        # it contradicts the lines it just printed.
        self.would_fetch = 0
        definitions = self._definitions(options.get("dataset"))
        if definitions is None:
            return

        if options["check"]:
            self._check_categories(definitions)
            return

        created = []
        for definition in definitions:
            created.extend(
                self._poll(definition, dry_run=options["dry_run"])
            )

        if options["dry_run"]:
            self.stdout.write(
                f"\nDry run: {self.would_fetch} file(s) would be "
                "fetched. Nothing downloaded or stored."
            )
            return

        pending = [u for u in created if u.status == UploadStatus.validated]
        rejected = [u for u in created if u.status == UploadStatus.rejected]
        self.stdout.write(
            f"\n{len(created)} upload row(s) created: "
            f"{len(pending)} validated, {len(rejected)} rejected."
        )
        if pending:
            self.stdout.write(
                "Awaiting review in Django admin — nothing has been "
                "applied."
            )
        if created and not options["no_email"]:
            recipients = notify_pending_uploads(created)
            self.stdout.write(f"Notified {len(recipients)} operator(s).")

    # --- helpers ------------------------------------------------------

    def _definitions(self, slug):
        if not slug:
            return list(DATASETS.values())
        if slug not in DATASETS:
            self.stderr.write(
                f"Unknown dataset '{slug}'. Known: "
                + ", ".join(sorted(DATASETS))
            )
            return None
        return [DATASETS[slug]]

    def _check_categories(self, definitions):
        try:
            available = geonode.existing_categories()
        except geonode.GeoNodeError as error:
            self.stderr.write(f"Could not read categories: {error}")
            return
        missing = []
        for definition in definitions:
            present = definition.geonode_category in available
            self.stdout.write(
                f"  {'OK     ' if present else 'MISSING'} "
                f"{definition.geonode_category}  ({definition.slug})"
            )
            if not present:
                missing.append(definition.geonode_category)
        if missing:
            self.stdout.write(
                f"\n{len(missing)} category/categories must be created in "
                "GeoNode before providers can publish to them. Until then "
                "those datasets are unreachable and this command will "
                "report nothing new for them, indefinitely."
            )

    def _poll(self, definition, dry_run=False):
        category = definition.geonode_category
        try:
            resources = geonode.list_documents(category)
        except geonode.GeoNodeError as error:
            # One category being unreadable says nothing about the others,
            # so this is logged and skipped rather than aborting the run.
            logger.error("GeoNode read failed for %s: %s", category, error)
            self.stderr.write(f"  {category}: unreadable ({error})")
            return []

        if not resources:
            return []

        created = []
        for resource in resources:
            outcome = self._ingest(definition, resource, dry_run=dry_run)
            if outcome:
                created.extend(outcome)
        return created

    def _ingest(self, definition, resource, dry_run=False):
        pk = resource.get("pk")
        label = geonode.resource_source_label(resource)
        as_of = geonode.resource_as_of(resource)

        if as_of is None:
            # Guessing a vintage would put a fabricated date on published
            # figures. The provider has to set one.
            self.stderr.write(
                f"  {definition.slug}: #{pk} has no date; skipped. "
                "Ask the publisher to set the resource date."
            )
            return []

        if dry_run:
            # Dedupe is on content, so without downloading we cannot know
            # whether this resource has changed. The id tells us whether it
            # has been seen at all, which is the difference between "new" and
            # "maybe a correction" — and stops dry-run implying that
            # everything in the category is unfetched.
            seen = DatasetUpload.objects.filter(geonode_id=pk).exists()
            self.would_fetch += 1
            self.stdout.write(
                f"  would fetch {definition.slug}: #{pk} {label} ({as_of})"
                + ("  [seen before; fetched only if the file changed]"
                   if seen else "  [new]")
            )
            return []

        try:
            payload = geonode.download(resource)
        except geonode.GeoNodeError as error:
            logger.error("Download failed for #%s: %s", pk, error)
            self.stderr.write(f"  {definition.slug}: #{pk} download failed")
            return []

        name = f"geonode_{pk}.csv"
        uploaded = SimpleUploadedFile(name, payload, "text/csv")
        digest = checksum_of(uploaded)
        if DatasetUpload.objects.filter(checksum=digest).exists():
            # Dedupe on content, not on resource id: a provider can replace
            # a document in place, so the id alone would hide a correction.
            # Re-downloading a few KB per run is cheaper than reasoning
            # about GeoNode's timestamps.
            return []

        try:
            created = uploads.create_uploads(
                uploaded=uploaded,
                source_label=label,
                as_of=as_of,
                user=None,
                origin=UploadOrigin.geonode,
                geonode_id=pk,
            )
        except ValidationError as error:
            self.stderr.write(f"  {definition.slug}: #{pk} rejected — "
                              f"{error.detail}")
            return []

        # OQ-14: recorded, never mailed. Notifying an external partner
        # automatically is an outward-facing action nobody has approved.
        publisher = geonode.resource_owner_email(resource)
        if publisher:
            for upload in created:
                upload.report["published_by"] = publisher
                upload.save(update_fields=["report"])

        for upload in created:
            self.stdout.write(
                f"  {upload.dataset}: #{pk} -> {upload.status_label.lower()}"
            )
        return created
