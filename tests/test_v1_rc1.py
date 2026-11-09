"""Static and isolated migration checks for v1.0 RC1 (no Flask dependency)."""
import ast
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

def source(name):return (ROOT/name).read_text()

def isolated(*names):
    tree=ast.parse(source('events.py'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    ns={'json':json,'Path':Path,'EVENT_SCREEN_IDS':frozenset(f'screen{i}' for i in range(1,21))}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<events>', 'exec'),ns)
    return ns

def test_migration_preserves_existing_screens_and_adds_ten():
    f=isolated('empty','normalize_screen','data_path','load')
    old=f['empty']()
    for n in range(11,21):old['screens'].pop(f'screen{n}')
    old['screens']['screen1']['title']='Existing lobby'
    old['screens']['screen10']['source_ids']=['calendar-a']
    with tempfile.TemporaryDirectory() as tmp:
        store=SimpleNamespace(root=Path(tmp))
        (store.root/'events.json').write_text(json.dumps(old))
        f['save']=lambda store,d:(store.root/'events.json').write_text(json.dumps(d))
        result=f['load'](store)
        assert len(result['screens'])==20
        assert result['screens']['screen1']['title']=='Existing lobby'
        assert result['screens']['screen10']['source_ids']==['calendar-a']
        assert result['screens']['screen20']['theme_override']==''
        assert len(json.loads((store.root/'events.json').read_text())['screens'])==20

def test_routes_and_screen_validation():
    s=source('events.py')
    assert "@app.get('/display/screen<int:n>')" in s
    assert "@app.get('/screen<int:n>')" in s
    assert 'range(1,21)' in s
    assert 'EVENT_SCREEN_IDS' in s
    assert 'effective_theme=config[' in s
    assert "theme_override']=='custom'" in s
    assert 'screen_config[\'theme_override\']=\'\'' in s
    assert 'request.args.get(\'orientation_preview\') if g.user else None' in s
    app=source('app.py')
    assert 're.fullmatch(r"/display/screen' in app
    assert 'render_template(\'events_kiosk.html\'' in app

def test_browser_rotation_and_preview():
    js=source('static/events-kiosk.js')
    css=source('static/events-kiosk.css')
    admin=source('static/events-admin.js')
    assert 'transform:rotate(90deg)' in css
    assert 'left:100vw;width:100vh;height:100vw' in css
    assert 'innerWidth>innerHeight' in js
    assert "editorPreview=query.get('editor_preview')==='1'" in js
    assert 'portrait-preview' in admin
    assert 'for(let i=1;i<=20;i++)' in admin
    assert "'/display/screen'+screen.value.slice(6)" in admin
    assert 'id="kiosk-shell"' in source('templates/events_kiosk.html')

def test_exactly_nineteen_examples_and_daily_room_recurrence():
    examples=list((ROOT/'examples').glob('*.ics'))
    assert len(examples)==19
    for name in ('a','b','c','d'):
        content=(ROOT/f'examples/demo-room-{name}.ics').read_text()
        assert content.count('RRULE:FREQ=DAILY')==4
    assert not (ROOT/'examples/hamradio-sample.ics').exists()
    assert (ROOT/'static/examples/maxs-events-custom-theme.css').exists()

def test_upgrade_preserves_network_settings_and_data():
    upgrade=source('upgrade.sh')
    assert 'systemctl restart maxs-events.service' in upgrade
    assert 'network_controller' not in upgrade
    assert 'rm -' not in upgrade
