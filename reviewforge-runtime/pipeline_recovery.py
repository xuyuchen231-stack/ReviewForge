"""Bounded immediate recovery around checkpointed stages, never false acceptance."""
import time


class UnitRevisionsPending(ValueError):
    """Other units have been processed; unresolved units still need review."""


def run_with_recovery(operation,classify,on_retry,sleep=time.sleep,max_retries=3):
    transient={'connection_failure','upstream_unavailable','invalid_response','response_truncated','rate_limit','weekly_allowance_exhausted'}
    for attempt in range(max_retries+1):
        try:return operation()
        except Exception as exc:
            failure=classify(exc)
            recoverable=isinstance(exc,UnitRevisionsPending) or failure.get('category') in transient
            if not recoverable or attempt==max_retries:raise
            # Long quota cooldowns stay explicit blockers; don't restart-spam.
            delay=max(10*(2**attempt),int(failure.get('retry_after_seconds',0) or 0))
            if delay>300:raise
            on_retry(exc,attempt+1)
            print('[major-revision] recovery='+str(attempt+1)+'/'+str(max_retries)+'; retry_after='+str(delay)+'s; saved checkpoints retained',flush=True)
            remaining=delay
            while remaining:
                step=min(20,remaining);sleep(step);remaining-=step
