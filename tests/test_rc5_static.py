"""RC5 source-level regressions runnable without Pi/Flask dependencies."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def text(path):return (ROOT/path).read_text()

def test_time_format_api_and_kiosk():
    assert 'def set_time_format' in text('models.py')
    assert '"12", "24"' in text('models.py')
    assert '/api/admin/system/time-format' in text('app.py')
    assert 'id="time-format"' in text('templates/system.html')
    assert 'time_format=store.state()' in text('events.py')
    js=text('static/events-kiosk.js')
    assert "timeFormat==='24'" in js
    assert 'd.theme,d.custom_theme_id,d.detail_status,d.time_format,d.display_date' in js

def test_detail_header():
    assert "c.setdefault('detail_header', '')" in text('events.py')
    assert "len(body['detail_header'])>100" in text('events.py')
    assert 'Subtitle (optional)' in text('templates/events_admin.html')
    assert "config.detail_header?.trim()" in text('static/events-kiosk.js')
    assert 'id="detail-subtitle"' in text('templates/events_kiosk.html')

def test_same_filename_preserves_source():
    js=text('static/events-sources.js')
    assert "f.set('replace_id',$('replace').value)" in js
    src=text('events.py')
    assert "s['name'].casefold()==name.casefold() and s['type']=='file'" in src
    assert "replace=src['id']" in src
    assert "src.setdefault('nickname',src['name'])" in src
    assert "src.setdefault('color','')" in src

def test_flash_and_alignment():
    html=text('templates/events_kiosk.html')
    css=text('static/events-kiosk.css')
    js=text('static/events-kiosk.js')
    assert 'class="kiosk-loading"' in html
    assert 'body.kiosk-loading #kiosk-shell' in css
    assert "document.body.classList.remove('kiosk-loading')" in js
    assert '.time.all-day{padding-bottom:' in css
    assert 'getComputedStyle(timeNode)' in js
    assert 'ctx.measureText' in js
    assert "--dash-width',widths.dash" in js
