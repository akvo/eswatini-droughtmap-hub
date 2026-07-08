#!/usr/bin/env bash
# shellcheck disable=SC2155

if ! command -v gdal-config >/dev/null 2>&1; then
    echo "Installing system dependencies (GDAL)..."
    apt-get update -y && apt-get install -y --no-install-recommends libgdal-dev gdal-bin
fi

set -e
pip -q install --upgrade pip
pip -q install --no-cache-dir -r requirements.txt
pip check

if [[ -v FREEZE ]]; then
  tail -f /dev/null
fi

python manage.py qcluster