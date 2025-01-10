#!/usr/bin/env bash
#shellcheck disable=SC3040

set -euo pipefail

pip -q install --upgrade pip
pip -q install --cache-dir=.pip -r requirements.txt

./manage.py migrate

echo "Running tests"
COVERAGE_PROCESS_START=./.coveragerc \
    coverage run --parallel-mode --concurrency=multiprocessing --rcfile=./.coveragerc \
    ./manage.py test --shuffle --parallel 4

echo "Coverage"
coverage combine --rcfile=./.coveragerc
coverage report -m --rcfile=./.coveragerc

if [[ -n "${COVERALLS_REPO_TOKEN:-}" ]]; then
     # Allow Git to traverse filesystems
    export GIT_DISCOVERY_ACROSS_FILESYSTEM=1

    # Mark the backend directory's root as safe for Git
    GIT_ROOT=$(git rev-parse --show-toplevel)
    git config --global --add safe.directory "$GIT_ROOT"

    # Debugging to ensure Git is configured correctly
    echo "Git root: $GIT_ROOT"
    echo "Safe directories: $(git config --global --get-all safe.directory)"

    # Run Coveralls
    coveralls --verbose
fi

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
