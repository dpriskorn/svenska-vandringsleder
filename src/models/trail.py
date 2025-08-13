import json
import logging

import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Trail(BaseModel):
    relation_id: int
    name: str = ""
    ref: str = ""
    network: str = ""
    length: float = 0.0  # km
    linear: bool = False
    wikidata: str = ""

    @classmethod
    def from_overpass_element(cls, el: dict) -> "Trail":
        """Create a Trail from Overpass API element"""
        return cls(
            relation_id=el["id"],
            name=el["tags"].get("name", ""),
            ref=el["tags"].get("ref", ""),
            network=el["tags"].get("network", ""),
            wikidata=el["tags"].get("wikidata", "")
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
