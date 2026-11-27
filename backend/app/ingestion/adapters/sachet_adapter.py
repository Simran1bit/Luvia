"""Fetch official disaster alerts from NDMA's SACHET system.

SACHET aggregates CAP (Common Alerting Protocol) alerts issued by IMD, CWC,
INCOIS and state disaster management authorities. NDMA publishes an all-India
RSS index; each item links to a CAP XML document holding the details
(event, severity, urgency, area, validity window).

The feed is public but not formally documented, so parsing is defensive:
anything missing is stored as None rather than guessed.
"""

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen

RSS_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
USER_AGENT = "LUVIA-Weather-Intelligence/1.0"
CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

# CAP severity -> LUVIA severity scale.
CAP_SEVERITY = {
    "extreme": "critical",
    "severe": "high",
    "moderate": "medium",
    "minor": "low",
}


def _get(url: str, timeout: int = 30) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _text(element, path, ns=None):
    if element is None:
        return None
    found = element.find(path, ns or {})
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def parse_rss(xml_bytes: bytes) -> list[dict]:
    """Parse the SACHET RSS index into lightweight alert stubs."""
    root = ET.fromstring(xml_bytes)
    items = []

    for item in root.iter("item"):
        identifier = _text(item, "guid")
        if not identifier:
            continue

        published = _text(item, "pubDate")
        try:
            published = parsedate_to_datetime(published).isoformat() if published else None
        except (TypeError, ValueError):
            published = None

        items.append({
            "identifier": identifier,
            "title": _text(item, "title"),
            "category": _text(item, "category"),
            "link": _text(item, "link"),
            "author": _text(item, "author"),
            "published_at": published,
        })

    return items


def parse_cap(xml_bytes: bytes) -> dict:
    """Extract the useful fields from one CAP 1.2 alert document."""
    root = ET.fromstring(xml_bytes)

    # Prefer the English info block when an alert is issued in several languages.
    infos = root.findall("cap:info", CAP_NS)
    info = next(
        (i for i in infos if (_text(i, "cap:language", CAP_NS) or "").lower().startswith("en")),
        infos[0] if infos else None,
    )

    areas = info.findall("cap:area", CAP_NS) if info is not None else []
    area_desc = "; ".join(filter(None, (_text(a, "cap:areaDesc", CAP_NS) for a in areas))) or None
    district_codes = [
        _text(g, "cap:value", CAP_NS)
        for a in areas
        for g in a.findall("cap:geocode", CAP_NS)
        if "district" in (_text(g, "cap:valueName", CAP_NS) or "").lower()
    ]

    cap_severity = _text(info, "cap:severity", CAP_NS)

    return {
        "cap_identifier": _text(root, "cap:identifier", CAP_NS),
        "sender": _text(root, "cap:sender", CAP_NS),
        "sent_at": _text(root, "cap:sent", CAP_NS),
        "msg_type": _text(root, "cap:msgType", CAP_NS),
        "event": _text(info, "cap:event", CAP_NS),
        "cap_category": _text(info, "cap:category", CAP_NS),
        "urgency": _text(info, "cap:urgency", CAP_NS),
        "cap_severity": cap_severity,
        "severity": CAP_SEVERITY.get((cap_severity or "").lower(), "unknown"),
        "certainty": _text(info, "cap:certainty", CAP_NS),
        "effective_at": _text(info, "cap:effective", CAP_NS),
        "expires_at": _text(info, "cap:expires", CAP_NS),
        "headline": _text(info, "cap:headline", CAP_NS),
        "description": _text(info, "cap:description", CAP_NS),
        "instruction": _text(info, "cap:instruction", CAP_NS),
        "area": area_desc,
        "district_codes": [c for c in district_codes if c],
    }


def fetch_sachet_alerts(known_identifiers=frozenset(), max_new: int = 150):
    """Fetch the RSS index and the CAP detail for alerts not seen before.

    ``known_identifiers`` lets the caller skip alerts already stored, so each
    run only downloads CAP documents for new alerts. Returns ``(alerts, failures)``.
    """
    try:
        stubs = parse_rss(_get(RSS_URL))
    except Exception as exc:
        return [], [{"alert": "SACHET RSS", "error": str(exc)}]

    alerts, failures = [], []
    new_stubs = [s for s in stubs if s["identifier"] not in known_identifiers][:max_new]

    for stub in new_stubs:
        detail = {}
        if stub.get("link"):
            try:
                detail = parse_cap(_get(stub["link"]))
            except Exception as exc:
                # Keep the RSS-level record even when the CAP document fails.
                failures.append({"alert": stub["identifier"], "error": str(exc)})
        alerts.append({**stub, **detail})

    return alerts, failures


if __name__ == "__main__":
    fetched, problems = fetch_sachet_alerts(max_new=3)
    print(f"Alerts: {len(fetched)}  failures: {len(problems)}")
    for alert in fetched:
        print(alert["identifier"], alert.get("severity"), alert.get("event"), "|", alert.get("area"))
