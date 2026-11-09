"use strict";
const get=id=>document.getElementById(id), admin=!!get('history-clear');
async function load(){try{const d=await MenuAPI.request('/api/admin/events/history');const b=get('history-rows');b.replaceChildren();if(admin)get('history-retention').value=String(d.retention_days);for(const e of d.entries){let tr=b.insertRow();for(const value of [new Date(e.time).toLocaleString(),e.actor,e.action])tr.insertCell().textContent=value;}if(!d.entries.length){const tr=b.insertRow();const cell=tr.insertCell();cell.colSpan=3;cell.textContent='No activity recorded.'}get('history-status').textContent=d.entries.length+' entries';}catch(e){get('history-status').textContent=e.message}}
get('history-reload').onclick=load;
if(admin){get('history-save').onclick=async()=>{try{const x=get('history-retention').value;await MenuAPI.request('/api/admin/events/history/settings',{method:'POST',body:JSON.stringify({retention_days:x==='forever'?x:Number(x)})});await load()}catch(e){get('history-status').textContent=e.message}};
get('history-clear').onclick=async()=>{if(!confirm('Permanently clear the administrative activity log? This does not delete calendars or settings.'))return;try{await MenuAPI.request('/api/admin/events/history/clear',{method:'POST',body:JSON.stringify({confirmation:'CLEAR'})});await load()}catch(e){get('history-status').textContent=e.message}}}
load();
