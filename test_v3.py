import tempfile
from pathlib import Path
from flask import Flask
from enterprise_v3 import VERSION, connect, create_or_update_admin, init_enterprise_db, register_enterprise_v3

def make_app(tmp):
    app=Flask(__name__,root_path=str(Path(__file__).parent));app.config.update(TESTING=True,V3_DATABASE=str(Path(tmp)/'audit.db'),SECRET_KEY='test-secret')
    register_enterprise_v3(app)
    return app

def test_version(): assert VERSION=='3.0.0'

def test_schema_and_login():
    with tempfile.TemporaryDirectory() as tmp:
        app=make_app(tmp)
        with app.app_context():
            create_or_update_admin('admin','StrongPass_2026!')
            with connect() as conn:
                assert conn.execute("SELECT COUNT(*) FROM v3_roles").fetchone()[0]>=6
                assert conn.execute("SELECT COUNT(*) FROM v3_permissions").fetchone()[0]>=10
        client=app.test_client();r=client.get('/v3/login');assert r.status_code==200
        with client.session_transaction() as s: token=s['v3_csrf']
        r=client.post('/v3/login',data={'csrf_token':token,'username':'admin','password':'StrongPass_2026!'},follow_redirects=False)
        assert r.status_code in (302,303)
        r=client.get('/v3/health');assert r.json['version']=='3.0.0'

def test_dashboard_after_login():
    with tempfile.TemporaryDirectory() as tmp:
        app=make_app(tmp)
        with app.app_context(): create_or_update_admin('admin','StrongPass_2026!')
        c=app.test_client();c.get('/v3/login')
        with c.session_transaction() as s: token=s['v3_csrf']
        c.post('/v3/login',data={'csrf_token':token,'username':'admin','password':'StrongPass_2026!'})
        r=c.get('/v3/');assert r.status_code==200;assert 'Kurumsal Gösterge Paneli'.encode() in r.data
