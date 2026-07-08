#!/bin/sh
set -eu

if ! command -v gdal-config >/dev/null 2>&1; then
    echo "Installing system dependencies (GDAL)..."
    apt-get update -y && apt-get install -y --no-install-recommends libgdal-dev gdal-bin
fi

pip -q install --upgrade pip
pip -q install --cache-dir=.pip -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
