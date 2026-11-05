#!/bin/bash
# Responsible for starting the API on Azure App Service.
# It first installs the ODBC Driver 18 for SQL Server if it is missing.
set -e

if ! odbcinst -q -d -n "ODBC Driver 18 for SQL Server" > /dev/null 2>&1; then
  # Reads the Debian version of this container (VERSION_ID, VERSION_CODENAME) to pick the right Microsoft package list.
  . /etc/os-release
  apt-get update
  apt-get install -y curl gnupg
  curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg
  microsoft_url="https://packages.microsoft.com/debian/${VERSION_ID}/prod"
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] ${microsoft_url} ${VERSION_CODENAME} main" \
    > /etc/apt/sources.list.d/mssql-release.list
  apt-get update
  ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
fi

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
