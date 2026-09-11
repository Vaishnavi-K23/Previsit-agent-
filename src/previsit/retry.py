"""Generic retry-with-backoff for transient failures against managed cloud
services. Observed directly in practice against both services this project
talks to: Azure SQL Database's free offer returned "not currently available,
retry later" (error 40613) and separately dropped a connection mid-transfer;
Qdrant Cloud's free tier returned "server disconnected without sending a
response" mid-upload. Both are expected, documented characteristics of a
shared/free managed tier under load or while resuming - not bugs in this
project's code - so the retry policy is centralized here once instead of
being reinvented per-service.

Backoff has to be genuinely patient, not just present: a first attempt at a
short backoff (a few seconds total) still exhausted every retry while a
service was transiently unavailable, and a cold-start resume was separately
confirmed to take up to 45 seconds on its own. Capped exponential backoff up
to 60s, six attempts (roughly 2-3 minutes of total budget), gives a real
chance of outlasting a resume/rebalance event instead of just performing a
retry for its own sake.
"""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

MAX_ATTEMPTS = 6
MAX_BACKOFF_SECONDS = 60


def with_retry(fn: Callable[[], T], exceptions: tuple[type[Exception], ...]) -> T:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except exceptions:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(min(MAX_BACKOFF_SECONDS, 5 * (2 ** (attempt - 1))))
    raise AssertionError("unreachable")  # loop always returns or raises above
