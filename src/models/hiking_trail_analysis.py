#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pycountry
from pydantic import BaseModel, Field

import config

logger = logging.getLogger(__name__)


class HikingTrailsAnalysis(BaseModel):
    """Per-country analysis and HTML report."""

    country_code: str = Field(..., min_length=2, max_length=2, description="ISO alpha-2 country code (e.g., 'SE')")

    def create_directories(self) -> None:
        logger.info(f"Creating directory '{self.html_country_dir}'")
        # self.country_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)

    @property
    def country_name(self) -> str:
        country = pycountry.countries.get(alpha_2=self.country_code.upper())
        if not country:
            raise ValueError(f"Invalid country code: {self.country_code}")
        return country.name

    @property
    def html_country_dir(self) -> Path:
        return config.html_output_directory / Path(self.country_code)

    @property
    def data_file(self) -> Path:
        return config.data_output_directory / Path(self.country_code) / Path("data.csv")

    @property
    def charts_dir(self) -> Path:
        return self.html_country_dir / "charts"

    @property
    def html_file(self) -> Path:
        return self.html_country_dir / "index.html"

    @staticmethod
    def waymarked_trails_url(relation_id: int) -> str:
        return f"https://hiking.waymarkedtrails.org/#route?id={relation_id}&type=relation"

    @staticmethod
    def osm_url(relation_id: int) -> str:
        return f"https://www.openstreetmap.org/relation/{relation_id}"

    def add_trail_links(
            self,
            df: pd.DataFrame,
            relation_id_col: str = "relation_id",
            waymarked_col: str = "waymarked-link",
            osm_col: str = "osm-link"
    ) -> pd.DataFrame:
        """Return a copy of df with added HTML link columns for Waymarked Trails and JOSM."""
        df = df.copy()
        df[waymarked_col] = df[relation_id_col].apply(
            lambda
                rid: f'<a href="{self.waymarked_trails_url(relation_id=rid)}" target="_blank">View in Waymarked Trails</a>'
        )
        df[osm_col] = df[relation_id_col].apply(
            lambda rid: f'<a href="{self.osm_url(relation_id=rid)}" target="_blank" title="View on OpenStreetMap.org">OSM</a>'
        )
        return df

    def run_analysis(self) -> None:
        """Run the full analysis pipeline for a single country."""
        if not self.data_file.exists():
            print(f"Data for {self.country_name} has not been fetched yet")
            return
        print(f"Working on {self.country_name}")
        self.create_directories()
        data = pd.read_csv(self.data_file)
        if data.empty:
            # todo output some meaningful html?
            return
        data = data[data['length'] > 0]

        # --- Basic stats ---
        mean_length = data['length'].mean()
        num_names = data['name'].notna().sum()
        perc_names = 100 * num_names / len(data) if len(data) else 0.0

        wikidata_trails = data[data['wikidata'].notna()]
        no_wikidata_trails = data[data['wikidata'].isna()]

        total_length_all = data['length'].sum()
        total_length_wikidata = wikidata_trails['length'].sum()
        total_length_no_wikidata = no_wikidata_trails['length'].sum()

        num_linear = int(data['linear'].sum()) if 'linear' in data.columns else 0
        num_trails = len(data)
        num_non_linear = num_trails - num_linear
        perc_linear = 100 * num_linear / num_trails if num_trails else 0.0
        perc_non_linear = 100 * num_non_linear / num_trails if num_trails else 0.0

        top_longest = data.nlargest(5, 'length')[['name', 'length']]
        top_shortest = data.nsmallest(5, 'length')[['name', 'length']]
        network_counts = data['network'].value_counts()

        # --- Non-linear trails ---
        # noinspection PyPep8
        non_linear_trails = data[data['linear'] == False] if 'linear' in data.columns else pd.DataFrame()
        non_linear_trails_sorted = non_linear_trails.sort_values(by='length', ascending=False)

        top_non_linear = pd.DataFrame()
        if not non_linear_trails.empty:
            df_with_links = self.add_trail_links(non_linear_trails_sorted)

            non_linear_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <title>{self.country_name} - All Non-linear Trails</title>
            <style>
            body {{ font-family: Arial, sans-serif; margin: 2em; }}
            h1, h2 {{ color: #2c3e50; }}
            table {{ border-collapse: collapse; margin-bottom: 2em; }}
            th, td {{ border: 1px solid #ccc; padding: 0.5em; text-align: left; }}
            a {{ color: #2980b9; }}
            </style>
            </head>
            <body>
            <h1>All Non-linear Trails in {self.country_name}</h1>
            {self._make_table(df_with_links[['name', 'length', 'waymarked-link', 'osm-link']])}
            </body>
            </html>
            """
            (self.html_file.parent / "non_linear.html").write_text(non_linear_html, encoding='utf-8')

            top_non_linear = self.add_trail_links(non_linear_trails_sorted.head(5))

        # --- Charts ---
        self._plot_histogram(data['length'], "Distribution of Trail Lengths",
                             self.charts_dir / f"{self.country_code.lower()}_hiking_trails_lengths_histogram.png")

        short_trails = data[data['length'] < 25]
        self._plot_histogram(short_trails['length'], "Distribution of Short Trails (<25 km)",
                             self.charts_dir / f"{self.country_code.lower()}_hiking_trails_short_lengths_histogram.png",
                             bins=15, color='lightgreen')

        long_trails = data[data['length'] >= 25]
        if not long_trails.empty:
            self._plot_histogram(long_trails['length'], "Distribution of Long Trails (>=25 km)",
                                 self.charts_dir / f"{self.country_code.lower()}_hiking_trails_long_lengths_histogram.png",
                                 bins=15, color='salmon')

        self._plot_bar(['With Wikidata', 'Without Wikidata'],
                       [total_length_wikidata, total_length_no_wikidata],
                       "Total Length of Trails With/Without Wikidata Links",
                       self.charts_dir / f"{self.country_code.lower()}_hiking_trails_wikidata_lengths.png")

        # --- Linear trails chart ---
        self._plot_bar(
            ['Linear Trails', 'Non-linear Trails'],
            [perc_linear, perc_non_linear],
            "Linearity of trails (%)",
            self.charts_dir / f"{self.country_code.lower()}_hiking_trails_linear_percentage.png",
            caption="Non-linear trails often have gaps in them so they should be checked"
        )

        # --- HTML ---
        non_linear_html_top5 = "<p>No non-linear trails found</p>"
        longest_trail_table_html = "<p>No trails longer than 25 km found</p>"
        longest_trail_chart_html = ""
        if not non_linear_trails.empty:
            non_linear_html_top5 = f"""        
            <h2>Top 5 Longest Non-linear Trails</h2>
            {self._make_table(top_non_linear[['name', 'length', 'waymarked-link', 'osm-link']])}
            <p>
                <a href="non_linear.html" style="display:inline-block; padding:0.5em 1em; 
                   background:#2980b9; color:white; text-decoration:none; border-radius:4px;">
                   More
                </a>
            </p>
            """
        if not long_trails.empty:
            longest_trail_table_html = self._make_table(top_longest)
            longest_trail_chart_html = """
            <img src="charts/{self.country_code.lower()}_hiking_trails_long_lengths_histogram.png" alt="Long trails histogram">
            """
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>{self.country_name} Hiking Trails Analysis</title>
        <style>
        body {{ font-family: Arial, sans-serif; margin: 2em; }}
        h1, h2 {{ color: #2c3e50; }}
        img {{ max-width: 100%; height: auto; margin-bottom: 2em; }}
        table {{ border-collapse: collapse; margin-bottom: 2em; }}
        th, td {{ border: 1px solid #ccc; padding: 0.5em; text-align: left; }}
        </style>
        </head>
        <body>
        <h1>{self.country_name} Hiking Trails Analysis</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>Summary Statistics</h2>
        <ul>
        <li>Mean trail length: {mean_length:.2f} km</li>
        <li>Trails with names: {num_names} ({perc_names:.2f}%)</li>
        <li>Total length of trails: {total_length_all:.2f} km</li>
        <li>Total length with Wikidata links: {total_length_wikidata:.2f} km</li>
        <li>Total length without Wikidata links: {total_length_no_wikidata:.2f} km</li>
        <li>Linear trails: {num_linear} ({perc_linear:.2f}%)</li>
        <li>Non-linear trails: {num_non_linear} ({perc_non_linear:.2f}%)</li>
        </ul>

        <h2>Top 5 Longest Trails</h2>
        {longest_trail_table_html}

        <h2>Top 5 Shortest Trails</h2>
        {self._make_table(top_shortest)}
        
        {non_linear_html_top5}
        
        <h2>Number of Trails per Network</h2>
        {self._make_table(network_counts.reset_index().rename(columns={'index': 'Network', 'network': 'Count'}))}

        <h2>Charts</h2>
        <img src="charts/{self.country_code.lower()}_hiking_trails_linear_percentage.png" 
     alt="Linear trails percentage chart">
        <img src="charts/{self.country_code.lower()}_hiking_trails_lengths_histogram.png" alt="Histogram of trail lengths">
        <img src="charts/{self.country_code.lower()}_hiking_trails_short_lengths_histogram.png" alt="Short trails histogram">
        {longest_trail_chart_html}
        <img src="charts/{self.country_code.lower()}_hiking_trails_wikidata_lengths.png" alt="Wikidata bar chart">

        </body>
        </html>
        """
        self.html_file.write_text(html, encoding='utf-8')
        print(f"HTML page generated: {self.html_file}")

    @staticmethod
    def _plot_histogram(series, title, outfile, bins=20, color='skyblue'):
        plt.figure(figsize=(10, 6))
        plt.hist(series, bins=bins, color=color, edgecolor='black')
        plt.title(title)
        plt.xlabel("Length (km)")
        plt.ylabel("Number of Trails")
        plt.tight_layout()
        plt.savefig(outfile)
        plt.close()

    @staticmethod
    def _plot_bar(labels, values, title, outfile, caption=""):
        plt.figure(figsize=(8, 6))
        plt.bar(labels, values, color=['skyblue', 'lightcoral'])
        plt.title(title)
        plt.ylabel("Total Length (km)")
        if caption:
            plt.figtext(0.5, -0.05, caption, wrap=True, ha="center", fontsize=10, style="italic")
        plt.tight_layout()
        plt.savefig(outfile, bbox_inches="tight")
        plt.close()

    @staticmethod
    def _make_table(df: pd.DataFrame) -> str:
        # Don't escape html
        return df.to_html(index=False, border=0, escape=False)

# --- Example usage ---
# 1) Generate per-country pages (you likely already do this)
# HikingTrailsAnalysis(country_code='SE').run_analysis()
# HikingTrailsAnalysis(country_code='NO').run_analysis()
# HikingTrailsAnalysis(country_code='FI').run_analysis()
#
# 2) Generate cross-country dashboard
# CrossCountryTrailsDashboard(country_codes=['SE','NO','FI']).run()
