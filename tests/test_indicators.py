from tradebot.indicators import ema, rsi
from tradebot.utils import infer_dust, round_down_to_step


def test_round_down_to_step():
    assert round_down_to_step(0.294705, 0.001) == 0.294


def test_infer_dust():
    assert abs(infer_dust(0.294705, 0.001) - 0.000705) < 1e-9


def test_ema_shapes():
    values = [1, 2, 3, 4, 5, 6]
    result = ema(values, 3)
    assert len(result) == len(values)
    assert result[-1] is not None


def test_rsi_shapes():
    values = [1, 2, 3, 4, 5, 4, 3, 4, 5, 6, 7, 6, 5, 6, 7, 8]
    result = rsi(values, 14)
    assert len(result) == len(values)
