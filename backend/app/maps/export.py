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
