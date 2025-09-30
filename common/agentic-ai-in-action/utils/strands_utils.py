#!/usr/bin/env python3
"""
Strands SDK Additional Utilies

Shared utilities for Strands Agent related workflow
"""

from ldai.tracker import TokenUsage

def event_loop_tracker(tracker, logger, **kwargs):   
    # Track Metrics
    if kwargs.get("result", False):        
        logger.debug(f"Metrics: {kwargs['result'].metrics}")
        tracker.track_success()
        tracker.track_duration(sum(kwargs['result'].metrics.cycle_durations))
        tracker.track_time_to_first_token(kwargs['result'].metrics.accumulated_metrics['latencyMs'])
        tokens = TokenUsage(
            total = kwargs['result'].metrics.accumulated_usage['totalTokens'],
            input = kwargs['result'].metrics.accumulated_usage['inputTokens'],
            output = kwargs['result'].metrics.accumulated_usage['outputTokens'],
        )
        tracker.track_tokens(tokens)