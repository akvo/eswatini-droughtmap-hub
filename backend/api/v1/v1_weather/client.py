import logging

import requests

logger = logging.getLogger(__name__)

# Property filters the source is known to silently drop (design D-2)
VERIFIED_FILTER_KEYS = ("name", "wigos_station_identifier")


class Wis2ClientError(Exception):
    pass


class Wis2Client:
    """OGC API — Features client for a wis2box instance.

    Two live-verified pygeoapi quirks make defensive fetching mandatory
    (design D-2):
    1. `next` links DROP property filters — so pagination is offset-based,
       resending every query param on every page.
    2. Filters are query-param-order sensitive: `name` must precede
       `wigos_station_identifier` or the station filter is silently ignored.
    Defense in depth: every returned feature is verified against the
    requested filters (raises on mismatch) and deduped on feature id.
    """

    PAGE_SIZE = 1000
    MAX_PAGES = 200

    def __init__(self, base_url: str, collection_id: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.collection_id = collection_id
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str, params: list):
        response = self.session.get(
            f"{self.base_url}/oapi/{path}",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def fetch_items(
        self,
        collection: str,
        filters: list = None,
        datetime_range: str = None,
    ) -> list:
        """Fetch all features with offset pagination + filter verification.

        `filters` is an ORDERED list of (key, value) tuples; callers must put
        `name` before `wigos_station_identifier` (quirk #2 above).
        """
        filters = list(filters or [])
        features = []
        seen_ids = set()
        for page in range(self.MAX_PAGES):
            params = [
                ("f", "json"),
                ("limit", self.PAGE_SIZE),
                ("offset", page * self.PAGE_SIZE),
            ] + filters
            if datetime_range:
                params.append(("datetime", datetime_range))
            data = self._get(f"collections/{collection}/items", params)
            batch = data.get("features", [])
            for feature in batch:
                self._verify_filters(feature, filters)
                feature_id = feature.get("id")
                if feature_id in seen_ids:
                    continue
                seen_ids.add(feature_id)
                features.append(feature)
            if len(batch) < self.PAGE_SIZE:
                break
        return features

    @staticmethod
    def _verify_filters(feature: dict, filters: list):
        properties = feature.get("properties", {})
        for key, value in filters:
            if key in VERIFIED_FILTER_KEYS and properties.get(key) != value:
                raise Wis2ClientError(
                    f"Source ignored filter {key}={value}; got "
                    f"{properties.get(key)!r} (feature {feature.get('id')})"
                )

    def fetch_stations(self) -> list:
        return self.fetch_items("stations")

    def fetch_observations(
        self,
        parameter: str,
        wigos_id: str,
        start: str = None,
    ) -> list:
        # name MUST precede wigos_station_identifier (quirk #2)
        filters = [
            ("name", parameter),
            ("wigos_station_identifier", wigos_id),
        ]
        datetime_range = f"{start}/.." if start else None
        return self.fetch_items(self.collection_id, filters, datetime_range)

    def earliest_report_time(self) -> str:
        """Probe the archive's oldest record — an advancing date across runs
        means the box purges on a rolling window (design D-6)."""
        data = self._get(
            f"collections/{self.collection_id}/items",
            [("f", "json"), ("limit", 1), ("sortby", "+reportTime")],
        )
        features = data.get("features", [])
        if not features:
            return None
        return features[0]["properties"].get("reportTime")
