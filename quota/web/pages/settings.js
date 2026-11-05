
const NUM=["daily_hours","weekly_hours","idle_minutes","remind_every_minutes","overtime_remind_minutes","private_remind_minutes"];
const DN=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
function drawDays(sel){$("workdays").replaceChildren(...DN.map((n,i)=>{const cb=el("input",{type:"checkbox","data-d":String(i)});cb.checked=sel.includes(i);return el("label",{},[cb,document.createTextNode(n)]);}));}
const pickedDays=()=>[...document.querySelectorAll("#workdays input")].filter(c=>c.checked).map(c=>Number(c.dataset.d));
const CHK=["track_categories","classify_by_title","track_apps","track_domains","track_titles"];
const TXT=["categories_text","titles_text","browsers_text"];
function say(t,ok){const m=$("msg");m.className="msg "+(ok?"ok":"bad");m.textContent=t;if(ok)setTimeout(()=>{m.textContent="";},3500);}
async function loadCfg(){try{const c=await (await fetch("/api/config")).json();
 NUM.forEach(k=>$("c_"+k).value=c[k]??"");$("c_alert_percents").value=(c.alert_percents||[]).join(", ");drawDays(c.workdays||[0,1,2,3,4]);
 CHK.forEach(k=>$("c_"+k).checked=!!c[k]);TXT.forEach(k=>$(k==="browsers_text"?k:k).value=c[k]||"");}
 catch(e){say("Couldn't reach Quota. Check that it is still running in your terminal.",false);}}
$("save").onclick=async()=>{const body={};NUM.forEach(k=>body[k]=$("c_"+k).value);body.alert_percents=$("c_alert_percents").value;body.workdays=pickedDays();
 CHK.forEach(k=>body[k]=$("c_"+k).checked);TXT.forEach(k=>body[k]=$(k).value);
 try{const r=await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),j=await r.json();
  if(!r.ok){say(j.error||"Couldn't save the changes.",false);return;}say("Changes saved.",true);loadCfg();loadOff();}
 catch(e){say("Couldn't reach Quota. Check that it is still running in your terminal.",false);}};
$("defaults").onclick=async()=>{try{const d=await (await fetch("/api/defaults")).json();TXT.forEach(k=>$(k).value=d[k]);say("Defaults loaded. Select Save changes to keep them.",true);}catch(e){say("Couldn't load the defaults.",false);}};
const dayDate=s=>{const[y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d);};
const isoD=d=>d.getFullYear()+"-"+p2(d.getMonth()+1)+"-"+p2(d.getDate());
const fd=d=>DOW[(d.getDay()+6)%7]+" "+d.getDate()+" "+MON[d.getMonth()]+" "+d.getFullYear();
function offMsg(t,ok){const m=$("off_msg");m.className="msg "+(ok?"ok":"bad");m.textContent=t;if(ok)setTimeout(()=>{m.textContent="";},4000);}
async function postOff(body){const r=await fetch("/api/days-off",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const j=await r.json();if(!r.ok)throw new Error(j.error||"Couldn't save the days off.");return j;}
async function loadOff(){
 try{const j=await (await fetch("/api/days-off")).json();OFFL=j.types;const wd=j.workdays;
  const cut=isoD(addDays(new Date(),-60)),keys=Object.keys(j.off).filter(k=>k>=cut).sort(),ranges=[];
  keys.forEach(k=>{const last=ranges[ranges.length-1];
   if(last&&last.type===j.off[k]){let ok=true,x=addDays(dayDate(last.to),1);while(isoD(x)<k){if(wd.includes((x.getDay()+6)%7)){ok=false;break;}x=addDays(x,1);}if(ok){last.to=k;last.n++;return;}}
   ranges.push({from:k,to:k,type:j.off[k],n:1});});
  Object.keys(j.part||{}).filter(k=>k>=cut).forEach(k=>ranges.push({from:k,to:k,type:j.part[k].type,n:1,hours:j.part[k].hours}));
  const host=$("off_list");host.replaceChildren();
  if(!ranges.length){host.append(el("div",{class:"empty",text:"No days off in the last 60 days or coming up. Pick dates above to add some."}));return;}
  ranges.sort((a,b)=>a.from<b.from?1:-1).forEach(r=>{
   const when=r.from===r.to?fd(dayDate(r.from)):fd(dayDate(r.from))+" to "+fd(dayDate(r.to));
   const label=(OFFL[r.type]||"Day off")+(r.hours?", "+r.hours+" h away, ":", ")+when+(r.hours?"":" ("+r.n+" day"+(r.n===1?"":"s")+")");
   const b=el("button",{type:"button",text:"Remove"});
   b.onclick=async()=>{try{await postOff({from:r.from,to:r.to,type:"none"});offMsg("Removed.",true);loadOff();}catch(e){offMsg(e.message,false);}};
   host.append(el("div",{class:"offrow"},[el("span",{text:label}),b]));});
 }catch(e){offMsg("Couldn't load your days off.",false);}
}
$("off_add").onclick=async()=>{const from=$("off_from").value,to=$("off_to").value||from;if(!from){offMsg("Pick a date first.",false);return;}
 try{const hrs=$("off_hours").value,body={from,to,type:$("off_type").value,workdays_only:$("off_wd").checked};if(hrs)body.hours=hrs;const j=await postOff(body);
  offMsg(j.changed?"Marked "+j.changed+" day"+(j.changed===1?"":"s")+(hrs?" with "+hrs+" h away.":" off."):"Nothing changed. That range has no working days. Untick 'Only mark my working days' to mark them anyway.",!!j.changed);loadOff();}
 catch(e){offMsg(e.message,false);}};
async function loadAway(){try{const j=await (await fetch("/api/offline")).json(),host=$("away_list");host.replaceChildren();
 if(!j.items.length){host.append(el("div",{class:"empty",text:"Nothing logged in the last 60 days. Use \"Log time away from the computer\" on the Today page."}));return;}
 j.items.forEach(day=>day.entries.forEach(e=>{const b=el("button",{type:"button",text:"Remove"});
  b.onclick=async()=>{try{const r=await fetch("/api/offline",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({date:day.date,remove:e.id})});
   if(!r.ok)throw 0;loadAway();}catch(x){$("away_msg").className="msg bad";$("away_msg").textContent="Couldn't remove that.";}};
  host.append(el("div",{class:"offrow"},[el("span",{text:fd(dayDate(day.date))+", "+e.start+", "+e.mins+" min, "+e.kind+(e.note?": "+e.note:"")+" ("+e.cat+")"}),b]));}));}
 catch(x){}}
$("testnotify").onclick=async()=>{const m=$("test_msg");
 try{const r=await fetch("/api/test-notify",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
  if(!r.ok)throw 0;m.className="msg ok";m.textContent="Sent. You should see a pop-up now.";setTimeout(()=>{m.textContent="";},6000);}
 catch(e){m.className="msg bad";m.textContent="Couldn't send the test.";}};

function aiMsg(t,ok){const m=$("ai_msg");m.className="msg "+(ok?"ok":"bad");m.textContent=t;if(ok)setTimeout(()=>{m.textContent="";},5000);}
async function aiPost(path,body){const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body||{})});
 const j=await r.json();if(!r.ok)throw new Error(j.error||"Couldn't do that.");return j;}
function drawAI(a){$("ai_endpoint").value=a.endpoint;$("ai_deployment").value=a.deployment;$("ai_version").value=a.api_version;$("ai_sites").checked=a.share_websites;$("ai_key").value="";
 $("ai_key").placeholder=a.key_set?(a.key_source==="environment"?"Using the key from your environment":"Saved"+(a.key_hint?" (ends "+a.key_hint+")":"")+". Leave empty to keep it."):"Paste your key";
 $("ai_clear").hidden=a.key_source!=="settings";}
async function loadAI(){try{drawAI(await (await fetch("/api/ai")).json());}catch(e){aiMsg("Couldn't load the assistant settings.",false);}}
const aiBody=()=>({endpoint:$("ai_endpoint").value,deployment:$("ai_deployment").value,api_version:$("ai_version").value,key:$("ai_key").value,share_websites:$("ai_sites").checked});
$("ai_save").onclick=async()=>{try{drawAI(await aiPost("/api/ai",aiBody()));aiMsg("Saved. Select Test connection to check it.",true);}catch(e){aiMsg(e.message,false);}};
$("ai_test").onclick=async()=>{aiMsg("Testing...",true);try{drawAI(await aiPost("/api/ai",aiBody()));const j=await aiPost("/api/ai/test");aiMsg("Connected. The model answered: "+j.reply,true);}catch(e){aiMsg(e.message,false);}};
$("ai_clear").onclick=async()=>{try{drawAI(await aiPost("/api/ai",Object.assign(aiBody(),{key:"",clear_key:true})));aiMsg("The saved key was removed.",true);}catch(e){aiMsg(e.message,false);}};
loadCfg();loadOff();loadAway();loadAI();
