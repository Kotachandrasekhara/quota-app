
let D=null,tab="Overview",current="30d";
const tile=(l,v,s)=>el("div",{class:"tile"},[el("div",{class:"v",text:v}),el("div",{class:"l",text:l}),el("div",{class:"s",text:s||" "})]);
function panel(parent,title,note){const body=el("div",{class:"chart"});const kids=[el("h2",{text:title})];if(note)kids.push(el("div",{class:"note",text:note}));kids.push(body);
 parent.append(el("section",{class:"panel"},kids));return body;}
const delta=(cur,prev)=>!prev?"no data for the period before":(cur>=prev?"▲ ":"▼ ")+Math.abs(Math.round((cur-prev)/prev*100))+"% vs the period before";
const pad=(parent)=>{const g=el("div",{class:"grid2"});parent.append(g);return g;};
function timesheet(parent,head,rows,foot){
 const det=el("details",{id:"tbl"},[el("summary",{text:"Timesheet (table view)"})]);
 det.append(rows.length?el("div",{class:"tablewrap"},[el("table",{},[el("thead",{},[el("tr",{},head.map((h,i)=>el("th",{class:i?"n":"",text:h})))]),
  el("tbody",{},rows.map(r=>el("tr",{},r.map((c,i)=>el("td",{class:i?"n":"",text:c}))))),el("tfoot",{},[el("tr",{},foot.map((c,i)=>el("td",{class:i?"n":"",text:c})))])])]):el("div",{class:"empty",text:"No tracked time in this range. Pick a longer range or wait until you have worked a bit."}));
 parent.append(el("section",{class:"panel"},[det]));
}
const WEBNOTE="Website names only, never the page or address.";
const WEBEMPTY="No website data in this range. Websites are read on Windows (Chrome, Edge, Brave, Firefox) and on a Mac (Chrome, Edge, Brave, Arc, Safari), not on Linux.";
function legendFor(host){const l=el("div",{class:"legend"});host.parentNode.insertBefore(l,host);catLegend(l);}
/* Time of day: hours per clock hour, stacked by category (or one category) */
function timeOfDay(host,series,withLegend){
 if(!series.some(s=>s.arr.some(v=>v>0))){host.append(el("div",{class:"empty",text:"No time-of-day data yet. It is recorded from now on."}));return;}
 if(withLegend)legendFor(host);
 columnChart(host,Array.from({length:24},(_,h)=>{const segs=series.map(s=>({v:s.arr[h]||0,color:s.color})),t=segs.reduce((a,s)=>a+s.v,0);
  return{title:p2(h)+":00 to "+p2(h)+":59",tick:p2(h),segs,rows:[[fh(t),"in this hour"]].concat(series.filter((s,j)=>segs[j].v>0).map(s=>[fh(s.arr[h]),s.name]))};}),
  {height:210,gap:40,label:"Hours by time of day"});
}
function renderOverview(main){
 const days=D.days,DB=D.daily_budget,WB=D.weekly_budget,worked=days.filter(d=>d.used>0),total=days.reduce((a,d)=>a+d.used,0);
 const longest=worked.reduce((a,d)=>d.used>(a?a.used:0)?d:a,null),overD=worked.filter(d=>d.used>d.budget&&!d.off).length,overW=D.weeks.filter(w=>w.used>w.budget).length,offN=days.filter(d=>d.off).length;
 const catTot=n=>days.reduce((a,d)=>a+(d.cats[n]||0),0);
 main.append(el("div",{class:"reporthead panel"},[el("div",{},[el("div",{class:"big",text:fh(total)}),el("div",{class:"sub",text:total.toLocaleString()+" tokens over "+worked.length+" worked day"+(worked.length===1?"":"s")+". "+delta(total,D.prior.used)})]),
  el("div",{class:"tilegrid"},[tile("Average per worked day",worked.length?fh(total/worked.length):"-",worked.length?pct(total/worked.length,DB)+" of daily budget":""),
   tile("Longest day",longest?fh(longest.used):"-",longest?fdate(parse(longest.date)):""),tile("Days over daily budget",String(overD),"budget "+fh(DB)+(offN?", "+offN+" day"+(offN===1?"":"s")+" off":"")),
   tile("Weeks over weekly budget",String(overW),"of "+D.weeks.length+", full budget "+fh(WB))])]));
 const sec=el("section",{class:"panel"},[el("h2",{text:"Where your time went"}),el("div",{class:"note",text:"Share of tracked time by category. Open one for its own dashboard."})]);
 const sb=el("div");sec.append(sb);const lg=el("div",{class:"legend"});sec.append(lg);
 const grid=el("div",{class:"catgrid"});
 META.forEach(c=>{const v=catTot(c.name),inner=[el("div",{class:"cname"},[el("i",{class:"sw",style:"background:"+catColor(c.slot)}),document.createTextNode(c.name)]),el("div",{class:"v",text:fh(v)}),
  el("div",{class:"s",text:pct(v,total)+" of your time. "+delta(v,D.prior.cats[c.name]||0)})];
  const card=c.slot?el("a",{class:"catcard",href:"#tab="+encodeURIComponent(c.name)},inner):el("div",{class:"catcard"},inner);
  if(c.slot)card.addEventListener("click",e=>{e.preventDefault();setTab(c.name);});grid.append(card);});
 sec.append(grid);main.append(sec);
 segBar(sb,META.map(c=>({name:c.name,slot:c.slot,value:catTot(c.name)})));catLegend(lg);
 const short=days.length<=14,mk=(it,label)=>it;
 let host=panel(main,"Daily time","Hours worked each day, by category, against your daily budget.");
 const l1=el("div",{class:"legend"});host.parentNode.insertBefore(l1,host);catLegend(l1,[{label:"Over daily budget",color:"var(--crit)"}].concat(offN?[{label:"Day off",color:"var(--grid)"}]:[],[{label:"Budget",line:true}]));
 const perDay=days.some(d=>d.away>0);
 columnChart(host,days.map(d=>{const dt=parse(d.date),over=d.used>d.budget&&!d.off,rows=[[fh(d.used),d.off?"worked on a day off":pct(d.used,d.budget)+" of that day's budget"]];if(d.off)rows.unshift([OFFL[d.off]||"Day off","marked as a day off"]);
   if(d.away)rows.unshift([fh(d.away)+" away",(OFFL[d.away_type]||"Leave")+", part of the day"]);
   if(d.offline)rows.push([fh(d.offline),"away from the computer (counted)"]);
   if(over)rows.push([fh(d.used-d.budget),"over budget"]);META.forEach(c=>{if((d.cats[c.name]||0)>0)rows.push([fh(d.cats[c.name]),c.name]);});if(d.first)rows.push([d.first+" to "+d.last,"first to last active"]);
   return{over,off:d.off,budget:perDay?d.budget:undefined,title:fdate(dt),rows,tick:short?DOW[(dt.getDay()+6)%7]+" "+dt.getDate():dt.getDate()+" "+MON[dt.getMonth()],segs:META.map(c=>({v:d.cats[c.name]||0,color:catColor(c.slot)}))};}),
  {budget:DB,budgetLabel:"Budget "+hrs(DB).toFixed(1)+"h",label:"Daily hours worked",markOver:true});
 host=panel(main,"Weekly totals","Full Monday to Sunday weeks that touch this range, against your weekly budget. A day off lowers that week's budget.");
 const l2=el("div",{class:"legend"});host.parentNode.insertBefore(l2,host);catLegend(l2,[{label:"Over weekly budget",color:"var(--crit)"},{label:"Budget",line:true}]);
 columnChart(host,D.weeks.map(w=>{const dt=parse(w.start),over=w.used>w.budget,rows=[[fh(w.used),pct(w.used,w.budget)+" of that week's budget ("+fh(w.budget)+")"]];
   if(over)rows.push([fh(w.used-w.budget),"over budget"]);META.forEach(c=>{if((w.cats[c.name]||0)>0)rows.push([fh(w.cats[c.name]),c.name]);});
   return{over,budget:w.budget,title:"Week of "+fdate(dt),rows,tick:dt.getDate()+" "+MON[dt.getMonth()],segs:META.map(c=>({v:w.cats[c.name]||0,color:catColor(c.slot)}))};}),
  {budget:WB,budgetLabel:"Budget "+hrs(WB).toFixed(1)+"h",label:"Weekly hours worked",markOver:true});
 host=panel(main,"Calendar","A stronger colour means closer to your daily budget. Red days went over.");
 const key=el("div",{class:"heatkey"});host.parentNode.append(key);
 heatmap(host,days,{value:d=>d.used,budget:DB,tint:"var(--brand)",key,label:"Calendar heatmap of daily hours"});
 const g=pad(main);
 const sums=Array(7).fill(0).map(()=>({}));const cnt=Array(7).fill(0);
 worked.forEach(d=>{if(d.off)return;cnt[d.weekday]++;META.forEach(c=>{sums[d.weekday][c.name]=(sums[d.weekday][c.name]||0)+(d.cats[c.name]||0);});});
 host=panel(g,"Average by weekday","Average hours on days you worked, by category. Days off are left out.");
 legendFor(host);
 columnChart(host,DOW.map((n,i)=>{const segs=META.map(c=>({v:cnt[i]?(sums[i][c.name]||0)/cnt[i]:0,color:catColor(c.slot)})),a=segs.reduce((x,s)=>x+s.v,0);
  return{title:n,tick:n,segs,rows:[[fh(a),cnt[i]?"average over "+cnt[i]+" day"+(cnt[i]===1?"":"s"):"no data"]].concat(META.filter((c,j)=>segs[j].v>0).map((c,j)=>[fh(segs[META.indexOf(c)].v),c.name]))};}),
  {budget:DB,budgetLabel:"Budget "+hrs(DB).toFixed(1)+"h",height:210,gap:34,label:"Average hours by weekday"});
 host=panel(g,"Time of day","Total hours by clock hour, by category."+(D.hours_estimated?" Days recorded before this feature are split in proportion to that day's category mix.":""));
 timeOfDay(host,META.map(c=>({name:c.name,color:catColor(c.slot),arr:D.cat_hours[c.name]||[]})),true);
 const g3=pad(main);
 host=panel(g3,"Where your time went, by app","Top apps in this range. The bar colour is the app's category.");
 appRows(host,D.apps.map(a=>({name:a.name,seconds:a.seconds,cat:a.cat,color:colorOf(a.cat)})),"No app data in this range. App tracking records from when it was switched on.");
 host=panel(g3,"Top websites",WEBNOTE);
 appRows(host,(D.domains||[]).map(a=>({name:a.name,seconds:a.seconds,cat:a.cat,color:colorOf(a.cat)})),WEBEMPTY);
 const names=META.map(c=>c.name);
 timesheet(main,["Date","Note","Time"].concat(names,["First active","Last active","% of budget"]),
  days.filter(d=>d.used>0||d.off||d.away).map(d=>[fdate(parse(d.date)),(d.off?(OFFL[d.off]||"Day off"):d.away?(OFFL[d.away_type]||"Leave")+" ("+fh(d.away)+")":"-")+(d.offline?(d.off||d.away?"; ":"")+fh(d.offline)+" away from computer":""),fh(d.used)].concat(names.map(n=>(d.cats[n]||0)?fh(d.cats[n]):"-"),[d.first||"-",d.last||"-",d.off?"-":pct(d.used,d.budget)])),
  ["Total","",fh(total)].concat(names.map(n=>fh(catTot(n))),["","",""]));
}
function renderCategory(main,name){
 const slot=SLOT[name],col=catColor(slot),days=D.days,DB=D.daily_budget;
 const val=d=>d.cats[name]||0,total=days.reduce((a,d)=>a+d.used,0),sum=days.reduce((a,d)=>a+val(d),0);
 const active=days.filter(d=>val(d)>0),best=active.reduce((a,d)=>val(d)>(a?val(a):0)?d:a,null);
 const peak=D.weeks.reduce((a,w)=>(w.cats[name]||0)>(a?(a.cats[name]||0):0)?w:a,null);
 main.append(el("div",{class:"reporthead panel"},[el("div",{},[el("div",{class:"cname"},[el("i",{class:"sw",style:"background:"+col}),document.createTextNode(name)]),el("div",{class:"big",text:fh(sum)}),
   el("div",{class:"sub",text:pct(sum,total)+" of your tracked time. "+delta(sum,D.prior.cats[name]||0)})]),
  el("div",{class:"tilegrid"},[tile("Average per active day",active.length?fh(sum/active.length):"-",active.length+" day"+(active.length===1?"":"s")+" with "+name.toLowerCase()),
   tile("Best day",best?fh(val(best)):"-",best?fdate(parse(best.date)):""),
   tile("Peak week",peak&&(peak.cats[name]||0)>0?fh(peak.cats[name]):"-",peak&&(peak.cats[name]||0)>0?"Week of "+fdate(parse(peak.start)):""),
   tile("Share of a typical day",active.length&&total?pct(sum,days.filter(d=>val(d)>0).reduce((a,d)=>a+d.used,0)):"-","on days with "+name.toLowerCase())])]));
 if(!sum){main.append(el("section",{class:"panel"},[el("h2",{text:"No "+name.toLowerCase()+" time in this range"}),el("div",{class:"empty",text:"Time lands here when the app in front matches this category's rules. Check or add rules under Settings, then Categories."})]));return;}
 const short=days.length<=14;
 let host=panel(main,"Daily time","Hours of "+name.toLowerCase()+" each day."+(days.some(d=>d.off)?" Shaded days are days off.":""));
 columnChart(host,days.map(d=>{const dt=parse(d.date);return{title:fdate(dt),tick:short?DOW[(dt.getDay()+6)%7]+" "+dt.getDate():dt.getDate()+" "+MON[dt.getMonth()],segs:[{v:val(d),color:col}],off:d.off,rows:[[fh(val(d)),(d.off?"day off, ":"")+pct(val(d),d.used)+" of that day"]]};}),{label:"Daily hours of "+name});
 host=panel(main,"Weekly totals","Full Monday to Sunday weeks that touch this range.");
 columnChart(host,D.weeks.map(w=>{const dt=parse(w.start),v=w.cats[name]||0;return{title:"Week of "+fdate(dt),tick:dt.getDate()+" "+MON[dt.getMonth()],segs:[{v,color:col}],rows:[[fh(v),pct(v,w.used)+" of that week"]]};}),{label:"Weekly hours of "+name});
 host=panel(main,"Calendar","A stronger colour means more of this category on that day.");
 const key=el("div",{class:"heatkey"});host.parentNode.append(key);
 heatmap(host,days,{value:val,tint:col,key,label:"Calendar heatmap of "+name});
 const g=pad(main),sums=Array(7).fill(0),cnt=Array(7).fill(0);active.forEach(d=>{if(d.off)return;sums[d.weekday]+=val(d);cnt[d.weekday]++;});
 host=panel(g,"Average by weekday","Average hours on days with "+name.toLowerCase()+".");
 columnChart(host,DOW.map((n,i)=>{const a=cnt[i]?sums[i]/cnt[i]:0;return{title:n,tick:n,segs:[{v:a,color:col}],rows:[[fh(a),cnt[i]?"average over "+cnt[i]+" day"+(cnt[i]===1?"":"s"):"no data"]]};}),{height:210,gap:34,label:"Average hours by weekday"});
 host=panel(g,"Time of day","When you do this, by clock hour."+(D.hours_estimated?" Days recorded before this feature are split in proportion to that day's category mix.":""));
 timeOfDay(host,[{name,color:col,arr:D.cat_hours[name]||[]}],false);
 const g3=pad(main);
 host=panel(g3,"Top apps","Where this category's time went.");
 appRows(host,(D.cat_apps[name]||[]).map(a=>({name:a.name,seconds:a.seconds,color:col})),"No app breakdown for this category in this range.");
 host=panel(g3,"Top websites","Websites you had open for "+name.toLowerCase()+". "+WEBNOTE);
 appRows(host,((D.cat_domains||{})[name]||[]).map(a=>({name:a.name,seconds:a.seconds,color:col})),WEBEMPTY);
 timesheet(main,["Date","Time","% of that day"],active.map(d=>[fdate(parse(d.date)),fh(val(d)),pct(val(d),d.used)]),["Total",fh(sum),pct(sum,total)]);
}
function render(){
 if(!D)return;setMeta(D.categories);OFFL=D.off_types||OFFL;
 $("range").textContent=fdate(parse(D.from))+" to "+fdate(parse(D.to));
 if(tab!=="Overview"&&!(SLOT[tab]>0))tab="Overview";
 drawTabs();const main=$("main");main.replaceChildren();
 tab==="Overview"?renderOverview(main):renderCategory(main,tab);
}
function drawTabs(){const mk=(name,slot)=>{const b=el("button",{class:"tab",role:"tab","aria-selected":String(tab===name)},slot?[el("i",{class:"sw",style:"background:"+catColor(slot)}),document.createTextNode(name)]:[document.createTextNode(name)]);b.onclick=()=>setTab(name);return b;};
 $("tabs").replaceChildren(mk("Overview",0),...(D?D.categories.filter(c=>c.slot):[]).map(c=>mk(c.name,c.slot)));}
function setTab(t){tab=t;try{history.replaceState(null,"","#tab="+encodeURIComponent(t));}catch(e){}render();}
function readHash(){const m=/tab=([^&]+)/.exec(location.hash);if(m)tab=decodeURIComponent(m[1]);}
const PRESETS=[["this-week","This week"],["last-week","Last week"],["this-month","This month"],["last-month","Last month"],["30d","Last 30 days"],["12w","Last 12 weeks"],["year","This year"]];
function presetRange(k){const t=new Date();t.setHours(0,0,0,0);const mon=mondayOf(t);
 switch(k){case"this-week":return[mon,addDays(mon,6)];case"last-week":return[addDays(mon,-7),addDays(mon,-1)];
 case"this-month":return[new Date(t.getFullYear(),t.getMonth(),1),t];case"last-month":return[new Date(t.getFullYear(),t.getMonth()-1,1),new Date(t.getFullYear(),t.getMonth(),0)];
 case"12w":return[addDays(mon,-77),t];case"year":return[new Date(t.getFullYear(),0,1),t];default:return[addDays(t,-29),t];}}
function drawPresets(){$("presets").replaceChildren(...PRESETS.map(([k,l])=>{const b=el("button",{text:l,class:k===current?"on":""});b.onclick=()=>{const[a,z]=presetRange(k);load(k,iso(a),iso(z));};return b;}));}
async function load(k,from,to){
 current=k;drawPresets();$("from").value=from;$("to").value=to;$("err").textContent="";$("main").style.opacity=.55;
 $("csvd").href=`/api/export.csv?kind=days&from=${from}&to=${to}`;$("csva").href=`/api/export.csv?kind=apps&from=${from}&to=${to}`;$("csvw").href=`/api/export.csv?kind=domains&from=${from}&to=${to}`;
 try{const r=await fetch(`/api/history?from=${from}&to=${to}`),j=await r.json();
  if(!r.ok)$("err").textContent=j.error||"Couldn't load history.";else{D=j;render();}}
 catch(e){$("err").textContent="Couldn't reach Quota. Check that it is still running in your terminal.";}
 $("main").style.opacity=1;
}
$("apply").onclick=()=>{if($("from").value&&$("to").value)load("custom",$("from").value,$("to").value);};
$("print").onclick=()=>window.print();
addEventListener("beforeprint",()=>{const t=$("tbl");if(t)t.open=true;});
addEventListener("hashchange",()=>{readHash();render();});
let rt;addEventListener("resize",()=>{clearTimeout(rt);rt=setTimeout(render,150);});
readHash();drawTabs();const[a0,z0]=presetRange("30d");load("30d",iso(a0),iso(z0));
