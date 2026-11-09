'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const base=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(base,'static/events-kiosk.js'),'utf8');
function extract(code,name){const begin=code.indexOf('function '+name+'(');assert(begin>=0,name+' missing');const open=code.indexOf('{',begin);let level=1,i=open+1;for(;level&&i<code.length;i++){if(code[i]==='{')level++;else if(code[i]==='}')level--}return code.slice(begin,i)}
class Elem{constructor(tag){this.tag=tag;this.className='';this.classes=[];this.classList={add:(...c)=>this.classes.push(...c)};this.children=[];this.style={};this.attributes={};this.textContent=''}append(...x){this.children.push(...x)}setAttribute(k,v){this.attributes[k]=v}}
const ctx={document:{createElement:tag=>new Elem(tag)},config:{mode:'today',show_description:true,color_code:true},timeText:r=>r.all_day?'All Day':r.start,fmtTime:s=>s,fmtDay:s=>s};vm.createContext(ctx);
vm.runInContext(['colorBar','eventRow'].map(n=>extract(source,n)).join('\n'),ctx);
const data={start:'10:00',end:'11:00',all_day:false,title:'Sample',description:'Description'};
let colored=ctx.eventRow({...data,source_color:'#ff0000'}),uncolored=ctx.eventRow({...data,source_color:''});
assert.equal(colored.children.length,3);assert.equal(uncolored.children.length,3);
assert.equal(colored.children[2].className,'body');assert.equal(uncolored.children[2].className,'body');
assert(colored.classes.includes('color-slots'));assert(uncolored.classes.includes('color-slots'));
assert(uncolored.children[1].classes.includes('color-empty'));
const allDay=ctx.eventRow({...data,all_day:true});assert.equal(allDay.children[0].children[0].textContent,'All Day');assert.equal(allDay.children[0].className,'time');assert(allDay.children[0].classes.includes('all-day'));assert.equal(allDay.children[2].className,'body');
const sourceCode=fs.readFileSync(path.join(base,'static/events-sources.js'),'utf8');vm.runInContext(extract(sourceCode,'normalizedHex'),ctx);
assert.equal(ctx.normalizedHex('ff00aa'),'#FF00AA');assert.equal(ctx.normalizedHex('#abcdef'),'#ABCDEF');assert.equal(ctx.normalizedHex(''),'');assert.equal(ctx.normalizedHex('#gg0000'),null);
assert(!sourceCode.includes("type='color'"));assert(!sourceCode.includes("type='checkbox'"));
const css=fs.readFileSync(path.join(base,'static/events-kiosk.css'),'utf8');assert(css.includes('.event.color-slots'));assert(css.includes('.detail-card.color-slots,.later .detail-card.color-slots'));
console.log('RC2 UI structural tests passed: All Day, color slot alignment, hex field, Detail alignment');
