from pathlib import Path

from tradebot.ui.dashboard import DashboardApp


def test_extract_training_output_path_dict_line():
    app = DashboardApp.__new__(DashboardApp)
    line = "{'symbol': 'SOLUSDT', 'output': 'C:/tmp/models/SOLUSDT_model.ubj', 'accuracy': 0.42}"
    assert app._extract_training_output_path(line) == 'C:/tmp/models/SOLUSDT_model.ubj'


def test_resolve_training_output_path_forces_ubj(tmp_path: Path):
    app = DashboardApp.__new__(DashboardApp)
    app.project_root = tmp_path

    class Entry:
        def get(self):
            return 'models/SOLUSDT_model.json'

    app.form = {'ai_model_path': Entry()}
    out = app._resolve_training_output_path('SOLUSDT')
    assert out.suffix == '.ubj'
    assert out.as_posix().endswith('/models/SOLUSDT_model.ubj')
