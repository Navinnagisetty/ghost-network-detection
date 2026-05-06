"""
Ghost Network Detection — NPPES Parser
Extracts key fields from NPPES raw data for comparison
"""
import boto3
import json
import csv
import io
import zipfile

S3_BUCKET = "ghost-network-detection-raw"
NPPES_KEY = "raw/nppes/NPPES_Data_Dissemination_April_2026_V2.zip"
OUTPUT_PREFIX = "processed/silver/nppes/"

# Fields we care about for ghost detection
FIELDS_TO_KEEP = [
    "NPI",
    "Entity Type Code",
    "Provider Last Name (Legal Name)",
    "Provider First Name",
    "Provider Middle Name",
    "Provider Credential Text",
    "Provider Business Practice Location Address First Line",
    "Provider Business Practice Location Address City Name",
    "Provider Business Practice Location Address State Name",
    "Provider Business Practice Location Address Postal Code",
    "Provider Business Practice Location Address Telephone Number",
    "Healthcare Provider Taxonomy Code_1",
    "NPI Deactivation Date",
    "NPI Reactivation Date",
    "Provider Gender Code",
    "Is Sole Proprietor"
]

def clean_record(record):
    return {
        "npi": record.get("NPI", "").strip(),
        "entity_type": record.get("Entity Type Code", "").strip(),
        "last_name": record.get("Provider Last Name (Legal Name)", "").strip(),
        "first_name": record.get("Provider First Name", "").strip(),
        "credential": record.get("Provider Credential Text", "").strip(),
        "address_line1": record.get(
            "Provider Business Practice Location Address First Line", "").strip(),
        "city": record.get(
            "Provider Business Practice Location Address City Name", "").strip(),
        "state": record.get(
            "Provider Business Practice Location Address State Name", "").strip(),
        "zip": record.get(
            "Provider Business Practice Location Address Postal Code", "").strip()[:5],
        "phone": record.get(
            "Provider Business Practice Location Address Telephone Number", "").strip(),
        "taxonomy": record.get("Healthcare Provider Taxonomy Code_1", "").strip(),
        "deactivation_date": record.get("NPI Deactivation Date", "").strip(),
        "gender": record.get("Provider Gender Code", "").strip()
    }

def main():
    s3 = boto3.client("s3", region_name="us-east-1")
    print(f"Reading NPPES from S3: {NPPES_KEY}")
    print("Note: 1GB file — this will take several minutes...")

    obj = s3.get_object(Bucket=S3_BUCKET, Key=NPPES_KEY)
    zip_bytes = obj["Body"].read()

    print("Parsing ZIP file...")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        csv_files = [f for f in z.namelist() if f.endswith(".csv")
                     and "npidata" in f.lower()]
        print(f"Found CSV files: {csv_files}")

        if not csv_files:
            print("No NPI data CSV found")
            return

        with z.open(csv_files[0]) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            batch = []
            batch_num = 0
            total = 0

            for row in reader:
                cleaned = clean_record(row)
                if cleaned["npi"] and cleaned["entity_type"] == "1":
                    batch.append(cleaned)
                    total += 1

                if len(batch) >= 50000:
                    key = f"{OUTPUT_PREFIX}nppes_batch_{batch_num:04d}.json"
                    s3.put_object(
                        Bucket=S3_BUCKET,
                        Key=key,
                        Body=json.dumps(batch).encode("utf-8")
                    )
                    print(f"  Saved batch {batch_num} — {total:,} records so far")
                    batch = []
                    batch_num += 1

            if batch:
                key = f"{OUTPUT_PREFIX}nppes_batch_{batch_num:04d}.json"
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=key,
                    Body=json.dumps(batch).encode("utf-8")
                )
                print(f"  Saved final batch — {total:,} total records")

    print(f"\nNPPES parsing complete")
    print(f"Individual providers extracted: {total:,}")
    print(f"Output: s3://{S3_BUCKET}/{OUTPUT_PREFIX}")

main()
