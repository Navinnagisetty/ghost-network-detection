"""
Ghost Network Detection — FastAPI Endpoint
Real-time ghost score lookup by NPI number
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import json
from functools import lru_cache

app = FastAPI(
    title="Ghost Network Detection API",
    description="Real-time provider ghost score lookup — detecting fake doctors in insurance directories",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

S3_BUCKET = "ghost-network-detection-raw"
SCORES_KEY = "processed/gold/ghost_scores/ghost_scores_all.json"

@lru_cache(maxsize=1)
def load_ghost_scores():
    """Load ghost scores from S3 — cached in memory"""
    print("Loading ghost scores from S3...")
    s3 = boto3.client("s3", region_name="us-east-1")
    data = json.loads(
        s3.get_object(Bucket=S3_BUCKET, Key=SCORES_KEY)["Body"].read()
    )
    # Build NPI lookup index
    index = {r["npi"]: r for r in data}
    print(f"Loaded {len(index):,} provider records")
    return index

@app.get("/")
def root():
    return {
        "name": "Ghost Network Detection API",
        "version": "1.0.0",
        "description": "Detecting fake providers in health insurance directories",
        "endpoints": {
            "/score/{npi}": "Get ghost score for a provider by NPI",
            "/stats": "Get overall detection statistics",
            "/high-risk": "Get top high risk providers",
            "/health": "Health check"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/score/{npi}")
def get_ghost_score(npi: str):
    """Get ghost score for a specific provider by NPI number"""
    index = load_ghost_scores()

    if npi not in index:
        raise HTTPException(
            status_code=404,
            detail=f"NPI {npi} not found in directory database"
        )

    record = index[npi]
    return {
        "npi": npi,
        "provider_name": record.get("provider_name", ""),
        "specialty": record.get("specialty", ""),
        "location": {
            "city": record.get("city", ""),
            "state": record.get("state", ""),
            "zip": record.get("zip", "")
        },
        "ghost_score": record.get("ghost_score", 0),
        "risk_tier": record.get("risk_tier", ""),
        "signals_triggered": record.get("signals_triggered", 0),
        "signal_details": record.get("signal_details", []),
        "found_in_nppes": record.get("in_nppes", False),
        "interpretation": {
            "HIGH": "Critical — provider likely unreachable, immediate action required",
            "MEDIUM": "Elevated — provider data has discrepancies, verification needed",
            "LOW": "Normal — provider data appears consistent across sources"
        }.get(record.get("risk_tier", "LOW"), "Unknown")
    }

@app.get("/stats")
def get_stats():
    """Get overall ghost network detection statistics"""
    index = load_ghost_scores()
    records = list(index.values())

    total = len(records)
    high = sum(1 for r in records if r.get("risk_tier") == "HIGH")
    medium = sum(1 for r in records if r.get("risk_tier") == "MEDIUM")
    low = sum(1 for r in records if r.get("risk_tier") == "LOW")

    return {
        "total_providers_scored": total,
        "risk_breakdown": {
            "HIGH": {"count": high, "pct": round(100*high/total, 1)},
            "MEDIUM": {"count": medium, "pct": round(100*medium/total, 1)},
            "LOW": {"count": low, "pct": round(100*low/total, 1)}
        },
        "key_finding": f"{round(100*high/total,1)}% of providers flagged as HIGH risk ghost providers",
        "data_source": "CMS Medicare Provider Directory vs NPPES Ground Truth",
        "states_covered": len(set(r.get("state","") for r in records)),
        "methodology": "5-signal ghost detection: address mismatch, specialty conflict, license expired, NPI collision, not accepting patients"
    }

@app.get("/high-risk")
def get_high_risk(limit: int = 10):
    """Get top high risk ghost providers"""
    index = load_ghost_scores()
    records = list(index.values())

    high_risk = [r for r in records if r.get("risk_tier") == "HIGH"]
    top = sorted(high_risk, key=lambda x: x.get("ghost_score", 0), reverse=True)[:limit]

    return {
        "total_high_risk": len(high_risk),
        "showing": len(top),
        "providers": [
            {
                "npi": r["npi"],
                "name": r.get("provider_name", ""),
                "specialty": r.get("specialty", ""),
                "state": r.get("state", ""),
                "ghost_score": r.get("ghost_score", 0),
                "signals": r.get("signals_triggered", 0)
            }
            for r in top
        ]
    }
