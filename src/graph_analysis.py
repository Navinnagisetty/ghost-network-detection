"""
Ghost Network Detection — Graph Intelligence Layer
Uses NetworkX to detect fraud patterns invisible to record-level checking
Finds shared addresses, NPI clusters, and systematic manipulation patterns
"""
import boto3
import json
import sys
subprocess = __import__('subprocess')
subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx", "-q"])
import networkx as nx
from collections import defaultdict, Counter

S3_BUCKET = "ghost-network-detection-raw"
SCORES_KEY = "processed/gold/ghost_scores/ghost_scores_all.json"
GRAPH_OUTPUT = "processed/gold/graph_analysis/graph_findings.json"

def build_provider_graph(data):
    """
    Build a graph where:
    - Nodes = providers, addresses, zip codes, specialties
    - Edges = relationships between them
    """
    print("Building provider graph...")
    G = nx.Graph()

    for record in data:
        npi = record.get("npi", "")
        if not npi:
            continue

        # Add provider node
        G.add_node(f"NPI:{npi}",
                   node_type="provider",
                   name=record.get("provider_name", ""),
                   specialty=record.get("specialty", ""),
                   ghost_score=record.get("ghost_score", 0),
                   risk_tier=record.get("risk_tier", "LOW"),
                   state=record.get("state", ""))

        # Add zip node and connect
        zip_code = record.get("zip", "")[:5]
        if zip_code:
            zip_node = f"ZIP:{zip_code}"
            G.add_node(zip_node, node_type="zip")
            G.add_edge(f"NPI:{npi}", zip_node)

        # Add phone node and connect
        phone = record.get("phone", "").strip()
        if phone and len(phone) >= 10:
            phone_node = f"PHONE:{phone}"
            G.add_node(phone_node, node_type="phone")
            G.add_edge(f"NPI:{npi}", phone_node)

        # Add specialty node and connect
        specialty = record.get("specialty", "").strip()
        if specialty:
            spec_node = f"SPEC:{specialty}"
            G.add_node(spec_node, node_type="specialty")
            G.add_edge(f"NPI:{npi}", spec_node)

    print(f"Graph built: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G

def find_shared_phone_clusters(data):
    """Find multiple providers sharing the same phone number — fraud signal"""
    phone_to_providers = defaultdict(list)
    for record in data:
        phone = record.get("phone", "").strip()
        npi = record.get("npi", "")
        if phone and len(phone) >= 10 and npi:
            phone_to_providers[phone].append({
                "npi": npi,
                "name": record.get("provider_name", ""),
                "state": record.get("state", ""),
                "ghost_score": record.get("ghost_score", 0)
            })

    clusters = {k: v for k, v in phone_to_providers.items() if len(v) >= 3}
    return sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)[:10]

def find_shared_zip_clusters(data):
    """Find zip codes with unusually high concentrations of ghost providers"""
    zip_stats = defaultdict(lambda: {"total": 0, "high_risk": 0, "providers": []})
    for record in data:
        zip_code = record.get("zip", "")[:5]
        if not zip_code:
            continue
        zip_stats[zip_code]["total"] += 1
        if record.get("risk_tier") == "HIGH":
            zip_stats[zip_code]["high_risk"] += 1
            zip_stats[zip_code]["providers"].append(
                record.get("provider_name", "")
            )

    suspicious = {
        k: v for k, v in zip_stats.items()
        if v["total"] >= 5 and v["high_risk"] / v["total"] >= 0.5
    }
    return sorted(
        suspicious.items(),
        key=lambda x: x[1]["high_risk"],
        reverse=True
    )[:10]

def find_npi_anomalies(data):
    """Find providers appearing multiple times with different locations"""
    npi_locations = defaultdict(list)
    for record in data:
        npi = record.get("npi", "")
        zip_code = record.get("zip", "")[:5]
        if npi and zip_code:
            npi_locations[npi].append({
                "zip": zip_code,
                "city": record.get("city", ""),
                "state": record.get("state", ""),
                "ghost_score": record.get("ghost_score", 0)
            })

    duplicates = {k: v for k, v in npi_locations.items() if len(v) > 1}
    return sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]

def classify_root_cause(signals):
    """Classify why a provider is a ghost based on signal patterns"""
    signal_names = [s.get("signal", "") for s in signals]

    if "npi_deactivated" in signal_names:
        return "CREDENTIAL_CHURN"
    elif "address_mismatch" in signal_names and "specialty_conflict" in signal_names:
        return "DATA_MANIPULATION"
    elif "missing_address" in signal_names and "missing_phone" in signal_names:
        return "DATA_ROT"
    elif "address_mismatch" in signal_names:
        return "ADDRESS_ROT"
    else:
        return "DIRECTORY_NEGLIGENCE"

def main():
    s3 = boto3.client("s3", region_name="us-east-1")

    print("Loading ghost scores...")
    data = json.loads(
        s3.get_object(Bucket=S3_BUCKET, Key=SCORES_KEY)["Body"].read()
    )
    print(f"Loaded {len(data):,} provider records")

    # Build graph
    G = build_provider_graph(data)

    # Find fraud patterns
    print("\nAnalyzing fraud patterns...")
    phone_clusters = find_shared_phone_clusters(data)
    zip_clusters = find_shared_zip_clusters(data)
    npi_duplicates = find_npi_anomalies(data)

    # Root cause classification
    print("Classifying root causes...")
    root_causes = Counter()
    for record in data:
        if record.get("risk_tier") == "HIGH":
            signals = record.get("signal_details", [])
            cause = classify_root_cause(signals)
            root_causes[cause] += 1

    # Graph statistics
    provider_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "provider"]
    high_risk_nodes = [n for n in provider_nodes
                      if G.nodes[n].get("ghost_score", 0) >= 50]

    findings = {
        "graph_stats": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "total_providers": len(provider_nodes),
            "high_risk_providers": len(high_risk_nodes)
        },
        "shared_phone_clusters": [
            {
                "phone": phone,
                "provider_count": len(providers),
                "providers": providers[:5]
            }
            for phone, providers in phone_clusters
        ],
        "high_ghost_zip_clusters": [
            {
                "zip": zip_code,
                "total_providers": stats["total"],
                "high_risk_count": stats["high_risk"],
                "ghost_rate_pct": round(100 * stats["high_risk"] / stats["total"], 1),
                "sample_providers": stats["providers"][:3]
            }
            for zip_code, stats in zip_clusters
        ],
        "npi_appearing_multiple_locations": [
            {
                "npi": npi,
                "location_count": len(locations),
                "locations": locations
            }
            for npi, locations in npi_duplicates
        ],
        "root_cause_breakdown": dict(root_causes),
        "key_findings": [
            f"Graph contains {G.number_of_nodes():,} nodes and {G.number_of_edges():,} edges",
            f"{len(phone_clusters)} phone numbers shared by 3+ providers — potential billing mill pattern",
            f"{len(zip_clusters)} zip codes with 50%+ ghost rate — geographic concentration of fraud",
            f"{len(npi_duplicates)} NPIs appearing at multiple locations simultaneously",
            f"Root cause breakdown: {dict(root_causes)}"
        ]
    }

    # Save to S3
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=GRAPH_OUTPUT,
        Body=json.dumps(findings, indent=2).encode("utf-8")
    )

    print("\n" + "="*60)
    print("GRAPH ANALYSIS COMPLETE")
    print("="*60)
    print(f"Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    print(f"\nPhone clusters (3+ providers same phone): {len(phone_clusters)}")
    for phone, providers in phone_clusters[:3]:
        print(f"  {phone}: {len(providers)} providers")

    print(f"\nHigh ghost zip codes (50%+ ghost rate): {len(zip_clusters)}")
    for zip_code, stats in zip_clusters[:3]:
        print(f"  ZIP {zip_code}: {stats['high_risk']}/{stats['total']} providers HIGH risk ({round(100*stats['high_risk']/stats['total'],1)}%)")

    print(f"\nNPIs at multiple locations: {len(npi_duplicates)}")
    for npi, locs in npi_duplicates[:3]:
        print(f"  NPI {npi}: {len(locs)} different locations")

    print(f"\nRoot cause breakdown:")
    for cause, count in root_causes.most_common():
        print(f"  {cause}: {count:,}")

    print(f"\nSaved to s3://{S3_BUCKET}/{GRAPH_OUTPUT}")

main()
