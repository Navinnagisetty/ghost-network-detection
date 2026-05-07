{{ config(materialized='table') }}

SELECT
    npi,
    provider_name,
    specialty,
    city,
    state,
    zip,
    phone,
    ghost_score,
    risk_tier,
    signals_triggered,
    in_nppes
FROM ghost_network.ghost_scores_nd
WHERE risk_tier = 'HIGH'
  AND ghost_score >= 50
ORDER BY ghost_score DESC, signals_triggered DESC
