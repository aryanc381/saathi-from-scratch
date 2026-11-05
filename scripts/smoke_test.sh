#!/bin/bash
# Responsible for checking that a deployed Saathi answers: the API health, a demo login (which proves SQL works) and the web login page.
# Usage: scripts/smoke_test.sh <api-url> <web-url>
# The login check needs the demo data in SQL (run `make seed` once). This is a quick sanity check after a deploy;
# the full smoke path in the README is still run by a person.
set -euo pipefail

api_url=$1
web_url=$2

# Calls a URL and fails if it does not answer 2xx. A fresh deploy can take a few minutes to start
# (the API installs the ODBC driver first), so it retries for about 4 minutes.
check() {
  echo "checking $*"
  curl --fail --silent --show-error --retry 24 --retry-delay 10 --retry-all-errors --output /dev/null "$@"
}

check "$api_url/health"
check "$web_url/login"
check --request POST --header "Content-Type: application/json" \
  --data '{"agent_id": "A-01", "passcode": "saathi-demo"}' "$api_url/auth/login"

echo "smoke test passed"
