"""
The one place the backend asks what time it is.

Everything calls clock.now() instead of pd.Timestamp.now() directly, so the tests
can pretend it's any point in a race weekend (Saturday before quali, Sunday after
the race...) and get the same answer every run.
"""
import pandas as pd


def now() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")
