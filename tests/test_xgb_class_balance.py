import math

from tradebot.training.class_balance import build_sample_weights, get_class_weight_map, serialize_class_weight_map


def test_none_profile_returns_unit_weights():
    weights, weight_map = build_sample_weights([0, 0, 1, 2], profile='none')
    assert all(math.isclose(float(value), 1.0) for value in weights)
    assert weight_map == {0: 1.0, 1: 1.0, 2: 1.0}


def test_balanced_profile_boosts_minority_classes():
    weight_map = get_class_weight_map([0, 0, 0, 0, 1, 2], profile='balanced')
    assert weight_map[1] > weight_map[0]
    assert weight_map[2] > weight_map[0]
    assert math.isclose(sum(weight_map.values()) / len(weight_map), 1.0, rel_tol=1e-9)


def test_buy_sell_boost_medium_profile_prefers_action_classes():
    weight_map = get_class_weight_map([0, 0, 1, 2], profile='buy_sell_boost_medium')
    assert weight_map[1] > weight_map[0]
    assert weight_map[2] > weight_map[0]
    serialized = serialize_class_weight_map(weight_map)
    assert set(serialized) == {'0', '1', '2'}
