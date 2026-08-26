"""Synthetic WIS2 feature factories mirroring the live wis2box shapes
(recorded 2026-07-15, see eswatini-v2/eswatini_weather_wis2.ipynb)."""

MBABANE = "0-20000-0-68391"
MOTI = "0-748-0-68384"


def obs_feature(
    wigos_id=MBABANE,
    name="air_temperature",
    value=15.0,
    end="2026-07-14T07:55:00Z",
    start=None,
    feature_id=None,
):
    phenomenon_time = f"{start}/{end}" if start else end
    return {
        "id": feature_id or f"{wigos_id}-{end}-{name}",
        "type": "Feature",
        "properties": {
            "name": name,
            "value": value,
            "units": "Celsius",
            "phenomenonTime": phenomenon_time,
            "reportTime": end,
            "reportId": f"{wigos_id}-{end}",
            "wigos_station_identifier": wigos_id,
        },
    }


def station_feature(
    wigos_id=MBABANE,
    name="MBABANE",
    lon=31.1427,
    lat=-26.336,
    elevation=1221,
    status="operational",
):
    return {
        "id": wigos_id,
        "type": "Feature",
        "properties": {
            "name": name,
            "wigos_station_identifier": wigos_id,
            "status": status,
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat, elevation],
        },
    }


def hourly_series(wigos_id, name, day, values, interval=False):
    """One feature per hour on `day` (YYYY-MM-DD) with the given values."""
    features = []
    for hour, value in enumerate(values):
        end = f"{day}T{hour:02d}:55:00Z"
        start = f"{day}T{hour - 1:02d}:55:00Z" if interval and hour else None
        if interval and not hour:
            start = f"{day}T00:00:00Z"
        features.append(
            obs_feature(
                wigos_id=wigos_id,
                name=name,
                value=value,
                end=end,
                start=start,
            )
        )
    return features
