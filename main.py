import logging

import pycountry

import config
from src.models.cross_country_analysis import CrossCountryAnalysis
from src.models.hiking_trail_analysis import HikingTrailsAnalysis
from src.models.hiking_trail_fetcher import HikingTrailFetcher
from src.models.index_generator import IndexGenerator

logging.basicConfig(
    level=config.loglevel,  # Change to logging.INFO to reduce output
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if __name__ == "__main__":
    if config.fetch_any_data:
        count = 0
        print("Fetching data for countries")
        for country in pycountry.countries:
            count += 1
            # noinspection PyUnresolvedReferences
            code = country.alpha_2
            # noinspection PyUnresolvedReferences
            name = country.name
            print(f"[{count}/{len(pycountry.countries)}] Fetching hiking trails for {name} ({code})")
            fetcher = HikingTrailFetcher(country_iso=code)
            fetcher.run()

    if config.analyze:
        print("Analyzing countries")
        count = 0
        for country in pycountry.countries:
            count += 1
            if count <= config.analyze_country_limit:
                # noinspection PyUnresolvedReferences
                code = country.alpha_2
                analysis = HikingTrailsAnalysis(country_code=code)
                analysis.run_analysis()
                # debug

    if config.analyze:
        print("Analyzing regions")
        # Europe
        cca_europe = CrossCountryAnalysis(name="europe", country_codes=[
            'AL', 'AD', 'AM', 'AT', 'AZ', 'BY', 'BE', 'BA', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE',
            'FI', 'FR', 'GE', 'DE', 'GR', 'HU', 'IS', 'IE', 'IT', 'KZ', 'XK', 'LV', 'LI', 'LT',
            'LU', 'MT', 'MD', 'MC', 'ME', 'NL', 'MK', 'NO', 'PL', 'PT', 'RO', 'RU', 'SM', 'RS',
            'SK', 'SI', 'ES', 'SE', 'CH', 'TR', 'UA', 'GB', 'VA'
        ])
        cca_europe.run()

        # Africa
        cca_africa = CrossCountryAnalysis(name="africa", country_codes=[
            'DZ', 'AO', 'BJ', 'BW', 'BF', 'BI', 'CV', 'CM', 'CF', 'TD', 'KM', 'CG', 'CD', 'DJ',
            'EG', 'GQ', 'ER', 'SZ', 'ET', 'GA', 'GM', 'GH', 'GN', 'GW', 'CI', 'KE', 'LS', 'LR',
            'LY', 'MG', 'MW', 'ML', 'MR', 'MU', 'MA', 'MZ', 'NA', 'NE', 'NG', 'RW', 'ST', 'SN',
            'SC', 'SL', 'SO', 'ZA', 'SS', 'SD', 'TZ', 'TG', 'TN', 'UG', 'EH', 'ZM', 'ZW'
        ])

        # Asia
        cca_asia = CrossCountryAnalysis(name="asia", country_codes=[
            'AF', 'AM', 'AZ', 'BH', 'BD', 'BT', 'BN', 'KH', 'CN', 'CY', 'GE', 'IN', 'ID', 'IR',
            'IQ', 'IL', 'JP', 'JO', 'KZ', 'KW', 'KG', 'LA', 'LB', 'MY', 'MV', 'MN', 'MM', 'NP',
            'KP', 'OM', 'PK', 'PS', 'PH', 'QA', 'SA', 'SG', 'KR', 'LK', 'SY', 'TW', 'TJ', 'TH',
            'TR', 'TM', 'AE', 'UZ', 'VN', 'YE'
        ])
        cca_asia.run()

        # North America
        cca_north_america = CrossCountryAnalysis(name="north_america", country_codes=[
            'AG', 'BS', 'BB', 'BZ', 'CA', 'CR', 'CU', 'DM', 'DO', 'SV', 'GD', 'GT', 'HT', 'HN',
            'JM', 'MX', 'NI', 'PA', 'KN', 'LC', 'VC', 'TT', 'US'
        ])
        cca_north_america.run()

        # South America
        cca_south_america = CrossCountryAnalysis(name="south_america", country_codes=[
            'AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'GY', 'PY', 'PE', 'SR', 'UY', 'VE'
        ])
        cca_south_america.run()

        # Oceania
        cca_oceania = CrossCountryAnalysis(name="oceania", country_codes=[
            'AU', 'FJ', 'KI', 'MH', 'FM', 'NR', 'NZ', 'PW', 'PG', 'WS', 'SB', 'TO', 'TV', 'VU'
        ])
        cca_oceania.run()

        # Finish
        ig = IndexGenerator()
        ig.generate_country_and_region_index()
