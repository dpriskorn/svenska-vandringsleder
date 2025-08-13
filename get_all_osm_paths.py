import logging

import requests
import csv
import json
import time
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

logging.basicConfig(
    level=logging.DEBUG,  # Change to logging.INFO to reduce output
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class Trail(BaseModel):
    relation_id: int
    name: str = ""
    ref: str = ""
    network: str = ""
    length: Optional[float] = None  # km
    linear: bool = False


class HikingTrailFetcher(BaseModel):
    overpass_timeout: int = 300
    waymarked_timeout: int = 10
    overpass_file: Path = Path("overpass_hiking_sweden.json")
    output_csv: Path = Path("sweden_hiking_trails.csv")
    lengths_cache_csv: Path = Path("lengths_cache.csv")
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    waymarked_base_url: str = "https://hiking.waymarkedtrails.org/api/v1/details/relation"
    sleep_seconds: float = 0.5

    _session: Optional[requests.Session] = None

    overpass_query: str = """
    [out:json][timeout:180];
    area["ISO3166-1"="SE"]["admin_level"="2"]->.se;
    rel(area.se)["type"="route"]["route"~"^(hiking|foot)$"];
    out tags;
    """

    def _get_session(self) -> requests.Session:
        """Lazy init for requests.Session"""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def fetch_overpass_and_save(self) -> None:
        """Fetch from Overpass API and save to local file"""
        print("Fetching hiking trails from Overpass API...")
        r = self._get_session().post(self.overpass_url, data={"data": self.overpass_query}, timeout=self.overpass_timeout)
        r.raise_for_status()
        data = r.json()
        with open(self.overpass_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved Overpass result to {self.overpass_file}")

    def load_overpass_file(self) -> dict:
        """Load Overpass JSON file from disk"""
        with open(self.overpass_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def extract_trails(data: dict) -> List[Trail]:
        """Extract trails as list of Trail objects"""
        trails = []
        for el in data.get("elements", []):
            if el["type"] == "relation":
                trails.append(
                    Trail(
                        relation_id=el["id"],
                        name=el["tags"].get("name", ""),
                        ref=el["tags"].get("ref", ""),
                        network=el["tags"].get("network", "")
                    )
                )
        return trails

    def load_lengths_cache(self) -> dict[int, float]:
        """Load previously fetched lengths from CSV"""
        if not self.lengths_cache_csv.exists():
            return {}
        cache = {}
        with open(self.lengths_cache_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache[int(row["relation_id"])] = float(row["length_km"])
        return cache

    def save_lengths_cache(self, cache: dict[int, float]) -> None:
        """Save lengths cache to CSV"""
        with open(self.lengths_cache_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["relation_id", "length_km"])
            writer.writeheader()
            for rel_id, length in cache.items():
                writer.writerow({"relation_id": rel_id, "length_km": length})

    def get_trail_length(self, rel_id: int) -> Optional[float]:
        """Fetch trail length from Waymarked Trails API (in km)"""
        url = f"{self.waymarked_base_url}/{rel_id}?lang=en"
        logging.debug(f"Fetching length for relation {rel_id} from {url}")
        try:
            r = self._get_session().get(url, timeout=self.waymarked_timeout)
            logging.debug(f"HTTP {r.status_code} response for {rel_id}")
            r.raise_for_status()
            data = r.json()
            # Save full API response to debug.json
            with open("debug.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # get output in meters
            return data.get("route").get("length", 0) / 1000
        except Exception as e:
            logging.error(f"Error fetching {rel_id}: {e}", exc_info=True)
            return None

    def add_lengths(self, trails: List[Trail]) -> None:
        """Fetch lengths for all trails and update in-place using cache"""
        cache = self.load_lengths_cache()
        total = len(trails)
        for idx, t in enumerate(trails, 1):
            logging.info(f"[{idx}/{total}] Processing trail {t.relation_id} ({t.name})")

            if t.relation_id in cache:
                t.length = cache[t.relation_id]
                logging.debug(f"  -> Using cached length: {t.length} km")
                continue

            t.length = self.get_trail_length(t.relation_id)
            if not t.length:
                logging.error(f"Length not found for trail {t.relation_id} ({t.name})")
                raise ValueError(f"Length not found for trail {t.relation_id} ({t.name})")

            cache[t.relation_id] = t.length
            logging.info(f"  -> Fetched length: {t.length} km")

            # Save cache incrementally
            self.save_lengths_cache(cache)
            time.sleep(self.sleep_seconds)

    def save_csv(self, trails: List[Trail]) -> None:
        """Save trails to CSV"""
        with open(self.output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=Trail.model_fields.keys())
            writer.writeheader()
            for t in trails:
                writer.writerow(t.model_dump())
        print(f"Saved CSV to {self.output_csv}")

    def run(self) -> None:
        """Main execution flow"""
        if not self.overpass_file.exists():
            self.fetch_overpass_and_save()

        overpass_data = self.load_overpass_file()
        trails = self.extract_trails(overpass_data)
        print(f"Found {len(trails)} trails in local file.")

        self.add_lengths(trails)
        self.save_csv(trails)


if __name__ == "__main__":
    fetcher = HikingTrailFetcher()
    fetcher.run()
