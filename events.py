"""Calendar source management and 20-screen kiosk for Max's Events."""
import ipaddress
import json
import os
import re
import socket
import threading
import time
import uuid
from datetime import datetime, date, timedelta, timezone, time as dtime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from flask import abort, jsonify, render_template, request, g, session
from icalendar import Calendar
import recurring_ical_events

EVENT_THEMES = ('wedding','party','holiday','conference','mixers','training','gaming','festival','academic','sports','museum','religious','memorial','vacation','wellness')
MAX_ICS = 2 * 1024 * 1024
MAX_CSS = 128 * 1024
CUSTOM_THEME_LIMIT = 30
EVENT_SCREEN_IDS = frozenset(f'screen{i}' for i in range(1, 21))
LOCK = threading.RLock()


def empty():
    return {'theme': 'conference', 'custom_theme_id': '', 'custom_themes': [], 'sources': [], 'screens': {f'screen{i}': {
        'title': '', 'detail_header': '', 'source_ids': [], 'view': 'list', 'color_code': False,
        'show_legend': False, 'include_all_day': False, 'orientation': 'landscape', 'mode': 'today',
        'hide_ended': True, 'future_hours': 'all', 'scroll': False, 'max_visible': 5,
        'date_mode': 'today', 'custom_date': '', 'show_description': True,
        'theme_override': '', 'custom_theme_id': ''
    } for i in range(1, 21)}}


# Activity data is independent of the original Max's Menu history/rollback state.
def history_path(store):
    return store.root / 'events-history.json'


def read_history(store):
    path=history_path(store)
    if not path.exists(): return {'retention_days':90,'entries':[]}
    result=json.loads(path.read_text())
    if result.get('retention_days') not in (30,90,180,365,'forever'):
        result['retention_days']=90
    if not isinstance(result.get('entries'),list): result['entries']=[]
    return result


def prune_history(data):
    days=data['retention_days']
    if days!='forever':
        cutoff=datetime.now(timezone.utc)-timedelta(days=days)
        data['entries']=[r for r in data['entries'] if datetime.fromisoformat(r['time'])>=cutoff]
    data['entries']=data['entries'][:3000]
    return data


def history_read(store):
    from models import atomic_json
    with LOCK:
        d=read_history(store)
        before=len(d['entries'])
        prune_history(d)
        if len(d['entries'])!=before:atomic_json(history_path(store),d)
        return d


def activity(store, actor, action):
    from models import atomic_json
    name=actor.get('username','system') if isinstance(actor,dict) else str(actor)
    with LOCK:
        d=read_history(store)
        d['entries'].insert(0,{'time':datetime.now(timezone.utc).isoformat(),'actor':name[:100],'action':str(action)[:300]})
        atomic_json(history_path(store),prune_history(d))


def data_path(store):
    return store.root / 'events.json'


def load(store):
    path=data_path(store)
    if not path.exists():
        save(store,empty())
    data=json.loads(path.read_text())
    data.setdefault('custom_themes', [])
    data.setdefault('custom_theme_id', '')
    # Preserve all ten existing screens and create screens 11-20 only if missing.
    defaults = empty()['screens']
    missing = [sid for sid in defaults if sid not in data.setdefault('screens', {})]
    if missing:
        for sid in missing: data['screens'][sid] = defaults[sid]
        save(store, data)
    for key,config in data.get('screens',{}).items():
        data['screens'][key]=normalize_screen(config)
    for src in data.get('sources',[]):
        src.setdefault('nickname',src['name']);src.setdefault('color','')
    return data


def save(store, d):
    from models import atomic_json
    atomic_json(data_path(store), d)


def custom_theme_file(store, theme_id):
    # Only generated UUID identifiers reach the filesystem.
    if not isinstance(theme_id, str) or not re.fullmatch(r'[0-9a-f]{32}', theme_id):
        raise ValueError('Invalid custom theme ID')
    return store.root / 'custom-themes' / (theme_id + '.css')


def validate_custom_css(data):
    if not data or len(data) > MAX_CSS:
        raise ValueError('CSS file must be between 1 byte and 128 KB.')
    try:
        css = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('CSS must be UTF-8 text.')
    # No external imports, resource requests, or active legacy CSS expressions.
    # The browser CSP separately disallows external images and styles.
    scrubbed = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    if re.search(r'@import\b|url\s*\(|expression\s*\(|@charset\b', scrubbed, re.I):
        raise ValueError('Custom CSS cannot contain @import, url(), expression(), or @charset.')
    if not re.search(r'\{[^{}]*:[^{}]*\}', scrubbed):
        raise ValueError('CSS must contain at least one style rule.')
    return css


def detail_reference(clock, display_date):
    """For a chosen day, use the server's local clock time on that day."""
    if not display_date:
        return clock
    return datetime.combine(date.fromisoformat(display_date), clock.timetz())


def normalize_screen(config):
    """Upgrade legacy single-source settings in memory; leave stored settings alone until saved."""
    c = dict(config)
    if 'source_ids' not in c:
        legacy = c.get('source_id')
        c['source_ids'] = [legacy] if legacy else []
    c['source_ids'] = list(dict.fromkeys(c['source_ids']))
    c.setdefault('view', 'list')
    c.setdefault('detail_header', '')
    c.setdefault('color_code', False)
    c.setdefault('show_legend', False)
    c.setdefault('include_all_day', False)
    c.setdefault('show_description', True)
    c.setdefault('date_mode', 'today')
    c.setdefault('custom_date', '')
    c.setdefault('theme_override', '')
    c.setdefault('custom_theme_id', '')
    c.pop('source_id', None)
    return c


def merged_events(store, config, sources, preview=None):
    """Merge sorted, source-tagged occurrences; preserve intentional duplicates."""
    selected = set(config.get('source_ids', []))
    combined = []
    for source in sources:
        if source['id'] not in selected:
            continue
        for event in filtered(store, config, source, preview):
            combined.append({**event, 'source_id': source['id'],
                             'source_name': source.get('nickname') or source['name'],
                             'source_color': source.get('color') or ''})
    combined.sort(key=lambda e: (0 if e['all_day'] else 1, e['start'], e['title'].casefold(), e['title'], e['source_name'].casefold()))
    return combined[:2000]


def detail_selection(rows, now, include_all_day=False):
    """Choose an active event first; an overlapping event is eligible for Later."""
    timed = [r for r in rows if not r['all_day']]
    day_events = [r for r in rows if r['all_day']] if include_all_day else []
    active = [r for r in timed if datetime.fromisoformat(r['start']) <= now < datetime.fromisoformat(r['end'])]
    future = [r for r in timed if datetime.fromisoformat(r['start']) > now]
    candidates = active + future
    # Earlier-started active event stays featured when a second event begins.
    featured = min(active, key=lambda r: (r['start'],r['title'].casefold())) if active else (future[0] if future else (day_events[0] if day_events else None))
    later = None
    if featured is not None:
        remaining = [r for r in timed if r is not featured and datetime.fromisoformat(r['end']) > now and
                     (r['start'] >= featured['start'])]
        remaining.sort(key=lambda r: (r['start'],r['title'].casefold(),r['title']))
        if remaining:
            later = remaining[0]
        elif featured['all_day'] and future:
            later = future[0]
    return featured, later


def nowtz(store):
    # System's configured time zone is the authority; do not trust player clocks.
    return ZoneInfo(store.state().get('settings',{}).get('timezone','America/New_York'))


def safe_url(raw):
    if not isinstance(raw,str) or len(raw)>2048: raise ValueError('Invalid URL')
    raw = ('https://' + raw[9:]) if raw.lower().startswith('webcal://') else raw
    url=urlsplit(raw)
    try: port=url.port
    except ValueError: raise ValueError("Invalid URL port")
    if url.scheme != 'https' or not url.hostname or url.username or url.password or port not in (None,443):
        raise ValueError('Use a public HTTPS iCalendar URL (webcal:// also accepted).')
    if url.hostname.lower() in ('localhost',) or url.hostname.endswith('.local'):
        raise ValueError('Private hosts are not supported.')
    try:
        ips=socket.getaddrinfo(url.hostname,443,type=socket.SOCK_STREAM)
        for info in ips:
            ip=ipaddress.ip_address(info[4][0])
            if not ip.is_global: raise ValueError('Calendar URLs must resolve to public internet addresses.')
    except socket.gaierror:
        raise ValueError('Could not resolve calendar hostname.')
    return raw


def fetch_ics(url):
    url=safe_url(url)
    # No automatic redirects or ambient proxies. Revalidate DNS for every fetch.
    sess=requests.Session();sess.trust_env=False
    try:
        with sess.get(url,timeout=(5,15),stream=True,allow_redirects=False,headers={'Accept':'text/calendar'}) as res:
            res.raise_for_status()
            if res.is_redirect: raise ValueError('Calendar redirect rejected. Supply its final HTTPS URL.')
            data=bytearray()
            for block in res.iter_content(16384):
                data.extend(block)
                if len(data)>MAX_ICS: raise ValueError('Calendar feed exceeds 2 MB.')
    except requests.RequestException as ex:
        raise ValueError(f'Calendar download failed: {str(ex)[:180]}')
    return bytes(data)


def validate_ics(content):
    if len(content)>MAX_ICS: raise ValueError('Calendar file exceeds 2 MB.')
    try:
        cal=Calendar.from_ical(content)
        if cal.name!='VCALENDAR': raise ValueError('Not an iCalendar file.')
        count=sum(1 for c in cal.walk('VEVENT'))
        if not count: raise ValueError('Calendar has no VEVENT entries.')
        return count
    except ValueError: raise
    except Exception as ex: raise ValueError('Invalid iCalendar data: '+str(ex)[:130])


def stored_filename(store,id):
    return store.root / 'calendar-files' / f'{id}.ics'


def event_rows(store,source,begin,end):
    fp=stored_filename(store,source['id'])
    if not fp.exists(): return []
    tz=nowtz(store)
    cal=Calendar.from_ical(fp.read_bytes())
    # Expand only within a bounded interval: protects us from infinitely recurring feeds.
    occurrences=recurring_ical_events.of(cal).between(begin,end)
    rows=[]
    for ev in occurrences:
        try:
            start=ev.decoded('DTSTART');finish=ev.decoded('DTEND') if ev.get('DTEND') else (start+timedelta(days=1) if isinstance(start,date) and not isinstance(start,datetime) else start+timedelta(hours=1))
            all_day=not isinstance(start,datetime)
            if all_day:
                start=datetime.combine(start,dtime.min,tzinfo=tz)
                finish=datetime.combine(finish,dtime.min,tzinfo=tz)
            else:
                start=start.replace(tzinfo=tz) if start.tzinfo is None else start.astimezone(tz)
                finish=finish.replace(tzinfo=tz) if finish.tzinfo is None else finish.astimezone(tz)
            rows.append({'title':str(ev.get('SUMMARY','Untitled event'))[:240],
                         'description':str(ev.get('DESCRIPTION',''))[:1000],
                         'start':start.isoformat(),'end':finish.isoformat(),'all_day':all_day})
        except (TypeError,ValueError,OverflowError,KeyError):
            continue
    rows.sort(key=lambda e:(0 if e['all_day'] else 1, e['start'], e['title'].casefold(), e['title']))
    return rows[:2000]


def filtered(store,config,source,preview=None):
    tz=nowtz(store)
    now=datetime.now(tz)
    selected_date = preview if preview is not None else (config.get('custom_date') if config.get('date_mode') == 'custom' else None)
    anchor=now
    if selected_date:
        try: anchor=datetime.combine(date.fromisoformat(selected_date),dtime.min,tzinfo=tz)
        except ValueError: raise ValueError('Invalid display date')
    mode=config.get('mode','today')
    if mode=='today':
        start=datetime.combine(anchor.date(),dtime.min,tzinfo=tz)
        end=start+timedelta(days=1)
        found=event_rows(store,source,start-timedelta(days=31),end)
        rows=[e for e in found if datetime.fromisoformat(e['start'])<end and datetime.fromisoformat(e['end'])>start]
    else:
        hours=config.get('future_hours','all')
        horizon=anchor+timedelta(days=365 if hours=='all' else 0,hours=0 if hours=='all' else int(hours))
        found=event_rows(store,source,anchor-timedelta(days=31),horizon+timedelta(days=1))
        rows=[e for e in found if (anchor<=datetime.fromisoformat(e['start'])<=horizon or datetime.fromisoformat(e['start'])<=anchor<datetime.fromisoformat(e['end']))]
    # Custom dates show the complete selected day, including events earlier that day.
    if config.get('hide_ended',True) and not selected_date:
        rows=[e for e in rows if datetime.fromisoformat(e['end'])>anchor]
    rows.sort(key=lambda e:(0 if e['all_day'] else 1, e['start'], e['title'].casefold(), e['title']))
    return rows[:2000]


def register_events(app,store):
    def guarded():
        if not g.user: abort(401)
    def admin():
        guarded()
        if g.user['role']!='admin':abort(403)
    def csrf():
        from hmac import compare_digest
        if not compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','')):abort(403)
    def req():
        d=request.get_json(silent=True)
        if not isinstance(d,dict):raise ValueError('Expected JSON object')
        return d
    def update_source(src, content, label=None):
        count=validate_ics(content)
        dest=stored_filename(store,src['id']);dest.parent.mkdir(exist_ok=True)
        tmp=dest.with_suffix('.tmp');tmp.write_bytes(content);os.replace(tmp,dest)
        src.update(size=len(content),event_count=count,updated_at=datetime.now(timezone.utc).isoformat(),status='Ready',error='')
        if label:src['name']=label[:100]
        src.setdefault('nickname',src['name'])
        src.setdefault('color','')

    @app.get('/api/admin/events/backup')
    def event_backup():
        admin()
        from io import BytesIO
        from zipfile import ZipFile, ZIP_DEFLATED
        from flask import send_file
        stream=BytesIO()
        with LOCK:
            d=load(store)
            with ZipFile(stream,'w',ZIP_DEFLATED) as z:
                z.writestr('events.json',json.dumps(d,indent=2))
                for src in d['sources']:
                    path=stored_filename(store,src['id'])
                    if path.exists():z.write(path,'calendar-files/'+src['id']+'.ics')
                for theme in d.get('custom_themes',[]):
                    path=custom_theme_file(store,theme['id'])
                    if path.exists():z.write(path,'custom-themes/'+theme['id']+'.css')
        stream.seek(0)
        return send_file(stream,as_attachment=True,download_name='maxs-events-calendars.zip',mimetype='application/zip')

    @app.get('/api/admin/events/history')
    def events_history():
        guarded()
        return jsonify(history_read(store))

    @app.post('/api/admin/events/history/settings')
    def events_history_settings():
        admin();csrf();body=req()
        if set(body)!={'retention_days'} or body['retention_days'] not in (30,90,180,365,'forever'):
            raise ValueError('Choose a valid retention period')
        from models import atomic_json
        with LOCK:
            d=read_history(store);d['retention_days']=body['retention_days']
            atomic_json(history_path(store),prune_history(d))
        return jsonify(ok=True)

    @app.post('/api/admin/events/history/clear')
    def events_history_clear():
        admin();csrf();body=req()
        if body!={'confirmation':'CLEAR'}:raise ValueError('Confirm CLEAR to delete history')
        from models import atomic_json
        with LOCK:
            d=read_history(store);d['entries']=[];atomic_json(history_path(store),d)
        return jsonify(ok=True)

    @app.get('/sources')
    def event_sources_page():admin();return render_template('events_sources.html')

    @app.get('/api/admin/events')
    def events_configuration():guarded();return jsonify(load(store))

    @app.get('/themes')
    def events_themes_page():
        admin();return render_template('events_themes.html')

    @app.get('/api/admin/events/custom-themes')
    def events_custom_themes():
        admin()
        d=load(store)
        return jsonify(themes=d['custom_themes'], active=d.get('custom_theme_id',''))

    @app.post('/api/admin/events/custom-themes/upload')
    def events_upload_custom_theme():
        admin();csrf()
        file=request.files.get('file')
        if not file or not file.filename or not file.filename.lower().endswith('.css'):
            raise ValueError('Choose a .css theme file.')
        css=validate_custom_css(file.stream.read(MAX_CSS+1))
        name=str(request.form.get('name','')).strip() or Path(file.filename).stem
        if not 1 <= len(name) <= 80 or any(ord(c)<32 for c in name):
            raise ValueError('Theme name must be 1–80 characters.')
        with LOCK:
            d=load(store)
            if len(d['custom_themes']) >= CUSTOM_THEME_LIMIT:
                raise ValueError('Maximum of 30 custom themes reached. Delete an unused theme first.')
            if any(t['name'].casefold()==name.casefold() for t in d['custom_themes']):
                raise ValueError('A custom theme already has that name.')
            theme_id=uuid.uuid4().hex
            path=custom_theme_file(store,theme_id)
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_suffix('.tmp')
            try:
                tmp.write_text(css,encoding='utf-8')
                os.replace(tmp,path)
                d['custom_themes'].append({'id':theme_id,'name':name})
                save(store,d)
            except Exception:
                tmp.unlink(missing_ok=True)
                path.unlink(missing_ok=True)
                raise
            activity(store,g.user,'Uploaded custom CSS theme: '+name)
        return jsonify(ok=True,theme={'id':theme_id,'name':name})

    @app.post('/api/admin/events/custom-themes/<theme_id>/delete')
    def events_delete_custom_theme(theme_id):
        admin();csrf()
        with LOCK:
            d=load(store)
            theme=next((t for t in d['custom_themes'] if t['id']==theme_id),None)
            if not theme:abort(404)
            d['custom_themes']=[t for t in d['custom_themes'] if t['id']!=theme_id]
            if d.get('theme')=='custom' and d.get('custom_theme_id')==theme_id:
                d['theme']='conference';d['custom_theme_id']=''
            for screen_config in d['screens'].values():
                if screen_config.get('theme_override')=='custom' and screen_config.get('custom_theme_id')==theme_id:
                    screen_config['theme_override']=''
                    screen_config['custom_theme_id']=''
            save(store,d)
            custom_theme_file(store,theme_id).unlink(missing_ok=True)
            activity(store,g.user,'Deleted custom CSS theme: '+theme['name'])
        return jsonify(ok=True,theme=d['theme'])

    @app.get('/api/events/custom-theme/<theme_id>.css')
    def events_custom_css(theme_id):
        from flask import send_file
        d=load(store)
        if not any(t['id']==theme_id for t in d['custom_themes']):abort(404)
        path=custom_theme_file(store,theme_id)
        if not path.is_file():abort(404)
        return send_file(path,mimetype='text/css',conditional=False)

    @app.post('/api/admin/events/theme')
    def events_save_theme():
        admin();csrf();body=req()
        chosen=body.get('theme')
        if chosen=='custom':
            if set(body)!={'theme','custom_theme_id'}:raise ValueError('Choose an uploaded custom theme.')
        elif set(body)!={'theme'} or chosen not in EVENT_THEMES:
            raise ValueError('Unknown theme')
        with LOCK:
            d=load(store)
            selected=body.get('custom_theme_id','') if chosen=='custom' else ''
            if chosen=='custom' and not any(t['id']==selected and custom_theme_file(store,t['id']).is_file() for t in d['custom_themes']):
                raise ValueError('Select an uploaded custom CSS theme.')
            previous=(d['theme'],d.get('custom_theme_id',''))
            d['theme']=chosen;d['custom_theme_id']=selected;save(store,d)
            if previous!=(chosen,selected):activity(store,g.user,'Changed theme to '+(selected if chosen=='custom' else chosen))
        return jsonify(ok=True,theme=chosen,custom_theme_id=selected)


    @app.post('/api/admin/events/screen/<sid>')
    def events_save_screen(sid):
        guarded();csrf()
        if sid not in EVENT_SCREEN_IDS:abort(404)
        body=req()
        allowed={'title','detail_header','source_ids','view','color_code','show_legend','include_all_day','orientation','mode','hide_ended','future_hours','scroll','max_visible','date_mode','custom_date','show_description','theme_override','custom_theme_id'}
        if set(body)!=allowed:raise ValueError('Unexpected screen fields')
        if not isinstance(body['title'],str) or len(body['title'])>100:raise ValueError('Invalid title')
        if not isinstance(body['detail_header'],str) or len(body['detail_header'])>100:raise ValueError('Invalid Detail Header')
        if body['date_mode'] not in ('today','custom') or not isinstance(body['custom_date'],str):raise ValueError('Invalid date selection')
        if body['date_mode']=='custom':
            try: date.fromisoformat(body['custom_date'])
            except ValueError: raise ValueError('Choose a valid custom date')
        else:
            # Today mode must never retain an old custom date.
            body['custom_date']=''
        if body['theme_override'] not in ('', 'custom', *EVENT_THEMES):raise ValueError('Invalid theme override')
        if not isinstance(body['custom_theme_id'],str):raise ValueError('Invalid custom theme')
        if body['theme_override']!='custom':body['custom_theme_id']=''
        if body['orientation'] not in ('landscape','portrait') or body['mode'] not in ('today','soon'):raise ValueError('Invalid display mode')
        if body['view'] not in ('list','detail'):raise ValueError('Invalid display type')
        if any(type(body[k]) is not bool for k in ('color_code','show_legend','include_all_day')):raise ValueError('Invalid display options')
        if not isinstance(body['source_ids'],list) or len(body['source_ids'])>100 or any(not isinstance(i,str) for i in body['source_ids']) or len(body['source_ids'])!=len(set(body['source_ids'])):raise ValueError('Invalid calendar selections')
        if body['future_hours'] not in (['all']+list(range(1,13))):raise ValueError('Invalid future window')
        if type(body['show_description']) is not bool:raise ValueError('Invalid description setting')
        if type(body['hide_ended']) is not bool or type(body['scroll']) is not bool or type(body['max_visible']) is not int or not 1<=body['max_visible']<=15:raise ValueError('Invalid scrolling options')
        with LOCK:
            d=load(store)
            if not set(body['source_ids']).issubset({s['id'] for s in d['sources']}):raise ValueError('Calendar not found')
            if body['theme_override']=='custom' and not any(t['id']==body['custom_theme_id'] and custom_theme_file(store,t['id']).is_file() for t in d['custom_themes']):
                raise ValueError('Choose an uploaded custom CSS theme')
            previous=normalize_screen(d['screens'][sid]);d['screens'][sid]=body;save(store,d)
            if previous!=body:activity(store,g.user,'Updated '+sid+' schedule settings')
        return jsonify(ok=True)

    @app.post('/api/admin/events/source/file')
    def events_upload():
        admin();csrf()
        file=request.files.get('file')
        if not file or not file.filename.lower().endswith('.ics'):raise ValueError('Select an .ics file')
        content=file.stream.read(MAX_ICS+1)
        name=request.form.get('name','').strip() or Path(file.filename).name
        if not name or len(name)>100:raise ValueError('Invalid calendar name')
        with LOCK:
            d=load(store);replace=request.form.get('replace_id','')
            if replace:
                src=next((s for s in d['sources'] if s['id']==replace and s['type']=='file'),None)
                if not src:raise ValueError('Uploaded calendar not found')
            else:
                src=next((s for s in d['sources'] if s['name'].casefold()==name.casefold() and s['type']=='file'),None)
                if src:
                    replace=src['id']
                else:
                    if any(s['name'].casefold()==name.casefold() for s in d['sources']):raise ValueError('Name is already used by a URL calendar')
                    src={'id':str(uuid.uuid4()),'name':name,'nickname':name,'color':'','type':'file','url':''};d['sources'].append(src)
            update_source(src,content,name);save(store,d)
            activity(store,g.user,('Replaced' if replace else 'Uploaded')+' calendar: '+src['name'])
        return jsonify(ok=True,source=src,replaced=bool(replace))

    @app.post('/api/admin/events/source/url')
    def events_add_url():
        admin();csrf();body=req()
        url=safe_url(body.get('url',''));content=fetch_ics(url)
        name=str(body.get('name','')).strip()
        if not name or len(name)>100:raise ValueError('Enter a calendar name (up to 100 characters)')
        with LOCK:
            d=load(store)
            if any(s['name'].casefold()==name.casefold() for s in d['sources']):raise ValueError('Calendar name already exists')
            src={'id':str(uuid.uuid4()),'name':name,'nickname':name,'color':'','type':'url','url':url};update_source(src,content);d['sources'].append(src);save(store,d)
            activity(store,g.user,'Subscribed to calendar: '+src['name'])
        return jsonify(ok=True,source=src)

    @app.post('/api/admin/events/source/<id>/appearance')
    def events_source_appearance(id):
        admin();csrf();body=req()
        if set(body) != {'nickname','color'}:raise ValueError('Invalid source settings')
        nickname=body['nickname'];color=body['color']
        if not isinstance(nickname,str) or not 1<=len(nickname.strip())<=100:raise ValueError('Nickname must be 1–100 characters')
        if not isinstance(color,str) or (color and not re.fullmatch(r'#[0-9a-fA-F]{6}',color)):raise ValueError('Choose a valid hex color or leave it blank')
        with LOCK:
            d=load(store);src=next((s for s in d['sources'] if s['id']==id),None)
            if not src:abort(404)
            previous=(src.get('nickname',src['name']),src.get('color',''))
            src.update(nickname=nickname.strip(),color=color.lower());save(store,d)
            if previous!=(nickname.strip(),color.lower()):activity(store,g.user,'Updated calendar appearance: '+src['name'])
        return jsonify(ok=True)

    @app.post('/api/admin/events/source/<id>/refresh')
    def events_refresh(id):
        admin();csrf()
        with LOCK:
            d=load(store);src=next((s for s in d['sources'] if s['id']==id and s['type']=='url'),None)
            if not src:abort(404)
            url=src['url']
        content=fetch_ics(url)
        with LOCK:
            d=load(store);src=next((s for s in d['sources'] if s['id']==id),None)
            if not src:abort(404)
            update_source(src,content);save(store,d)
        return jsonify(ok=True)

    @app.post('/api/admin/events/source/<id>/delete')
    def events_delete(id):
        admin();csrf();body=req()
        with LOCK:
            d=load(store);src=next((s for s in d['sources'] if s['id']==id),None)
            if not src:abort(404)
            attached=[sid for sid,c in d['screens'].items() if id in normalize_screen(c)['source_ids']]
            if attached and body.get('confirm') is not True:return jsonify(error='Assigned to '+', '.join(attached)+'. Confirm deletion.',screens=attached),409
            d['sources']=[s for s in d['sources'] if s['id']!=id]
            for sid in attached:
                c=normalize_screen(d['screens'][sid]);c['source_ids']=[x for x in c['source_ids'] if x!=id];d['screens'][sid]=c
            save(store,d);stored_filename(store,id).unlink(missing_ok=True)
            activity(store,g.user,'Deleted calendar: '+src['name'])
        return jsonify(ok=True)

    @app.get('/api/events/<sid>')
    def events_kiosk_data(sid):
        if sid not in EVENT_SCREEN_IDS:abort(404)
        d=load(store)
        config=normalize_screen(d['screens'][sid])
        preview=request.args.get('preview') if g.user else None
        if preview is not None and preview != 'today':
            try: date.fromisoformat(preview)
            except ValueError:raise ValueError('Invalid preview date')
        render_config=dict(config)
        orientation_preview=request.args.get('orientation_preview') if g.user else None
        if orientation_preview in ('landscape','portrait'):
            render_config['orientation']=orientation_preview
        if preview=='today':render_config.update(date_mode='today',custom_date='')
        display_date=(None if preview=='today' else preview) if preview is not None else (config['custom_date'] if config['date_mode']=='custom' else None)
        data=merged_events(store,render_config,d['sources'],None if preview=='today' else preview)
        if render_config['view']=='detail' and not render_config['include_all_day']:
            data=[r for r in data if not r['all_day']]
        clock=datetime.now(nowtz(store))
        # Custom dates preserve the selected day but use the current local time.
        anchor=detail_reference(clock,display_date)
        featured,later=detail_selection(data,anchor,render_config['include_all_day']) if render_config['view']=='detail' else (None,None)
        available=[{'id':s['id'],'nickname':s.get('nickname') or s['name'],'color':s.get('color','')} for s in d['sources'] if s['id'] in config['source_ids']]
        detail_status=('NOW' if featured and (featured['all_day'] or datetime.fromisoformat(featured['start'])<=anchor<datetime.fromisoformat(featured['end'])) else 'NEXT')
        effective_theme=config['theme_override'] or d.get('theme','conference')
        effective_custom=config['custom_theme_id'] if config['theme_override']=='custom' else (d.get('custom_theme_id','') if not config['theme_override'] else '')
        return jsonify(config=render_config,rows=data,featured=featured,later=later,calendars=available,detail_status=detail_status,
                       theme=effective_theme,custom_theme_id=effective_custom,time_format=store.state()['settings'].get('time_format','12'),now=clock.isoformat(),timezone=str(nowtz(store)),display_date=display_date)

    @app.get('/display/screen<int:n>')
    @app.get('/screen<int:n>')
    def kiosk_page(n):
        if n not in range(1,21):abort(404)
        theme_preview=''
        requested=request.args.get('theme_preview','')
        if g.user and (requested in EVENT_THEMES or (requested.startswith('custom:') and any(t['id']==requested[7:] for t in load(store)['custom_themes']))):
            theme_preview=requested
        return render_template('events_kiosk.html',screen=f'screen{n}',theme_preview=theme_preview)

    def scheduled_refresh():
        # Each URL source refreshes from external calendar every 15 minutes.
        while True:
            time.sleep(900)
            with LOCK: sources=[dict(s) for s in load(store)['sources'] if s['type']=='url']
            for src in sources:
                try:
                    content=fetch_ics(src['url'])
                    with LOCK:
                        d=load(store);updated=next((s for s in d['sources'] if s['id']==src['id'] and s['type']=='url' and s['url']==src['url']),None)
                        if updated:update_source(updated,content);save(store,d)
                except Exception as ex:
                    with LOCK:
                        d=load(store);old=next((s for s in d['sources'] if s['id']==src['id']),None)
                        if old:old.update(status='Using cached data',error=str(ex)[:180]);save(store,d)
    if not app.config.get('TESTING') and os.environ.get('EVENTS_DISABLE_REFRESH')!='1':
        threading.Thread(target=scheduled_refresh,daemon=True,name='ical-refresh').start()
