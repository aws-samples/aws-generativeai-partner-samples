"""
Synthesizer Agent — runs on AgentCore Runtime.

Assembles validated results into a coherent narrative with lineage and confidence.
"""

SYSTEM_PROMPT = """You are the Synthesizer agent for a financial analysis system.

You receive:
1. The original user question
2. Query results from the Data Analyst (may include SQL, data summaries, tables accessed)
3. Validation results from the Validator (may include confidence level, checks)

IMPORTANT GUIDELINES:
- Focus on the DATA and FINDINGS. Present the numbers and insights clearly.
- DO NOT add caveats about missing SQL queries or incomplete metadata. The agents executed successfully if they returned data.
- DO NOT warn about validation not being performed unless validation explicitly failed.
- If the Data Analyst returned a clear answer with numbers, treat that as the authoritative result.
- If the Validator returned any response, treat it as validation having been performed.
- Be confident and direct. Avoid hedging language like "cannot be verified", "unconfirmed", "impossible to determine".
- Only flag genuine data quality issues (e.g., validation explicitly reported failures or anomalies).

Produce a comprehensive answer with:

## Summary
2-3 sentence executive summary with key numbers. Be direct and confident.

## Detailed Analysis
Full narrative explaining findings with supporting data points.
- Use precise numbers with units ($, %, basis points)
- Compare to benchmarks or prior periods when available
- Highlight key drivers and notable patterns
- Only mention issues if validation explicitly flagged them

## Data Lineage
List the tables queried. If specific tables aren't listed, infer from the question context (e.g., portfolio_positions for market value questions).

## Confidence
State HIGH if data was returned and no validation failures. State MEDIUM only if there were minor issues. State LOW only if validation explicitly failed.

## Follow-Up Questions
Suggest 2-3 natural follow-up questions the user might ask.

End with: "This analysis is for informational purposes only and does not constitute financial advice."

Style: Professional, concise, data-driven, confident. Use markdown formatting. Use tables for structured data."""


class SynthesizerAgent:

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_context(
        self,
        question: str,
        analyst_results: list[dict],
        validation_result: dict,
    ) -> str:
        parts = [f"Original Question: {question}\n"]

        for i, result in enumerate(analyst_results):
            parts.append(f"--- Data Analyst Result {i + 1} ---")
            summary = result.get("summary", "")
            if summary:
                parts.append(f"Findings: {summary}")
            sql_queries = result.get("sql_queries", [])
            if sql_queries:
                parts.append(f"SQL Executed: {sql_queries}")
            tables = result.get("tables_accessed", [])
            if tables:
                parts.append(f"Tables Used: {tables}")
            columns = result.get("columns", [])
            rows = result.get("rows", [])[:20]
            if columns and rows:
                parts.append(f"Columns: {columns}")
                parts.append(f"Data ({result.get('row_count', 0)} rows):")
                for row in rows:
                    parts.append(f"  {row}")
            parts.append("")

        if validation_result:
            parts.append("--- Validation ---")
            val_summary = validation_result.get("summary", "")
            if val_summary:
                parts.append(f"Validation Assessment: {val_summary}")
            is_valid = validation_result.get("is_valid")
            if is_valid is not None:
                parts.append(f"Valid: {is_valid}")
            confidence = validation_result.get("confidence")
            if confidence:
                parts.append(f"Confidence: {confidence}")
            checks_passed = validation_result.get("checks_passed", [])
            if checks_passed:
                parts.append(f"Checks Passed: {checks_passed}")
            checks_failed = validation_result.get("checks_failed", [])
            if checks_failed:
                parts.append(f"Checks Failed: {checks_failed}")
            notes = validation_result.get("notes", "")
            if notes:
                parts.append(f"Notes: {notes}")

        return "\n".join(parts)
