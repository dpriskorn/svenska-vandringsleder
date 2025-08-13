from pathlib import Path

fetch_from_waymarkedtrails = False
analyze = True
fetch_data = False
# This limit helps us gather a got set of data for many different countries
# We don't need all the trails at the beginning
fetch_limit_for_waymarkedtrails = 100
html_output_directory = Path("public")
data_output_directory = Path("data")
output_csv: Path = Path("data.csv")
output_json: Path = Path(f"overpass.json")
lengths_cache_csv: Path = Path("lengths_cache.csv")
overpass_url: str = "https://overpass-api.de/api/interpreter"
waymarked_base_url: str = "https://hiking.waymarkedtrails.org/api/v1/details/relation"
