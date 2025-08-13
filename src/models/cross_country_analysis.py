from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import pycountry
from matplotlib import pyplot as plt
from pydantic import BaseModel, Field

import config

logger = logging.getLogger(__name__)


class CrossCountryAnalysis(BaseModel):
    """Aggregates multiple countries and builds a single HTML dashboard with comparisons."""
    name: str
    country_codes: List[str] = Field(..., description="List of ISO alpha-2 country codes (e.g., ['SE','NO','FI'])")

    @property
    def prefix(self) -> Path:
        return config.html_output_directory / Path("regions")

    @property
    def region_dir(self) -> Path:
        return self.prefix / self.name

    @property
    def charts_dir(self) -> Path:
        # We make a chart dir for each region for now to keep it simple
        return self.region_dir / "charts"

    @property
    def html_file(self) -> Path:
        return self.prefix / self.name / "index.html"

    @staticmethod
    def _country_name(code: str) -> str:
        c = pycountry.countries.get(alpha_2=code.upper())
        return c.name if c else code.upper()

    @staticmethod
    def _country_data_path(code: str) -> Path:
        return config.data_output_directory / code / "data.csv"

    def _load_country_df(self, code: str) -> pd.DataFrame | None:
        path = self._country_data_path(code)
        if not path.exists():
            return None
        df = pd.read_csv(path)
        if 'length' not in df.columns:
            return None
        df = df[df['length'] > 0].copy()
        df['country_code'] = code.upper()
        df['country_name'] = self._country_name(code)
        # normalize linear to numeric 0/1 if present
        if 'linear' in df.columns:
            df['linear'] = pd.to_numeric(df['linear'], errors='coerce').fillna(0).astype(int)
        return df

    def _summarize_country(self, df: pd.DataFrame) -> dict:
        trails = int(len(df))
        mean_len = float(df['length'].mean()) if trails else 0.0
        named = int(df['name'].notna().sum()) if 'name' in df.columns else 0
        pct_named = 100 * named / trails if trails else 0.0
        total_len = float(df['length'].sum())
        wd_mask = df['wikidata'].notna() if 'wikidata' in df.columns else pd.Series([False] * trails)
        wd_count = int(wd_mask.sum())
        pct_wd_count = 100 * wd_count / trails if trails else 0.0
        wd_len = float(df.loc[wd_mask, 'length'].sum()) if trails else 0.0
        pct_wd_len = 100 * wd_len / total_len if total_len else 0.0
        linear_count = int(df['linear'].sum()) if 'linear' in df.columns else 0
        pct_linear = 100 * linear_count / trails if trails else 0.0
        # absolute path to that country's HTML page
        # Absolute path to the per-country HTML page
        country_page_abs = config.html_output_directory / df['country_code'].iat[0] / "index.html"
        # Compute proper relative path from this region's index.html
        relative_link = os.path.relpath(country_page_abs, start=self.html_file.parent)
        #print(relative_link)
        #exit(0)
        return {
            'country_code': df['country_code'].iat[0],
            'country_name': df['country_name'].iat[0],
            'trails': trails,
            'mean_length_km': round(mean_len, 2),
            'total_length_km': round(total_len, 2),
            'percent_named': round(pct_named, 2),
            'linear_trails': linear_count,
            'percent_linear': round(pct_linear, 2),
            'wikidata_trails': wd_count,
            'percent_wikidata_by_count': round(pct_wd_count, 2),
            'wikidata_length_km': round(wd_len, 2),
            'percent_wikidata_by_length': round(pct_wd_len, 2),
            'country_page': relative_link,
        }

    @staticmethod
    def _plot_bar(labels: List[str], values: List[float], title: str, ylabel: str, outfile: Path):
        plt.figure(figsize=(12, 7))
        plt.bar(labels, values)
        plt.title(title)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(outfile)
        plt.close()

    def run(self) -> None:
        self.charts_dir.mkdir(parents=True, exist_ok=True)

        # load and summarize
        rows = []
        loaded_any = False
        for code in self.country_codes:
            df = self._load_country_df(code)
            if df is None or df.empty:
                continue
            loaded_any = True
            rows.append(self._summarize_country(df))

        if not loaded_any:
            raise FileNotFoundError("No country data found. Ensure per-country data CSVs exist under '<CC>-trails-analysis/data/<CC>/data.csv'.")

        summary = pd.DataFrame(rows).sort_values('total_length_km', ascending=False)

        # charts
        labels = summary['country_code'].tolist()
        self._plot_bar(labels, summary['total_length_km'].tolist(),
                       'Total Trail Length by Country', 'Total length (km)',
                       self.charts_dir / 'total_length_by_country.png')

        self._plot_bar(labels, summary['mean_length_km'].tolist(),
                       'Mean Trail Length by Country', 'Mean length (km)',
                       self.charts_dir / 'mean_length_by_country.png')

        self._plot_bar(labels, summary['percent_wikidata_by_length'].tolist(),
                       'Wikidata Coverage by Length', 'Coverage by length (%)',
                       self.charts_dir / 'wikidata_coverage_by_length.png')

        self._plot_bar(labels, summary['percent_wikidata_by_count'].tolist(),
                       'Wikidata Coverage by Count', 'Coverage by count (%)',
                       self.charts_dir / 'wikidata_coverage_by_count.png')

        self._plot_bar(labels, summary['percent_linear'].tolist(),
                       'Linear Trails Share by Country', 'Linear trails (%)',
                       self.charts_dir / 'linear_share_by_country.png')

        # add link column
        summary_display = summary.copy()
        summary_display['Country'] = summary_display.apply(
            lambda r: f"<a href='{r['country_page']}'>{r['country_name']} ({r['country_code']})</a>", axis=1
        )
        summary_display = summary_display[[
            'Country', 'trails', 'mean_length_km', 'total_length_km',
            'percent_named', 'linear_trails', 'percent_linear',
            'wikidata_trails', 'percent_wikidata_by_count',
            'wikidata_length_km', 'percent_wikidata_by_length'
        ]]

        # HTML dashboard
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <title>Hiking Trails – Cross-country Dashboard</title>
          <style>
            body {{ font-family: Arial, sans-serif; margin: 2em; }}
            h1, h2 {{ color: #2c3e50; }}
            img {{ max-width: 100%; height: auto; margin: 1.25em 0; }}
            table {{ border-collapse: collapse; margin: 1em 0; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 0.5em; text-align: left; }}
            th {{ background: #f7f7f7; }}
          </style>
        </head>
        <body>
          <h1>Hiking Trails – Cross-country Dashboard</h1>
          <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>

          <h2>Country Summary</h2>
          {summary_display.to_html(index=False, border=0, escape=False)}

          <h2>Comparative Charts</h2>
          <img src="charts/total_length_by_country.png" alt="Total length by country" />
          <img src="charts/mean_length_by_country.png" alt="Mean length by country" />
          <img src="charts/wikidata_coverage_by_length.png" alt="Wikidata coverage by length" />
          <img src="charts/wikidata_coverage_by_count.png" alt="Wikidata coverage by count" />
          <img src="charts/linear_share_by_country.png" alt="Linear share by country" />
        </body>
        </html>
        """
        self.html_file.write_text(html, encoding='utf-8')
        print(f"Cross-country HTML dashboard generated: {self.html_file}")


