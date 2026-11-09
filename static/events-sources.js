'use strict';const $=id=>document.getElementById(id);let sources=[];
async function json(url,body){const r=await fetch(url,{method:'POST',headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content,...(body instanceof FormData?{}:{'Content-Type':'application/json'})},body:body instanceof FormData?body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Object.assign(new Error(data.error||'Request failed'),{status:r.status,data});return data}
// A small curated palette, rather than the browser's unrestricted native picker.
const PALETTE=[
 '#FFFFFF','#E4E4E4','#B6B6B6','#777777','#353535','#000000','#FFF2CC','#FFCC99','#FF9999','#FF6666',
 '#FF0000','#F28C28','#FFCC00','#FFFF66','#CCFF66','#99CC33','#33CC66','#00B050','#00A88F','#00CCCC',
 '#CC3300','#D9661F','#CC9900','#B5B900','#669900','#339933','#009966','#008080','#0099CC','#3399FF',
 '#800000','#993300','#996600','#808000','#336600','#006633','#006666','#005580','#0066CC','#003399',
 '#990066','#CC33CC','#9933FF','#6666CC','#6600CC','#663399','#333399','#CC6699','#FF66CC','#FF99CC',
 '#F4CCCC','#FCE5CD','#FFF2CC','#D9EAD3','#D0E0E3','#CFE2F3','#D9D2E9','#EAD1DC','#A4C2F4','#B4A7D6'
];
function normalizedHex(s){const v=s.trim();if(!v)return '';const c=v.startsWith('#')?v:'#'+v;return /^#[a-fA-F0-9]{6}$/.test(c)?c.toUpperCase():null}
function textColor(hex){if(!hex)return '#172b3c';const n=parseInt(hex.slice(1),16);const r=(n>>16)&255,g=(n>>8)&255,b=n&255;return (r*.299+g*.587+b*.114)<145?'#FFFFFF':'#15232B'}
let activePalette=null;
function closePalette(){if(activePalette){activePalette.hidden=true;activePalette=null}}
document.addEventListener('pointerdown',e=>{if(activePalette&&!activePalette.parentElement.contains(e.target))closePalette()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closePalette()});
function createAppearance(source,cell){
 const container=document.createElement('div');container.className='source-appearance';
 const nickname=document.createElement('input');nickname.className='source-nickname';nickname.type='text';nickname.maxLength=100;nickname.value=source.nickname||source.name;nickname.setAttribute('aria-label','Calendar nickname');
 const paletteButton=document.createElement('button');paletteButton.type='button';paletteButton.className='source-palette-button';paletteButton.title='Choose calendar color';paletteButton.setAttribute('aria-label','Choose calendar color');paletteButton.setAttribute('aria-expanded','false');
 const wheel=document.createElement('span');wheel.className='source-wheel';wheel.setAttribute('aria-hidden','true');paletteButton.append(wheel);
 const hex=document.createElement('input');hex.type='text';hex.className='source-hex';hex.maxLength=7;hex.placeholder='#RRGGBB';hex.value=source.color||'';hex.setAttribute('aria-label','Calendar color hexadecimal code');hex.spellcheck=false;
 const error=document.createElement('span');error.className='source-color-error';error.hidden=true;error.setAttribute('role','alert');
 const picker=document.createElement('div');picker.className='source-palette';picker.hidden=true;
 const grid=document.createElement('div');grid.className='source-palette-grid';
 const chosen=()=>normalizedHex(hex.value);
 function paint(value){hex.style.backgroundColor=value||'#FFFFFF';hex.style.color=textColor(value);hex.style.borderColor=value?'#777':'#999'}
 function choose(value){hex.value=value;paint(value);error.hidden=true;closePalette()}
 for(const color of PALETTE){const b=document.createElement('button');b.type='button';b.style.backgroundColor=color;b.title=color;b.setAttribute('aria-label','Choose '+color);b.onclick=()=>choose(color);grid.append(b)}
 const clear=document.createElement('button');clear.type='button';clear.textContent='Clear color';clear.onclick=()=>choose('');
 picker.append(grid,clear);
 paletteButton.onclick=()=>{if(!picker.hidden){closePalette();return}closePalette();const bounds=paletteButton.getBoundingClientRect();picker.style.top=Math.max(8,Math.min(bounds.bottom+4,window.innerHeight-330))+'px';picker.style.left=Math.max(8,Math.min(bounds.left,window.innerWidth-280))+'px';picker.hidden=false;activePalette=picker};
 hex.onblur=()=>{const value=chosen();if(value===null){error.textContent='Enter a six-digit hex color (e.g. #33AA66), or leave blank.';error.hidden=false;return}hex.value=value;paint(value);error.hidden=true};
 hex.oninput=()=>{error.hidden=true};
 const save=document.createElement('button');save.type='button';save.textContent='Save';save.onclick=async()=>{
   const value=chosen();if(value===null){error.textContent='Enter a valid six-digit color or leave blank.';error.hidden=false;return}
   hex.value=value;paint(value);try{await json('/api/admin/events/source/'+source.id+'/appearance',{nickname:nickname.value,color:value});status('Calendar appearance saved.');closePalette();await load()}catch(e){status(e.message,true)}
 };
 container.append(nickname,paletteButton,hex,save,picker,error);cell.append(container);paint(normalizedHex(source.color||'')||'');
}
async function load(){
 const d=await MenuAPI.request('/api/admin/events');sources=d.sources;
 $('replace').replaceChildren(new Option('Create new',''));
 for(const source of sources.filter(x=>x.type==='file'))$('replace').add(new Option(source.name,source.id));
 const root=$('sources-list');root.replaceChildren();if(!sources.length){root.textContent='No calendars uploaded yet.';return}
 const table=document.createElement('table');table.className='calendar-sources-table';
 const head=table.insertRow();for(const label of ['Source','Nickname / Color','Last update','Events','Status','Actions'])head.insertCell().textContent=label;
 for(const source of sources){
   const tr=table.insertRow();const sourceCell=tr.insertCell();if(source.type==='url'&&/^https:\/\//i.test(source.url||'')){const a=document.createElement('a');a.href=source.url;a.textContent=source.name;a.title=source.url;a.target='_blank';a.rel='noopener noreferrer';sourceCell.append(a)}else{sourceCell.textContent=source.name}const type=document.createElement('small');type.textContent=' ('+source.type+')';sourceCell.append(type);createAppearance(source,tr.insertCell());
   for(const value of [source.updated_at?new Date(source.updated_at).toLocaleString():'',source.event_count||0,source.status||''])tr.insertCell().textContent=value;
   const actions=tr.insertCell();
   if(source.type==='url'){
     const refresh=document.createElement('button');refresh.type='button';refresh.textContent='Refresh';
     refresh.onclick=async()=>{
       refresh.disabled=true;refresh.replaceChildren();const spinner=document.createElement('span');spinner.className='calendar-spinner';spinner.setAttribute('aria-hidden','true');refresh.append(spinner,document.createTextNode(' Refresh'));
       status('Refreshing '+source.name+'...',false);
       try{await json('/api/admin/events/source/'+source.id+'/refresh',{});await load();status(source.name+' refreshed successfully.',false)}
       catch(e){status('Refresh failed for '+source.name+': '+e.message+'. Previously saved events are unchanged.',true)}
       finally{refresh.disabled=false;refresh.textContent='Refresh'}
     };actions.append(refresh);
   }
   const del=document.createElement('button');del.textContent='Delete';del.onclick=async()=>{if(!confirm('Delete calendar "'+source.name+'"?'))return;try{await json('/api/admin/events/source/'+source.id+'/delete',{confirm:false})}catch(e){if(e.status===409&&e.data.screens&&confirm(e.message+' Delete anyway?'))await json('/api/admin/events/source/'+source.id+'/delete',{confirm:true});else{status(e.message);return}}await load()};actions.append(del)
 }root.append(table)
}
const feedbackTimers=new Map();
function showFeedback(id,message,error=false){
 const el=$(id);clearTimeout(feedbackTimers.get(id));feedbackTimers.delete(id);
 el.hidden=false;el.className='calendar-action-status '+(error?'error':'success');el.textContent=message;
 if(!error){const timer=setTimeout(()=>{if(feedbackTimers.get(id)===timer){el.hidden=true;feedbackTimers.delete(id)}},3000);feedbackTimers.set(id,timer)}
}
function status(t,error=false){showFeedback('status',t,error)}
function feedback(id,message,error=false){showFeedback(id,message,error)}
$('upload').onsubmit=async e=>{e.preventDefault();const f=new FormData();const file=$('file').files[0];if(!file)return;f.set('file',file);f.set('name',$('filename').value);f.set('replace_id',$('replace').value);const button=e.target.querySelector('button[type=submit],button.primary');button.disabled=true;$('upload-status').hidden=true;
 try{const d=await json('/api/admin/events/source/file',f);e.target.reset();feedback('upload-status',(d.replaced?'Replaced':'Uploaded')+' '+d.source.name+' successfully.'+(d.replaced?' Existing screen assignments and calendar appearance were preserved.':''));await load()}
 catch(ex){feedback('upload-status','Upload failed: '+ex.message+'. Existing calendar data was not changed.',true)}finally{button.disabled=false}};
$('url-form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button[type=submit],button.primary');button.disabled=true;$('subscription-status').hidden=true;
 try{const d=await json('/api/admin/events/source/url',{name:$('urlname').value,url:$('url').value});e.target.reset();feedback('subscription-status','Subscription '+d.source.name+' added successfully.');await load()}
 catch(ex){feedback('subscription-status','Subscription failed: '+ex.message,true)}finally{button.disabled=false}};load().catch(e=>status(e.message));
