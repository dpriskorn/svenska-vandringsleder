import csv
import json
import logging
import time
from pathlib import Path
from typing import Optional, List

import requests
from pydantic import BaseModel

import config
from src.models.trail import Trail

logger = logging.getLogger(__name__)


class HikingTrailFetcher(BaseModel):
    country_iso: str
    overpass_timeout: int = 300
    waymarked_timeout: int = 10
    sleep_seconds: float = 0.5

    _session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def create_directories(self) -> None:
        logger.info(f"Creating directory '{self.country_dir}'")
        self.country_dir.mkdir(parents=True, exist_ok=True)

    @property
    def country_dir(self) -> Path:
        return config.data_output_directory / self.country_iso

    @property
    def csv_file(self) -> Path:
        return config.data_output_directory / self.country_iso / config.output_csv

    @property
    def overpass_file(self) -> Path:
        return config.data_output_directory / self.country_iso / config.output_json

    def fetch_overpass_and_save(self) -> None:
        print("Fetching hiking trails from Overpass API...")
        overpass_query: str = f"""
        [out:json][timeout:180];
        area["ISO3166-1"="{self.country_iso}"]["admin_level"="2"]->.country;
        rel(area.country)["type"="route"]["route"~"^(hiking|foot)$"];
        out tags;
        """
        start_time = time.perf_counter()

        r = self._get_session().post(
            config.overpass_url,
            data={"data": overpass_query},
            timeout=self.overpass_timeout
        )

        duration = time.perf_counter() - start_time
        logger.info(f"Overpass query completed in {duration:.2f} seconds")
        r.raise_for_status()
        data = r.json()
        with open(self.overpass_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved Overpass result to {self.overpass_file}")

    def load_overpass_file(self) -> dict:
        with open(self.overpass_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def extract_trails(data: dict) -> List[Trail]:
        trails = []
        for el in data.get("elements", []):
            if el["type"] == "relation":
                trails.append(Trail.from_overpass_element(el))
        return trails

    def load_lengths_cache(self) -> dict[int, dict]:
        """Load cached length & linear from CSV"""
        if not config.lengths_cache_csv.exists():
            return {}
        cache = {}
        with open(config.lengths_cache_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache[int(row["relation_id"])] = {
                    "length": float(row["length_km"]),
                    "linear": row["linear"].lower() == "true"
                }
        return cache

    def save_lengths_cache(self, cache: dict[int, dict]) -> None:
        """Save length & linear to cache CSV"""
        with open(config.lengths_cache_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["relation_id", "length_km", "linear"])
            writer.writeheader()
            for rel_id, vals in cache.items():
                writer.writerow({
                    "relation_id": rel_id,
                    "length_km": vals["length"],
                    "linear": vals["linear"]
                })

    def add_lengths(self, trails: List[Trail]) -> None:
        cache = self.load_lengths_cache()
        total = len(trails)
        for idx, t in enumerate(trails, 1):
            if idx <= config.fetch_limit_for_waymarkedtrails:
                logging.info(f"[{idx}/{total}] Processing trail {t.relation_id} ({t.name})")

                if t.relation_id in cache:
                    t.length = cache[t.relation_id]["length"]
                    t.linear = cache[t.relation_id]["linear"]
                    logging.debug(f"  -> Using cached: {t.length} km, linear={t.linear}")
                    continue

                t.fetch_waymarked_data(self._get_session(), config.waymarked_base_url, self.waymarked_timeout)
                if t.length is None:
                    logging.error(f"Length not found for trail {t.relation_id} ({t.name})")
                    raise ValueError(f"Length not found for trail {t.relation_id} ({t.name})")

                cache[t.relation_id] = {"length": t.length, "linear": t.linear}
                logging.info(f"  -> Fetched: {t.length} km, linear={t.linear}")

                self.save_lengths_cache(cache)  # save incrementally
                time.sleep(self.sleep_seconds)
                # exit(0)

    def save_csv(self, trails: List[Trail]) -> None:
        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=Trail.model_fields.keys())
            writer.writeheader()
            for t in trails:
                writer.writerow(t.model_dump())
        print(f"Saved CSV to {self.csv_file}")

    def run(self) -> None:
        if not self.csv_file.exists():
            self.create_directories()
            if not self.overpass_file.exists():
                self.fetch_overpass_and_save()

            overpass_data = self.load_overpass_file()
            trails = self.extract_trails(overpass_data)
            print(f"Found {len(trails)} trails in local file.")
            if config.fetch_from_waymarkedtrails:
                self.add_lengths(trails)
                self.save_csv(trails)
