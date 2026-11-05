/* A2UI-style generative UI for the Ask page.
   The assistant may describe a small view as JSON lines (surfaceUpdate, dataModelUpdate, beginRendering, deleteSurface).
   We draw it ONLY from the fixed catalog below, with textContent and no URLs, HTML or scripts, so a model (or a
   website name in the data) can never inject code. Unknown components are skipped. */
const A2 = (() => {
 const LIM = {components: 60, depth: 6, str: 300, rows: 40, items: 30, cols: 8};
 const PAGES = ["/", "/reports", "/chat", "/settings"];
 const cut = (s, n = LIM.str) => String(s == null ? "" : s).slice(0, n);
 function at(data, path) {let v = data; for (const k of String(path).split("/").filter(Boolean)) {if (v == null || typeof v !== "object") return undefined; v = v[k];} return v;}
 function val(v, data) { // {literalString|literalNumber|literalBoolean|path} or a plain value
  if (v && typeof v === "object" && !Array.isArray(v)) {
   if ("literalString" in v) return v.literalString; if ("literalNumber" in v) return v.literalNumber;
   if ("literalBoolean" in v) return v.literalBoolean; if ("path" in v) return at(data, v.path); return undefined;}
  return v;}
 const str = (v, d) => cut(val(v, d));
 const num = (v, d) => {const n = Number(val(v, d)); return isFinite(n) ? n : 0;};
 const arr = (v, d, max) => {const a = val(v, d); return Array.isArray(a) ? a.slice(0, max) : [];};
 const nice = n => Math.abs(n) >= 100 || Number.isInteger(n) ? String(Math.round(n * 10) / 10) : String(Math.round(n * 100) / 100);

 function objects(text) { // complete top-level {...} objects, whether or not the model put each on one line
  const out = []; let depth = 0, from = -1, inStr = false, esc = false; text = String(text).slice(0, 60000);
  for (let i = 0; i < text.length; i++) {const c = text[i];
   if (inStr) {if (esc) esc = false; else if (c === "\\") esc = true; else if (c === '"') inStr = false; continue;}
   if (c === '"' && depth > 0) inStr = true;
   else if (c === "{") {if (depth++ === 0) from = i;}
   else if (c === "}" && depth > 0 && --depth === 0) out.push(text.slice(from, i + 1));}
  return out;}
 function parse(text) { // JSON lines -> surfaces
  const S = {};
  for (const t of objects(text)) {
   let m; try {m = JSON.parse(t);} catch (e) {continue;}
   if (!m || typeof m !== "object") continue;
   const u = m.surfaceUpdate, d = m.dataModelUpdate, b = m.beginRendering, x = m.deleteSurface;
   const sid = cut((u || d || b || x || {}).surfaceId || "main", 40);
   const s = S[sid] || (S[sid] = {comps: {}, data: {}, root: null});
   if (x) delete S[sid];
   if (u && Array.isArray(u.components)) for (const c of u.components.slice(0, LIM.components))
    if (c && typeof c.id === "string" && c.component && typeof c.component === "object" && Object.keys(s.comps).length < LIM.components) s.comps[c.id] = c.component;
   if (d && d.contents && typeof d.contents === "object") {
    if (d.path && d.path !== "/") {const keys = String(d.path).split("/").filter(Boolean); let o = s.data;
     keys.slice(0, -1).forEach(k => {if (typeof o[k] !== "object" || !o[k]) o[k] = {}; o = o[k];}); if (keys.length) o[keys[keys.length - 1]] = d.contents;}
    else Object.assign(s.data, d.contents);}
   if (b) s.root = cut(b.root || "root", 60);
  }
  return S;}

 function render(sid, s, onAct) {
  const C = s.comps, D = s.data, seen = new Set();
  function kids(spec, depth) {return ((spec && spec.explicitList) || []).slice(0, 40).map(id => node(id, depth + 1)).filter(Boolean);}
  function node(id, depth) {
   const def = C[id]; if (!def || depth > LIM.depth || seen.has(id)) return null; seen.add(id);
   const type = Object.keys(def)[0], p = def[type] || {}; let out = null;
   if (type === "Column" || type === "Row") out = el("div", {class: "a2-" + type.toLowerCase()}, kids(p.children, depth));
   else if (type === "Card") out = el("div", {class: "a2-card"}, p.child ? [node(p.child, depth + 1)].filter(Boolean) : kids(p.children, depth));
   else if (type === "Text") {const h = {h1: "h3", h2: "h4", h3: "h5"}[p.usageHint]; out = el(h || "p", {class: "a2-text " + (p.usageHint === "caption" ? "a2-cap" : ""), text: str(p.text, D)});}
   else if (type === "Divider") out = el("hr", {class: "a2-hr"});
   else if (type === "Stat") out = el("div", {class: "a2-stat"}, [el("div", {class: "a2-sl", text: str(p.label, D)}), el("div", {class: "a2-sv", text: str(p.value, D)}),
    p.detail ? el("div", {class: "a2-sd", text: str(p.detail, D)}) : ""].filter(Boolean));
   else if (type === "Progress") {const v = num(p.value, D), mx = Math.max(num(p.max, D) || 1, 1e-9), r = Math.max(0, Math.min(1, v / mx)), over = v > mx;
    const f = el("span", {style: "width:" + (r * 100).toFixed(1) + "%"}), track = el("div", {class: "a2-track" + (over ? " over" : ""), role: "progressbar", "aria-valuenow": String(Math.round(v)), "aria-valuemax": String(Math.round(mx))}, [f]);
    out = el("div", {class: "a2-prog"}, [el("div", {class: "a2-row2"}, [el("span", {text: str(p.label, D)}), el("b", {text: str(p.detail, D) || Math.round(r * 100) + "%"})]), track]);}
   else if (type === "BarChart") {const items = arr(p.items, D, LIM.items).filter(i => i && typeof i === "object");
    const mx = Math.max(...items.map(i => Math.abs(Number(i.value) || 0)), 1e-9), unit = str(p.unit, D);
    const rows = items.map(i => {const v = Number(i.value) || 0, lbl = cut(i.label, 40), w = Math.max(0, Math.abs(v) / mx * 100);
     const r = el("div", {class: "a2-bar", tabindex: "0", title: lbl + ": " + nice(v) + (unit ? " " + unit : "")}, [el("span", {class: "a2-bl", text: lbl}),
      el("span", {class: "a2-bt"}, [el("span", {style: "width:" + w.toFixed(1) + "%"})]), el("span", {class: "a2-bv", text: nice(v) + (unit ? " " + unit : "")})]); return r;});
    out = el("div", {class: "a2-chart", role: "img", "aria-label": str(p.title, D) || "Bar chart"}, [p.title ? el("div", {class: "a2-ct", text: str(p.title, D)}) : "", ...rows].filter(Boolean));}
   else if (type === "Table") {const cols = arr(p.columns, D, LIM.cols), rws = arr(p.rows, D, LIM.rows), t = el("table");
    t.append(el("tr", {}, cols.map(c => el("th", {text: cut(c, 40)}))));
    rws.forEach(r => {if (Array.isArray(r)) t.append(el("tr", {}, r.slice(0, LIM.cols).map(c => el("td", {text: cut(c, 80)}))));});
    out = el("div", {class: "a2-tablewrap"}, [t]);}
   else if (type === "Button") {const label = (p.child && C[p.child] && C[p.child].Text) ? str(C[p.child].Text.text, D) : str(p.label, D);
    const a = p.action || {}, ctx = {}; (Array.isArray(a.context) ? a.context : []).forEach(c => {if (c && c.key) ctx[cut(c.key, 30)] = str(c.value, D);});
    const b = el("button", {type: "button", class: "a2-btn", text: label || "Go"});
    b.onclick = () => {
     if (a.name === "ask" && ctx.question) onAct({ask: ctx.question});
     else if (a.name === "open" && PAGES.includes(ctx.page)) location.href = ctx.page;};
    out = b;}
   seen.delete(id); return out;}
  const root = node(s.root || "root", 0);
  return root ? el("div", {class: "a2-surface", "data-surface": sid}, [root]) : null;}

 /* Splits an answer into text and ```a2ui blocks. A block that is still arriving is reported as pending. */
 function split(text) {
  const parts = []; const re = /```a2ui[ \t]*\n([\s\S]*?)```/g; let last = 0, m;
  while ((m = re.exec(text))) {if (m.index > last) parts.push({text: text.slice(last, m.index)}); parts.push({ui: m[1]}); last = re.lastIndex;}
  let rest = text.slice(last); const open = rest.search(/```a2ui/);
  if (open >= 0) {if (open > 0) parts.push({text: rest.slice(0, open)}); parts.push({pending: true});}
  else if (rest) parts.push({text: rest});
  return parts;}
 const strip = text => split(text).map(p => p.ui != null ? "[a chart or table was shown here]" : p.pending ? "" : p.text).join("");
 return {parse, render, split, strip};
})();
