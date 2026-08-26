import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from api.v1.v1_publication.models import PublicationGeonode
from api.v1.v1_publication.constants import (
    GEONODE_SSL_VERIFY,
    GEONODE_REQUEST_TIMEOUT,
    CDIGeonodeCategory,
)
from api.v1.v1_publication.utils import geonode_auth


class Command(BaseCommand):
    help = (
        "Backfill/refresh PublicationGeonode cache from GeoNode "
        "(manual recovery only)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--category",
            nargs="?",
            default=None,
            help="Target category identifier. If omitted, syncs all.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show resources that would be updated/created.",
        )

    def handle(self, *args, **options):
        category = options.get("category")
        dry_run = options.get("dry_run")

        if category:
            categories = [category]
        else:
            categories = list(CDIGeonodeCategory.FieldStr.keys())

        self.stdout.write(
            f"Starting GeoNode cache sync for categories: {categories}"
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN: No database writes will be made.")
            )

        for cat in categories:
            self.stdout.write(f"Syncing category: {cat}...")
            self.sync_category(cat, dry_run)

        self.stdout.write(
            self.style.SUCCESS("GeoNode cache sync completed successfully.")
        )

    def sync_category(self, category, dry_run):
        page = 1
        page_size = 20
        total_synced = 0

        while True:
            url = (
                f"{settings.GEONODE_BASE_URL}/api/v2/resources"
                f"?filter{{category.identifier}}={category}"
                f"&filter{{subtype}}=raster"
                f"&page={page}"
                f"&page_size={page_size}"
                f"&sort[]=-date"
            )
            try:
                response = requests.get(
                    url,
                    auth=geonode_auth(),
                    verify=GEONODE_SSL_VERIFY,
                    timeout=GEONODE_REQUEST_TIMEOUT,
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to fetch page {page} for {category}: {e}"
                    )
                )
                break

            if response.status_code != 200:
                self.stderr.write(
                    self.style.ERROR(
                        f"GeoNode returned status {response.status_code} "
                        f"for page {page}."
                    )
                )
                break

            data = response.json()
            resources = data.get("resources", [])
            if not resources:
                break

            for res in resources:
                geonode_id = res.get("pk")
                title = res.get("title")
                # Parse date (GeoNode resource date string)
                date_str = res.get("date")
                year_month = None
                if date_str:
                    try:
                        # GeoNode dates are usually YYYY-MM-DD...
                        year_month = datetime.strptime(
                            date_str[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        try:
                            # Fallback if only YYYY-MM
                            year_month = datetime.strptime(
                                date_str[:7], "%Y-%m"
                            ).date()
                        except ValueError:
                            pass

                if not year_month:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping resource {geonode_id}: "
                            f"invalid date string '{date_str}'"
                        )
                    )
                    continue

                # Parse created datetime
                created_str = res.get("created")
                resource_created = None
                if created_str:
                    try:
                        resource_created = datetime.fromisoformat(
                            created_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                msg = (
                    f"Resource {geonode_id} ({year_month}): '{title}' "
                    f"[file_size={res.get('filesize')}]"
                )
                self.stdout.write(msg)

                if not dry_run:
                    PublicationGeonode.objects.update_or_create(
                        geonode_id=geonode_id,
                        defaults={
                            "category": category,
                            "title": title,
                            "year_month": year_month,
                            "subtype": res.get("subtype", "raster"),
                            "detail_url": res.get("detail_url"),
                            "embed_url": res.get("embed_url"),
                            "thumbnail_url": res.get("thumbnail_url"),
                            "download_url": res.get("download_url"),
                            "file_size": res.get("filesize"),
                            "resource_created": resource_created,
                            "raw": res,
                        },
                    )
                total_synced += 1

            # Check if there is a next page
            total = data.get("total", 0)
            if page * page_size >= total:
                break
            page += 1

        self.stdout.write(
            f"Synced {total_synced} resources for category {category}."
        )
