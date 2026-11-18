
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone


IMD_WFS_URL = "https://reactjs.imd.gov.in/geoserver/ows"

PARAMS = {
    "service": "WFS",
    "version": "1.1.0",
    "request": "GetFeature",
    "typeName": "imd:district_warnings_india",
    "srsName": "EPSG:4326",
    "outputFormat": "application/json",
}


def fetch_imd_district_warnings():
    """Fetch official IMD district-wise warning records."""
    query = urllib.parse.urlencode(PARAMS)
    url = f"{IMD_WFS_URL}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LUVIA-Weather-Intelligence/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    features = payload.get("features", [])
    fetched_at = datetime.now(timezone.utc).isoformat()
    warnings = []

    for feature in features:
        props = feature.get("properties") or {}
        district = props.get("District")

        if not district:
            continue

        days = []

        for day in range(1, 6):
            code = props.get(f"Day_{day}")
            color = props.get(f"Day{day}_Color")
            description = props.get(f"Day{day}_text")

            days.append({
                "day": day,
                "warning_code": str(code).strip() if code is not None else None,
                "color_code": color,
                "description": (
                    str(description).strip()
                    if description and str(description).strip()
                    else None
                ),
            })

        warnings.append({
            "source": "IMD",
            "source_url": url,
            "district": str(district).strip(),
            "state": props.get("state") or None,
            "issue_date": props.get("Date"),
            "updated_at": props.get("updated_at"),
            "fetched_at": fetched_at,
            "days": days,
        })

    return warnings


if __name__ == "__main__":
    records = fetch_imd_district_warnings()
    print(f"IMD district records received: {len(records)}")

    for record in records[:5]:
        print(json.dumps(record, indent=2, ensure_ascii=False))
