import logging
from pathlib import Path

loglevel = logging.INFO
fetch_from_waymarkedtrails = True
analyze = False
fetch_any_data = True
# This limit helps us gather a got set of data for many different countries
# We don't need all the trails at the beginning
fetch_limit_for_waymarkedtrails = 100
# Used during dev
analyze_country_limit = 250  # set to 250 to analyze all
html_output_directory = Path("public")
data_output_directory = Path("data")
output_csv: Path = Path("data.csv")
output_json: Path = Path(f"overpass.json")
lengths_cache_csv: Path = Path("lengths_cache.csv")
overpass_url: str = "https://overpass-api.de/api/interpreter"
waymarked_base_url: str = "https://hiking.waymarkedtrails.org/api/v1/details/relation"
