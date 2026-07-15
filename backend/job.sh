#!/usr/bin/env bash
set -e

# Single Rundeck entry point — the task argument is REQUIRED so a
# mis-configured job fails loudly instead of running the wrong thing.
#   ./job.sh reviews                      overdue-review notifications
#   ./job.sh weather [--from YYYY-MM-DD]  daily WIS2 ingestion (WX-1);
#                                         --from backfills a window
TASK="${1:-}"
shift || true

case "$TASK" in
  reviews)
    ./manage.py check_overdue_reviews "$@"
    ;;
  weather)
    ./manage.py fetch_weather_observations "$@"
    ;;
  *)
    echo "Usage: $0 {reviews|weather} [extra args]" >&2
    exit 1
    ;;
esac
