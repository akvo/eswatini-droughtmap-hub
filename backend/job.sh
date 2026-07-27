#!/usr/bin/env bash
set -e

# Single Rundeck entry point — the task argument is REQUIRED so a
# mis-configured job fails loudly instead of running the wrong thing.
#   ./job.sh reviews                      overdue-review notifications
#   ./job.sh weather [--from YYYY-MM-DD]  daily WIS2 ingestion (WX-1);
#                                         --from backfills a window
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
  cs-reminders)
    ./manage.py send_cs_reminders "$@"
    ;;
  *)
    echo "Usage: $0 {reviews|weather|rasters|cs-reminders} [extra args]" >&2
    exit 1
    ;;
esac
