"""v1.0 RC2 source-level checks that do not require Flask."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_maximum_visible_events_extended_everywhere():
    assert 'range(1,16)' in (ROOT/'templates/events_admin.html').read_text()
    assert "1<=body['max_visible']<=15" in (ROOT/'events.py').read_text()
    js=(ROOT/'static/events-kiosk.js').read_text()
    assert 'Math.min(15,Math.max(1,Number(config.max_visible)||5))' in js
    assert 'Math.min(15,Number(config.max_visible)||5)' in js
    assert 'rows.length>count' in js
    assert 'rows.length>slots' in js

def test_portrait_scaling_and_landscape_preservation():
    js=(ROOT/'static/events-kiosk.js').read_text()
    assert "if(config.orientation==='portrait'){portraitLayout(v,track,count,gap);return;}" in js
    assert 'const portraitScale=1;' in js
    assert 'Math.max(14,Math.min(38,w*.028,h*.055))*portraitScale' in js
    assert 'Math.max(12,Math.min(27,w*.021,h*.042))*portraitScale' in js
    assert 'Math.max(12,Math.min(39,w*.026,h*.057))*portraitScale' in js
    assert 'const maxTimeWidth=w*.58' in js
    assert 'if(widths.needed>maxTimeWidth)' in js
    assert 'Math.max(normalHeight,textHeight)' in js

def test_upgrade_preserves_application_data():
    s=(ROOT/'upgrade.sh').read_text()
    assert 'systemctl restart maxs-events.service' in s
    assert 'network_service' not in s
    assert 'rm -' not in s
    assert 'data' in s

def test_equal_start_end_time_shows_only_start_in_list_and_detail():
    js=(ROOT/'static/events-kiosk.js').read_text()
    css=(ROOT/'static/events-kiosk.css').read_text()
    assert 'function sameDisplayTime(r)' in js
    assert "fmtTime(r.start)!==fmtTime(r.end)" in js
    assert "sameDisplayTime(r)?'':' – '+fmtTime(r.end)" in js
    assert "time.classList.add('single-time');time.append(s)" in js
    assert 'time.textContent=timeText(r)' in js
    assert '.time.single-time' in css
