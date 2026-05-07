<div align="center">

# Ghost Network Detection System

### Production-Grade Healthcare Compliance Pipeline on AWS

[![AWS](https://img.shields.io/badge/AWS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![AWS Glue](https://img.shields.io/badge/AWS_Glue-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/glue)
[![Amazon Athena](https://img.shields.io/badge/Athena-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/athena)
[![Amazon Bedrock](https://img.shields.io/badge/Bedrock-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/bedrock)
[![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://getdbt.com)
[![Step Functions](https://img.shields.io/badge/Step_Functions-FF4F8B?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/step-functions)
[![NetworkX](https://img.shields.io/badge/NetworkX-013243?style=for-the-badge&logo=python&logoColor=white)](https://networkx.org)

</div>

---

## Why This Project Exists

The Senate Finance Committee (May 2023) found that **80%+ of listed Medicare Advantage mental health providers were unreachable** when patients called. CMS 2025 mandates 90% directory accuracy compliance. CAQH estimates $2.8B/yr in directory maintenance burden across payers.

This project builds a production-grade ghost network detection system that ingests real government data, detects fake providers, classifies root causes, and generates AI compliance alerts — directly addressing the problem CMS is actively enforcing.

---

## Results

| Metric | Value |
|--------|-------|
| Providers scored | 380,000 across 56 states |
| HIGH risk ghost providers | 5,442 (1.4%) |
| Mental health ghost rate | 55.4% — 38x higher than average |
| Address mismatches detected | 234,664 |
| Deactivated NPIs still listed | 951 |
| Phantom providers (no NPPES record) | 7 |
| Shared phone clusters | 3,809 providers sharing one number |
| Root cause — data manipulation | 4,122 providers |
| Bedrock AI compliance alerts | 10 plain-English audit reports |
| dbt data quality tests | 11 / 11 passing |
| Graph nodes analyzed | 357,519 |

---

## Key Findings

**Finding 1 — Mental health providers have a 55.4% ghost rate** — 38x higher than the overall average. Directly confirms the Senate Finance Committee finding from real government data.

**Finding 2 — Nebraska has the worst state ghost rate at 6.7%** — Washington 4.1%, Alaska 3.5%.

**Finding 3 — ZIP code 92677 (Laguna Niguel, CA) has a 91.2% ghost rate** — 62 of 68 listed providers flagged HIGH risk. Geographic concentration of fraud detected only through graph analysis.

**Finding 4 — Phone number 212-263-9700 is listed for 3,809 different providers** — systematic pattern invisible to record-level checking, revealed by NetworkX graph analysis.

**Finding 5 — 75.7% of HIGH risk providers are classified as data manipulation** — not negligence, not data rot. Active manipulation of directory records.

---

## Architecture
DATA SOURCES (all public)
Transparency in Coverage JSON · NPPES Registry · CMS Medicare · State Medical Boards
↓
INGEST LAYER
EventBridge → Lambda → S3 raw bucket
↓
ETL LAYER
AWS Glue → Athena → dbt Silver models
↓
DETECTION ENGINE
5 ghost signals · address mismatch · specialty conflict · license expired · NPI collision · not accepting
↓
GRAPH INTELLIGENCE (NetworkX)
Fraud cluster detection · shared phone patterns · geographic concentration · root cause classification
↓
AI LAYER (Amazon Bedrock · Claude Haiku)
Plain-English compliance alerts with specific remediation recommendations
↓
ORCHESTRATION
AWS Step Functions · 5-step pipeline · weekly schedule
↓
OUTPUTS
dbt Gold models · Athena tables · FastAPI endpoint · Tableau dashboard
---

## AWS Stack

| Service | Role |
|---------|------|
| S3 | Raw + processed data lake |
| AWS Glue | ETL — normalize 5 payer schemas |
| Amazon Athena | Serverless SQL on S3 |
| Amazon Bedrock | Claude Haiku compliance alert generation |
| AWS Step Functions | Weekly pipeline orchestration |
| Lambda | Event-driven ingestion triggers |
| EventBridge | Scheduled pipeline execution |

---

## Data Sources

| Source | Records | Purpose |
|--------|---------|---------|
| NPPES NPI Registry | 8M+ providers | Ground truth — who is actually licensed |
| CMS Medicare Provider Data | 380,000 providers | What directories claim |
| State Medical Board APIs | 50 states | License status verification |
| CMS Audit + MA Enrollment | 5,000+ plans | Complaint patterns |

---

## Ghost Detection Signals

| Signal | Weight | What It Means |
|--------|--------|---------------|
| Address mismatch vs NPPES | 25 | Provider listed at wrong location |
| Specialty conflict same NPI | 25 | Different specialty in different systems |
| License expired / deactivated | 30 | NPI formally deactivated, still listed |
| NPI collision multiple addresses | 10 | Same NPI at 50+ locations |
| Not accepting patients | 10 | Listed as available but closed |

---

## dbt Models
models/gold/
├── gold_ghost_by_state.sql       — Ghost rate per US state
├── gold_ghost_by_specialty.sql   — Ghost rate per specialty
├── gold_high_risk_providers.sql  — All 5,442 HIGH risk providers
└── schema.yml                    — 11 data quality tests
**PASS=11 WARN=0 ERROR=0**

---

## Repository Structure
ghost-network-detection/
├── src/
│   ├── ingest_cms_providers.py   — CMS API → S3
│   ├── parse_nppes.py            — NPPES zip → silver layer
│   ├── detect_ghosts.py          — 5-signal ghost scoring
│   ├── graph_analysis.py         — NetworkX fraud patterns
│   ├── generate_alerts.py        — Bedrock AI alerts
│   ├── ghost_signals.py          — Signal definitions
│   └── api.py                    — FastAPI NPI lookup endpoint
├── dbt/                          — Gold layer SQL models
├── notebooks/
│   └── ghost_network_analysis.ipynb — 5 analyst findings
├── screenshots/
└── README.md
---

## Interview Talking Points

**Why graph analysis?**
Record-level checking finds individual mismatches. Graph analysis finds systematic patterns — 3,809 providers sharing one phone number is a billing mill pattern that only becomes visible when you map the relationships between providers, addresses, and contact information as a network.

**Why Bedrock for compliance alerts?**
Compliance officers act on sentences not numbers. A ghost score of 100 requires interpretation. Claude Haiku converts the quantitative signal — deactivated NPI, zip code mismatch, missing phone — into a specific, actionable compliance report with a recommended remediation timeline. That is the last-mile delivery problem in data products.

**Why dbt on AWS Athena?**
Version-controlled SQL with automated testing running on every pipeline execution. If risk_tier ever contains a value outside HIGH/MEDIUM/LOW the pipeline fails immediately. That's production-grade data quality discipline.

**Why Step Functions over Airflow?**
Airflow requires a running server. Step Functions is serverless — it costs nothing when idle and scales automatically. For a weekly pipeline with defined dependencies, Step Functions is the right AWS-native tool.

---

## Contact

**Navin Kumar Nagisetty** — Stamford, CT

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/navinnagisetty/)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:navinnagisetty@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Navinnagisetty)
