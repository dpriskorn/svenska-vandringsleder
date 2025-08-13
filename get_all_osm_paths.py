import logging
import requests
import csv
import json
import time
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,  # Change to logging.INFO to reduce output
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class Trail(BaseModel):
    relation_id: int
    name: str = ""
    ref: str = ""
    network: str = ""
    length: float = 0.0  # km
    linear: bool = False

    @classmethod
    def from_overpass_element(cls, el: dict) -> "Trail":
        """Create a Trail from Overpass API element"""
        return cls(
            relation_id=el["id"],
            name=el["tags"].get("name", ""),
            ref=el["tags"].get("ref", ""),
            network=el["tags"].get("network", "")
        )

    def fetch_waymarked_data(self, session: requests.Session, base_url: str, timeout: int) -> None:
        """Fetch and set length + linear from Waymarked Trails API"""
        url = f"{base_url}/{self.relation_id}?lang=en"
        logging.debug(f"Fetching Waymarked data for {self.relation_id} from {url}")

        r = session.get(url, timeout=timeout)
        logging.debug(f"HTTP {r.status_code} response for {self.relation_id}")

        if r.status_code == 404:
            with open("waymarked_404.log", "a", encoding="utf-8") as f:
                f.write(f"{self.relation_id}\n")
            logging.warning(f"404 Not Found for relation {self.relation_id}, continuing")
            return  # skip further processing

        r.raise_for_status()  # will raise for all other error codes

        data = r.json()
        # Save last response for debugging
        with open("debug.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        route_data = data.get("route", {})
        if "length" in route_data:
            self.length = route_data["length"] / 1000  # meters → km
        else:
            raise Exception("No length in data")
        if "linear" in route_data:
            if route_data["linear"] == "yes":
                self.linear = True
            else:
                self.linear = False
        else:
            raise Exception("No linear in data")


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
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def fetch_overpass_and_save(self) -> None:
        print("Fetching hiking trails from Overpass API...")
        r = self._get_session().post(
            self.overpass_url,
            data={"data": self.overpass_query},
            timeout=self.overpass_timeout
        )
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
        if not self.lengths_cache_csv.exists():
            return {}
        cache = {}
        with open(self.lengths_cache_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache[int(row["relation_id"])] = {
                    "length": float(row["length_km"]),
                    "linear": row["linear"].lower() == "true"
                }
        return cache

    def save_lengths_cache(self, cache: dict[int, dict]) -> None:
        """Save length & linear to cache CSV"""
        with open(self.lengths_cache_csv, "w", newline="", encoding="utf-8") as f:
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
            logging.info(f"[{idx}/{total}] Processing trail {t.relation_id} ({t.name})")

            if t.relation_id in cache:
                t.length = cache[t.relation_id]["length"]
                t.linear = cache[t.relation_id]["linear"]
                logging.debug(f"  -> Using cached: {t.length} km, linear={t.linear}")
                continue

            t.fetch_waymarked_data(self._get_session(), self.waymarked_base_url, self.waymarked_timeout)
            if t.length is None:
                logging.error(f"Length not found for trail {t.relation_id} ({t.name})")
                raise ValueError(f"Length not found for trail {t.relation_id} ({t.name})")

            cache[t.relation_id] = {"length": t.length, "linear": t.linear}
            logging.info(f"  -> Fetched: {t.length} km, linear={t.linear}")

            self.save_lengths_cache(cache)  # save incrementally
            time.sleep(self.sleep_seconds)
            # exit(0)


    def save_csv(self, trails: List[Trail]) -> None:
        with open(self.output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=Trail.model_fields.keys())
            writer.writeheader()
            for t in trails:
                writer.writerow(t.model_dump())
        print(f"Saved CSV to {self.output_csv}")

    def run(self) -> None:
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
