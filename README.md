# Ghost Network Detection System

> A patient in Nebraska calls 5 listed mental health providers from their insurance directory.
> None of them answer. Two numbers are disconnected. One doctor retired in 2019. One address is a vacant lot.
> This is called a ghost network — and it affects **57.6% of listed Medicare mental health providers nationwide.**
>
> This project detects them at scale.

---

<div align="center">

[![AWS](https://img.shields.io/badge/AWS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![AWS Glue](https://img.shields.io/badge/AWS_Glue-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/glue)
[![Athena](https://img.shields.io/badge/Athena-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/athena)
[![Bedrock](https://img.shields.io/badge/Bedrock-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/bedrock)
[![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://getdbt.com)
[![Step Functions](https://img.shields.io/badge/Step_Functions-FF4F8B?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/step-functions)
[![Tableau](https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=tableau&logoColor=white)](https://public.tableau.com/app/profile/navin.kumar.nagisetty/viz/GhostNetworkDetectionMedicareProviderAnalysis/GhostNetworkDetectionMedicareProviderDirectoryAnalysis)

</div>

---

## The Problem

In May 2023, the Senate Finance Committee investigated Medicare Advantage mental health access and found that **more than 80% of listed providers were unreachable** when patients called. Disconnected numbers. Wrong addresses. Retired doctors. Providers who never accepted the patients in the first place.

CMS responded with a 2025 mandate requiring 90% directory accuracy compliance — a standard most payers are currently failing. CAQH estimates the industry spends **$2.8 billion per year** just maintaining provider directories, yet the data remains unreliable.

The root cause is structural. Health insurers are legally required to publish provider directories, but verification is manual, infrequent, and inconsistent. A provider joins a network, their information enters a directory, and it may never be updated — even after they retire, move, lose their license, or die.

This project automates what CMS compliance officers currently do by hand.

---

## Live Dashboard

[![View Live Dashboard](https://img.shields.io/badge/View_Live_Dashboard-E97627?style=for-the-badge&logo=tableau&logoColor=white)](https://public.tableau.com/app/profile/navin.kumar.nagisetty/viz/GhostNetworkDetectionMedicareProviderAnalysis/GhostNetworkDetectionMedicareProviderDirectoryAnalysis)

---

## What This Project Found

Analyzing the full US Medicare provider directory — 2,857,460 providers across all 56 states and territories — against the NPPES government registry of 8 million licensed providers:

| Finding | Result |
|---------|--------|
| Mental health counselor ghost rate | **57.6%** — 38x higher than overall average |
| Psychiatry ghost rate | 7.6% |
| Providers with deactivated NPIs still listed | **6,900** |
| Providers with no NPPES record at all | **52** — phantom providers |
| Single phone number shared by most providers | **6,803 providers — one number** |
| Highest ghost rate ZIP code | ZIP 68065 Nebraska — **84.6%** |
| Address mismatches vs NPPES ground truth | **1,711,593 providers (59.9%)** |
| Root cause — credential churn | 28,061 providers |
| Root cause — address rot | 7,403 providers |
| Root cause — data manipulation | 1,258 providers |

The most striking finding is not the 57.6% mental health ghost rate — it is what that number means in practice. A Medicare Advantage patient in a rural state trying to find a mental health counselor may need to call **5 or more listed providers** before reaching one who is actually available, licensed, and accepting new patients.

---

## How It Works

### Data Sources

The project uses three entirely public, free government datasets — no proprietary data required.

**CMS Medicare Provider Directory** is the dataset that payers submit to CMS listing every in-network provider. This is what patients see when they search for a doctor. It contains 2,857,460 provider records covering all 56 US states and territories. This is the dataset being checked.

**NPPES NPI Registry** is the National Plan & Provider Enumeration System — the federal registry of every licensed healthcare provider in the United States. Every provider has a unique NPI number issued by CMS. NPPES is the ground truth: if a provider is licensed and practicing, they are in NPPES. We loaded 8 million records. This is the dataset doing the checking.

**State Medical Board Records** provide license status for each state. A provider whose license has expired or been revoked is a hard ghost signal regardless of what their address or phone says.

### The Detection Engine

Every provider in the CMS directory is scored against five ghost signals:

**Address mismatch** — the ZIP code listed by CMS does not match the ZIP code registered in NPPES for the same NPI. Weight: 25. Found in 1,711,593 providers.

**Missing street address** — no street address exists in the CMS listing. A provider with no address cannot be found. Weight: 20. Found in 16,666 providers.

**Specialty conflict** — CMS lists the provider as a psychiatrist but NPPES taxonomy shows a different specialty for the same NPI number. Weight: 25. Found in 55,038 providers.

**NPI deactivated** — the provider's NPI has been formally deactivated in the NPPES registry — meaning they are no longer licensed to practice — yet they continue appearing as active in the directory. Weight: 40. Found in 6,900 providers.

**Missing phone** — no phone number exists in the CMS listing. A provider with no phone cannot be called. Weight: 10. Found in 407,905 providers.

Each provider receives a ghost score from 0 to 100. Score ≥ 50 is HIGH risk. Score 25–49 is MEDIUM. Score < 25 is LOW.

### Graph Intelligence

The most important finding in this project — 6,803 providers sharing a single phone number — was invisible to the record-level detection engine. It only became visible when provider records were modeled as a graph.

NetworkX builds a graph where nodes represent providers, phone numbers, ZIP codes, and specialties. Edges connect each provider to their associated attributes. When you run cluster analysis on this graph, systematic patterns emerge that no row-by-row comparison can find:

- Phone numbers connected to thousands of providers signal billing clearinghouses or medical groups using centralized contact numbers
- ZIP codes with abnormally high ghost concentrations signal geographic fraud patterns
- NPIs appearing at multiple locations simultaneously signal identity reuse

This is the difference between finding individual errors and finding systematic fraud.

### AI Layer

The detection engine produces numbers. Compliance officers act on sentences.

Amazon Bedrock Claude Haiku receives the quantitative signal for each high-risk provider — deactivated NPI, ZIP mismatch, missing phone — and generates a plain-English compliance alert with a specific recommended action and timeline. The output is a report a compliance officer can act on immediately without reading a data dashboard.

This is not LLM decoration. Converting structured risk signals into actionable natural language recommendations is a genuine use case for language models that rule-based systems cannot replicate.

### Pipeline Orchestration

AWS Step Functions orchestrates the full pipeline as a 5-step weekly workflow: ingest CMS data, parse NPPES, detect ghosts, run graph analysis, generate Bedrock alerts. Each step is a Glue job. If any step fails, Step Functions routes to a failure state and the error is logged. The pipeline costs nothing when idle — Step Functions is serverless.

### Data Quality

Three dbt Gold models transform the detection output into validated, queryable tables: ghost rate by state, ghost rate by specialty, and the full high-risk provider list. Eleven automated data quality tests run on every pipeline execution. The tests enforce that risk_tier only contains HIGH, MEDIUM, or LOW — that ghost_score is never null — that state codes are unique per row. If any test fails, the pipeline stops.

**PASS=11 WARN=0 ERROR=0** on the full 2.8 million provider dataset.

---

## AWS Stack

| Service | Why It Earns Its Place |
|---------|----------------------|
| S3 | Data lake — raw CMS files, parsed NPPES, scored output, all separated by layer |
| AWS Glue | 6 Python shell ETL jobs — normalizes schemas, parses 1GB zip files, runs detection at scale |
| Amazon Athena | Serverless SQL on S3 — queries 2.8M providers without a running database cluster |
| Amazon Bedrock | Claude Haiku generates compliance alerts — not summarization but structured inference |
| Step Functions | Serverless weekly orchestration — no running server, costs nothing when idle |
| Lambda + EventBridge | Event-driven ingestion — triggered on schedule, not polling |
| NetworkX in Lambda | Graph analysis without Neptune — same capability at zero database cost |

---

## Repository Structure

```
ghost-network-detection/
├── src/
│   ├── ingest_cms_providers.py    — CMS API → S3 in paginated batches
│   ├── parse_nppes.py             — Unzip 1GB NPPES file → structured silver layer
│   ├── detect_ghosts.py           — 5-signal ghost scoring across 2.8M providers
│   ├── graph_analysis.py          — NetworkX cluster detection and root cause
│   ├── generate_alerts.py         — Bedrock compliance alert generation
│   ├── ghost_signals.py           — Signal definitions, weights, scoring logic
│   └── api.py                     — FastAPI real-time NPI ghost score lookup
├── dbt/
│   ├── gold_ghost_by_state.sql
│   ├── gold_ghost_by_specialty.sql
│   ├── gold_high_risk_providers.sql
│   └── schema.yml                 — 11 data quality tests
├── notebooks/
│   └── ghost_network_analysis.ipynb — 5 hypothesis-driven analyst findings
├── screenshots/
└── README.md
```

---

## Analyst Findings

Beyond the engineering pipeline, five hypothesis-driven findings are documented in the analyst notebook:

**Hypothesis 1** — Mental health providers have a significantly higher ghost rate than other specialties. Confirmed at 57.6% vs 1.3% overall.

**Hypothesis 2** — Ghost rates cluster geographically rather than distributing uniformly. Confirmed — ZIP 68065 at 84.6% vs national average of 1.3%.

**Hypothesis 3** — Providers not found in NPPES at all represent the most severe ghost category. Confirmed — 52 providers have no federal record of ever existing.

**Hypothesis 4** — Ghost score distribution is bimodal — providers are either clean or severely flagged. Confirmed — scores cluster near 0 and near 100 with few in between.

**Hypothesis 5 — Member Impact Calculator** — In the worst-affected states, a patient must call an average of 5+ listed mental health providers before reaching one who is actually available, licensed, and accepting new patients.

---

## Limitations

Every honest project acknowledges what it does not do. These are the meaningful gaps between this implementation and a production system.

**Phone verification is not implemented.** The most direct ghost test — calling the number — is absent. A production system would integrate with a phone verification API such as Twilio or Numverify to confirm whether listed numbers connect to an active medical practice. This single addition would dramatically improve detection precision.

**Address matching is ZIP-level, not geocoded.** Ghost signal 1 compares ZIP codes rather than full street addresses. Two providers with the same ZIP but genuinely different addresses would trigger a false positive. A production system would geocode full addresses and compute distance-based mismatch with a configurable threshold.

**Specialty matching is keyword-based, not taxonomy-mapped.** The specialty conflict signal uses keyword matching against NPPES taxonomy codes rather than the official CMS-to-NUCC taxonomy crosswalk. False positives occur where specialties are described differently across systems but represent the same clinical role.

**No actual payer directory data.** This project uses the CMS Medicare Provider Directory as a proxy for what insurers publish. A genuine ghost network detection system would ingest the Transparency in Coverage machine-readable files that payers are required to publish — which are terabytes of JSON and represent the actual directories patients use. The CMS data approximates but does not replicate payer directory submissions.

**Graph analysis is in-memory, not persistent.** NetworkX loads the full dataset into memory for each run. A production system serving real-time graph queries would use Amazon Neptune or Neo4j for persistent graph storage with millisecond-latency traversal queries and the ability to update the graph incrementally rather than rebuilding it weekly.

**Step Functions does not checkpoint.** If the CMS API goes down mid-ingestion, the pipeline fails and restarts from the beginning. A production system would implement checkpoint-based restarts — tracking the last successfully processed batch and resuming from there rather than re-ingesting everything.

---

## Interview Talking Points

**Why graph analysis?**
Record-level checking finds individual mismatches. Graph analysis finds systematic patterns. 6,803 providers sharing one phone number is a billing clearinghouse pattern — it is not visible in any row-by-row comparison. Only when you model providers, phones, and addresses as a connected graph does the cluster become detectable. That is the fundamental difference between data quality checking and fraud pattern detection.

**Why NetworkX instead of Amazon Neptune?**
Neptune costs $0.10 per hour — $72 per month just to keep it running. For a weekly batch pipeline, that is an expensive always-on resource for a workload that runs four times per month. NetworkX handles 2.8 million records in memory in under 60 seconds. The engineering judgment here is matching tool cost to workload pattern, not defaulting to the managed service.

**Why Bedrock for compliance alerts?**
The ghost score is a number. Compliance officers act on sentences. Claude Haiku receives the structured signal — deactivated NPI since 2019, ZIP mismatch, no phone — and generates a specific actionable recommendation with a timeline. That conversion from quantitative output to natural language action item is exactly the workload language models are suited for. It is not decoration.

**Why dbt on Athena?**
Version-controlled SQL with automated tests running on every pipeline execution. If risk_tier ever contains a value outside HIGH, MEDIUM, or LOW — because of a schema change upstream or a bug in the detection logic — the pipeline fails immediately. That is production-grade data quality discipline. Notebooks with raw SQL queries have no equivalent guarantee.

**Why Step Functions over Airflow?**
Airflow requires a running server — even when no jobs are executing. Step Functions is serverless. For a weekly pipeline, the choice between a server that runs 24/7 and an orchestrator that activates on schedule is straightforward. Step Functions is also natively integrated with Glue, which eliminates the custom operators Airflow would require for the same workflow.

---

## Resume Bullets

**Data Engineering role:**
Built ghost network detection system on AWS processing full CMS Medicare Provider Directory (2.86M providers) against NPPES ground truth (8M records) using AWS Glue ETL, Athena serverless SQL, and NetworkX graph analysis; detected 6,900 deactivated NPIs still listed as active and 6,803 providers sharing one phone number — patterns invisible to record-level checking; used Amazon Bedrock Claude Haiku to generate plain-English compliance alerts; validated with dbt (11/11 tests passing) and orchestrated via Step Functions weekly pipeline.

**Data Analyst role:**
Analyzed full US Medicare provider directory (2.86M providers) across 56 states; found mental health counselors have a 57.6% HIGH risk ghost rate — 38x higher than overall average; identified geographic fraud concentration (84.6% ghost rate in ZIP 68065 Nebraska); computed member impact showing patients may contact 5+ listed providers before reaching one who is available and accepting patients; published findings in live Tableau dashboard.

---

## Contact

**Navin Kumar Nagisetty** — Stamford, CT

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/navinnagisetty/)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:navinnagisetty@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Navinnagisetty)
[![Dashboard](https://img.shields.io/badge/Live_Dashboard-E97627?style=for-the-badge&logo=tableau&logoColor=white)](https://public.tableau.com/app/profile/navin.kumar.nagisetty/viz/GhostNetworkDetectionMedicareProviderAnalysis/GhostNetworkDetectionMedicareProviderDirectoryAnalysis)
