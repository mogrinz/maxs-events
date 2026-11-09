"""Static regression checks for PDF theme refresh, no Flask dependency."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/'static/events-kiosk.css').read_text()
JS=(ROOT/'static/events-themes.js').read_text()
FONTS=json.loads((ROOT/'theme-fonts.json').read_text())
THEMES=['academic','conference','festival','gaming','holiday','memorial','mixers','museum','party','religious','sports','training','vacation','wedding','wellness']


def test_all_theme_ids_are_preserved():
    for key in THEMES:
        assert f'body[data-theme="{key}"]' in CSS


def test_pdf_font_families_and_colors():
    for name in ['Great Vibes','Montserrat','DM Serif Display','Press Start 2P','Bungee','Berkshire Swash','Sora','Anton','Libre Baskerville','Bebas Neue','Crimson Pro','Alegreya','Pacifico','Fraunces']:
        assert name in CSS
    for color in ['#F6F0E7','#0F2A4A','#1E1D1B','#0A0E1A','#1B0B33','#0E7C86','#F3F5EF']:
        assert color in CSS
    assert len(FONTS)>=60


def test_dropdown_sort_and_custom_selection():
    assert '.sort((a,b)=>a[1].localeCompare(b[1]))' in JS
    assert "new Option('--- Custom ---','custom')" in JS
    assert "customOptions" in JS
    assert 'gaming' in JS and 'Retro' in JS
    assert 'mixers' in JS and 'Mixer' in JS


def test_css_cache_version():
    assert 'events-kiosk.css?v=' in (ROOT/'templates/events_kiosk.html').read_text()
