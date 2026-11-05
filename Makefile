# Responsible for the short commands to generate data, train the ML models, deploy Azure and seed it.
# Load your env first:  set -a; source .env; set +a
.PHONY: generate train deploy-infra seed

# Regenerates the synthetic data and policy PDFs (deterministic).
generate:
	python data/generate.py

# Trains the intent classifier and the Renewal Radar model into ml/artifacts.
train:
	python -m ml.intent.train
	python -m ml.radar.train

# Creates every Azure resource. Needs RG, SQL_ADMIN_PASSWORD and JWT_SECRET.
deploy-infra:
	az deployment group create -g $(RG) -f infra/bicep/main.bicep -p @infra/params/parameters.json sqlAdminPassword=$(SQL_ADMIN_PASSWORD) jwtSecret=$(JWT_SECRET)

# Loads SQL, uploads the PDFs, then builds the search index and indexer.
seed:
	python data/seed/scripts/load_sql.py
	python data/seed/scripts/upload_blob.py
	python data/seed/scripts/create_index.py
