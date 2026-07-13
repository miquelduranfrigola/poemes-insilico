"""Assemble the self-contained "Tour de França" page (index.html).

An animated map that plays through every edition of the Tour de France from 1985
to 2026. Europe is drawn once as a faint outline; a 1985->2026 timeline scrubs the
years, and for each year the day's stages trace onto the map as bowed arcs between
their start and finish towns. Prior years can accumulate as faint ghosts (a
palimpsest of four decades) or clear.

Everything is inlined -- the Space Mono webfont, the computed routes
(results/routes.json) and the simplified basemap (data/europe.geojson) -- so the
page makes no external requests. Same cream / ink / Space Mono language as the rest
of the gallery. The shared keyboard-nav snippet is appended at the end.
"""

from __future__ import annotations

import json
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
SHARED = POEM_ROOT.parent.parent / "shared" / "vendor"

ROUTES = POEM_ROOT / "results" / "routes.json"
GEOJSON = POEM_ROOT / "data" / "europe.geojson"
POEM_MD = POEM_ROOT / "poem.md"


def _poem_html() -> str:
    """Render poem.md (skipping its H1 title) as simple verse/stanza HTML."""
    lines = POEM_MD.read_text(encoding="utf-8").splitlines()
    out, seen_title = [], False
    for line in lines:
        if line.startswith("# ") and not seen_title:
            seen_title = True
            continue
        if not line.strip():
            out.append('<span class="br"></span>')
        else:
            import html as _html
            out.append('<span class="v">' + _html.escape(line.strip()) + "</span>")
    return "\n".join(out)


def build() -> Path:
    font_css = (SHARED / "spacemono.css").read_text(encoding="utf-8")
    nav = (SHARED / "menu-nav.html").read_text(encoding="utf-8")
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    meta = routes["meta"]

    page = (_TEMPLATE
            .replace("{{FONT}}", font_css)
            .replace("{{FIRST}}", str(meta["first_year"]))
            .replace("{{LAST}}", str(meta["last_year"]))
            .replace("{{NYEARS}}", str(meta["n_years"]))
            .replace("{{NSTAGES}}", str(meta["n_stages"]))
            .replace("{{POEM}}", _poem_html())
            .replace("{{ROUTES}}", json.dumps(routes, ensure_ascii=False, separators=(",", ":")))
            .replace("{{GEO}}", json.dumps(geo, ensure_ascii=False, separators=(",", ":"))))

    out = POEM_ROOT / "index.html"
    out.write_text(page + nav, encoding="utf-8")
    return out


_TEMPLATE = r"""<title>Tour de França</title>
<style>
{{FONT}}
  :root{
    --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb; --hair:#e7e1d7;
    --land:#e5ded3; --landline:#d3cabb; --ghost:rgba(40,40,40,.07);
    --accent:#2f7d68; --red:#c7513b;
    --mono:"Space Mono", ui-monospace, Menlo, Consolas, monospace;
  }
  *{ scrollbar-width:none; -ms-overflow-style:none; box-sizing:border-box; }
  *::-webkit-scrollbar{ display:none; width:0; height:0; }
  html{ overflow-x:hidden; }
  html, body{ margin:0; padding:0; background:var(--ground); }
  .wrap{ background:var(--ground); color:var(--ink); font-family:var(--mono);
         font-size:14px; line-height:1.65; min-height:100vh; -webkit-font-smoothing:antialiased; }
  .wrap a{ color:var(--ink); text-decoration:none; transition:opacity .15s ease; }
  .wrap a:hover{ opacity:.55; }
  .site{ display:flex; align-items:flex-start; min-height:100vh; }

  .index{ width:220px; flex:none; position:sticky; top:0; align-self:flex-start;
          height:100vh; overflow:auto; padding:30px 22px; border-right:1px solid var(--line); }
  .brand{ margin-bottom:26px; line-height:1.35; }
  .brand b{ font-weight:700; font-size:14px; display:block; letter-spacing:-.01em; }
  .brand span{ display:block; color:var(--muted); font-size:11px; margin-top:4px;
               text-transform:uppercase; letter-spacing:.08em; }
  .menu{ list-style:none; margin:0; padding:0; font-size:14px; }
  .menu li a{ display:block; padding:3px 0; }
  .menu li a.on{ text-decoration:underline; text-underline-offset:3px; }

  .view{ flex:1; min-width:0; }
  .entry{ display:none; }
  .entry.on{ display:block; }

  /* ---- MAP ---- */
  .map-entry.on{ display:flex; flex-direction:column; height:100vh; }
  .maphead{ padding:clamp(20px,3vw,34px) clamp(22px,4vw,52px) 6px; display:flex;
            align-items:baseline; gap:22px; flex-wrap:wrap; }
  .yr{ font-weight:700; font-size:clamp(40px,7vw,74px); letter-spacing:-.03em; line-height:1;
       font-variant-numeric:tabular-nums; }
  .stat{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
  .stat b{ color:var(--ink); font-weight:700; }
  .stat .dep{ text-transform:none; letter-spacing:0; }
  .mapbox{ flex:1; min-height:0; position:relative; padding:0 clamp(14px,3vw,40px); }
  svg.map{ width:100%; height:100%; display:block; }
  .land{ fill:var(--land); stroke:var(--landline); stroke-width:.6; }
  .route{ fill:none; stroke:var(--ink); stroke-width:1.4; stroke-linecap:round;
          stroke-linejoin:round; vector-effect:non-scaling-stroke; }
  .route.ghost{ stroke:var(--ghost); stroke-width:1; }
  .route.live{ stroke:var(--ink); }
  .route.head{ stroke:var(--accent); stroke-width:2.2; }
  .draw{ transition:stroke-dashoffset var(--dur,.5s) ease; }

  .controls{ padding:10px clamp(22px,4vw,52px) clamp(18px,3vw,30px); display:flex;
             align-items:center; gap:18px; border-top:1px solid var(--hair); flex-wrap:wrap; }
  .play{ font:inherit; font-size:12px; letter-spacing:.08em; text-transform:uppercase;
         background:var(--ink); color:var(--ground); border:0; border-radius:2px;
         padding:8px 16px; cursor:pointer; }
  .play:hover{ opacity:.8; }
  input[type=range]{ flex:1; min-width:180px; accent-color:var(--ink); cursor:pointer; }
  .rail{ font-size:11px; color:var(--muted); letter-spacing:.1em; font-variant-numeric:tabular-nums; }
  .toggle{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);
           display:flex; align-items:center; gap:7px; cursor:pointer; user-select:none; }
  .toggle input{ accent-color:var(--accent); }

  /* ---- TEXT PAGES ---- */
  .prosewrap{ max-width:1000px; margin:0 auto; padding:clamp(40px,7vw,104px) clamp(22px,6vw,80px); }
  .kicker{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }
  .title{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em; margin:0; }
  .poem{ font-size:15px; line-height:2.0; margin-top:clamp(28px,5vw,48px); }
  .poem .v{ display:block; }
  .poem .br{ display:block; height:.9em; }
  .prose{ max-width:64ch; }
  .prose p{ margin:0 0 16px; }
  .prose .seclab{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:34px 0 12px; }
  .prose .note{ border-left:2px solid var(--red); padding-left:16px; color:var(--muted); }

  @media (max-width:900px){
    .site{ display:block; }
    .index{ width:auto; position:static; height:auto; overflow:visible; padding:20px 22px;
            border-right:0; border-bottom:1px solid var(--line);
            display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 18px; }
    .brand{ margin:0 14px 0 0; }
    .menu{ display:flex; flex-wrap:wrap; gap:4px 16px; }
    .map-entry.on{ height:auto; }
    .mapbox{ height:60vh; }
  }
  @media (prefers-reduced-motion: reduce){ .draw{ transition:none; } }
</style>

<div class="wrap"><div class="site">
  <nav class="index">
    <div class="brand"><a data-target="map" href="#map"><b>Tour de França</b></a>
      <span>{{NYEARS}} edicions · {{FIRST}}–{{LAST}}</span></div>
    <ol class="menu">
      <li><a data-target="map" href="#map">El mapa</a></li>
      <li><a data-target="poem" href="#poem">El poema</a></li>
      <li><a data-target="method" href="#method">Metodologia</a></li>
    </ol>
  </nav>

  <main class="view">
    <section class="entry map-entry on" id="map">
      <div class="maphead">
        <div class="yr" id="yr">{{FIRST}}</div>
        <div>
          <div class="stat"><b id="ns">0</b> etapes · <b id="km">0</b> km</div>
          <div class="stat dep">Gran Sortida: <b id="dep">—</b></div>
        </div>
      </div>
      <div class="mapbox"><svg class="map" id="svg" preserveAspectRatio="xMidYMid meet">
        <g class="land" id="land"></g>
        <g id="routes"></g>
      </svg></div>
      <div class="controls">
        <button class="play" id="play">▶ Reprodueix</button>
        <span class="rail" id="y0">{{FIRST}}</span>
        <input type="range" id="slider" min="0" value="0" step="1">
        <span class="rail" id="y1">{{LAST}}</span>
        <label class="toggle"><input type="checkbox" id="acc" checked> Acumula els anys</label>
      </div>
    </section>

    <section class="entry" id="poem">
      <div class="prosewrap">
        <p class="kicker">Miquel Duran-Frigola</p>
        <h1 class="title">Tour de França</h1>
        <div class="poem">{{POEM}}</div>
      </div>
    </section>

    <section class="entry" id="method">
      <div class="prosewrap">
        <h1 class="title">Metodologia</h1>
        <div class="prose" style="margin-top:28px">
          <p>Cada dia de cada Tour, de {{FIRST}} a {{LAST}} —{{NSTAGES}} etapes en
             total—, es dibuixa com un arc entre la vila de sortida i la d'arribada.</p>
          <p class="seclab">Com es fa</p>
          <p>Les etapes s'extreuen dels articles de la Viquipèdia de cada edició
             (vila de sortida, vila d'arribada, distància i tipus). Cada vila es
             geocodifica amb OpenStreetMap (Nominatim) i el traçat de cada etapa és
             una corba de Bézier quadràtica entre els dos punts, corbada lleugerament
             perquè els recorreguts repetits se superposin i el mapa sembli un
             palimpsest. Les contrarellotges i pròlegs en circuit es dibuixen com un
             petit bucle al voltant de la vila.</p>
          <p class="seclab">Una advertència honesta</p>
          <p class="note">Els arcs són reconstruccions que uneixen la sortida i
             l'arribada, <b>no</b> les carreteres reals. Els traçats GPS només
             existeixen a partir del 2014 aproximadament; per als anys anteriors mai
             es van registrar. El que veus és la forma d'un record, no un mapa de
             ruta.</p>
        </div>
      </div>
    </section>
  </main>
</div></div>

<script>
  var ROUTES = {{ROUTES}};
  var GEO = {{GEO}};
  (function(){
    var years = ROUTES.years;
    var svg = document.getElementById('svg');
    var W = 1000, PAD = 26;

    // ---- projection: fixed extent from the basemap bbox ----
    var minLon=1e9, maxLon=-1e9, minLat=1e9, maxLat=-1e9;
    function scan(c){ if(c[0]<minLon)minLon=c[0]; if(c[0]>maxLon)maxLon=c[0];
                      if(c[1]<minLat)minLat=c[1]; if(c[1]>maxLat)maxLat=c[1]; }
    GEO.features.forEach(function(f){
      var g=f.geometry, polys=g.type==='Polygon'?[g.coordinates]:g.coordinates;
      polys.forEach(function(poly){ poly.forEach(function(ring){ ring.forEach(scan); }); });
    });
    var k = Math.cos((minLat+maxLat)/2 * Math.PI/180);
    var spanX = (maxLon-minLon)*k, spanY = (maxLat-minLat);
    var H = Math.round((W-2*PAD) * spanY/spanX) + 2*PAD;
    svg.setAttribute('viewBox', '0 0 '+W+' '+H);
    function px(lon){ return PAD + (lon-minLon)*k/spanX * (W-2*PAD); }
    function py(lat){ return PAD + (maxLat-lat)/spanY * (H-2*PAD); }
    function dpath(pts){  // pts are [lat,lon]
      var d=''; for(var i=0;i<pts.length;i++){ d+=(i?'L':'M')+px(pts[i][1]).toFixed(1)+','+py(pts[i][0]).toFixed(1); }
      return d;
    }

    // ---- draw the land once ----
    var land = document.getElementById('land'), lp='';
    GEO.features.forEach(function(f){
      var g=f.geometry, polys=g.type==='Polygon'?[g.coordinates]:g.coordinates;
      polys.forEach(function(poly){ poly.forEach(function(ring){
        var d=''; for(var i=0;i<ring.length;i++){ d+=(i?'L':'M')+px(ring[i][0]).toFixed(1)+','+py(ring[i][1]).toFixed(1); }
        lp += '<path d="'+d+'Z"/>';
      }); });
    });
    land.innerHTML = lp;

    // ---- state ----
    var routesG = document.getElementById('routes');
    var SVGNS = 'http://www.w3.org/2000/svg';
    var cur = 0, playing = false, timer = null, accumulate = true;
    var slider = document.getElementById('slider');
    slider.max = years.length - 1;

    var elYr=document.getElementById('yr'), elNs=document.getElementById('ns'),
        elKm=document.getElementById('km'), elDep=document.getElementById('dep');

    function fmt(n){ return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' '); }

    function readout(y){
      elYr.textContent = y.year; elNs.textContent = y.n_stages;
      elKm.textContent = fmt(y.total_km); elDep.textContent = y.grand_depart || '—';
    }

    function drawStages(stages, animate, ghost, idx){
      stages.forEach(function(s, i){
        var p = document.createElementNS(SVGNS,'path');
        p.setAttribute('d', dpath(s.points));
        p.setAttribute('class', ghost ? 'route ghost' : 'route live');
        routesG.appendChild(p);
        if(animate){
          var len = p.getTotalLength();
          p.style.strokeDasharray = len; p.style.strokeDashoffset = len;
          p.classList.add('head');
          setTimeout(function(){
            if(cur!==idx) return;              // year changed under us: abort
            p.classList.add('draw');
            p.style.setProperty('--dur', Math.min(.7, .28 + s.km/1400)+'s');
            p.style.strokeDashoffset = 0;
            setTimeout(function(){ p.classList.remove('head'); }, 700);
          }, i * 70);
        }
      });
    }

    function showYear(idx, animate){
      cur = idx; slider.value = idx; readout(years[idx]);
      if(animate){
        // demote what is already drawn to ghost (or wipe), then trace this year in
        if(!accumulate){ routesG.innerHTML=''; }
        else [].slice.call(routesG.children).forEach(function(p){ p.setAttribute('class','route ghost'); });
        drawStages(years[idx].stages, true, false, idx);
      } else {
        // static (re)build: full palimpsest up to idx when accumulating
        routesG.innerHTML = '';
        if(accumulate){ for(var j=0;j<idx;j++) drawStages(years[j].stages, false, true, j); }
        drawStages(years[idx].stages, false, false, idx);
      }
    }

    function stop(){ playing=false; clearTimeout(timer);
      document.getElementById('play').textContent='▶ Reprodueix'; }
    function play(){
      playing=true; document.getElementById('play').textContent='❙❙ Pausa';
      if(cur >= years.length-1) showYear(0, true); else showYear(cur, true);
      function tick(){
        if(!playing) return;
        var y = years[cur];
        var span = 700 + y.n_stages*70 + 500;  // draw time + hold
        timer = setTimeout(function(){
          if(!playing) return;
          if(cur >= years.length-1){ stop(); return; }
          showYear(cur+1, true); tick();
        }, span);
      }
      tick();
    }

    document.getElementById('play').addEventListener('click', function(){
      if(playing) stop(); else play();
    });
    slider.addEventListener('input', function(){ stop(); showYear(+slider.value, false); });
    document.getElementById('acc').addEventListener('change', function(e){
      accumulate = e.target.checked; showYear(cur, false);
    });

    // ---- section routing (menu) ----
    var links = [].slice.call(document.querySelectorAll('[data-target]'));
    var entries = [].slice.call(document.querySelectorAll('.entry'));
    function route(id){
      var found=false;
      entries.forEach(function(e){ var on=e.id===id; e.classList.toggle('on',on); if(on)found=true; });
      if(!found){ id='map'; document.getElementById('map').classList.add('on'); }
      links.forEach(function(a){ a.classList.toggle('on', a.dataset.target===id); });
      if(id!=='map') stop();
    }
    links.forEach(function(a){ a.addEventListener('click', function(ev){
      ev.preventDefault(); history.replaceState(null,'','#'+a.dataset.target); route(a.dataset.target);
    }); });

    showYear(0, false);
    route(location.hash ? location.hash.slice(1) : 'map');
  })();
</script>
"""


if __name__ == "__main__":
    print(build())
