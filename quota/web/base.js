
const $=id=>document.getElementById(id);
const NS="http://www.w3.org/2000/svg";
const MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],DOW=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
function el(t,a={},k=[]){const e=document.createElement(t);for(const n in a){if(n==="text")e.textContent=a[n];else e.setAttribute(n,a[n]);}k.forEach(c=>e.append(c));return e;}
function sv(t,a={},k=[]){const e=document.createElementNS(NS,t);for(const n in a){if(n==="text")e.textContent=a[n];else e.setAttribute(n,a[n]);}k.forEach(c=>e.append(c));return e;}
const p2=n=>String(n).padStart(2,"0");
const iso=d=>d.getFullYear()+"-"+p2(d.getMonth()+1)+"-"+p2(d.getDate());
const parse=s=>{const[y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d);};
const addDays=(d,n)=>{const x=new Date(d);x.setDate(x.getDate()+n);return x;};
const mondayOf=d=>addDays(d,-((d.getDay()+6)%7));
const hrs=s=>s/3600;
const fh=s=>{const a=Math.max(0,Math.round(s));return Math.floor(a/3600)+"h "+p2(Math.floor(a%3600/60))+"m";};
const fdate=d=>DOW[(d.getDay()+6)%7]+" "+d.getDate()+" "+MON[d.getMonth()]+" "+d.getFullYear();
const pct=(a,b)=>b?Math.round(a/b*100)+"%":"-";
let META=[],SLOT={},OFFL={holiday:"Holiday",leave:"Leave",sick:"Sick day"};
function setMeta(l){META=l;SLOT={};l.forEach(c=>SLOT[c.name]=c.slot);}
const catColor=s=>s?"var(--c"+s+")":"var(--other)";
const colorOf=n=>catColor(SLOT[n]||0);
const tip=$("tip");
function showTip(ev,title,rows){tip.replaceChildren(el("div",{class:"tt",text:title}),...rows.map(r=>el("div",{class:"tr"},[el("b",{text:r[0]}),el("span",{text:" "+r[1]})])));tip.style.display="block";
const w=tip.offsetWidth,h=tip.offsetHeight;let x=ev.clientX+14,y=ev.clientY+14;if(x+w>innerWidth-8)x=ev.clientX-w-14;if(y+h>innerHeight-8)y=ev.clientY-h-14;tip.style.left=Math.max(4,x)+"px";tip.style.top=Math.max(4,y)+"px";}
function hideTip(){tip.style.display="none";}
function hover(n,title,rows){n.addEventListener("pointermove",e=>showTip(e,title,rows));n.addEventListener("pointerleave",hideTip);
n.addEventListener("focus",()=>{const r=n.getBoundingClientRect();showTip({clientX:r.left+r.width/2,clientY:r.top},title,rows);});n.addEventListener("blur",hideTip);n.setAttribute("tabindex","0");}
function barPath(x,y,w,h,r){r=Math.min(r,w/2,h);return `M${x},${y+h}V${y+r}Q${x},${y} ${x+r},${y}H${x+w-r}Q${x+w},${y} ${x+w},${y+r}V${y+h}Z`;}
function axis(maxH){const st=[0.5,1,2,2.5,5,10,20,25,50,100,200];let step=st[st.length-1];for(const s of st){if(maxH/s<=5){step=s;break;}}return{step,top:Math.max(step,Math.ceil(maxH/step-1e-9)*step)};}
/* Column chart. Each item has segs [{v,color}] stacked bottom to top. Bars are at most 24px wide,
   4px rounded at the data end, square on the baseline, with a 2px surface gap between segments. */
function columnChart(host,items,o){
 host.replaceChildren();
 const W=Math.max(320,host.clientWidth||700),H=o.height||220,m={l:42,r:o.budget?96:8,t:22,b:26},pw=W-m.l-m.r,ph=H-m.t-m.b;
 const tot=it=>it.segs.reduce((a,s)=>a+s.v,0);
 const maxV=Math.max(o.budget||0,1,...items.map(tot),...items.map(i=>i.budget||0));
 const{step,top}=axis(hrs(maxV)*1.08);
 const y=v=>m.t+ph-(hrs(v)/top)*ph;
 const svg=sv("svg",{viewBox:`0 0 ${W} ${H}`,width:W,height:H,role:"img","aria-label":o.label});
 for(let t=0;t<=top+1e-9;t+=step){const yy=y(t*3600);svg.append(sv("line",{x1:m.l,x2:W-m.r,y1:yy,y2:yy,class:t===0?"bs":"gl"}),sv("text",{x:m.l-8,y:yy+4,"text-anchor":"end",class:"ax",text:(Number.isInteger(t)?t:t.toFixed(1))+"h"}));}
 const n=items.length,band=pw/n,bw=Math.max(1,Math.min(24,band-2)),every=Math.max(1,Math.ceil((o.gap||54)/band));
 items.forEach((it,i)=>{
  if(it.off)svg.append(sv("rect",{x:m.l+band*i,y:m.t,width:band,height:ph,class:"offband"}));
  const cx=m.l+band*i+band/2,g=sv("g",{class:"bar"}),live=it.segs.filter(s=>s.v>0);let cum=0;
  live.forEach((s,j)=>{const y0=y(cum+s.v),y1=y(cum),gap=j>0?2:0,h=Math.max(1,y1-y0-gap),last=j===live.length-1;
   g.append(sv("path",{d:last?barPath(cx-bw/2,y0,bw,h,4):`M${cx-bw/2},${y0}h${bw}v${h}h${-bw}Z`,class:"fill",fill:s.color}));cum+=s.v;});
  g.append(sv("rect",{x:m.l+band*i,y:m.t,width:band,height:ph,fill:"transparent"}));
  if(o.markOver&&it.over)g.append(sv("circle",{cx,cy:y(tot(it))-9,r:4,fill:"var(--crit)",stroke:"var(--surface)","stroke-width":2}));
  hover(g,it.title,it.rows);svg.append(g);
  if(i%every===0)svg.append(sv("text",{x:cx,y:H-8,"text-anchor":"middle",class:"ax",text:it.tick}));
 });
 if(o.budget){const per=items.some(it=>it.budget!==undefined&&it.budget!==o.budget);
  if(per){items.forEach((it,i)=>{if(!(it.budget>0))return;const yy=y(it.budget);svg.append(sv("line",{x1:m.l+band*i+2,x2:m.l+band*(i+1)-2,y1:yy,y2:yy,class:"bg"}));});
   const lb=items[n-1].budget>0?items[n-1].budget:o.budget;svg.append(sv("text",{x:W-m.r+8,y:y(lb)+4,"text-anchor":"start",class:"bl",text:"Budget"}));}
  else{const yy=y(o.budget);svg.append(sv("line",{x1:m.l,x2:W-m.r,y1:yy,y2:yy,class:"bg"}),sv("text",{x:W-m.r+8,y:yy+4,"text-anchor":"start",class:"bl",text:o.budgetLabel}));}}
 host.append(svg);
}
function legend(host,items){host.replaceChildren(...items.map(i=>el("span",{class:"lg"},[i.line?el("i",{class:"ln"}):el("i",{class:"sw",style:"background:"+i.color}),document.createTextNode(i.label)])));}
const catLegend=(host,extra=[])=>legend(host,META.map(c=>({label:c.name,color:catColor(c.slot)})).concat(extra));
/* One whole split into parts: tall bar, share printed inside only when it fits */
function segBar(host,parts){
 host.replaceChildren();
 const tot=parts.reduce((a,p)=>a+p.value,0);
 if(!tot){host.append(el("div",{class:"empty",text:"No time recorded yet. Quota counts while you type or move the mouse."}));return;}
 const wpx=host.clientWidth||600,bar=el("div",{class:"seg",role:"img","aria-label":"Share of time by category"});
 parts.filter(p=>p.value>0).forEach(p=>{const share=p.value/tot,label=Math.round(share*100)+"%";
  const d=el("div",{class:"s s"+p.slot,style:`flex:${p.value} 1 0;background:${catColor(p.slot)}`,text:(share*wpx>label.length*8+22)?label:""});
  hover(d,p.name,[[fh(p.value),Math.round(share*100)+"% of tracked time"]]);bar.append(d);});
 host.append(bar);
}
function appRows(host,items,emptyText){
 host.replaceChildren();
 if(!items.length){host.append(el("div",{class:"empty",text:emptyText||"No app data yet."}));return;}
 const at=items.reduce((a,b)=>a+b.seconds,0),mx=Math.max(1,...items.map(a=>a.seconds));
 items.forEach(a=>{const r=el("div",{class:"ar"},[el("div",{class:"an",text:a.name}),el("div",{class:"ab"},[el("div",{style:`width:${a.seconds/mx*100}%;background:${a.color||"var(--brand)"}`})]),el("div",{class:"at",text:fh(a.seconds)})]);
  hover(r,a.name,[[fh(a.seconds),pct(a.seconds,at)+" of this list"]].concat(a.cat?[[a.cat,"category"]]:[]));host.append(r);});
}
/* Calendar heatmap: one tint, five steps; red marks days over the daily budget */
function heatmap(host,days,o){
 host.replaceChildren();
 const start=mondayOf(parse(days[0].date)),last=parse(days[days.length-1].date),cols=Math.floor(Math.round((last-start)/864e5)/7)+1;
 const cs=Math.max(11,Math.min(34,Math.floor((host.clientWidth-44)/cols)-3)),L=40,T=18,W=L+cols*(cs+3),H=T+7*(cs+3);
 const mx=Math.max(1,...days.map(o.value)),PCT=[0,22,42,62,82];
 const lv=(v,b)=>{if(v<=0)return 0;if(o.budget){const B=b>0?b:o.budget;return v>B?5:v<=.25*B?1:v<=.5*B?2:v<=.75*B?3:4;}return Math.min(4,Math.ceil(v/mx*4));};
 const fill=l=>l===0?"var(--grid)":l===5?"var(--crit)":`color-mix(in srgb, ${o.tint} ${PCT[l]}%, var(--surface))`;
 const by=new Map(days.map(d=>[d.date,d]));
 const svg=sv("svg",{viewBox:`0 0 ${W} ${H}`,width:W,height:H,role:"img","aria-label":o.label});
 svg.append(sv("defs",{},[sv("pattern",{id:"hatch",width:6,height:6,patternUnits:"userSpaceOnUse",patternTransform:"rotate(45)"},[sv("rect",{width:6,height:6,style:"fill:var(--grid)"}),sv("line",{x1:0,y1:0,x2:0,y2:6,style:"stroke:var(--base);stroke-width:2.5"})])]));
 [0,2,4].forEach(r=>svg.append(sv("text",{x:L-8,y:T+r*(cs+3)+cs-2,"text-anchor":"end",class:"ax",text:DOW[r]})));
 for(let c=0;c<cols;c++){const mon=addDays(start,7*c);
  if(c===0||mon.getMonth()!==addDays(start,7*(c-1)).getMonth())svg.append(sv("text",{x:L+c*(cs+3),y:11,class:"ax",text:MON[mon.getMonth()]}));
  for(let r=0;r<7;r++){const d=addDays(start,7*c+r),it=by.get(iso(d));if(!it)continue;const v=o.value(it);
   const lvl=it.off?(v>0?4:-1):lv(v,it.budget);
   const rect=sv("rect",{x:L+c*(cs+3),y:T+r*(cs+3),width:cs,height:cs,rx:3,style:"fill:"+(lvl<0?"url(#hatch)":fill(lvl)),class:"cell"});
   const rows=[[fh(v),it.off?"worked on a day off":(o.budget?pct(v,it.budget>0?it.budget:o.budget)+" of that day's budget":"")]];if(it.off)rows.unshift([OFFL[it.off]||"Day off","marked as a day off"]);
   if(it.away)rows.unshift([fh(it.away)+" away",(OFFL[it.away_type]||"Leave")+", part of the day"]);
   hover(rect,fdate(d),rows);svg.append(rect);}}
 host.append(svg);
 if(o.key)o.key.replaceChildren(document.createTextNode("Less"),...[0,1,2,3,4].map(i=>el("i",{style:"background:"+fill(i)})),document.createTextNode("More"),
  ...(o.budget?[el("i",{style:"background:var(--crit);margin-left:10px"}),document.createTextNode("Over budget")]:[]),
  ...(days.some(d=>d.off)?[el("i",{class:"hatchsw",style:"margin-left:10px"}),document.createTextNode("Day off")]:[]));
}
/* Private mode: lives in memory on the server, so it is always off when Quota starts */
let PRIV=false;
function setPriv(v){PRIV=!!v;const b=$("priv"),bar=$("privbar");if(b)b.setAttribute("aria-checked",String(PRIV));if(bar)bar.hidden=!PRIV;}
async function syncPriv(){try{const j=await (await fetch("/api/pause")).json();if(j.paused!==PRIV){setPriv(j.paused);dispatchEvent(new Event("privchange"));}}catch(e){}}
async function sendPriv(want){try{const r=await fetch("/api/pause",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({paused:want})});const j=await r.json();setPriv(j.paused);dispatchEvent(new Event("privchange"));}catch(e){}}
if($("priv")){$("priv").onclick=()=>sendPriv(!PRIV);$("privoff").onclick=()=>sendPriv(false);syncPriv();setInterval(syncPriv,6000);}
(function(){const b=$("theme");if(b)b.onclick=()=>{const cur=document.documentElement.getAttribute("data-theme")||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");
 const nx=cur==="dark"?"light":"dark";document.documentElement.setAttribute("data-theme",nx);try{localStorage.setItem("quota-theme",nx);}catch(e){}};
 document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("on",a.dataset.nav===document.body.dataset.page));})();
