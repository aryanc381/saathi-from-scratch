#!/bin/bash
# Responsible for starting the API on Azure App Service. The ODBC Driver 18 for SQL Server must be installed on the host.
uvicorn app.main:app --host 0.0.0.0 --port 8000
