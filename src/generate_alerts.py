"""
Ghost Network Detection — Bedrock AI Alert Generator
Takes top ghost providers and generates plain-English
compliance alerts using Claude Haiku via Amazon Bedrock
"""
import boto3
import json

S3_BUCKET = "ghost-network-detection-raw"
SCORES_KEY = "processed/gold/ghost_scores/ghost_scores_all.json"
ALERTS_KEY = "processed/gold/ai_alerts/ghost_alerts.json"
MODEL_ID = "anthropic.claude-haiku-20240307-v1:0"

def generate_alert(provider, bedrock):
    prompt = f"""You are a healthcare compliance analyst reviewing insurance provider directories.

Generate a concise 2-3 sentence compliance alert for this flagged provider:

Provider: {provider['provider_name']}
NPI: {provider['npi']}
Specialty: {provider['specialty']}
Location: {provider['city']}, {provider['state']} {provider['zip']}
Ghost Score: {provider['ghost_score']}/100
Risk Tier: {provider['risk_tier']}
Signals Triggered: {provider['signals_triggered']}
Signal Details: {json.dumps(provider['signal_details'])}
Found in NPPES Registry: {provider['in_nppes']}

Write a plain-English alert a compliance officer can act on immediately.
Include the specific risk, what it means for patients, and recommended action.
Be direct and specific. No bullet points."""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    })

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

def main():
    s3 = boto3.client("s3", region_name="us-east-1")
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

    print("Loading ghost scores...")
    data = json.loads(
        s3.get_object(Bucket=S3_BUCKET, Key=SCORES_KEY)["Body"].read()
    )

    # Get top 10 highest risk providers
    high_risk = [r for r in data if r["risk_tier"] == "HIGH"]
    high_risk_sorted = sorted(
        high_risk, key=lambda x: x["ghost_score"], reverse=True
    )[:10]

    print(f"Generating AI alerts for top {len(high_risk_sorted)} high-risk providers...")

    alerts = []
    for i, provider in enumerate(high_risk_sorted):
        print(f"  Alert {i+1}/{len(high_risk_sorted)}: {provider['provider_name']}...")
        try:
            alert_text = generate_alert(provider, bedrock)
            alerts.append({
                **provider,
                "ai_alert": alert_text,
                "alert_generated": True
            })
            print(f"    Done — score {provider['ghost_score']}/100")
        except Exception as e:
            print(f"    Error: {e}")
            alerts.append({**provider, "ai_alert": str(e), "alert_generated": False})

    # Save alerts
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=ALERTS_KEY,
        Body=json.dumps(alerts, indent=2).encode("utf-8")
    )

    print(f"\nAlerts saved to s3://{S3_BUCKET}/{ALERTS_KEY}")
    print(f"\nSample alert:")
    if alerts:
        print(f"Provider: {alerts[0]['provider_name']}")
        print(f"Score: {alerts[0]['ghost_score']}/100")
        print(f"Alert: {alerts[0].get('ai_alert', 'N/A')}")

main()
