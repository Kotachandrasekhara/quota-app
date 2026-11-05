
let S=null,fetchedAt=0,sig="",intro=true,introStart=0,dismissedAlert=0;
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
function remainingNow(){if(!S)return 0;return S.week_remaining-(S.active?(Date.now()-fetchedAt)/1000:0);}
function severity(f){return f>=1?"crit":f>=.75?"warn":"ok";}
function paintCount(v){
 const r=Math.round(v),c=$("count");c.classList.toggle("over",r<0);
 c.textContent=r>=0?r.toLocaleString():"+"+(-r).toLocaleString();
 $("countsub").textContent=r>=0?fh(r)+" left of "+fh(S.weekly_budget)+" (1 token = 1 second of active time)":"over your "+fh(S.weekly_budget)+" week by "+fh(-r);
 const used=S.weekly_budget-r,f=used/Math.max(1,S.weekly_budget),fill=$("fuelfill");
 fill.style.width=Math.min(100,Math.max(0,f*100))+"%";
 fill.style.background=f>=1?"var(--crit)":f>=.75?"var(--warn)":"var(--brand)";
}
function frame(now){const t=Math.min(1,(now-introStart)/900),e=1-Math.pow(1-t,3);
 if(t<1){const target=remainingNow();$("count").textContent=Math.round(target*e).toLocaleString();requestAnimationFrame(frame);}else{intro=false;paintCount(remainingNow());}}
setInterval(()=>{if(S&&!intro)paintCount(remainingNow());},1000);
function render(){
 setMeta(S.categories);OFFL=S.off_types;
 $("date").textContent=new Date().toLocaleDateString(undefined,{weekday:"long",day:"numeric",month:"long"});
 const wf=S.week_used/Math.max(1,S.weekly_budget),sev=severity(wf);
 $("banner").hidden=S.week_remaining>0;
 const lab={ok:["✓","On track"],warn:["!","Heads up"],crit:["✕","Over budget"]}[sev];
 $("pill").replaceChildren(el("span",{class:"ico "+sev,text:lab[0]}),document.createTextNode(lab[1]));
 const tk=S.weekly_budget+"/"+S.daily_budget,firstRun=!$("fuel").dataset.ticks;
 if($("fuel").dataset.ticks!==tk){$("fuel").querySelectorAll("b").forEach(b=>b.remove());const frag=[];
  for(let k=1;k<S.weekly_budget/S.daily_budget-1e-6;k++)frag.push(el("b",{style:"left:"+(k*S.daily_budget/S.weekly_budget*100)+"%"}));
  $("fuel").append(...frag);$("fuel").dataset.ticks=tk;
  $("fuelnote").textContent="Each gap marks one day of budget ("+fh(S.daily_budget)+")."+(S.week_off>0?" "+S.week_off+" day"+(S.week_off===1?"":"s")+" off this week.":"");}
 if(firstRun){if(reduce){intro=false;paintCount(remainingNow());}else{introStart=performance.now();requestAnimationFrame(frame);}}
 else if(!intro)paintCount(remainingNow());
 $("f1").textContent=fh(S.week_used);$("f1l").textContent="Used this week ("+Math.round(wf*100)+"%)";
 $("f2").textContent=fh(S.today_used);
 $("f2l").textContent=S.today_off?"Today is a day off ("+(OFFL[S.today_off]||"day off").toLowerCase()+")":(S.today_remaining>=0?"Today, "+fh(S.today_remaining)+" left of "+fh(S.today_budget):"Today, "+fh(-S.today_remaining)+" over "+fh(S.today_budget));
 $("f3").textContent=(Math.max(0,S.week_remaining)/S.daily_budget).toFixed(1);$("f3l").textContent="Full days left at "+fh(S.daily_budget);
 const chip=$("chiptext");$("dot").className="dot"+(S.active?" on":"");
 if(S.paused)chip.textContent="Private mode: nothing is being recorded";
 else if(!S.idle_supported)chip.textContent="Counting all running time (idle detection unavailable)";
 else if(S.active)chip.textContent=S.now&&S.now.app?"Working in "+S.now.app+(S.now.cat?" ("+S.now.cat+")":""):"Working";
 else chip.textContent="Idle, tokens paused";
 const off=S.today_off,away=S.today_away;$("offbanner").hidden=!(off||away);
 if(off){const wd=S.workdays.includes(S.days.findIndex(d=>d.today));
  $("offtext").textContent="Today is marked as "+(OFFL[off]||"a day off").toLowerCase()+"."+(wd?" Your tokens for the week are already "+fh(S.daily_budget)+" lower.":"");}
 else if(away)$("offtext").textContent="You are away for "+fh(away)+" today ("+(OFFL[S.today_away_type]||"leave").toLowerCase()+"). Today's budget is "+fh(S.today_budget)+" instead of "+fh(S.daily_budget)+".";
 /* categories */
 segBar($("segbar"),META.map(c=>({name:c.name,slot:c.slot,value:S.cats_today[c.name]||0})));
 catLegend($("legend"));
 const rows=[el("div",{class:"crow head-row"},[el("div",{text:"Category"}),el("div",{text:"Today"}),el("div",{class:"wk",text:"This week"}),el("div")])];
 META.forEach(c=>{const inner=[el("div",{class:"nm"},[el("i",{class:"sw",style:"background:"+catColor(c.slot)}),document.createTextNode(c.name)]),
  el("div",{class:"t"},[el("b",{text:fh(S.cats_today[c.name]||0)})]),el("div",{class:"t wk"},[el("b",{text:fh(S.cats_week[c.name]||0)})]),
  el("div",{class:"go",text:c.slot?"Open dashboard":""})];
  if(c.slot){const a=el("a",{class:"crow",href:"/reports#tab="+encodeURIComponent(c.name)},inner);rows.push(a);}else rows.push(el("div",{class:"crow"},inner));});
 $("crows").replaceChildren(...rows);
 /* week chart (rebuilt only when the data changes, so tooltips stay put) */
 const s2=JSON.stringify(S.days.map(d=>[d.used,d.today,d.off,d.away]))+S.daily_budget;
 const perDay=S.days.some(d=>d.away>0);
 if(s2!==sig){sig=s2;
  columnChart($("week"),S.days.map(d=>({title:fdate(parse(d.date)),tick:d.label,over:d.used>d.budget&&!d.off,off:d.off,budget:perDay?d.budget:undefined,
   segs:META.map(c=>({v:d.cats[c.name]||0,color:catColor(c.slot)})),
   rows:(d.off?[[OFFL[d.off]||"Day off","marked as a day off"]]:d.away?[[fh(d.away)+" away",(OFFL[d.away_type]||"leave")+", part of the day"]]:[]).concat([[fh(d.used),d.off?"worked":pct(d.used,d.budget)+" of that day's budget"]],META.filter(c=>(d.cats[c.name]||0)>0).map(c=>[fh(d.cats[c.name]),c.name]))})),
   {budget:S.daily_budget,budgetLabel:"Budget "+hrs(S.daily_budget).toFixed(1)+"h",label:"Hours per day this week",markOver:true,height:230,gap:30});
  catLegend($("wlegend"),[{label:"Over daily budget",color:"var(--crit)"},{label:"Day off",color:"var(--grid)"},{label:"Budget",line:true}]);}
 appRows($("apps"),S.apps_today.map(a=>({name:a.name,seconds:a.seconds,cat:a.cat,color:colorOf(a.cat)})),"Nothing yet today. Apps appear here as you work.");
 fillCats();
 const al=S.last_alert,fresh=al&&Date.now()/1000-al.ts<900&&al.ts!==dismissedAlert;
 $("alertbar").hidden=!fresh;if(fresh){$("altitle").textContent=al.title+" (at "+al.time+").";$("altext").textContent=al.live==="week_left"?"Left this week now: "+fh(Math.max(0,S.week_remaining))+".":al.message;}
 $("acard").hidden=!S.offline_today.length;
 $("aways").replaceChildren(...S.offline_today.map(e=>{const b=el("button",{type:"button",text:"Remove"});
  b.onclick=async()=>{try{await postAway({date:iso(new Date()),remove:e.id});}catch(x){}poll();};
  return el("div",{class:"offrow"},[el("span",{text:e.start+", "+e.mins+" min, "+e.kind+(e.note?": "+e.note:"")+" ("+e.cat+")"}),b]);}));
 $("wcard").hidden=!S.domains_today.length;
 if(S.domains_today.length)appRows($("webs"),S.domains_today.map(a=>({name:a.name,seconds:a.seconds,cat:a.cat,color:colorOf(a.cat)})));
 $("tcard").hidden=!S.titles_today.length;
 if(S.titles_today.length)appRows($("titles"),S.titles_today);
}
async function poll(){
 try{const r=await fetch("/api/status");if(!r.ok)throw 0;S=await r.json();fetchedAt=Date.now();$("err").textContent="";render();}
 catch(e){$("err").textContent="Couldn't reach K(Qu)ota. Check that it is still running in your terminal.";}
}
async function postOff(body){const r=await fetch("/api/days-off",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const j=await r.json();if(!r.ok)throw new Error(j.error||"Couldn't save that.");return j;}
const syncOff=()=>{const none=$("o_type").value==="none",part=$("o_len").value==="part";$("o_lwrap").hidden=none;$("o_hwrap").hidden=none||!part;};
$("o_len").onchange=syncOff;$("o_type").onchange=syncOff;
$("offmenu").addEventListener("toggle",()=>{if($("offmenu").open){$("o_date").value=iso(new Date());$("o_msg").textContent="";syncOff();}});
$("offform").onsubmit=async e=>{e.preventDefault();const m=$("o_msg"),d=$("o_date").value,type=$("o_type").value,part=$("o_len").value==="part"&&type!=="none";
 const body={from:d,to:d,type,workdays_only:false};if(part)body.hours=$("o_hours").value;
 try{const j=await postOff(body);m.className="msg ok";m.textContent=j.changed?"Saved.":"Nothing to change.";$("offmenu").open=false;poll();}
 catch(err){m.className="msg bad";m.textContent=err.message;}};
function fillCats(){const sel=$("a_cat");if(sel.dataset.n===String(META.length))return;sel.dataset.n=String(META.length);
 sel.replaceChildren(...META.map(c=>el("option",{value:c.name,text:c.name})));if(META.some(c=>c.name==="Meetings"))sel.value="Meetings";}
async function postAway(body){const r=await fetch("/api/offline",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const j=await r.json();if(!r.ok)throw new Error(j.error||"Couldn't save that.");return j;}
$("awaymenu").addEventListener("toggle",()=>{if($("awaymenu").open){$("offmenu").open=false;$("a_date").value=iso(new Date());$("a_msg").textContent="";}});
$("offmenu").addEventListener("toggle",()=>{if($("offmenu").open)$("awaymenu").open=false;});
$("awayform").onsubmit=async e=>{e.preventDefault();const m=$("a_msg");
 try{await postAway({date:$("a_date").value,start:$("a_start").value,minutes:$("a_mins").value,kind:$("a_kind").value,category:$("a_cat").value,note:$("a_note").value});
  m.className="msg ok";m.textContent="Saved.";$("a_note").value="";$("awaymenu").open=false;poll();}
 catch(err){m.className="msg bad";m.textContent=err.message;}};
$("aldismiss").onclick=()=>{if(S&&S.last_alert)dismissedAlert=S.last_alert.ts;$("alertbar").hidden=true;};
$("offremove").onclick=async()=>{const d=S&&S.days.find(x=>x.today);if(!d)return;try{await postOff({from:d.date,to:d.date,type:"none",workdays_only:false});}catch(e){}poll();};
addEventListener("privchange",poll);
poll();setInterval(poll,3000);
let rt;addEventListener("resize",()=>{clearTimeout(rt);rt=setTimeout(()=>{sig="";if(S)render();},200);});
