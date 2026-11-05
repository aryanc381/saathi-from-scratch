# 02. Connect Saathi to real Azure

The first real run. About 1 to 2 hours, mostly waiting for Azure. Nothing here has been tried on real Azure yet, so expect to fix small things. Write them down.

## The journey

```mermaid
flowchart TD
    S1["1 Sign in"] --> S2["2 Check quotas"]
    S2 --> S3["3 Resource group"]
    S3 --> S4["4 make deploy-infra"]
    S4 --> S5["5 Fill .env"]
    S5 --> S6["6 SQL firewall"]
    S6 --> S7["7 make seed"]
    S7 --> S8["8 Check the search index"]
    S8 --> S9["9 ML models<br/>optional first"]
    S9 --> S10["10 Point the API at ML"]
    S8 --> S11["11 Deploy the code"]
    S10 --> S11
    S11 --> S12["12 Verify"]
    S12 --> G3["Guide 03: smoke tests"]
    G3 --> S13["13 Tear down"]
```

Steps 9 and 10 can wait. The API works with `ML_PROVIDER=local` until you do them.

## What gets created

```mermaid
flowchart TB
    subgraph RG["Resource group saathi-from-scratch-rg, centralus"]
        WEB["App Service web<br/>Blazor UI"]
        API["App Service API<br/>FastAPI"]
        KV["Key Vault<br/>5 secrets"]
        SQL[("Azure SQL Basic")]
        SRCH["AI Search Basic<br/>index policy_chunks"]
        BLOB[("Blob Storage<br/>policies container")]
        AI["Foundry<br/>gpt-4.1-mini and<br/>text-embedding-3-small"]
        ML["Azure ML workspace"]
        MON["Log Analytics and<br/>Application Insights"]
    end
    WEB --> API
    API --> SQL
    API --> SRCH
    API --> AI
    API -.->|"after step 9"| ML
    API -->|"Key Vault references"| KV
    BLOB -->|"indexer + skillset"| SRCH
    SRCH -->|"embeddings"| AI
    ML --> MON
```

Names get a 6-character suffix, for example `saathifs-api-x7k2pq`. You read them from the deploy output in step 4.

## Where secrets live

```mermaid
flowchart LR
    ENV[".env on your laptop<br/>gitignored"] --> U1["make seed, ML scripts,<br/>local API"]
    KV["Key Vault"] --> U2["deployed API<br/>reads at startup"]
    GH["GitHub secrets"] --> U3["cd.yml"]
    NEVER["git history"] -.->|"never"| X["no secret goes here"]
```

---

## Steps

### 1. Sign in

```bash
az login
az account set --subscription "<your subscription id>"
az extension add --name ml
```

### 2. Check quotas

In the Azure AI Foundry portal, Management, Quota, region **Central US**. You need:

| Item | Needed |
|---|---|
| `gpt-4.1-mini`, GlobalStandard | 50K tokens per minute |
| `text-embedding-3-small`, Standard | 50K tokens per minute |
| Azure ML, `Standard_D2a_v4` | 2 instances of 2 cores (step 9) |

If a quota is missing, change the region or the numbers in `infra/params/parameters.json` before step 4.

### 3. Create the resource group

```bash
export RG=saathi-from-scratch-rg
az group create --name $RG --location centralus
```

### 4. Create the resources

In `.env` set `RG`, `SQL_ADMIN_PASSWORD` and `JWT_SECRET` (the JWT_SECRET is 32+ characters). The SQL password needs upper case, lower case, a digit and a symbol, but **no** `;`, `=`, `{` or `}`, because it goes into a connection string.

```bash
set -a; source .env; set +a
make deploy-infra          # 10 to 15 minutes
```

Then read the names:

```bash
az deployment group show --resource-group $RG --name main --query properties.outputs --output yaml
```

| Output | You will use it as |
|---|---|
| `apiUrl`, `webUrl` | the two sites |
| `foundryEndpoint` | `AZURE_OPENAI_ENDPOINT`; the name is the part before `.openai.azure.com` |
| `searchEndpoint` | `AZURE_SEARCH_ENDPOINT`; the name is the part before `.search.windows.net` |
| `sqlServer` | in the SQL connection string; the server name is the part before `.database.windows.net` |
| `storageAccount`, `mlWorkspace` | in the commands below |

```mermaid
flowchart TD
    D["make deploy-infra"] --> OK{"Succeeded?"}
    OK -->|yes| N["Read the outputs"]
    OK -->|no| E["Read the error"]
    E --> Q["Quota or region?<br/>change parameters.json"]
    E --> NM["Name already taken?<br/>wait or use another resource group"]
    E --> P["SQL password rejected?<br/>fix the characters"]
    Q --> D
    NM --> D
    P --> D
```

### 5. Fill `.env`

| Variable | Value / command |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | the `foundryEndpoint` output |
| `AZURE_OPENAI_API_KEY` | `az cognitiveservices account keys list --resource-group $RG --name <foundry name> --query key1 --output tsv` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | `gpt-4.1-mini` |
| `AZURE_OPENAI_EMBED_DEPLOYMENT` | `text-embedding-3-small` |
| `AZURE_SEARCH_ENDPOINT` | the `searchEndpoint` output |
| `AZURE_SEARCH_ADMIN_KEY` | `az search admin-key show --resource-group $RG --service-name <search name> --query primaryKey --output tsv` |
| `AZURE_SEARCH_INDEX_NAME` | `policy_chunks` |
| `AZURE_STORAGE_CONNECTION_STRING` | `az storage account show-connection-string --resource-group $RG --name <storageAccount> --query connectionString --output tsv` |
| `SQL_CONNECTION_STRING` | `"Driver={ODBC Driver 18 for SQL Server};Server=tcp:<sqlServer>,1433;Database=saathifs;Uid=saathiadmin;Pwd=<SQL_ADMIN_PASSWORD>;Encrypt=yes;TrustServerCertificate=no;"` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id --output tsv` |
| `AZURE_RESOURCE_GROUP` | `saathi-from-scratch-rg` |
| `AZURE_ML_WORKSPACE` | the `mlWorkspace` output |

Set the three mode switches to `azure`, `azure` and `local` for now. Never commit `.env`.

### 6. Open the SQL firewall for your IP

```bash
MY_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create --resource-group $RG --server <sql server name> \
  --name my-ip --start-ip-address $MY_IP --end-ip-address $MY_IP
```

### 7. Load the data

```bash
pip install -r data/requirements.txt
set -a; source .env; set +a
make seed
```

```mermaid
flowchart LR
    M["make seed"] --> A["load_sql.py<br/>schema and demo rows"]
    A --> B["upload_blob.py<br/>13 PDFs"]
    B --> C["create_index.py<br/>index, data source,<br/>skillset, indexer"]
    A --> SQL[("SQL")]
    B --> BL[("Blob")]
    C --> SR["Search"]
    SR -->|"starts a run"| IX["indexer reads the PDFs"]
```

Expect SQL: 3 agents, 6 customers, 6 policies, 18 interactions. Blob container `policies`: 13 PDFs.

### 8. Check the search index

```bash
curl -s -H "api-key: $AZURE_SEARCH_ADMIN_KEY" \
  "$AZURE_SEARCH_ENDPOINT/indexers/policies-indexer/status?api-version=2024-07-01"
curl -s -H "api-key: $AZURE_SEARCH_ADMIN_KEY" \
  "$AZURE_SEARCH_ENDPOINT/indexes/policy_chunks/docs/\$count?api-version=2024-07-01"
```

The status should end `success`, and the count should be **13**. If the count is 0, look at the errors in the status reply.

```mermaid
flowchart TD
    C["Index count"] --> Z{"13?"}
    Z -->|yes| OK["Good"]
    Z -->|0| E1["Indexer failed:<br/>read errors in the status reply"]
    Z -->|other| E2["Some PDFs failed:<br/>check the skillset and the embedding deployment name"]
```

### 9. ML models (can wait)

```bash
pip install -r ml/requirements.txt
make train
python ml/azureml/scripts/register.py
python ml/azureml/scripts/deploy.py      # 10 to 20 minutes per endpoint; they cost money while running
```

```mermaid
flowchart LR
    T["make train"] --> R["register.py"]
    R --> D["deploy.py"]
    D --> E1["saathi-intent-ep"]
    D --> E2["saathi-radar-ep"]
    E1 --> K["az ml online-endpoint<br/>get-credentials"]
    E2 --> K
```

Get each endpoint's URL and key:

```bash
az ml online-endpoint show --name saathi-intent-ep --resource-group $RG --workspace-name $AZURE_ML_WORKSPACE --query scoring_uri --output tsv
az ml online-endpoint get-credentials --name saathi-intent-ep --resource-group $RG --workspace-name $AZURE_ML_WORKSPACE
```

Repeat for `saathi-radar-ep`. Try the intent endpoint once:

```bash
echo '{"text": "when does my policy renew?"}' > /tmp/request.json
az ml online-endpoint invoke --name saathi-intent-ep --resource-group $RG --workspace-name $AZURE_ML_WORKSPACE --request-file /tmp/request.json
```

You should get `{"label": "renewal", "confidence": ...}`.

### 10. Point the API at the ML endpoints

The deployed API starts with `ML_PROVIDER=local`. After step 9, switch it:

```bash
az webapp config appsettings set --resource-group $RG --name <api app name> --settings \
  ML_PROVIDER=azure INTENT_ENDPOINT_URL=<url> INTENT_ENDPOINT_KEY=<key> \
  RADAR_ENDPOINT_URL=<url> RADAR_ENDPOINT_KEY=<key>
```

### 11. Deploy the code

```mermaid
flowchart LR
    SP["1 Create a service principal"] --> SEC["2 Add 3 GitHub secrets"]
    SEC --> RUN["3 Run the CD workflow"]
    RUN --> A["Deploy API"]
    RUN --> B["Deploy web"]
    A --> SM["Smoke check"]
    B --> SM
```

```bash
az ad sp create-for-rbac --name saathi-cd --role contributor \
  --scopes /subscriptions/<subscription id>/resourceGroups/$RG --sdk-auth > credentials.json
gh secret set AZURE_CREDENTIALS --repo aryanc381/saathi-from-scratch < credentials.json
gh secret set AZURE_WEBAPP_NAME_API --repo aryanc381/saathi-from-scratch --body "<api app name>"
gh secret set AZURE_WEBAPP_NAME_WEB --repo aryanc381/saathi-from-scratch --body "<web app name>"
rm credentials.json
gh workflow run CD --repo aryanc381/saathi-from-scratch
gh run watch --repo aryanc381/saathi-from-scratch
```

The first start of the API takes 1 to 2 minutes, because `startup.sh` installs the ODBC driver.

### 12. Verify

```bash
scripts/smoke_test.sh <apiUrl> <webUrl>
```

It checks the API health, a demo login (which proves SQL works) and the web login page. Then do [guide 03](03-e2e-smoke-tests.md).

### 13. Tear down

```bash
scripts/teardown.sh saathi-from-scratch-rg     # asks you to type the group name
az ad sp delete --id <the appId in credentials.json>
```

Also delete the three GitHub secrets. The ML endpoints and AI Search Basic are the parts that cost the most while idle.

---

## When the deployed site misbehaves

```mermaid
flowchart TD
    P["Something is wrong"] --> W{"Which part?"}
    W -->|"web page will not load"| W1["Web app log stream:<br/>is API_URL set?"]
    W -->|"login fails"| L1{"Health OK?"}
    L1 -->|no| H1["API did not start:<br/>log stream, ODBC install, missing setting"]
    L1 -->|yes| L2["SQL: firewall, seed not run,<br/>wrong connection string"]
    W -->|"chat says service unavailable"| C1["Foundry or Search:<br/>keys, endpoint, deployment names,<br/>read the API log for the URL"]
    W -->|"chat says search_misconfigured"| C2["PDF names or text<br/>do not follow the rules"]
    W -->|"radar says unavailable"| R1["ML endpoint:<br/>ML_PROVIDER, URL, key"]
```

| Symptom | Look at |
|---|---|
| API will not start | `az webapp log tail --resource-group $RG --name <api app name>` |
| `KeyError` in the log | an app setting is missing |
| `Can't open lib 'ODBC Driver 18'` | the startup install failed; check the log for `apt-get` |
| Key Vault reference shows as text | the API's identity has no access yet; restart the app |
| Blazor page loads but is dead | WebSockets off on the web app (the Bicep turns them on) |

Next: [03 End-to-end smoke tests](03-e2e-smoke-tests.md).
