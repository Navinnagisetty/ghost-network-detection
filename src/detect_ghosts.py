"""
Ghost Network Detection — Core Detection Engine
Compares CMS provider directory against NPPES ground truth
Flags providers matching any of the 5 ghost signals
"""
import boto3
import json

S3_BUCKET = "ghost-network-detection-raw"
CMS_PREFIX = "raw/cms/providers/"
NPPES_PREFIX = "processed/silver/nppes/"
OUTPUT_PREFIX = "processed/gold/ghost_scores/"

def load_nppes_index(s3):
    """Build NPI lookup dict from NPPES silver layer"""
    print("Loading NPPES index...")
    nppes = {}
    
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=NPPES_PREFIX)
    
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            data = json.loads(
                s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
            )
            for record in data:
                npi = record.get("npi", "").strip()
                if npi:
                    nppes[npi] = record
    
    print(f"NPPES index loaded: {len(nppes):,} providers")
    return nppes

def detect_ghost_signals(cms_record, nppes_record):
    """
    Compare a CMS provider record against NPPES ground truth.
    Returns list of triggered ghost signals with evidence.
    """
    signals = []
    
    # Signal 1 — Address mismatch
    cms_zip = str(cms_record.get("zip_code", ""))[:5].strip()
    nppes_zip = str(nppes_record.get("zip", ""))[:5].strip()
    if cms_zip and nppes_zip and cms_zip != nppes_zip:
        signals.append({
            "signal": "address_mismatch",
            "evidence": f"CMS zip: {cms_zip} vs NPPES zip: {nppes_zip}",
            "weight": 25
        })
    
    # Signal 2 — Missing street address
    cms_addr = cms_record.get("adr_ln_1", "").strip()
    if not cms_addr:
        signals.append({
            "signal": "missing_address",
            "evidence": "No street address in CMS directory",
            "weight": 20
        })
    
    # Signal 3 — Specialty mismatch
    cms_spec = cms_record.get("pri_spec", "").strip().upper()
    nppes_tax = nppes_record.get("taxonomy", "").strip()
    if cms_spec and nppes_tax:
        # Flag if CMS lists psychiatry but NPPES shows different taxonomy
        psych_keywords = ["PSYCHIATRY", "MENTAL HEALTH", "PSYCHOLOGY"]
        cms_is_psych = any(k in cms_spec for k in psych_keywords)
        if cms_is_psych and "2084" not in nppes_tax:
            signals.append({
                "signal": "specialty_conflict",
                "evidence": f"CMS: {cms_spec} | NPPES taxonomy: {nppes_tax}",
                "weight": 25
            })
    
    # Signal 4 — Deactivated NPI
    deactivation = nppes_record.get("deactivation_date", "").strip()
    if deactivation:
        signals.append({
            "signal": "npi_deactivated",
            "evidence": f"NPI deactivated on {deactivation}",
            "weight": 40
        })
    
    # Signal 5 — Missing phone
    cms_phone = cms_record.get("telephone_number", "").strip()
    if not cms_phone:
        signals.append({
            "signal": "missing_phone",
            "evidence": "No phone number in CMS directory",
            "weight": 10
        })
    
    return signals

def compute_score(signals):
    return min(sum(s["weight"] for s in signals), 100)

def get_tier(score):
    if score >= 50: return "HIGH"
    elif score >= 25: return "MEDIUM"
    return "LOW"

def main():
    s3 = boto3.client("s3", region_name="us-east-1")
    nppes = load_nppes_index(s3)
    
    print("Processing CMS provider batches...")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=CMS_PREFIX)
    
    all_scored = []
    total_processed = 0
    ghost_count = 0
    
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            
            records = json.loads(
                s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
            )
            
            for cms_record in records:
                npi = str(cms_record.get("npi", "")).strip()
                nppes_record = nppes.get(npi, {})
                
                signals = detect_ghost_signals(cms_record, nppes_record)
                score = compute_score(signals)
                tier = get_tier(score)
                
                scored = {
                    "npi": npi,
                    "provider_name": f"{cms_record.get('provider_last_name','')} {cms_record.get('provider_first_name','')}".strip(),
                    "specialty": cms_record.get("pri_spec", ""),
                    "state": cms_record.get("state", ""),
                    "city": cms_record.get("citytown", ""),
                    "zip": cms_record.get("zip_code", ""),
                    "phone": cms_record.get("telephone_number", ""),
                    "ghost_score": score,
                    "risk_tier": tier,
                    "signals_triggered": len(signals),
                    "signal_details": signals,
                    "in_nppes": bool(nppes_record)
                }
                
                all_scored.append(scored)
                total_processed += 1
                if score > 0:
                    ghost_count += 1
    
    # Save results
    output_key = f"{OUTPUT_PREFIX}ghost_scores_all.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=json.dumps(all_scored).encode("utf-8")
    )
    
    high = sum(1 for r in all_scored if r["risk_tier"] == "HIGH")
    medium = sum(1 for r in all_scored if r["risk_tier"] == "MEDIUM")
    low = sum(1 for r in all_scored if r["risk_tier"] == "LOW")
    
    print(f"\nDetection complete")
    print(f"Total providers scored: {total_processed:,}")
    print(f"Providers with ghost signals: {ghost_count:,}")
    print(f"HIGH risk: {high:,}")
    print(f"MEDIUM risk: {medium:,}")
    print(f"LOW risk: {low:,}")
    print(f"Results saved to: s3://{S3_BUCKET}/{output_key}")

main()
