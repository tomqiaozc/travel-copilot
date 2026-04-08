def generate_google_maps_url(places: list) -> str:
    """Generate a Google Maps directions URL for a list of ordered places."""
    if not places:
        return ""

    waypoints = []
    for p in places:
        place_id = p.get("google_place_id")
        if place_id:
            waypoints.append(f"place_id:{place_id}")
        else:
            lat = p.get("latitude")
            lng = p.get("longitude")
            if lat and lng:
                waypoints.append(f"{lat},{lng}")

    if not waypoints:
        return ""

    # Google Maps directions URL format
    base = "https://www.google.com/maps/dir/"
    return base + "/".join(waypoints)


def generate_export_links(places: list) -> list:
    """Generate per-day Google Maps links."""
    # Group by day
    days = {}
    for p in places:
        day = p.get("day_number")
        if day is not None:
            days.setdefault(day, []).append(p)

    # Sort each day by order_in_day
    links = []
    for day_num in sorted(days.keys()):
        day_places = sorted(days[day_num], key=lambda x: x.get("order_in_day") or 0)
        url = generate_google_maps_url(day_places)
        links.append({"day": day_num, "url": url, "place_count": len(day_places)})

    return links


import xml.etree.ElementTree as ET


def generate_kml(places: list, trip_name: str) -> str:
    """Generate a KML file with places grouped by day as folders."""
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = ET.SubElement(kml, "Document")
    ET.SubElement(document, "name").text = trip_name

    # Group by day, skip places without coordinates
    days: dict = {}
    for p in places:
        if not p.get("latitude") or not p.get("longitude"):
            continue
        day = p.get("day_number")
        days.setdefault(day, []).append(p)

    for day_key in days:
        days[day_key].sort(key=lambda x: x.get("order_in_day") or 0)

    # Numbered days first, then unassigned
    sorted_keys = sorted((k for k in days if k is not None), key=int)
    if None in days:
        sorted_keys.append(None)

    for day_key in sorted_keys:
        folder = ET.SubElement(document, "Folder")
        folder_name = f"Day {day_key}" if day_key is not None else "Unassigned"
        ET.SubElement(folder, "name").text = folder_name

        for p in days[day_key]:
            placemark = ET.SubElement(folder, "Placemark")
            ET.SubElement(placemark, "name").text = p.get("name", "")

            desc_parts = [p.get("type", "")]
            if p.get("note"):
                desc_parts.append(p["note"])
            ET.SubElement(placemark, "description").text = " · ".join(desc_parts)

            point = ET.SubElement(placemark, "Point")
            ET.SubElement(point, "coordinates").text = (
                f"{p['longitude']},{p['latitude']},0"
            )

    return ET.tostring(kml, encoding="unicode", xml_declaration=True)
