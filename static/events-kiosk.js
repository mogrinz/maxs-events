'use strict';
const $=id=>document.getElementById(id),query=new URLSearchParams(location.search),preview=query.get('preview');
const editorPreview=query.get('editor_preview')==='1';
const screen=document.querySelector('meta[name="events-screen"]').content;
const themePreview=document.querySelector('meta[name="events-theme-preview"]')?.content;
let timeFormat='12';let detailStatus='NEXT';let config=null,rows=[],featured=null,later=null,calendars=[],displayDate=null,serverNow=Date.now(),received=Date.now(),loopHeight=0,scrollStart=performance.now(),canScroll=false,lastFingerprint='';
function now(){return new Date(serverNow+Date.now()-received)}
function formatter(options){return new Intl.DateTimeFormat('en-US',{timeZone:window.TZ||'America/New_York',...options})}
function fmtTime(iso){return formatter({hour:timeFormat==='24'?'2-digit':'numeric',minute:'2-digit',hourCycle:timeFormat==='24'?'h23':'h12'}).format(new Date(iso))}
function fmtDay(iso){return formatter({weekday:'short'}).format(new Date(iso))}
function clockDate(){const current=now();$('clock').textContent=formatter({hour:timeFormat==='24'?'2-digit':'numeric',minute:'2-digit',hourCycle:timeFormat==='24'?'h23':'h12'}).format(current);$('date').textContent=displayDate?new Intl.DateTimeFormat('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric',timeZone:'UTC'}).format(new Date(displayDate+'T12:00:00Z')):formatter({weekday:'long',month:'long',day:'numeric',year:'numeric'}).format(current)}
function sameDisplayTime(r){if(r.all_day||fmtTime(r.start)!==fmtTime(r.end))return false;const date=formatter({year:'numeric',month:'2-digit',day:'2-digit'});return date.format(new Date(r.start))===date.format(new Date(r.end))}
function timeText(r){if(r.all_day)return(config.mode==='soon'?fmtDay(r.start)+' ':'')+'All Day';return(config.mode==='soon'?fmtDay(r.start)+' ':'')+fmtTime(r.start)+(sameDisplayTime(r)?'':' – '+fmtTime(r.end))}
function colorBar(r){
  if(!config.color_code)return null;
  const c=document.createElement('span');c.className='source-color';
  c.setAttribute('aria-hidden','true');
  if(r.source_color)c.style.backgroundColor=r.source_color;
  else c.classList.add('color-empty');
  return c;
}
function eventRow(r){const e=document.createElement('div');e.className='event';const time=document.createElement('div');time.className='time';const content=timeText(r);if(r.all_day){time.classList.add('all-day');const allDayText=document.createElement('span');allDayText.className='all-day-text';allDayText.textContent=content;time.append(allDayText)}else{const s=document.createElement('span');s.className='time-start';s.textContent=(config.mode==='soon'?fmtDay(r.start)+' ':'')+fmtTime(r.start);if(sameDisplayTime(r)){time.classList.add('single-time');time.append(s)}else{const dash=document.createElement('span');dash.className='time-dash';dash.textContent='–';const end=document.createElement('span');end.className='time-end';end.textContent=fmtTime(r.end);time.append(s,dash,end)}}const body=document.createElement('div');body.className='body';const name=document.createElement('div');name.className='name';name.textContent=r.title;body.append(name);if(config.show_description!==false&&r.description){const desc=document.createElement('div');desc.className='description';desc.textContent=r.description;body.append(desc)}e.append(time);const bar=colorBar(r);if(bar){e.classList.add('color-slots');if(r.source_color)e.classList.add('has-source-color');e.append(bar)}e.append(body);return e}
function section(label,r,primary){const wrapper=document.createElement('section');wrapper.className=primary?'featured':'later';const head=document.createElement('div');head.className='section-label';head.textContent=label;wrapper.append(head);if(!r){const empty=document.createElement('div');empty.className='detail-empty';empty.textContent=primary?'No upcoming events':'No later events scheduled';wrapper.append(empty);return wrapper}const card=document.createElement('div');card.className='detail-card';const bar=colorBar(r);if(bar){card.classList.add('color-slots');card.append(bar)}const body=document.createElement('div');body.className='detail-copy';const time=document.createElement('div');time.className='detail-time';time.textContent=timeText(r);const title=document.createElement('div');title.className='detail-title';title.textContent=r.title;body.append(time,title);if(config.show_description!==false&&r.description){const d=document.createElement('div');d.className='detail-description';d.textContent=r.description;body.append(d)}card.append(body);wrapper.append(card);return wrapper}
function legend(){const footer=$('legend');footer.replaceChildren();footer.hidden=!(config.color_code&&config.show_legend&&calendars.some(c=>c.color));if(footer.hidden)return;for(const c of calendars.filter(c=>c.color)){const item=document.createElement('span');item.className='legend-item';const dot=document.createElement('span');dot.className='legend-dot';dot.style.background=c.color||'transparent';item.append(dot,document.createTextNode(c.nickname));footer.append(item)}}
function portraitLayout(v,track,count,gap){
 const w=v.clientWidth,h=v.clientHeight;
 const each=Array.from(track.querySelectorAll('.event'));
 if(!each.length)return;
 const slotHeight=Math.max(50,(h-gap*count)/count);
 const targetTextPx=Math.max(23,Math.min(66,slotHeight*.31+7));
 const timeWidth=Math.min(w*.40,Math.max(w*.34,170));
 track.style.setProperty('--time-width',timeWidth+'px');
 const ctx=document.createElement('canvas').getContext('2d');
 const firstTime=each[0].querySelector('.time');
 const st=firstTime?getComputedStyle(firstTime):null;
 const family=st?.fontFamily||'Arial',weight=st?.fontWeight||'700';
 const strings=rows.filter(r=>!r.all_day).flatMap(r=>[(config.mode==='soon'?fmtDay(r.start)+' ':'')+fmtTime(r.start),fmtTime(r.end)]);
 // The three-line time column has no need for large gaps around the dash.
 let timePx=Math.max(27,Math.min(82,targetTextPx*1.30));
 const maxTextWidth=timeWidth-22;
 for(let i=0;i<6;i++){
  ctx.font=`${weight} ${timePx}px ${family}`;
  const widest=Math.max(0,...strings.map(t=>ctx.measureText(t).width));
  if(widest<=maxTextWidth)break;
  timePx=Math.max(16,timePx*maxTextWidth/widest*.985);
 }
 track.style.setProperty('--time-font',timePx+'px');
 // Fit every title and description against one common size. Measure the
 // longest *whole word* in every row, using each theme's actual font face.
 // Include the full schedule, not just the first visible screenful, so the
 // typography stays stable as rows scroll into view.
 const originals=each.slice(0,rows.length);
 let commonPx=targetTextPx;
 const textNodes=originals.flatMap(el=>[el.querySelector('.name'),el.querySelector('.description')].filter(Boolean));
 const available=Math.max(55,w-timeWidth-52);
 for(const node of textNodes){
  const cs=getComputedStyle(node);
  const words=(node.textContent||'').split(/\s+/).filter(Boolean);
  if(!words.length)continue;
  ctx.font=`${cs.fontStyle} ${cs.fontWeight} ${targetTextPx}px ${cs.fontFamily}`;
  const widest=Math.max(...words.map(word=>ctx.measureText(word).width));
  if(widest>available)commonPx=Math.min(commonPx,targetTextPx*available/widest*.96);
 }
 commonPx=Math.max(12,Math.floor(commonPx*10)/10);
 track.style.setProperty('--title-font',commonPx+'px');
 track.style.setProperty('--desc-font',commonPx+'px');
 each.forEach(el=>{
  el.style.height='auto';el.classList.remove('tall');
  const time=el.querySelector('.time');
  for(const node of [el.querySelector('.name'),el.querySelector('.description')]){
   if(!node)continue;
   node.style.fontSize=commonPx+'px';
   node.style.overflowWrap='normal';node.style.wordBreak='normal';node.style.hyphens='none';
  }
  if(time){
   time.style.fontSize=timePx+'px';time.style.display='';
   time.style.flexDirection='';time.style.justifyContent='center';
   time.style.alignItems='center';time.style.gap='0';time.style.whiteSpace='nowrap';
   for(const node of time.children){node.style.fontSize='inherit';node.style.width='100%';node.style.textAlign='center'}
  }
 });
 // Re-check the rendered text after CSS layout. All rows share the same
 // font size; if the actual font metrics require it, reduce them together.
 for(let pass=0;pass<5;pass++){
  const overflow=textNodes.some(node=>node.scrollWidth>node.clientWidth+2);
  if(!overflow)break;
  commonPx=Math.max(12,commonPx*.93);
  track.style.setProperty('--title-font',commonPx+'px');
  track.style.setProperty('--desc-font',commonPx+'px');
  each.forEach(el=>{
   for(const node of [el.querySelector('.name'),el.querySelector('.description')])if(node)node.style.fontSize=commonPx+'px';
  });
 }
 const measured=originals.map(el=>{
  const body=el.querySelector('.body'),time=el.querySelector('.time');
  const textHeight=Math.max(body?.scrollHeight||0,time?.scrollHeight||0)+12;
  return Math.max(slotHeight,textHeight);
 });
 each.forEach((el,i)=>{const height=measured[i%rows.length];el.style.height=height+'px';el.classList.toggle('tall',height>slotHeight+3)});
 const first=each[0],second=each[rows.length];
 loopHeight=first&&second?second.offsetTop-first.offsetTop:0;
 canScroll=!!config.scroll&&rows.length>count;
 if(!canScroll)track.style.transform='translateY(0)';
}

function layout(){if(!config||config.view==='detail')return;const v=$('viewport'),track=$('track');const count=Math.min(15,Math.max(1,Number(config.max_visible)||5)),gap=Math.max(3,Math.min(8,v.clientHeight*.008));track.style.setProperty('--row-gap',gap+'px');if(config.orientation==='portrait'){portraitLayout(v,track,count,gap);return;}const w=v.clientWidth,h=v.clientHeight;// Landscape typography unchanged.
// The time column is measured after scaling so ranges remain on one line.
const portraitScale=1;
const titlePx=Math.max(14,Math.min(38,w*.028,h*.055))*portraitScale;
const descPx=Math.max(12,Math.min(27,w*.021,h*.042))*portraitScale;
let timePx=Math.max(12,Math.min(39,w*.026,h*.057))*portraitScale;const nonAll=rows.filter(r=>!r.all_day);
const starts=nonAll.map(r=>(config.mode==='soon'?fmtDay(r.start)+' ':'')+fmtTime(r.start));
const ends=nonAll.map(r=>fmtTime(r.end));
const inset=Math.max(12,w*.015);
const timeNode=track.querySelector('.time');const style=timeNode?getComputedStyle(timeNode):null;
const family=style?.fontFamily||'Arial';const weight=style?.fontWeight||'700';const fontStyle=style?.fontStyle||'normal';
const ctx=document.createElement('canvas').getContext('2d');
function measure(px){ctx.font=`${fontStyle} ${weight} ${px}px ${family}`;
 const sw=Math.max(0,...starts.map(x=>ctx.measureText(x).width));
 const ew=Math.max(0,...ends.map(x=>ctx.measureText(x).width));
 const aw=Math.max(0,...rows.filter(r=>r.all_day).map(r=>ctx.measureText(timeText(r)).width));
 const gap=Math.max(8,px*.38);const dash=Math.max(ctx.measureText('–').width+gap,px*.7);
 return {sw,ew,aw,dash,needed:Math.max(aw,sw+ew+dash)+inset+Math.max(8,w*.01)};
}
const maxTimeWidth=w*.58;let widths=measure(timePx);
if(widths.needed>maxTimeWidth){timePx=Math.max(9,timePx*maxTimeWidth/widths.needed);widths=measure(timePx)}
const used=Math.min(maxTimeWidth,Math.max(70,widths.needed));
track.style.setProperty('--time-font',timePx+'px');track.style.setProperty('--title-font',titlePx+'px');track.style.setProperty('--desc-font',descPx+'px');
track.style.setProperty('--time-width',used+'px');
track.style.setProperty('--start-width',widths.sw+'px');track.style.setProperty('--end-width',widths.ew+'px');track.style.setProperty('--dash-width',widths.dash+'px');
const each=Array.from(track.querySelectorAll('.event'));each.forEach(el=>{el.style.height='auto';el.classList.remove('tall')});const normalHeight=Math.max(58,(h-gap*count)/count);const measured=each.slice(0,rows.length).map(el=>{const body=el.querySelector('.body');const textHeight=body.scrollHeight+18;return Math.max(normalHeight,textHeight)});each.forEach((el,i)=>{const height=measured[i%rows.length];el.style.height=height+'px';el.classList.toggle('tall',height>normalHeight+3)});const first=each[0],second=each[rows.length];loopHeight=first&&second?second.offsetTop-first.offsetTop:0;canScroll=!!config.scroll&&rows.length>count;if(!canScroll)track.style.transform='translateY(0)'}
function render(){const track=$('track');track.replaceChildren();const detailSubtitle=config.view==='detail'&&config.detail_header?.trim();$('title').textContent=config.title||"Today's Events";const subtitle=$('detail-subtitle');subtitle.hidden=!detailSubtitle;subtitle.textContent=detailSubtitle||'';subtitle.style.color=getComputedStyle($('title')).color;document.body.classList.toggle('detail-view',config.view==='detail');legend();if(config.view==='detail'){track.append(section(detailStatus,featured,true),section('LATER',later,false));canScroll=false;return}if(!rows.length){track.append(section('',null,true));canScroll=false;return}const slots=Math.max(1,Math.min(15,Number(config.max_visible)||5));const visible=!config.scroll&&rows.length>slots?rows.slice(0,slots):rows;for(const r of visible)track.append(eventRow(r));if(config.scroll&&rows.length>slots){const sep=document.createElement('div');sep.className='cycle-separator';track.append(sep);for(const r of rows)track.append(eventRow(r));track.append(sep.cloneNode())}layout();track.style.transform='translateY(0)';scrollStart=performance.now()}
function applyOrientation(){const rotate=!!config&&config.orientation==='portrait'&&!editorPreview&&innerWidth>innerHeight;document.body.classList.toggle('rotate-portrait',rotate);document.body.classList.toggle('portrait-layout',!!config&&config.orientation==='portrait');}
function applyTheme(theme,customId){
 const link=$('custom-theme-css');
 const selected=themePreview||theme||'conference';
 const id=selected.startsWith('custom:')?selected.slice(7):(selected==='custom'?customId:'');
 document.body.dataset.theme=id?'custom':selected;
 if(id&&/^[0-9a-f]{32}$/.test(id)){
   const href='/api/events/custom-theme/'+id+'.css';
   if(link.getAttribute('href')!==href){link.setAttribute('href',href);link.onload=()=>{const subtitle=$('detail-subtitle');if(subtitle)subtitle.style.color=getComputedStyle($('title')).color;if(config)layout()}}
   link.disabled=false;
 }else{link.disabled=true;link.removeAttribute('href')}
}
function animate(t){if(canScroll&&loopHeight>0){const distance=((t-scrollStart)*17/1000)%loopHeight;$('track').style.transform=`translateY(${-distance}px)`}requestAnimationFrame(animate)}
async function refresh(){try{const params=new URLSearchParams();if(preview)params.set('preview',preview);if(editorPreview)params.set('orientation_preview',query.get('orientation_preview')||'landscape');const url='/api/events/'+screen+(params.size?'?'+params.toString():'');const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Could not load schedule');const d=await r.json();const fingerprint=JSON.stringify([d.config,d.rows,d.featured,d.later,d.calendars,d.theme,d.custom_theme_id,d.detail_status,d.time_format,d.display_date]);const changed=fingerprint!==lastFingerprint;lastFingerprint=fingerprint;config=d.config;rows=d.rows;featured=d.featured;later=d.later;calendars=d.calendars;displayDate=d.display_date;detailStatus=d.detail_status||'NEXT';timeFormat=d.time_format==='24'?'24':'12';window.TZ=d.timezone;applyOrientation();applyTheme(d.theme,d.custom_theme_id);serverNow=new Date(d.now).getTime();received=Date.now();if(changed)render();if(config.view==='detail'&&featured){const label=$('track').querySelector('.featured .section-label');if(label){label.textContent=detailStatus}}clockDate();document.body.classList.remove('kiosk-loading')}catch(e){console.error('Schedule refresh failed',e);if(!config){$('title').textContent='Unable to load events';document.body.classList.remove('kiosk-loading')}}}
let resizeHandle;window.addEventListener('resize',()=>{clearTimeout(resizeHandle);resizeHandle=setTimeout(()=>{if(config){applyOrientation();layout()}},90)});setInterval(clockDate,1000);setInterval(refresh,15000);requestAnimationFrame(animate);refresh();if(document.fonts){document.fonts.ready.then(()=>{if(config)layout()});document.fonts.addEventListener?.('loadingdone',()=>{if(config)layout()})}
