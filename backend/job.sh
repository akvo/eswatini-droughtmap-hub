#!/usr/bin/env bash
set -e

# Single Rundeck entry point — the task argument is REQUIRED so a
# mis-configured job fails loudly instead of running the wrong thing.
#   ./job.sh reviews                      overdue-review notifications
#   ./job.sh weather [--from YYYY-MM-DD]  daily WIS2 ingestion (WX-1);
#                                         --from backfills a window
#   ./job.sh cdi [--publication ID]       retry CDI extraction for
#                                         publications with empty
#                                         initial_values (GeoNode was down)
#   ./job.sh cs-reminders                 monthly citizen-science reminders
#                                         (WX-6; schedule 1st of month 07:00)
TASK="${1:-}"
shift || true

case "$TASK" in
  reviews)
    ./manage.py check_overdue_reviews "$@"
    ;;
  weather)
    ./manage.py fetch_weather_observations "$@"
    ;;
  rasters)
    ./manage.py attach_component_rasters "$@"
    ;;
  cdi)
    ./manage.py retry_cdi_extraction "$@"
    ;;
  cs-reminders)
    ./manage.py send_cs_reminders "$@"
    ;;
  precipitation)
    # No argument: defaults to the latest published month, which is the month
    # the Precipitation tab asks for. Skips instantly if already stored, and
    # exits 0 while CHIRPS has not published the month yet — africa_monthly
    # lags the month end by a few weeks, so a daily run is what actually
    # catches it, and every other day is a single file-exists check.
    ./manage.py fetch_chirps_monthly "$@"
    ;;
  *)
    echo "Usage: $0 {reviews|weather|rasters|cdi|cs-reminders|precipitation} [extra args]" >&2
    exit 1
    ;;
esac
