import logging

import pycountry

import config
from src.models.hiking_trail_analysis import HikingTrailsAnalysis
from src.models.hiking_trail_fetcher import HikingTrailFetcher

logging.basicConfig(
    level=logging.INFO,  # Change to logging.INFO to reduce output
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if __name__ == "__main__":
    count = 0
    # Get all ISO 3166-1 alpha-2 country codes
    for country in pycountry.countries:
        count += 1
        # noinspection PyUnresolvedReferences
        code = country.alpha_2
        # noinspection PyUnresolvedReferences
        name = country.name
        print(f"[{count}/{len(pycountry.countries)}] Fetching hiking trails for {name} ({code})")
        fetcher = HikingTrailFetcher(country_iso=code)

        try:
            # Replace this with your actual fetch method
            fetcher.run()
            # print(f"Would run: {fetcher.overpass_query[:200]}...")  # preview query
        except Exception as e:
            print(f"Error fetching trails for {code}: {e}")

        if config.analyze:
            analysis = HikingTrailsAnalysis(country_code=code)
            analysis.run_analysis()
        # # Be polite with API servers
        # sleep(fetcher.sleep_seconds)
