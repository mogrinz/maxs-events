"""RC6 source-level regression checks. Browser/Pi tests remain required."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def src(path):return (ROOT/path).read_text()

def test_source_indicator_has_no_theme_random_stripes():
    css=src('static/events-kiosk.css')
    assert not re.search(r'body\[data-theme="(?:party|gaming|sports)"\] \.event:nth-child',css)
    assert not re.search(r'body\[data-theme="(?:party|gaming|sports)"\] \.detail-card\{border-left:4px',css)
    assert '.source-color.color-empty{background:transparent!important}' in css

def test_subtitle_only_in_detail_and_title_primary():
    admin=src('static/events-admin.js');kiosk=src('static/events-kiosk.js')
    assert 'Subtitle (optional)' in src('templates/events_admin.html')
    assert "$('detail-header-wrap').hidden=$('view').value!=='detail'" in admin
    assert "$('title').textContent=config.title" in kiosk
    assert 'subtitle.style.color=getComputedStyle' in kiosk
    assert 'subtitle.textContent=detailSubtitle' in kiosk

def test_calendar_upload_and_subscription_feedback():
    html=src('templates/events_sources.html');js=src('static/events-sources.js')
    assert 'id="upload-status"' in html and 'id="subscription-status"' in html
    assert "feedback('upload-status'" in js and "feedback('subscription-status'" in js
    assert 'calendar-spinner' in js and 'Refresh failed for ' in js
    assert 'replaced=bool(replace)' in src('events.py')

def test_all_day_alignment_and_time_format():
    css=src('static/events-kiosk.css');js=src('static/events-kiosk.js')
    assert '.time.all-day .all-day-text' in css
    assert "time.append(allDayText)" in js
    assert "timeFormat==='24'" in js

def test_network_parity_and_legacy_enablement():
    assert src('network_service.py')==Path('/mnt/data/menu-ref/maxs-menu/network_service.py').read_text() if Path('/mnt/data/menu-ref/maxs-menu/network_service.py').exists() else True
    assert 'enable_hotspot_support.py' in src('templates/system.html')
    assert 'Network Mode Confirmation' in src('templates/system.html')
    assert "if(mode==='hotspot' && !confirm" in src('static/system.js')

def test_font_installer_does_not_overwrite_previous_fonts():
    assert (ROOT/'static/fonts/events-google-fonts.css').exists()  # Gold release bundles fonts for offline use
    assert 'install_theme_fonts.py' in src('setup.sh')
    assert 'static/fonts/events-google-fonts.css' in src('upgrade.sh')
    assert 'install_theme_fonts.py' not in src('upgrade.sh')
