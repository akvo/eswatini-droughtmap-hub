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
#   ./job.sh dataset-uploads              fetch provider files from the
#                                         GeoNode dataset categories (PA-6)
#   ./job.sh confidence [--period YYYY-MM] AgERA5 satellite Tmax for the
#                                         confidence score (WX-11; monthly,
#                                         10th) — default: previous month
#   ./job.sh chirps-observations          CHIRPS mm per Inkhundla for the
#                                         satellite-difference card (WX-10;
#                                         monthly, 20th)
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
  dataset-uploads)
    # Fetches files providers published to the GeoNode dataset
    # categories, validates them and STOPS at validated: the operator
    # still confirms the diff in admin (PA-6 D-3). Idempotent — dedupe
    # is on file content — so a missed run costs nothing.
    #
    # Scheduled daily at midnight as a PROVISIONAL default: no partner has
    # told us how often they will publish yet. These datasets refresh a few
    # times a year, so daily is generous; revisit once DWA/JRBA/CSO say what
    # their actual cadence is. A run that finds nothing is one catalogue read
    # per category.
    ./manage.py fetch_dataset_uploads "$@"
    ;;
  confidence)
    # The satellite temperature half of the confidence score: one CDS
    # request per month, monthly mean of the daily 24 h maximum per
    # Inkhundla into AdministrationObservation(parameter="tmax"). AgERA5
    # lags real time by ~8 days, so the 10th is the first safe day for the
    # previous month; the upsert is idempotent and --from/--to backfill.
    # The score itself stays derived at read time (WX-11 D-3).
    ./manage.py fetch_agera5_observations "$@"
    ;;
  chirps-observations)
    # NOT `precipitation` above: that one keeps a raster window for the
    # National overview map; this one writes per-Inkhundla mm rows for the
    # station-vs-satellite card (WX-10). Default range re-fetches every
    # month since the first station reading (idempotent), so a CHIRPS month
    # published late is picked up on the next monthly tick.
    ./manage.py fetch_chirps_observations "$@"
    ;;
  *)
    echo "Usage: $0 {reviews|weather|rasters|cdi|cs-reminders|precipitation|dataset-uploads|confidence|chirps-observations} [extra args]" >&2
    exit 1
    ;;
esac
