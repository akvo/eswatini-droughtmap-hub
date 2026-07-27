import re
from pathlib import Path
from types import SimpleNamespace
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Jobs, JobTypes, JobStatus
from .job import job_done_hook


class JobAPITestCase(APITestCase):
    def setUp(self):
        """
        Set up initial data for the tests.
        """
        self.job = Jobs.objects.create(
            type=JobTypes.test, status=JobStatus.done, result="Sample Job"
        )

    def test_view_job_success(self):
        """
        Test fetching an existing job by ID.
        """
        url = reverse(
            "view_job", kwargs={"version": "v1", "job_id": self.job.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.job.id)
        self.assertEqual(response.data["result"], self.job.result)

    def test_view_job_not_found(self):
        """
        Test fetching a job that does not exist.
        """
        url = reverse("view_job", kwargs={"version": "v1", "job_id": 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_job_success(self):
        """
        Test creating a new job with a valid name.
        """
        url = reverse("create_job", kwargs={"version": "v1"})
        response = self.client.get(url, {"name": "Test Job"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the job is created in the database
        job_id = response.data["job_id"]
        created_job = Jobs.objects.get(pk=job_id)
        self.assertEqual(created_job.result, "Test Job")
        self.assertEqual(created_job.type, JobTypes.test)
        self.assertEqual(created_job.status, JobStatus.on_progress)

    def test_create_job_missing_name(self):
        """
        Test creating a new job without providing a name.
        """
        url = reverse("create_job", kwargs={"version": "v1"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_job_done_hook_marks_done(self):
        """job_done_hook marks the linked Job done on task success."""
        job = Jobs.objects.create(
            task_id="task-abc",
            type=JobTypes.test,
            status=JobStatus.pending,
        )
        task = SimpleNamespace(id="task-abc", success=True, result="ok")
        job_done_hook(task)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.done)
        self.assertEqual(job.result, "ok")
        self.assertEqual(job.attempt, 1)

    def test_job_done_hook_marks_failed(self):
        """job_done_hook marks the linked Job failed on task failure."""
        job = Jobs.objects.create(
            task_id="task-fail",
            type=JobTypes.test,
            status=JobStatus.pending,
        )
        task = SimpleNamespace(id="task-fail", success=False, result="boom")
        job_done_hook(task)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.failed)

    def test_job_done_hook_missing_job_is_noop(self):
        """job_done_hook silently returns when no Job matches the task."""
        task = SimpleNamespace(id="no-such-task", success=True, result="ok")
        # Should not raise
        job_done_hook(task)

    def test_feedback_success(self):
        """
        Test submitting feedback successfully.
        """
        url = reverse("feedback", kwargs={"version": "v1"})
        response = self.client.post(
            url,
            {
                "email": "visitor@mail.com",
                "feedback": "This is a test feedback",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Feedback received successfully"
        )


class CronJobScriptTestCase(SimpleTestCase):
    """
    The crontab and job.sh drift apart silently: cron only logs the usage
    error to cron.log, so a task name that job.sh does not accept means the
    scheduled command never runs and nobody is told. This happened once
    already, when job.sh gained a required task argument while the crontab
    still invoked it bare.
    """

    base_dir = Path(settings.BASE_DIR)

    def _job_sh_tasks(self):
        # Task names are the case-branch labels in job.sh, e.g. "  reviews)".
        job_sh = (self.base_dir / "job.sh").read_text()
        return set(re.findall(r"^\s*([\w-]+)\)", job_sh, re.MULTILINE))

    def _cron_tasks(self):
        cron = (self.base_dir / "eswatini-cron").read_text()
        return re.findall(r"job\.sh\s*(\S*)", cron)

    def test_every_cron_task_is_handled_by_job_sh(self):
        known = self._job_sh_tasks()
        self.assertIn("reviews", known)
        for task in self._cron_tasks():
            # A bare "./job.sh" (task == "") hits the usage branch and exits 1.
            self.assertIn(
                task,
                known,
                f"crontab calls './job.sh {task}', which job.sh does not "
                f"handle (known tasks: {sorted(known)}).",
            )

    # Tasks job.sh handles on purpose without a crontab entry yet. "rasters"
    # backfills missing component rasters across every publication; the first
    # production sweep is meant to be run by hand and watched, with the
    # crontab entry following in a separate commit. Remove from this set when
    # it is scheduled.
    unscheduled_by_design = {"rasters"}

    def test_every_job_sh_task_is_scheduled(self):
        scheduled = set(self._cron_tasks())
        for task in self._job_sh_tasks() - self.unscheduled_by_design:
            self.assertIn(
                task,
                scheduled,
                f"job.sh handles '{task}' but no crontab entry runs it.",
            )

    def test_job_sh_never_schedules_the_demo_seeder(self):
        # publications_seeder creates publications already marked published,
        # with validated_values copied from initial_values — a homepage demo
        # bypass, not a sync job. Scheduling it would auto-publish every
        # GeoNode CDI raster with no review. The retry path is the
        # attach_component_rasters command, which only adds raster rows.
        job_sh = (self.base_dir / "job.sh").read_text()
        self.assertNotIn("publications_seeder", job_sh)
        self.assertNotIn(
            "publications_seeder",
            (self.base_dir / "eswatini-cron").read_text(),
        )
