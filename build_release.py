#!/usr/bin/env python3
"""Build the standalone offline Max's Events distribution from the source tree."""
import hashlib, pathlib, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parent
OMIT={'.events.env','.menu.env','.env','SHA256SUMS'}
OMIT_DIRS={'.git','.venv','data','__pycache__','.pytest_cache','patch-backups'}
OMIT_PREFIX=('maxs-events-backup','maxs-menu-backups','pre-restore-backups')
SUFFIXES={'.py','.sh','.js','.css','.html','.svg','.ttf','.woff','.woff2','.txt','.json','.md','.ics','.yml','.yaml'}

def build(output):
    output=pathlib.Path(output).resolve()
    if output.suffix!='.zip' or output.is_relative_to(ROOT):
        raise ValueError('Output ZIP must be outside source tree')
    selected=[]
    for f in ROOT.rglob('*'):
        if not f.is_file():continue
        r=f.relative_to(ROOT)
        if f.is_symlink():raise ValueError(f'Symlink not allowed: {r}')
        if any(part in OMIT_DIRS or part.startswith(OMIT_PREFIX) for part in r.parts):continue
        if f.name in OMIT or (f.suffix=='.json' and 'backup' in f.name.lower()) or (f.suffix not in SUFFIXES and f.name not in {'.gitignore','LICENSE'}):continue
        if f.suffix in {'.pyc','.log'}:continue
        selected.append((r.as_posix(),f.read_bytes()))
    paths={n for n,_ in selected}
    required={'app.py','events.py','models.py','setup.sh','install_service.py','install_theme_fonts.py','theme-fonts.json','README.md','LICENSE','static/fonts/events-google-fonts.css'}
    if required-paths:raise ValueError('Required files missing: '+str(sorted(required-paths)))
    if not any(n.endswith('.woff2') for n in paths):raise ValueError('Bundled WOFF2 fonts missing')
    selected.sort()
    manifest=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in selected)
    selected.append(('SHA256SUMS',manifest.encode()))
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in selected:
            info=zipfile.ZipInfo('maxs-events/'+name,date_time=(2026,11,8,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=((0o100755 if name.endswith('.sh') else 0o100644)<<16)
            z.writestr(info,data)
    with zipfile.ZipFile(output) as z:
        assert not z.testzip()
    return output,len(selected)
if __name__=='__main__':
    out,count=build(sys.argv[1] if len(sys.argv)>1 else ROOT.parent/'maxs-events-v1.0-offline.zip')
    print(f'{out}: {count} files SHA256 {hashlib.sha256(out.read_bytes()).hexdigest()}')
