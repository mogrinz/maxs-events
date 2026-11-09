"""RC7 regression checks that run without Flask/icalendar or a physical Pi."""
import ast
from datetime import datetime
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
def src(path):return (ROOT/path).read_text()

def load_functions(*names):
    source=ast.parse(src('events.py'))
    functions=[node for node in source.body if isinstance(node,ast.FunctionDef) and node.name in names]
    import re
    namespace={'datetime':datetime,'date':__import__('datetime').date,'re':re,'MAX_CSS':128*1024}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<isolated functions>','exec'),namespace)
    return namespace

def test_detail_reference_uses_current_time_on_custom_date():
    fn=load_functions('detail_reference')['detail_reference']
    now=datetime.fromisoformat('2026-11-05T10:22:30-05:00')
    assert fn(now,'2026-10-30')==datetime.fromisoformat('2026-10-30T10:22:30-05:00')
    assert fn(now,None)==now

def test_detail_selection_excludes_past_events_on_custom_date():
    funcs=load_functions('detail_reference','detail_selection')
    ref=funcs['detail_reference'](datetime.fromisoformat('2026-11-05T10:22:00-04:00'),'2026-10-30')
    def event(title,start,end):return {'title':title,'start':'2026-10-30T'+start+'-04:00','end':'2026-10-30T'+end+'-04:00','all_day':False}
    rows=[event('Doors Open','08:30:00','09:15:00'),event('Welcome','09:00:00','09:45:00'),event('Panel','11:00:00','12:00:00'),event('Workshop','13:00:00','14:00:00')]
    featured,later=funcs['detail_selection'](rows,ref)
    assert featured['title']=='Panel' and later['title']=='Workshop'

def test_css_validation_and_security():
    validate=load_functions('validate_custom_css')['validate_custom_css']
    assert 'color:red' in validate(b'body { color:red }')
    for content in [b'',b'a'*131073,b'@import "https://x"; body{color:red}',b'body{background:url(https://x)}',b'body{color:expression(alert(1))}',b'\xff']:
        with pytest.raises(ValueError):validate(content)

def test_theme_routes_and_persistent_storage():
    code=src('events.py')
    for path in ('/api/admin/events/custom-themes/upload','/api/admin/events/custom-themes/<theme_id>/delete','/api/events/custom-theme/<theme_id>.css'):
        assert path in code
    assert "store.root / 'custom-themes'" in code
    assert "d.setdefault('custom_themes', [])" not in code  # uses data migration, not temporary in-memory state
    assert "data.setdefault('custom_themes', [])" in code
    assert "z.write(path,'custom-themes/'" in code
    assert "chosen=='custom'" in code

def test_theme_ui_and_kiosk_loading():
    html=src('templates/events_themes.html')
    js=src('static/events-themes.js')
    kiosk=src('static/events-kiosk.js')
    assert 'maxs-events-custom-theme.css' in html
    assert 'custom-theme-file' in html and 'custom-theme-delete' in html
    assert "new Option('--- Custom ---','custom')" in js
    assert "form.set('file',file)" in js
    assert "applyTheme(d.theme,d.custom_theme_id)" in kiosk
    assert 'detailStatus=d.detail_status' in kiosk
    assert "label.textContent=detailStatus" in kiosk
    assert 'link.disabled=false' in kiosk

def test_calendar_sources_and_hotspot_fixes():
    js=src('static/events-sources.js')
    assert "a.href=source.url" in js
    assert "refresh.textContent='Refresh'" in js
    assert "status('Refresh failed for '" in js
    assert 'os.chown(state_path,state_stat.st_uid,state_stat.st_gid)' in src('enable_hotspot_support.py')
    assert '(request.path == "/api/admin/system/restore"' in src('app.py')
    assert 'if isinstance(error, PermissionError)' in src('app.py')
