import random
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from faker import Faker
from datetime import datetime, timedelta
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import (
    Publication,
    Review,
)
from api.v1.v1_publication.constants import (
    PublicationStatus,
    DroughtCategory,
)

fake = Faker()


# Generate dummy narrative content
def generate_dummy_narrative():
    title = fake.sentence(nb_words=6)  # Generate a title with 6 words
    author = fake.name()  # Generate a random author name
    date = fake.date()  # Generate a random date
    content = "\n".join(
        [f"<p>{fake.paragraph(nb_sentences=5)}</p>" for _ in range(5)]
    )

    # Combine into HTML
    html_narrative = f"""
    <narrative>
        <h1>{title}</h1>
        <p><strong>Author:</strong> {author}</p>
        <p><strong>Date:</strong> {date}</p>
        {content}
    </narrative>
    """
    return html_narrative


def get_category(value: float):
    if (value <= 0 and value <= 2):
        return DroughtCategory.d4
    if (value > 2 and value <= 5):
        return DroughtCategory.d3
    if (value > 5 and value <= 10):
        return DroughtCategory.d2
    if (value > 10 and value <= 20):
        return DroughtCategory.d1
    if (value > 20 and value <= 30):
        return DroughtCategory.d0
    return DroughtCategory.none


class Command(BaseCommand):
    help = "Generates fake publication data"

    def add_arguments(self, parser):
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
        )

    def handle(self, *args, **kwargs):
        test = kwargs.get("test")
        topojson_file_path = "./source/eswatini.topojson"

        with open(topojson_file_path, "r") as f:
            topo_data = json.load(f)
        features = topo_data.get('objects', {}).values()
        administration_ids = [
            f["properties"]["administration_id"]
            for fg in features
            for f in fg.get('geometries', [])
        ]

        cdi_geonode_ids = [108, 107, 106, 44]
        if test:
            cdi_geonode_ids = [44, 106]

        # Initialize the start date to December of the previous year
        current_date = datetime(datetime.now().year, datetime.now().month, 1)

        for index, cdi_geonode_id in enumerate(cdi_geonode_ids):
            # Calculate the last day of the current month
            year = current_date.year
            month = current_date.month
            last_day_of_month = monthrange(year, month)[1]
            due_date = datetime(year, month, last_day_of_month)

            # Calculate the previous month from due_date
            due_date_obj = datetime.strptime(
                due_date.strftime("%Y-%m-%d"), "%Y-%m-%d"
            )
            prev_month = due_date_obj - relativedelta(months=1)
            year_month = f"{prev_month.strftime('%Y-%m')}-01"

            # Get the start of the previous month
            start_date = datetime(prev_month.year, prev_month.month, 1)

            # Decrement the current date by one month for the next iteration
            current_date -= relativedelta(months=1)

            status = PublicationStatus.in_review
            if index > 0:
                status = random.choice([
                    PublicationStatus.in_validation,
                    PublicationStatus.published
                ])
            initial_values = []
            for a_id in administration_ids:
                init_value = random.uniform(0, 100)
                initial_values.append({
                    "administration_id": a_id,
                    "value": init_value,
                    "category": get_category(init_value)
                })

            publication = Publication.objects.filter(
                cdi_geonode_id=cdi_geonode_id,
                year_month=year_month,
            ).first()

            if not publication:
                publication = Publication.objects.create(
                    cdi_geonode_id=cdi_geonode_id,
                    year_month=year_month,
                    initial_values=initial_values,
                    status=status,
                    due_date=due_date,
                )

            reviewers = SystemUser.objects.filter(
                role=UserRoleTypes.reviewer
            ).all()

            if publication.status == PublicationStatus.published:
                if not settings.TEST_ENV:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Publication ID: {publication.id} was published"
                        )
                    )
                published_at = due_date + timedelta(
                    days=random.randint(1, 7)
                )
                publication.status = PublicationStatus.published
                publication.published_at = timezone.make_aware(published_at)
                publication.narrative = generate_dummy_narrative()
                publication.bulletin_url = (
                    "https://www.ipcinfo.org/fileadmin/"
                    "user_upload/ipcinfo/docs/"
                    "IPC_Eswatini_AFI_2019June2020March.pdf"
                )
                publication.validated_values = [
                    {
                        "administration_id": v["administration_id"],
                        "value": v["value"] + 5,
                        "category": get_category(v["value"] + 5)
                    }
                    for v in initial_values
                ]
                publication.save()

            for reviewer in reviewers:
                review, _ = Review.objects.get_or_create(
                    publication=publication,
                    user=reviewer
                )

                is_completed = (
                    publication.status != PublicationStatus.in_review
                )

                suggestion_values = []
                for v in initial_values:
                    s_value = v["value"]
                    comment = None
                    reviewed = random.choice([
                        None,
                        True
                    ])
                    if is_completed:
                        reviewed = True

                    is_diff = fake.boolean()
                    if is_diff:
                        comment = fake.sentence(nb_words=8)
                        s_value = random.uniform(0, 100)

                    suggestion_values.append({
                        "administration_id": v["administration_id"],
                        "value": s_value,
                        "comment": comment,
                        "reviewed": reviewed,
                        "category": get_category(s_value),
                    })

                review.is_completed = is_completed
                review.suggestion_values = suggestion_values

                if is_completed:
                    completed_at = start_date + timedelta(
                        days=random.randint(0, (due_date - start_date).days)
                    )
                    review.is_completed = True
                    review.completed_at = timezone.make_aware(completed_at)

                review.save()

        if not settings.TEST_ENV:
            self.stdout.write(self.style.SUCCESS(
                "Fake publication generation complete!"
            ))
