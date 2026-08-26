# Research Report: Getting Weather Data Programmatically from WIS2 (wis2box instance <WIS2_HOST>)

**Date**: 2026-07-15
**Method**: Live probing of the instance + official WMO documentation
**Confidence**: High — every command below was executed and verified against the live instance today.

---

## Executive Summary

`http://<WIS2_HOST>` is a **wis2box** instance (v1.2.0) operated by **SwaziMet (Eswatini Meteorological Service)**. It publishes **hourly SYNOP surface observations** and exposes three access channels, **none of which require authentication for reading data**:

| Channel | Endpoint | Auth | Use case |
|---|---|---|---|
| OGC API (pygeoapi) | `http://<WIS2_HOST>/oapi` | None | Query historical/recent decoded observations as JSON |
| MQTT broker | `mqtt://<WIS2_HOST>:1883` | `everyone` / `everyone` | Real-time push notifications of new data |
| HTTP file server | `http://<WIS2_HOST>/data/...` | None | Download raw BUFR files linked from notifications |

**Key confusion resolved**: the *wis2downloader* API docs you found describe a tool you would run **on your own machine** to subscribe to a WIS2 broker and auto-download files. It is **not** the API you call to fetch data *from* this instance. For your goal — "get weather data programmatically" — you only need the OGC API (option 1) and optionally MQTT (option 2).

---

## 1. The Mental Model (what confused you)

WIS2 is a **publish/subscribe** system, not a classic request/response API:

1. The wis2box **publishes a notification message** on MQTT every time a new observation file arrives.
2. The notification contains a **canonical link** to the raw data file (BUFR format).
3. Separately, wis2box **decodes** the observations and serves them through an **OGC API — Features** endpoint (pygeoapi) — this is the easy, JSON-native way to get data.

The `wis2downloader` is a *subscriber-side helper daemon*: you install it locally, point it at a broker, and it downloads files into a directory as notifications arrive. Its API (the one with `/subscriptions` endpoints) manages *its own* subscription list. The `401` returned by `http://<WIS2_HOST>/wis2downloader` is that instance's private downloader, protected by an admin token (`wis2box auth add-token`) — it is not meant for external users.

---

## 2. What This Instance Contains (verified)

`GET http://<WIS2_HOST>/oapi/collections?f=json` returns:

| Collection ID | Content |
|---|---|
| `urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations` | **Decoded surface observations** (111,163+ records, live) |
| `messages` | WIS2 notification messages (6,646+, includes BUFR links) |
| `stations` | Station metadata (WIGOS identifiers, locations) |
| `discovery-metadata` | Dataset catalogue record incl. MQTT topic |

Dataset: *"Hourly synoptic observations from fixed-land stations (SYNOP)"*.
MQTT topic: `origin/a/wis2/sz-swazimet/data/core/weather/surface-based-observations/synop`.

Each observation feature is **one parameter at one time at one station**, e.g.:

```json
{
  "name": "air_temperature",
  "value": 12.65,
  "units": "Celsius",
  "phenomenonTime": "2026-07-14T07:55:00Z",
  "wigos_station_identifier": "0-20000-0-68391",
  "reportId": "0-20000-0-68391-202607140755"
}
```

---

## 3. Option 1 (Recommended): OGC API — Features

Standard REST/JSON, no auth. Base: `http://<WIS2_HOST>/oapi`.

### Useful queries (all verified working)

```bash
# List collections
curl "http://<WIS2_HOST>/oapi/collections?f=json"

# List stations
curl "http://<WIS2_HOST>/oapi/collections/stations/items?f=json"

# Latest observations (paged)
curl "http://<WIS2_HOST>/oapi/collections/urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations/items?f=json&limit=100&sortby=-reportTime"

# Filter: one station, one parameter, a date range  (returned 83 records when tested)
curl "http://<WIS2_HOST>/oapi/collections/urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations/items?f=json&wigos_station_identifier=0-20000-0-68391&name=air_temperature&datetime=2026-07-14/2026-07-15&limit=100"
```

Query parameters supported: `limit`, `offset`, `datetime` (RFC3339 instant or `start/end` interval), `sortby`, `bbox`, plus **any property as a filter** (`name=`, `wigos_station_identifier=`, `reportId=`...). Paginate via `offset` or the `next` link in the response.

### Python example

```python
import requests

OAPI = "http://<WIS2_HOST>/oapi"
COLL = "urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations"

def get_observations(station: str, parameter: str, start: str, end: str) -> list[dict]:
    """Fetch decoded observations, following pagination."""
    url = f"{OAPI}/collections/{COLL}/items"
    params = {
        "f": "json", "limit": 1000,
        "wigos_station_identifier": station,
        "name": parameter,
        "datetime": f"{start}/{end}",
    }
    out = []
    while url:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        out += [f["properties"] for f in data["features"]]
        url = next((l["href"] for l in data.get("links", []) if l["rel"] == "next"), None)
        params = None  # next link already carries the query string
    return out

obs = get_observations("0-20000-0-68391", "air_temperature",
                       "2026-07-14T00:00:00Z", "2026-07-15T00:00:00Z")
for o in obs:
    print(o["phenomenonTime"], o["value"], o["units"])
```

Interactive API console (Swagger): `http://<WIS2_HOST>/oapi/openapi?f=html`

---

## 4. Option 2: Real-Time via MQTT

Verified: broker at `<WIS2_HOST>:1883`, credentials `everyone`/`everyone`, connection accepted (CONNACK rc=0).

```python
import json
import paho.mqtt.client as mqtt

TOPIC = "origin/a/wis2/sz-swazimet/data/core/weather/surface-based-observations/synop"

def on_message(client, userdata, msg):
    notification = json.loads(msg.payload)
    # canonical link -> raw BUFR file
    for link in notification.get("links", []):
        if link["rel"] == "canonical":
            print("New data:", link["href"])

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set("everyone", "everyone")
client.connect("<WIS2_HOST>", 1883)
client.subscribe(TOPIC)
client.on_message = on_message
client.loop_forever()
```

Notes:
- Notifications are published when new observations arrive (~hourly for SYNOP); expect quiet periods.
- Small payloads (<4 KB) are also embedded base64 in `properties.content.value`.
- The same dataset is also reachable via the **Global Broker** (`globalbroker.meteo.fr:8883`, TLS, same `everyone` credentials, topic `cache/a/wis2/sz-swazimet/...`) — more reliable than the origin box for production use.

---

## 5. Option 3: Raw BUFR Files

Notification `links[rel=canonical]` point at freely downloadable BUFR, e.g. (verified, HTTP 200):

```
http://<WIS2_HOST>/data/2026-07-15/wis/urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations/WIGOS_0-20000-0-68391_20260715T045400.bufr4
```

Decode with `eccodes` (`pip install eccodes`) or skip BUFR entirely by using Option 1 — the OGC API already serves the decoded values.

You can also mine past file links from the `messages` collection:

```bash
curl "http://<WIS2_HOST>/oapi/collections/messages/items?f=json&sortby=-datetime&limit=10"
```

---

## 6. About the wis2downloader Docs You Found

- The [wis2downloader API reference](https://world-meteorological-organization.github.io/wis2downloader/en/api-reference.html) documents a **standalone service you self-host** (default `localhost:5002`). Its `/subscriptions` endpoints tell *your* downloader which MQTT topics to watch; files land in a local directory.
- Its docs say the API itself has **no built-in authentication** — deployments put it behind a reverse proxy. That is exactly why `http://<WIS2_HOST>/wis2downloader` returns **401**: it's the operator's own protected instance (wis2box bearer-token auth, created with `wis2box auth add-token`). You are not expected to use it.
- If you *want* automated file mirroring on your side: run wis2downloader (or the lighter `pywis-pubsub`) locally and subscribe to the Global Broker.

```bash
pip install pywis-pubsub
# config points at globalbroker.meteo.fr / topic cache/a/wis2/sz-swazimet/#
pywis-pubsub subscribe --config local.yml --download
```

---

## 7. Authentication Summary

| Resource | Auth required? |
|---|---|
| `/oapi` collections & items on this instance | **No** (dataset is open; tested) |
| MQTT broker `:1883` | Username/password `everyone`/`everyone` (public convention) |
| `/data/...` BUFR files | **No** |
| `/wis2downloader` on the instance | **Yes** — operator admin token, not for external users |
| Closed datasets (general wis2box) | `Authorization: Bearer <token>`, tokens issued by the operator via `wis2box auth add-token` |

---

## 8. Recommendations

1. **Historical/analytical use** → Option 1 (OGC API). Simplest, JSON, filterable, no auth.
2. **Real-time pipeline** → Option 2 (MQTT) to trigger, then either parse the embedded BUFR/canonical link or re-query the OGC API for decoded values.
3. **Production real-time** → subscribe to the Global Broker (`globalbroker.meteo.fr:8883`, topic `cache/a/wis2/sz-swazimet/#`) rather than the origin box, which may be less available.
4. Ignore the wis2downloader API reference unless you decide to self-host that component.

## Sources

- Live probing of `http://<WIS2_HOST>` (2026-07-15): `/oapi`, collections, items queries, `/data/` BUFR download, MQTT CONNACK test, discovery-metadata record.
- [wis2box 1.3.0 — Getting started](https://docs.wis2box.wis.wmo.int/en/1.3.0/user/getting-started.html)
- [wis2box 1.3.0 — Downloading data from WIS2](https://docs.wis2box.wis.wmo.int/en/1.3.0/user/downloading-data.html)
- [wis2box 1.3.0 — Authentication and access control](https://docs.wis2box.wis.wmo.int/en/1.3.0/reference/auth.html)
- [wis2downloader — API reference](https://world-meteorological-organization.github.io/wis2downloader/en/api-reference.html)
