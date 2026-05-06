import sys
import json
import boto3
import urllib.request
import urllib.parse

S3_BUCKET = "ghost-network-detection-raw"
S3_PREFIX = "raw/cms/providers/"
BASE_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/mj5m-pzi6/0"
BATCH_SIZE = 500

def fetch_batch(offset):
    params = urllib.parse.urlencode({
        "limit": BATCH_SIZE,
        "offset": offset
    })
    url = f"{BASE_URL}?{params}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    s3 = boto3.client("s3", region_name="us-east-1")

    print("Getting total provider count...")
    data = fetch_batch(0)
    total = data.get("count", 0)
    print(f"Total providers nationwide: {total:,}")

    all_records = []
    offset = 0
    batch_num = 0

    while offset < total:
        print(f"Fetching batch {batch_num+1} — offset {offset:,} of {total:,}...")
        data = fetch_batch(offset)
        results = data.get("results", [])

        if not results:
            break

        all_records.extend(results)
        offset += BATCH_SIZE
        batch_num += 1

        if len(all_records) >= 10000:
            key = f"{S3_PREFIX}batch_{batch_num:04d}.json"
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=json.dumps(all_records).encode("utf-8"),
                ContentType="application/json"
            )
            print(f"  Saved {len(all_records):,} records to {key}")
            all_records = []

    if all_records:
        key = f"{S3_PREFIX}batch_{batch_num+1:04d}.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(all_records).encode("utf-8"),
            ContentType="application/json"
        )
        print(f"  Saved final {len(all_records):,} records to {key}")

    print(f"\nDone. Batches written: {batch_num+1}")

main()
