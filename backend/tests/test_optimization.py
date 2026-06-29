"""Deterministic tests for the route optimizer — no model, no ADK."""
from atlas.optimization.route import (
    haversine_km, distance_matrix, nearest_neighbor_order, two_opt,
    allocate_days, optimize_route,
)


def test_haversine_known_distance():
    # Tokyo to Kyoto is roughly 360 km as the crow flies.
    assert 330 < haversine_km((35.68, 139.69), (35.01, 135.77)) < 390


def test_allocate_days_sums_to_total_and_weights():
    days = allocate_days([2, 1, 1], total_days=10)
    assert sum(days) == 10
    assert all(d >= 1 for d in days)     # every stop gets at least a day
    assert days[0] == max(days)          # heaviest stop gets the most


def test_two_opt_never_worse_than_nearest_neighbor():
    pts = [(35.68, 139.69), (35.01, 135.77), (34.69, 135.50), (36.14, 137.25), (35.92, 139.48)]
    m = distance_matrix(pts)
    nn = nearest_neighbor_order(m)
    opt = two_opt(nn, m)
    nn_len = sum(m[nn[i]][nn[i + 1]] for i in range(len(nn) - 1))
    opt_len = sum(m[opt[i]][opt[i + 1]] for i in range(len(opt) - 1))
    assert opt_len <= nn_len + 1e-9


def test_optimize_route_orders_and_allocates():
    areas = [
        {"name": "Tokyo", "region": "Kanto", "latitude": 35.68, "longitude": 139.69, "weight": 4},
        {"name": "Kyoto", "region": "Kansai", "latitude": 35.01, "longitude": 135.77, "weight": 3},
        {"name": "Hakone", "region": "Kanto", "latitude": 35.23, "longitude": 139.02, "weight": 2},
    ]
    route = optimize_route(areas, total_days=9)
    assert {a["name"] for a in route} == {"Tokyo", "Kyoto", "Hakone"}
    assert sum(a["days"] for a in route) == 9
    assert route[0]["day_start"] == 1
    for prev, cur in zip(route, route[1:]):          # contiguous day ranges
        assert cur["day_start"] == prev["day_end"] + 1