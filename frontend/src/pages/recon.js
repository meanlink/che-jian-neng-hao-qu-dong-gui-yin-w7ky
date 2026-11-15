import {bills,recon,datasets} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {table} from '../components/common/table.js';
import {ReconStatus} from '../constants/enums.js';
import {esc,fmt,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
import {parseCSV} from '../utils/csv.js';
let filter='';
const itemCols=[{key:'day',label:'日期'},{key:'line',label:'线体'},{key:'kwh',label:'样本电量kWh'},{key:'dataset_id',label:'来源批次'}];
function groupCard(g,admin){
 const actions=[];
 if(admin&&g.status==='pending')actions.push('<button class="button small" data-confirm="'+g.id+'">确认核销</button>');
 if(admin&&g.status!=='revoked')actions.push('<button class="button small" data-revoke="'+g.id+'">撤销</button>');
 actions.push('<button class="text-button" data-items="'+g.id+'">逐笔对应 ↓</button>');
 return '<article class="recon-group"><div class="recon-head"><div><strong>'+esc(g.name)+'</strong><p>账单 '+esc(g.bill_no)+' · '+esc(g.line)+' · '+esc(g.start_day)+' 至 '+esc(g.end_day)+'</p><small>建组 '+date(g.created_at)+(g.confirmed_at?' · 确认 '+date(g.confirmed_at):'')+(g.revoked_at?' · 撤销 '+date(g.revoked_at):'')+'</small>'+(g.revoke_reason?'<small>撤销原因：'+esc(g.revoke_reason)+'</small>':'')+'</div><span class="recon-status s-'+esc(g.status)+'">'+esc(ReconStatus[g.status]||g.status)+'</span></div><div class="metrics"><div><span>账单电量</span><strong>'+fmt(g.bill_kwh)+'<small>kWh</small></strong></div><div><span>样本合计</span><strong>'+fmt(g.sample_kwh)+'<small>kWh</small></strong></div><div><span>差额</span><strong>'+fmt(g.diff_kwh)+'<small>kWh</small></strong></div></div>'+(g.issues.length?'<div class="warning">'+g.issues.map(i=>esc(i)).join('<br>')+'</div>':'')+'<div class="recon-actions">'+actions.join('')+'</div><div class="recon-items" id="items-'+g.id+'"></div></article>';
}
export async function reconPage(){
 const [billList,groupList,dsList]=await Promise.all([bills.list(),recon.groups(filter),datasets.list()]);
 workspace.datasets=dsList;
 const admin=session.user.role==='admin',writable=session.user.role!=='viewer';
 const open=billList.filter(b=>!b.claimed);
 const tabs=[['','全部'],['pending','待核对'],['mismatch','差异'],['confirmed','已确认'],['revoked','已撤销']];
 return heading('06 / RECONCILIATION','电量对账与核销','供电账单与车间日耗分别留存，在此按日样本组成核销组。逐日覆盖齐全且总量相符才可确认；缺日、重叠或差额的组保留待处理。','<button class="button" id="refresh-recon">刷新 ↻</button>')
 +'<div class="recon-grid"><section class="panel"><div class="section-title"><h2>导入供电账单</h2></div><form id="bill-form"><label>上传 CSV 或 JSON<input type="file" id="bill-file" accept=".json,.csv"></label><label>账单 JSON<textarea name="bills" rows="5" placeholder=\'[{"bill_no":"GD-202608-P01","line":"冲压P01","start_day":"2026-08-01","end_day":"2026-08-31","kwh":25410.5}]\' required></textarea></label><p class="hint">字段：bill_no 账单号 / line 线体 / start_day、end_day 起止日 / kwh 电量。账单号唯一，重复导入整批拒绝。</p><button type="submit" class="primary" '+(writable?'':'disabled')+'>校验并导入账单</button></form>'
 +'<div class="section-title"><h2>新建核销组</h2></div><form id="group-form"><label>核销组名称<input name="name" required minlength="2" placeholder="例如：2026年6月 冲压P01 电费核销"></label><label>供电账单（未占用）<select name="bill_id" id="group-bill" required>'+(open.length?open.map(b=>'<option value="'+b.id+'">'+esc(b.bill_no)+' · '+esc(b.line)+' · '+esc(b.start_day)+' 至 '+esc(b.end_day)+' · '+fmt(b.kwh)+' kWh</option>').join(''):'<option value="">暂无未占用账单</option>')+'</select></label><label>日样本批次<select name="dataset_id" id="group-dataset" required>'+dsList.map(d=>'<option value="'+d.id+'">'+esc(d.name)+' · '+d.rows+' 条</option>').join('')+'</select></label><div id="day-picker"><p class="hint">选择账单与批次后，此处列出该线体全部日样本供勾选。</p></div><p class="hint" id="day-total"></p><button type="submit" class="primary" '+(writable&&open.length&&dsList.length?'':'disabled')+'>评估并保存核销组</button></form><p class="hint">确认与撤销仅业务负责人可操作。确认后账单与所选线体日期被锁定，后续导入的同线同日数据不改变已确认结论。</p></section>'
 +'<section><div class="section-title"><h2>供电账单</h2><span>'+billList.length+' 张 · '+open.length+' 张未占用</span></div><div class="bill-list">'+billList.map(b=>'<article><div><strong>'+esc(b.bill_no)+'</strong><p>'+esc(b.line)+' · '+esc(b.start_day)+' 至 '+esc(b.end_day)+'</p><small>来源 '+esc(b.source)+' · 导入 '+date(b.created_at)+'</small></div><div class="bill-side"><strong>'+fmt(b.kwh)+' kWh</strong><span class="bill-state '+(b.claimed?'used':'')+'">'+(b.claimed?'已核销占用':'未占用')+'</span></div></article>').join('')+(!billList.length?'<p class="empty">尚未导入账单。先在左侧导入供电账单。</p>':'')+'</div>'
 +'<div class="section-title"><h2>核销组</h2><span>'+groupList.length+' 组</span></div><div class="recon-tabs">'+tabs.map(t=>'<button class="text-button'+(filter===t[0]?' active':'')+'" data-tab="'+t[0]+'">'+t[1]+'</button>').join('')+'</div><div class="recon-list">'+groupList.map(g=>groupCard(g,admin)).join('')+(!groupList.length?'<p class="empty">该状态下暂无核销组。</p>':'')+'</div></section></div>';
}
async function loadDays(refresh){
 const billSel=document.querySelector('#group-bill'),dsSel=document.querySelector('#group-dataset'),box=document.querySelector('#day-picker'),total=document.querySelector('#day-total');
 if(!billSel||!billSel.value){box.innerHTML='<p class="hint">暂无未占用账单。</p>';return;}
 const bill=await bills.get(billSel.value),ds=await datasets.get(dsSel.value);
 const rows=ds.records.filter(r=>r.line===bill.line).sort((a,b)=>String(a.day).localeCompare(String(b.day)));
 if(!rows.length){box.innerHTML='<p class="hint">批次中没有线体 '+esc(bill.line)+' 的日样本。</p>';total.textContent='';return;}
 box.innerHTML='<div class="day-grid">'+rows.map(r=>{const inRange=r.day>=bill.start_day&&r.day<=bill.end_day;return '<label class="day-cell'+(inRange?'':' out')+'"><input type="checkbox" data-day="'+esc(r.day)+'" data-kwh="'+r.kwh+'" '+(inRange?'checked':'')+'><span>'+esc(r.day)+'</span><small>'+fmt(r.kwh)+'</small></label>';}).join('')+'</div>';
 const update=()=>{const picked=[...box.querySelectorAll('input:checked')];const sum=picked.reduce((s,c)=>s+Number(c.dataset.kwh),0);total.textContent='已选 '+picked.length+' 天 · 样本合计 '+fmt(Math.round(sum*10000)/10000)+' kWh · 账单 '+fmt(bill.kwh)+' kWh · 差额 '+fmt(Math.round((sum-bill.kwh)*10000)/10000)+' kWh';};
 box.querySelectorAll('input').forEach(c=>c.onchange=update);update();
}
export function bindRecon(refresh){
 let source='manual.json';
 document.querySelector('#refresh-recon').onclick=refresh;
 document.querySelector('#bill-file').addEventListener('change',async e=>{try{const file=e.target.files[0];if(!file)return;source=file.name;const text=await file.text(),rows=file.name.endsWith('.csv')?parseCSV(text):JSON.parse(text);document.querySelector('[name=bills]').value=JSON.stringify(rows,null,2);}catch(error){notify(error.message,true);}});
 submit(document.querySelector('#bill-form'),async f=>{const rows=JSON.parse(f.get('bills'));const list=Array.isArray(rows)?rows:[rows];await bills.import({source,bills:list});notify('账单已导入 '+list.length+' 张');await refresh();});
 const billSel=document.querySelector('#group-bill'),dsSel=document.querySelector('#group-dataset');
 if(billSel&&dsSel){billSel.onchange=()=>loadDays(refresh).catch(e=>notify(e.message,true));dsSel.onchange=()=>loadDays(refresh).catch(e=>notify(e.message,true));if(billSel.value)loadDays(refresh).catch(e=>notify(e.message,true));}
 submit(document.querySelector('#group-form'),async f=>{const days=[...document.querySelectorAll('#day-picker input:checked')].map(c=>c.dataset.day);if(!days.length)throw new Error('请至少勾选一天日样本');await recon.create({name:f.get('name'),bill_id:Number(f.get('bill_id')),dataset_id:Number(f.get('dataset_id')),days});notify('核销组已保存，逐日覆盖与总量已评估');await refresh();});
 document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=async()=>{filter=b.dataset.tab;await refresh();});
 document.querySelectorAll('[data-confirm]').forEach(b=>b.onclick=async()=>{try{await recon.confirm(b.dataset.confirm);notify('核销组已确认，账单与线体日期已锁定');await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-revoke]').forEach(b=>b.onclick=async()=>{const reason=prompt('撤销原因（可选）：','')??'';try{await recon.revoke(b.dataset.revoke,reason);notify('核销组已撤销，占用已释放，可重新编组');await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-items]').forEach(b=>b.onclick=async()=>{const box=document.querySelector('#items-'+b.dataset.items);if(box.innerHTML){box.innerHTML='';return;}try{const g=await recon.get(b.dataset.items);box.innerHTML=table(itemCols,g.items,'该组没有留存日样本。');}catch(e){notify(e.message,true);}});
}
