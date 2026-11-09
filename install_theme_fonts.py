#!/usr/bin/env python3
"""Verify fully bundled Google Fonts, no network required for installation."""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
css=ROOT/'static/fonts/events-google-fonts.css'
specs=json.loads((ROOT/'theme-fonts.json').read_text())
if not css.is_file():raise SystemExit('ERROR: Bundled font CSS is missing.')
content=css.read_text()
blocks=re.findall(r'@font-face\s*\{[^}]*\}',content,re.S)
problems=[]
for item in specs:
    family=item['family'];weight=str(item['weight']);style='italic' if item['italic'] else 'normal'
    eligible=[]
    for block in blocks:
        def prop(name):
            m=re.search(r'(?<![\w-])'+re.escape(name)+r'\s*:\s*([^;]+);',block)
            return (m.group(1).strip().strip('"\'') if m else '')
        if (prop('font-family')==family and prop('font-weight')==weight and prop('font-style')==style):eligible.append(block)
    if not eligible:problems.append(f'{family} {weight} {style}: no matching @font-face')
for basename in re.findall(r'/static/fonts/([^"\')]+\.woff2)',content):
    path=css.parent/basename
    if not path.is_file() or path.stat().st_size<1000:problems.append(f'Missing or invalid font: {basename}')
if problems:
    raise SystemExit('Incomplete bundled font assets:\n'+'\n'.join(problems))
print(f'PASS: All {len(specs)} bundled font variants verified locally; no Internet needed for fonts.')
