"""
Data the backend loads once at startup (see lifespan in main.py) and every endpoint
reads from. They live here, not in main.py, so the endpoint files can all share
them without importing main (which would be circular).
"""
fantasy_table = None
current_prices = None
price_changes = None
race_schedule = None
backtest_cache = None
