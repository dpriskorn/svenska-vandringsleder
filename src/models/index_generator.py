from __future__ import annotations

import pycountry
from pydantic import BaseModel

import config
from src.models.cross_country_analysis import logger


class IndexGenerator(BaseModel):
    @staticmethod
    def generate_country_and_region_index() -> None:
        """Generate an index.html with links to all country analyses."""
        print("Making country and region index")
        country_links = []
        region_links = []
        # Countries
        for path in config.html_output_directory.glob("*/index.html"):
            country_code = path.parent.name.upper()
            logger.debug(f"working on {country_code}")
            # exit(0)
            country_name = pycountry.countries.get(alpha_2=country_code).name
            rel_path = path.relative_to(config.html_output_directory)
            country_links.append(f'<li><a href="{rel_path}">{country_name}</a></li>')

        # Regions
        for path in config.html_output_directory.glob("regions/*/index.html"):
            #print(path)
            #exit(0)
            region_name = path.parent.name
            #print(region_name)
            #exit(0)
            rel_path = path.relative_to(config.html_output_directory)
            region_links.append(f'<li><a href="{rel_path}">{region_name}</a></li>')

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>Hiking Trails Analyses - Index</title>
        <style>
        body {{ font-family: Arial, sans-serif; margin: 2em; }}
        h1 {{ color: #2c3e50; }}
        </style>
        </head>
        <body>
        <h1>Hiking Trails Analyses</h1>
        <h2>Countries</h2>
        <ul>
        {''.join(country_links)}
        </ul>
        <h2>Regions</h2>
        <ul>
        {''.join(region_links)}
        </ul>
        </body>
        </html>
        """
        (config.html_output_directory / "index.html").write_text(html, encoding="utf-8")
        print(f"Global index.html generated at {config.html_output_directory / 'index.html'}")
