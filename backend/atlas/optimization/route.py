"""Pure, dependency-free route optimization. No ADK, no LLM — just geometry and
heuristics, so it is fully deterministic and unit-testable."""
from __future__ import annotations

import math
from typing import Sequence

Coord = tuple[float, float]  # (latitude, longitude)


def haversine_km(a: Coord, b: Coord) -> float:
    """Great-circle distance between two (lat, lng) points, in kilometers."""
    radius = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def distance_matrix(points: Sequence[Coord]) -> list[list[float]]:
    """Symmetric matrix of pairwise great-circle distances."""
    return [[haversine_km(p, q) for q in points] for p in points]


def _route_length(order: Sequence[int], matrix: Sequence[Sequence[float]]) -> float:
    return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def nearest_neighbor_order(matrix: Sequence[Sequence[float]], start: int = 0) -> list[int]:
    """Greedy TSP construction: always hop to the closest unvisited node."""
    n = len(matrix)
    if n == 0:
        return []
    visited = [start]
    unvisited = set(range(n)) - {start}
    while unvisited:
        last = visited[-1]
        nxt = min(unvisited, key=lambda j: matrix[last][j])
        visited.append(nxt)
        unvisited.discard(nxt)
    return visited


def two_opt(order: list[int], matrix: Sequence[Sequence[float]]) -> list[int]:
    """Local-search refinement: reverse segments while it shortens the route."""
    best = list(order)
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue
                candidate = best[:i] + best[i:j][::-1] + best[j:]
                if _route_length(candidate, matrix) < _route_length(best, matrix) - 1e-9:
                    best = candidate
                    improved = True
    return best


def allocate_days(weights: Sequence[float], total_days: int) -> list[int]:
    """Spread total_days across stops: one each minimum, the rest by weight."""
    n = len(weights)
    if n == 0:
        return []
    if total_days <= n:
        # Not enough days for every stop — give a day each to the heaviest stops.
        ranked = sorted(range(n), key=lambda i: weights[i], reverse=True)
        days = [0] * n
        for i in ranked[:total_days]:
            days[i] = 1
        return days
    base = [1] * n
    remaining = total_days - n
    total_w = sum(weights) or float(n)
    extra = [int(remaining * (w / total_w)) for w in weights]
    days = [b + e for b, e in zip(base, extra)]
    # Hand out any rounding leftovers to the heaviest stops.
    leftover = total_days - sum(days)
    ranked = sorted(range(n), key=lambda i: weights[i], reverse=True)
    k = 0
    while leftover > 0:
        days[ranked[k % n]] += 1
        leftover -= 1
        k += 1
    return days


def optimize_route(areas: list[dict], total_days: int) -> list[dict]:
    """Order `areas` to minimize travel, then allocate days.

    Each area dict needs: name, region, latitude, longitude, and weight (relative
    importance, e.g. how many interests it matches). Returns a new list in visit
    order, each augmented with days, day_start, and day_end. Stops that don't fit in
    the day budget are dropped.
    """
    if not areas:
        return []
    points: list[Coord] = [(a["latitude"], a["longitude"]) for a in areas]
    matrix = distance_matrix(points)
    order = two_opt(nearest_neighbor_order(matrix), matrix)
    ordered = [areas[i] for i in order]
    weights = [max(1.0, float(a.get("weight", 1))) for a in ordered]
    days = allocate_days(weights, total_days)
    result: list[dict] = []
    cursor = 1
    for area, d in zip(ordered, days):
        if d <= 0:
            continue
        result.append({**area, "days": d, "day_start": cursor, "day_end": cursor + d - 1})
        cursor += d
    return result