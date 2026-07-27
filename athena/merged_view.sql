-- Serving Layer: the Lambda-architecture "merge" query.
-- Combines the batch layer's full-history correctness with the speed
-- layer's recent-window freshness into one queryable view, the AWS
-- equivalent of serving/merge_view.py.

CREATE OR REPLACE VIEW bus_reliability.merged_serving_view AS
SELECT
    b.route_id,
    b.average_score   AS historical_average_score,
    b.total_trips     AS historical_total_trips,
    s.avg_score       AS recent_window_average_score,
    s.event_count     AS recent_window_event_count,
    ROUND(s.avg_score - b.average_score, 2) AS recent_vs_history_delta
FROM bus_reliability.batch_per_route b
LEFT JOIN bus_reliability.speed_worst_routes s
    ON b.route_id = s.route_id
ORDER BY recent_vs_history_delta ASC NULLS LAST;

-- Example query for the report/demo: routes whose reliability has degraded
-- most sharply in the last window compared to their historical average.
-- SELECT * FROM bus_reliability.merged_serving_view
-- WHERE recent_vs_history_delta IS NOT NULL
-- ORDER BY recent_vs_history_delta ASC
-- LIMIT 10;
