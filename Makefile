# Load your env first:  set -a; source .env; set +a
.PHONY: generate deploy-infra seed

# Regenerates the synthetic data and policy PDFs (deterministic).
generate:
	python data/generate.py

# Creates every Azure resource. Needs RG, SQL_ADMIN_PASSWORD and JWT_SECRET.
deploy-infra:
	az deployment group create -g $(RG) -f infra/main.bicep -p @infra/parameters.json sqlAdminPassword=$(SQL_ADMIN_PASSWORD) jwtSecret=$(JWT_SECRET)

# Loads SQL, uploads the PDFs, then builds the search index and indexer.
seed:
	python data/seed/load_sql.py
	python data/seed/upload_blob.py
	python data/seed/create_index.py
