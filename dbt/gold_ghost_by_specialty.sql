{{ config(materialized='table') }}

SELECT
    specialty,
    COUNT(*)                                                    AS total_providers,
    SUM(CASE WHEN risk_tier = 'HIGH'   THEN 1 ELSE 0 END)     AS high_risk,
    SUM(CASE WHEN risk_tier = 'MEDIUM' THEN 1 ELSE 0 END)     AS medium_risk,
    ROUND(100.0 * SUM(CASE WHEN risk_tier = 'HIGH' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct,
    ROUND(AVG(ghost_score), 1)                                 AS avg_ghost_score
FROM ghost_network.ghost_scores_nd
WHERE specialty != ''
GROUP BY specialty
HAVING COUNT(*) >= 10
ORDER BY high_risk_pct DESC
