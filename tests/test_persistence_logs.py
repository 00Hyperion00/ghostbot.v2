from tradebot.models import LogEvent
from tradebot.persistence import SQLiteStore



def test_fetch_logs_supports_limit_zero_and_order(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'test.db'))
    store.append_log(LogEvent(ts=1, level='INFO', code='A', message='one'))
    store.append_log(LogEvent(ts=2, level='INFO', code='B', message='two'))
    store.append_log(LogEvent(ts=3, level='INFO', code='C', message='three'))

    asc = store.fetch_logs(limit=0, order='asc')
    desc = store.fetch_logs(limit=2, order='desc')

    assert [item['code'] for item in asc] == ['A', 'B', 'C']
    assert [item['code'] for item in desc] == ['C', 'B']
