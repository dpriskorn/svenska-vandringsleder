#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pycountry
from pydantic import BaseModel, Field


class HikingTrailsAnalysis(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO alpha-2 country code (e.g., 'SE')")

    @property
    def country_name(self) -> str:
        """Return full country name from ISO code."""
        country = pycountry.countries.get(alpha_2=self.country_code.upper())
        if not country:
            raise ValueError(f"Invalid country code: {self.country_code}")
        return country.name

    @property
    def prefix(self) -> Path:
        """Base output directory."""
        return Path(f"{self.country_code}-trails-analysis")

    @property
    def data_file(self) -> Path:
        """CSV file with hiking trail data."""
        return self.prefix / f"data/{self.country_code}/data.csv"

    @property
    def charts_dir(self) -> Path:
        """Charts output directory."""
        return self.prefix / "charts"

    @property
    def html_file(self) -> Path:
        """Generated HTML file."""
        return self.prefix / "index.html"

    def run_analysis(self) -> None:
        """Run the full analysis pipeline."""
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        data = pd.read_csv(self.data_file)
        data = data[data['length'] > 0]

        # --- Basic stats ---
        mean_length = data['length'].mean()
        num_names = data['name'].notna().sum()
        perc_names = 100 * num_names / len(data)

        wikidata_trails = data[data['wikidata'].notna()]
        no_wikidata_trails = data[data['wikidata'].isna()]

        total_length_all = data['length'].sum()
        total_length_wikidata = wikidata_trails['length'].sum()
        total_length_no_wikidata = no_wikidata_trails['length'].sum()

        num_linear = data['linear'].sum()
        num_trails = len(data)
        num_non_linear = num_trails - num_linear
        perc_linear = 100 * num_linear / num_trails
        perc_non_linear = 100 * num_non_linear / num_trails

        top_longest = data.nlargest(5, 'length')[['name', 'length']]
        top_shortest = data.nsmallest(5, 'length')[['name', 'length']]
        network_counts = data['network'].value_counts()

        # --- Charts ---
        self._plot_histogram(data['length'], "Distribution of Trail Lengths",
                             self.charts_dir / f"{self.country_code.lower()}_hiking_trails_lengths_histogram.png")

        short_trails = data[data['length'] < 25]
        self._plot_histogram(short_trails['length'], "Distribution of Short Trails (<25 km)",
                             self.charts_dir / f"{self.country_code.lower()}_hiking_trails_short_lengths_histogram.png",
                             bins=15, color='lightgreen')

        long_trails = data[data['length'] >= 25]
        self._plot_histogram(long_trails['length'], "Distribution of Long Trails (>=25 km)",
                             self.charts_dir / f"{self.country_code.lower()}_hiking_trails_long_lengths_histogram.png",
                             bins=15, color='salmon')

        self._plot_bar(['With Wikidata', 'Without Wikidata'],
                       [total_length_wikidata, total_length_no_wikidata],
                       "Total Length of Trails With/Without Wikidata Links",
                       self.charts_dir / f"{self.country_code.lower()}_hiking_trails_wikidata_lengths.png")

        # --- HTML ---
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
        {self._make_table(top_longest)}

        <h2>Top 5 Shortest Trails</h2>
        {self._make_table(top_shortest)}

        <h2>Number of Trails per Network</h2>
        {self._make_table(network_counts.reset_index().rename(columns={'index': 'Network', 'network': 'Count'}))}

        <h2>Charts</h2>
        <img src="charts/{self.country_code.lower()}_hiking_trails_lengths_histogram.png" alt="Histogram of trail lengths">
        <img src="charts/{self.country_code.lower()}_hiking_trails_short_lengths_histogram.png" alt="Short trails histogram">
        <img src="charts/{self.country_code.lower()}_hiking_trails_long_lengths_histogram.png" alt="Long trails histogram">
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
    def _plot_bar(labels, values, title, outfile):
        plt.figure(figsize=(8, 6))
        plt.bar(labels, values, color=['skyblue', 'lightcoral'])
        plt.title(title)
        plt.ylabel("Total Length (km)")
        plt.tight_layout()
        plt.savefig(outfile)
        plt.close()

    @staticmethod
    def _make_table(df: pd.DataFrame) -> str:
        """Convert DataFrame to HTML table."""
        return df.to_html(index=False, border=0)


