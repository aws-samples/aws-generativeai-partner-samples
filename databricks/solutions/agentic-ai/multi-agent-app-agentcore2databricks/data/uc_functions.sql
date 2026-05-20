-- Unity Catalog functions for use by the Validator agent via UC Functions MCP Server.
-- Run these against your Databricks workspace after creating finserv_catalog.

-- Validates that a numeric value falls within expected bounds
CREATE OR REPLACE FUNCTION finserv_catalog.core.check_bounds(
    value DOUBLE COMMENT 'Value to check',
    lower_bound DOUBLE COMMENT 'Minimum acceptable value',
    upper_bound DOUBLE COMMENT 'Maximum acceptable value'
)
RETURNS STRING
COMMENT 'Checks if a value is within expected bounds. Returns PASS or FAIL with details.'
RETURN CASE
    WHEN value IS NULL THEN 'FAIL: value is NULL'
    WHEN value < lower_bound THEN CONCAT('FAIL: ', CAST(value AS STRING), ' < lower bound ', CAST(lower_bound AS STRING))
    WHEN value > upper_bound THEN CONCAT('FAIL: ', CAST(value AS STRING), ' > upper bound ', CAST(upper_bound AS STRING))
    ELSE CONCAT('PASS: ', CAST(value AS STRING), ' within [', CAST(lower_bound AS STRING), ', ', CAST(upper_bound AS STRING), ']')
END;

-- Computes percentage change between two values
CREATE OR REPLACE FUNCTION finserv_catalog.core.pct_change(
    current_value DOUBLE COMMENT 'Current period value',
    prior_value DOUBLE COMMENT 'Prior period value'
)
RETURNS DOUBLE
COMMENT 'Computes percentage change: (current - prior) / prior * 100'
RETURN CASE
    WHEN prior_value = 0 THEN NULL
    ELSE (current_value - prior_value) / prior_value * 100
END;

-- Summarizes sector exposure for a given segment
CREATE OR REPLACE FUNCTION finserv_catalog.core.sector_exposure_summary(
    segment_filter STRING COMMENT 'Customer segment to filter (RETAIL, HNW, INSTITUTIONAL)'
)
RETURNS TABLE(sector STRING, total_market_value DOUBLE, position_count BIGINT, avg_unrealized_pnl DOUBLE)
COMMENT 'Returns sector-level exposure summary for a given customer segment'
RETURN
    SELECT
        p.sector,
        SUM(p.market_value) AS total_market_value,
        COUNT(*) AS position_count,
        AVG(p.unrealized_pnl) AS avg_unrealized_pnl
    FROM finserv_catalog.risk.portfolio_positions p
    JOIN finserv_catalog.core.accounts a ON p.account_id = a.account_id
    JOIN finserv_catalog.core.customers c ON a.customer_id = c.customer_id
    WHERE c.segment = segment_filter
    GROUP BY p.sector
    ORDER BY total_market_value DESC;
