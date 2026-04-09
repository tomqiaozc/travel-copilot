from collections import defaultdict

from app.maps.distance import calculate_distance_km


def assign_to_days(new_places: list[dict], existing_places: list[dict]) -> list[dict]:
    """Assign new places to days using nearest-day + cheapest-insertion.

    Args:
        new_places: list of dicts with latitude/longitude set.
        existing_places: list of existing trip places with day_number/order_in_day.

    Returns:
        new_places with day_number and order_in_day set.
    """
    # Build working structure: day_number -> ordered list of places
    days: dict[int, list[dict]] = defaultdict(list)
    for p in existing_places:
        dn = p.get("day_number")
        if dn is not None:
            days[dn].append(p)

    # Sort each day by order_in_day
    for dn in days:
        days[dn].sort(key=lambda x: x.get("order_in_day", 0))

    for np in new_places:
        lat = np.get("latitude")
        lon = np.get("longitude")
        if lat is None or lon is None:
            np["day_number"] = 1
            np["order_in_day"] = len(days.get(1, []))
            days[1].append(np)
            continue

        # DAY SELECTION: pick day with minimum average distance
        if not days:
            best_day = 1
        else:
            best_day = None
            best_avg = float("inf")
            for dn, day_places in days.items():
                coords = [(p["latitude"], p["longitude"]) for p in day_places
                          if p.get("latitude") is not None and p.get("longitude") is not None]
                if not coords:
                    continue
                avg_dist = sum(
                    calculate_distance_km(lat, lon, c[0], c[1]) for c in coords
                ) / len(coords)
                if avg_dist < best_avg:
                    best_avg = avg_dist
                    best_day = dn
            if best_day is None:
                best_day = 1

        # POSITION SELECTION: cheapest insertion
        day_places = days[best_day]
        coords_list = [(p.get("latitude"), p.get("longitude")) for p in day_places]

        if len(day_places) == 0:
            insert_pos = 0
        elif len(day_places) == 1:
            insert_pos = 1
        else:
            best_cost = float("inf")
            insert_pos = len(day_places)  # default: append

            # Check inserting at the beginning (position 0)
            first_lat, first_lon = coords_list[0]
            if first_lat is not None and first_lon is not None:
                cost_front = calculate_distance_km(lat, lon, first_lat, first_lon)
                if cost_front < best_cost:
                    best_cost = cost_front
                    insert_pos = 0

            # Check inserting between adjacent places (positions 1..N-1)
            for i in range(len(day_places) - 1):
                p_i_lat, p_i_lon = coords_list[i]
                p_next_lat, p_next_lon = coords_list[i + 1]
                if any(c is None for c in [p_i_lat, p_i_lon, p_next_lat, p_next_lon]):
                    continue
                cost = (
                    calculate_distance_km(p_i_lat, p_i_lon, lat, lon)
                    + calculate_distance_km(lat, lon, p_next_lat, p_next_lon)
                    - calculate_distance_km(p_i_lat, p_i_lon, p_next_lat, p_next_lon)
                )
                if cost < best_cost:
                    best_cost = cost
                    insert_pos = i + 1

            # Check inserting at the end (position N)
            last_lat, last_lon = coords_list[-1]
            if last_lat is not None and last_lon is not None:
                cost_end = calculate_distance_km(last_lat, last_lon, lat, lon)
                if cost_end < best_cost:
                    insert_pos = len(day_places)

        # Insert into working structure; only set order on new place
        np["day_number"] = best_day
        np["order_in_day"] = insert_pos
        day_places.insert(insert_pos, np)

    return new_places
