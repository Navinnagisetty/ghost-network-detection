"""
Ghost Network Detection — Signal Definitions
5 ghost signals used to score each provider
"""

GHOST_SIGNALS = {
    "address_mismatch": {
        "description": "Payer address does not match NPPES ground truth",
        "weight": 25,
        "severity": "HIGH"
    },
    "specialty_conflict": {
        "description": "Payer specialty differs from NPPES specialty for same NPI",
        "weight": 25,
        "severity": "HIGH"
    },
    "license_expired": {
        "description": "Provider license expired or inactive in state medical board",
        "weight": 30,
        "severity": "CRITICAL"
    },
    "npi_collision": {
        "description": "Same NPI listed at 10+ different addresses across payers",
        "weight": 10,
        "severity": "MEDIUM"
    },
    "not_accepting": {
        "description": "Provider marked not accepting patients but listed as available",
        "weight": 10,
        "severity": "MEDIUM"
    }
}

def compute_ghost_score(signals_triggered):
    """
    Given a list of triggered signal keys,
    return a ghost score 0-100
    """
    score = 0
    for signal in signals_triggered:
        if signal in GHOST_SIGNALS:
            score += GHOST_SIGNALS[signal]["weight"]
    return min(score, 100)

def get_risk_tier(score):
    if score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MEDIUM"
    else:
        return "LOW"

if __name__ == "__main__":
    # Test
    test_signals = ["address_mismatch", "specialty_conflict"]
    score = compute_ghost_score(test_signals)
    tier = get_risk_tier(score)
    print(f"Test signals: {test_signals}")
    print(f"Ghost score: {score}")
    print(f"Risk tier: {tier}")
