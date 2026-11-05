
const SUGGEST=["How am I doing this week?","Where did my time go in the last 30 days?","When in the day do I work the most?","Plan the rest of my week so I stay within my tokens."];
let chat=[],busy=false,ctrl=null;
const say=(t)=>{$("err").textContent=t||"";};
/* A small, safe Markdown view: bold, code, lists and tables, built with textContent only. */
function inline(host,text){text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach(p=>{if(!p)return;
 if(p.startsWith("**")&&p.endsWith("**")&&p.length>4)host.append(el("b",{text:p.slice(2,-2)}));
 else if(p.startsWith("`")&&p.endsWith("`")&&p.length>2)host.append(el("code",{text:p.slice(1,-1)}));
 else host.append(document.createTextNode(p));});}
function md(host,text){host.replaceChildren();const lines=text.replace(/\r/g,"").split("\n");let i=0;
 while(i<lines.length){const L=lines[i];
  if(!L.trim()){i++;continue;}
  if(/^\s*\|/.test(L)){const rows=[];while(i<lines.length&&/^\s*\|/.test(lines[i])){rows.push(lines[i]);i++;}
   const cells=r=>r.trim().replace(/^\||\|$/g,"").split("|").map(c=>c.trim());
   const body=rows.filter(r=>!/^\s*\|?[\s:|-]+\|?\s*$/.test(r)||!/-/.test(r)).map(cells);
   if(body.length){const t=el("table"),head=body.shift();t.append(el("tr",{},head.map(c=>{const th=el("th");inline(th,c);return th;})));
    body.forEach(r=>t.append(el("tr",{},r.map(c=>{const td=el("td");inline(td,c);return td;}))));host.append(t);}continue;}
  if(/^\s*([-*]|\d+\.)\s+/.test(L)){const ord=/^\s*\d+\./.test(L),ul=el(ord?"ol":"ul");
   while(i<lines.length&&/^\s*([-*]|\d+\.)\s+/.test(lines[i])){const li=el("li");inline(li,lines[i].replace(/^\s*([-*]|\d+\.)\s+/,""));ul.append(li);i++;}host.append(ul);continue;}
  const para=[];while(i<lines.length&&lines[i].trim()&&!/^\s*(\||([-*]|\d+\.)\s)/.test(lines[i])){para.push(lines[i].replace(/^#+\s*/,""));i++;}
  const p=el("p");inline(p,para.join(" "));host.append(p);}}
const uiCache=new Map();
/* An answer is prose plus optional A2UI views (stat tiles, bars, tables, buttons) drawn from a fixed, safe catalog. */
function answer(host,text){const parts=A2.split(text);if(!parts.some(p=>p.ui!=null||p.pending)){md(host,text);return;}
 host.replaceChildren();
 parts.forEach(p=>{if(p.pending){host.append(el("div",{class:"a2-pending",text:"Building a view…"}));return;}
  if(p.ui!=null){let n=uiCache.get(p.ui);if(!n){const S=A2.parse(p.ui),k=Object.keys(S)[0];n=k?A2.render(k,S[k],a=>{if(a.ask)ask(a.ask);}):null;if(n)uiCache.set(p.ui,n);}
   if(n)host.append(n);return;}
  if(p.text.trim()){const d=el("div");md(d,p.text);host.append(d);}});}
function bubble(role,text,cls){const b=el("div",{class:"bubble"+(cls?" "+cls:"")});
 if(role==="user")b.textContent=text;else answer(b,text);
 $("msgs").append(el("div",{class:"msg-row "+(role==="user"?"me":"bot")},[b]));b.scrollIntoView({block:"end"});return b;}
function setBusy(v){busy=v;$("send").hidden=v;$("stop").hidden=!v;$("q").disabled=v;if(!v)$("q").focus();}
async function ask(text){text=text.trim();if(!text||busy)return;say("");
 chat.push({role:"user",content:text});bubble("user",text);$("chips").hidden=true;$("q").value="";$("newchat").hidden=false;
 const out=bubble("assistant","","wait");let got="";ctrl=new AbortController();setBusy(true);
 try{const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({messages:chat}),signal:ctrl.signal});
  if(!r.ok){const j=await r.json();throw new Error(j.error||"Couldn't ask.");}
  const rd=r.body.getReader(),dec=new TextDecoder();let buf="";
  for(;;){const{value,done}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});
   let n;while((n=buf.indexOf("\n"))>=0){const ln=buf.slice(0,n).trim();buf=buf.slice(n+1);if(!ln)continue;
    const o=JSON.parse(ln);if(o.type==="RUN_ERROR")throw new Error(o.message||"Something went wrong.");
    if(o.type==="TEXT_MESSAGE_CONTENT"&&o.delta){got+=o.delta;answer(out,got);out.classList.add("wait");out.scrollIntoView({block:"end"});}}}
  out.classList.remove("wait");if(got)chat.push({role:"assistant",content:A2.strip(got)});else{out.classList.add("err");out.textContent="No answer came back. Try again.";}
 }catch(e){out.classList.remove("wait");
  if(e.name==="AbortError"){if(got)chat.push({role:"assistant",content:A2.strip(got)});else out.remove();}
  else{out.classList.add("err");const msg=el("div",{text:e.message||"Something went wrong."});out.append(got?el("hr"):"",msg);if(got)chat.push({role:"assistant",content:A2.strip(got)});else chat.pop();}}
 ctrl=null;setBusy(false);}
$("composer").onsubmit=e=>{e.preventDefault();ask($("q").value);};
$("q").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();ask($("q").value);}});
$("stop").onclick=()=>{if(ctrl)ctrl.abort();};
$("newchat").onclick=()=>{if(ctrl)ctrl.abort();chat=[];$("msgs").replaceChildren();$("chips").hidden=false;$("newchat").hidden=true;say("");};
$("chips").replaceChildren(...SUGGEST.map(t=>{const b=el("button",{type:"button",text:t});b.onclick=()=>ask(t);return b;}));
$("seen").addEventListener("toggle",async()=>{if(!$("seen").open)return;
 try{const j=await (await fetch("/api/chat/context")).json();$("ctx").textContent=j.text;}catch(e){$("ctx").textContent="Couldn't load the summary.";}});
(async()=>{try{const a=await (await fetch("/api/ai")).json();$("empty").hidden=a.configured;$("chatbox").hidden=!a.configured;}
 catch(e){say("Couldn't reach K(Qu)ota. Check that it is still running in your terminal.");}})();
