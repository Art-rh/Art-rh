"""Desenha os SVGs do README a partir de scripts/data.json, na identidade do arthurrangelh.com.br."""
import base64, io, json, os
from datetime import date, datetime, timedelta, timezone
from html import escape
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
os.makedirs(OUT, exist_ok=True)
D = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
BRT = timezone(timedelta(hours=-3))
NOW = datetime.fromisoformat(D["generated_at"])

C = dict(
    green="#0D2420", green2="#0A1815", ink="#12140F", paper="#F2EFE8", cream="#F4F2EC",
    mint="#8FE3B8", sage="#A9BDB6", mute="#8A9B96", stone="#9A958A", taupe="#57534A",
    rust="#D9542B", rust2="#B03F1D", amber="#E8B04A", sky="#9AB8E8", sand="#C3BCAC",
)

# Nomes de repos privados que já são públicos no portfólio. O resto aparece como "projeto privado".
DISPLAY = {
    "Aetheria-OS": ("Aetheria OS", "produto próprio"),
    "AetherFinance": ("AetherFinance", "produto próprio"),
    "ceclin-app": ("Ceclin — app do paciente", "cliente · healthtech"),
    "ia-ceclin": ("IA Ceclin — agente de atendimento", "cliente · healthtech"),
    "ia-ceclin-nest": ("IA Ceclin — serviço NestJS", "cliente · healthtech"),
    "ia-ceclin-mcp": ("IA Ceclin — MCP server", "cliente · healthtech"),
    "confirma-consultas": ("Confirma Consultas", "cliente · clínica"),
    "confirma-consultas-chatwoot": ("Confirma Consultas — Chatwoot", "cliente · clínica"),
    "portal-do-cliente": ("Portal do Cliente", "cliente · jurídico"),
}

def label_for(repo):
    if repo["name"] in DISPLAY:
        return DISPLAY[repo["name"]]
    return (repo["name"], "open source") if not repo["private"] else ("Projeto privado", "sob NDA")

def n(v):
    return f"{v:,}".replace(",", ".")

def ago(iso):
    s = (NOW - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds()
    if s < 3600: return f"há {max(1, int(s // 60))} min"
    if s < 86400: return f"há {int(s // 3600)}h"
    return f"há {int(s // 86400)}d"

# ───────────────────────── fontes ─────────────────────────
def load(name, wght=None):
    f = TTFont(os.path.join(HERE, "fonts", name))
    if wght and "fvar" in f:
        f = instancer.instantiateVariableFont(f, {"wght": wght})
    return f

FONTS = {"serif": load("serif.woff2"), "serif-i": load("serif-italic.woff2"),
         "sora": load("sora.woff2", 400), "mono": load("mono.woff2", 500)}
FAMILY = {"serif": ("IS", "normal"), "serif-i": ("IS", "italic"), "sora": ("Sora", "normal"), "mono": ("FC", "normal")}

def width(text, font, size, spacing=0):
    f = FONTS[font]; cmap = f.getBestCmap(); hmtx = f["hmtx"]; upm = f["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(ch), cmap[ord("?")])][0] for ch in text) * size / upm + spacing * len(text)

class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title, self.parts, self.used = w, h, title, [], {k: set() for k in FONTS}

    def add(self, s): self.parts.append(s)

    def text(self, x, y, s, font, size, fill, spacing=0, anchor="start", opacity=None, extra=""):
        self.used[font].update(s)
        fam, style = FAMILY[font]
        op = f' opacity="{opacity}"' if opacity is not None else ""
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-style="{style}" font-size="{size}" '
                 f'fill="{fill}" text-anchor="{anchor}"{ls}{op}{extra}>{escape(s)}</text>')
        return width(s, font, size, spacing)

    def font_css(self):
        css = []
        for key, chars in self.used.items():
            if not chars: continue
            buf = io.BytesIO(); FONTS[key].save(buf); buf.seek(0); f = TTFont(buf)
            opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["kern", "liga"]
            sub = subset.Subsetter(opts); sub.populate(text="".join(chars) + " "); sub.subset(f)
            out = io.BytesIO(); f.flavor = "woff2"; f.save(out)
            fam, style = FAMILY[key]
            css.append(f"@font-face{{font-family:'{fam}';font-style:{style};"
                       f"src:url(data:font/woff2;base64,{base64.b64encode(out.getvalue()).decode()}) format('woff2')}}")
        return "".join(css)

    def save(self, name, extra_css=""):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
               f'role="img" aria-label="{escape(self.title)}"><title>{escape(self.title)}</title>'
               f'<style>{self.font_css()}{extra_css}</style>\n' + "\n".join(self.parts) + "\n</svg>")
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh: fh.write(svg)
        print(f"{name}: {len(svg)/1024:.1f} KB")

def panel(s, fill, clip_id):
    s.add(f'<defs><clipPath id="{clip_id}"><rect width="{s.w}" height="{s.h}" rx="14"/></clipPath></defs>'
          f'<g clip-path="url(#{clip_id})"><rect width="{s.w}" height="{s.h}" fill="{fill}"/>')

def heading(s, y, label, plain, italic, label_color, plain_color, italic_color, size=40):
    s.text(48, y, label, "mono", 11.5, label_color, spacing=2)
    w = s.text(48, y + 50, plain, "serif", size, plain_color, spacing=-0.4)
    s.text(48 + w, y + 50, italic, "serif-i", size, italic_color, spacing=-0.4)

def pill(s, x, y, label, color, size=10):
    w = width(label, "mono", size, 1.2) + 20
    s.add(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="22" rx="11" fill="{color}" fill-opacity=".1" stroke="{color}" stroke-opacity=".45"/>')
    s.text(x + 10, y + 15, label, "mono", size, color, spacing=1.2)
    return w

BLINK = "@keyframes b{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:b 1.1s step-end infinite}"
BEAT = "@keyframes h{0%,100%{opacity:1}50%{opacity:.3}}.beat{animation:h 2s ease-in-out infinite}"

LAST_COMMIT = D["last_commit"] or D["generated_at"]

# ───────────────────────── header ─────────────────────────
def header():
    W, H = 1200, 470
    s = Svg(W, H, f"Arthur Rangel — engenheiro de software full-stack. {n(D['commits_year'])} commits nos últimos 12 meses.")
    panel(s, C["green"], "hc")
    s.add(f'<defs><pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{C["mint"]}" stroke-opacity=".035"/></pattern></defs>'
          f'<rect width="{W}" height="{H}" fill="url(#g)"/>')
    # barra superior
    s.add(f'<rect x="48" y="36" width="40" height="40" rx="8" fill="{C["ink"]}" stroke="{C["cream"]}" stroke-opacity=".12"/>')
    s.text(56, 61.5, "ar", "mono", 15, C["cream"]); s.text(74, 61.5, "_", "mono", 15, C["mint"], extra=' class="blink"')
    s.text(102, 64, "Arthur Rangel", "serif", 26, C["cream"])
    live = f"ÚLTIMO COMMIT {ago(LAST_COMMIT).upper()}"
    lw = width(live, "mono", 11, 1.6) + 44
    s.add(f'<rect x="{W-48-lw:.1f}" y="40" width="{lw:.1f}" height="32" rx="16" fill="{C["mint"]}" fill-opacity=".05" stroke="{C["mint"]}" stroke-opacity=".3"/>'
          f'<circle cx="{W-48-lw+18:.1f}" cy="56" r="3.5" fill="{C["mint"]}" class="beat"/>')
    s.text(W - 48 - lw + 32, 60, live, "mono", 11, C["mint"], spacing=1.6)
    s.add(f'<line x1="48" y1="100" x2="{W-48}" y2="100" stroke="{C["cream"]}" stroke-opacity=".08"/>')
    # coluna esquerda
    s.text(48, 150, "ENGENHEIRO DE SOFTWARE FULL-STACK · RIO DE JANEIRO", "mono", 11, C["sage"], spacing=2)
    s.text(48, 222, "Construo sistemas", "serif", 62, C["cream"], spacing=-0.6)
    w2 = width("que rodam em produção.", "serif-i", 62, -0.6)
    s.add(f'<rect x="40" y="240" width="{w2 + 26:.1f}" height="76" fill="{C["mint"]}" fill-opacity=".1"/>')
    s.text(48, 295, "que rodam em produção.", "serif-i", 62, C["mint"], spacing=-0.6)
    s.text(48, 356, "Agentes de IA, automação e produto. TypeScript e Python,", "sora", 16, C["sage"])
    s.text(48, 382, "do schema ao deploy — e quase sempre depois das 21h.", "sora", 16, C["sage"])
    # terminal
    tx, ty, tw, th = 650, 128, 502, 270
    s.add(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="10" fill="{C["green2"]}" stroke="{C["cream"]}" stroke-opacity=".1"/>'
          f'<line x1="{tx}" y1="{ty+34}" x2="{tx+tw}" y2="{ty+34}" stroke="{C["cream"]}" stroke-opacity=".07"/>')
    for i, col in enumerate((C["rust"], C["amber"], C["mint"])):
        s.add(f'<circle cx="{tx+20+i*16}" cy="{ty+17}" r="4.5" fill="{col}" fill-opacity=".75"/>')
    s.text(tx + tw / 2, ty + 21, "arthur@rj: ~/repos", "mono", 11, C["mute"], anchor="middle")
    lines = [
        ("git log --author=arthur --since=1.year | count", f"{n(D['commits_year'])} commits"),
        ("git log --author=arthur --since=30.days | count", f"{n(D['commits_30d'])} commits"),
        ("ls ~/repos | wc -l", f"{D['repos_total']} repositórios · {D['repos_private']} privados"),
        ("streak --current --best", f"{D['streak_current']} dias seguidos · recorde {D['streak_longest']}"),
    ]
    y = ty + 64
    for cmd, res in lines:
        w = s.text(tx + 20, y, "$ ", "mono", 12, C["mint"])
        s.text(tx + 20 + w, y, cmd, "mono", 12, C["cream"])
        s.text(tx + 20, y + 20, "→ " + res, "mono", 12, C["sage"])
        y += 48
    w = s.text(tx + 20, y - 2, "$ ", "mono", 12, C["mint"])
    s.add(f'<rect x="{tx+20+w:.1f}" y="{y-13}" width="8" height="15" fill="{C["mint"]}" class="blink"/>')
    # status bar
    s.add(f'<rect y="{H-40}" width="{W}" height="40" fill="{C["green2"]}"/><line x1="0" y1="{H-40}" x2="{W}" y2="{H-40}" stroke="{C["cream"]}" stroke-opacity=".06"/>'
          f'<rect y="{H-40}" width="92" height="40" fill="{C["mint"]}"/>')
    s.text(46, H - 15, "main", "mono", 12, C["green"], anchor="middle")
    x = 112
    for seg in ("~/arthur-rangel", "github.com/Art-rh"):
        x += s.text(x, H - 15, seg, "mono", 12, C["mute"]) + 18
        s.add(f'<line x1="{x-9}" y1="{H-28}" x2="{x-9}" y2="{H-12}" stroke="{C["cream"]}" stroke-opacity=".1"/>')
    s.text(W - 24, H - 15, "BRT · UTC−3", "mono", 12, C["mute"], anchor="end")
    s.add("</g>")
    s.save("header.svg", BLINK + BEAT)

# ───────────────────────── atividade + heatmap ─────────────────────────
def activity():
    W, H = 1200, 470
    s = Svg(W, H, f"{n(D['commits_year'])} commits nos últimos 12 meses; {n(D['commits_30d'])} nos últimos 30 dias; "
                  f"{D['active_days_year']} dias ativos; sequência atual de {D['streak_current']} dias, recorde de {D['streak_longest']}; "
                  f"{D['prs_year']} pull requests.")
    panel(s, C["ink"], "ac")
    heading(s, 60, "01 — ATIVIDADE · ÚLTIMOS 12 MESES", f"{n(D['commits_year'])} commits, ",
            "a maioria em código que você não vê.", C["mint"], C["cream"], C["mint"])
    kpis = [(n(D["commits_30d"]), "COMMITS · 30 DIAS"), (str(D["active_days_year"]), "DIAS ATIVOS"),
            (f"{D['streak_current']}d", "SEQUÊNCIA ATUAL"), (f"{D['streak_longest']}d", "MAIOR SEQUÊNCIA"),
            (n(D["prs_year"]), "PULL REQUESTS")]
    col = (W - 96) / len(kpis)
    for i, (v, l) in enumerate(kpis):
        x = 48 + i * col
        s.add(f'<line x1="{x:.1f}" y1="146" x2="{x + col - 20:.1f}" y2="146" stroke="{C["cream"]}" stroke-opacity=".14"/>')
        s.text(x, 194, v, "serif", 40, C["cream"], spacing=-0.4)
        s.text(x, 216, l, "mono", 10, C["stone"], spacing=1.5)
    # heatmap (semanas começando no domingo, como o GitHub)
    per_day = D["per_day"]
    today = NOW.astimezone(BRT).date()
    end = today + timedelta(days=(5 - today.weekday()) % 7)            # sábado desta semana
    start = end - timedelta(days=53 * 7 - 1)
    cell, gap = 15, 4
    gx, gy = 96, 270
    vals = sorted(v for v in per_day.values() if v)
    q = [vals[int(len(vals) * p)] for p in (.25, .5, .75)] if vals else [1, 2, 3]
    shades = ["#1C201A", "#1E4A3C", "#2F7558", "#5BB58A", C["mint"]]
    def shade(v):
        if not v: return shades[0]
        return shades[1 + sum(v > t for t in q)]
    months = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
    last_month = None
    for w in range(53):
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            if day > today: continue
            v = per_day.get(day.isoformat(), 0)
            x, y = gx + w * (cell + gap), gy + d * (cell + gap)
            s.add(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{shade(v)}"><title>{day.strftime("%d/%m/%Y")}: {v} commits</title></rect>')
            if d == 0 and day.month != last_month and day.day <= 7:
                s.text(x, gy - 12, months[day.month - 1], "mono", 10, C["stone"], spacing=1.2)
                last_month = day.month
    for d, lab in ((1, "SEG"), (3, "QUA"), (5, "SEX")):
        s.text(48, gy + d * (cell + gap) + 11.5, lab, "mono", 10, C["stone"], spacing=1)
    ly = gy + 7 * (cell + gap) + 24
    s.text(48, ly + 4, "commits autorais no branch principal · repos públicos e privados · atualizado "
           + NOW.astimezone(BRT).strftime("%d/%m/%Y"), "mono", 10.5, C["mute"], spacing=0.6)
    x = W - 48 - 5 * 19 - 46
    s.text(x - 8, ly + 4, "menos", "mono", 10.5, C["mute"], anchor="end")
    for i, c in enumerate(shades):
        s.add(f'<rect x="{x + i*19}" y="{ly-8}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')
    s.text(x + 5 * 19 + 4, ly + 4, "mais", "mono", 10.5, C["mute"])
    s.add("</g>")
    s.save("activity.svg")

# ───────────────────────── ritmo + linguagens ─────────────────────────
WEEKDAY_PT = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
WEEKDAY_PHRASE = ["às segundas", "às terças", "às quartas", "às quintas", "às sextas", "aos sábados", "aos domingos"]

def rhythm():
    W, H = 1200, 480
    hours, wd = D["hours"], D["weekdays"]
    ph = max(range(24), key=lambda h: hours[h]); pw = max(range(7), key=lambda d: wd[d])
    # linguagens ponderadas por commit nos últimos 12 meses (bytes distorcem com vendor/lockfile)
    by_lang = {k: [v, D["lang_colors"].get(k)] for k, v in D["lang_commits"].items()}
    tot = sum(v[0] for v in by_lang.values()) or 1
    langs = sorted(((k, v[0] * 100 / tot, v[1]) for k, v in by_lang.items()), key=lambda t: -t[1])
    s = Svg(W, H, f"Ritmo: pico de commits às {ph}h e {WEEKDAY_PHRASE[pw]}. Linguagens por commit: "
                  + ", ".join(f"{k} {p:.0f}%" for k, p, _ in langs))
    panel(s, C["paper"], "rc")
    heading(s, 60, "02 — RITMO", f"Rendo mais às {ph}h, ", f"principalmente {WEEKDAY_PHRASE[pw]}.",
            C["rust2"], C["ink"], C["green"])
    # por hora
    bx, by, bw, bh = 48, 330, 640, 150
    s.text(bx, 168, "COMMITS POR HORA · BRT", "mono", 10.5, C["taupe"], spacing=1.8)
    mx = max(hours) or 1; step = bw / 24
    for h in range(24):
        hh = max(2, hours[h] / mx * bh)
        fill = C["rust"] if h == ph else C["ink"]
        op = "1" if h == ph else ".82"
        s.add(f'<rect x="{bx + h*step + 2:.1f}" y="{by - hh:.1f}" width="{step - 6:.1f}" height="{hh:.1f}" rx="2" fill="{fill}" fill-opacity="{op}"><title>{h}h: {hours[h]} commits</title></rect>')
        if h % 3 == 0:
            s.text(bx + h * step + step / 2 - 2, by + 20, f"{h:02d}", "mono", 10, C["taupe"], anchor="middle")
    s.add(f'<line x1="{bx}" y1="{by+0.5}" x2="{bx+bw-4}" y2="{by+0.5}" stroke="{C["ink"]}" stroke-opacity=".25"/>')
    s.text(bx + ph * step + step / 2 - 2, by - hours[ph] / mx * bh - 10, f"{hours[ph]}", "mono", 10.5, C["rust2"], anchor="middle")
    # por dia da semana
    dx, dw = 752, 400
    s.text(dx, 168, "POR DIA DA SEMANA", "mono", 10.5, C["taupe"], spacing=1.8)
    mxd = max(wd) or 1
    for i in range(7):
        y = 190 + i * 20
        bl = max(2, wd[i] / mxd * (dw - 90))
        s.text(dx, y + 10, WEEKDAY_PT[i], "mono", 10, C["taupe"], spacing=1)
        s.add(f'<rect x="{dx+40}" y="{y}" width="{bl:.1f}" height="12" rx="2" fill="{C["rust"] if i == pw else C["ink"]}" fill-opacity="{1 if i == pw else .82}"/>')
        s.text(dx + 48 + bl, y + 10, str(wd[i]), "mono", 10, C["taupe"])
    # linguagens
    lx, ly2, lw = 48, 404, W - 96
    s.text(lx, ly2 - 14, "LINGUAGENS · POR COMMIT, ÚLTIMOS 12 MESES", "mono", 10.5, C["taupe"], spacing=1.8)
    x = lx
    palette = [C["green"], "#2F7558", "#5BB58A", C["amber"], C["rust"], C["sky"], C["sand"]]
    for i, (k, p, _) in enumerate(langs):
        segw = lw * p / 100
        s.add(f'<rect x="{x:.1f}" y="{ly2}" width="{max(segw - 2, 1):.1f}" height="10" fill="{palette[i % len(palette)]}"/>')
        x += segw
    x = lx
    for i, (k, p, _) in enumerate(langs[:6]):
        s.add(f'<rect x="{x}" y="{ly2+28}" width="10" height="10" rx="2" fill="{palette[i % len(palette)]}"/>')
        x += 16 + s.text(x + 16, ly2 + 37, k, "sora", 13, C["ink"])
        x += 6 + s.text(x + 6, ly2 + 37, f"{p:.0f}%", "mono", 11, C["taupe"]) + 28
    s.add("</g>")
    s.save("rhythm.svg")

# ───────────────────────── em andamento ─────────────────────────
def now_panel():
    rows = D["repos_30d"]
    W = 1200; rowh = 62; top = 178
    H = top + rowh * len(rows) + 56
    s = Svg(W, H, "Em andamento nos últimos 30 dias: " + "; ".join(
        f"{label_for(r)[0]} ({r['commits']} commits)" for r in rows))
    panel(s, C["green"], "nc")
    heading(s, 60, "03 — EM ANDAMENTO · ÚLTIMOS 30 DIAS", "Onde os commits estão indo ", "agora.",
            C["mint"], C["cream"], C["mint"])
    cols = [48, 520, 680, 1000]
    for x, h in zip(cols, ("PROJETO", "LINGUAGEM", "COMMITS · 30D", "ÚLTIMO")):
        s.text(x, top - 18, h, "mono", 10.5, C["mute"], spacing=1.8)
    s.add(f'<line x1="48" y1="{top-6}" x2="{W-48}" y2="{top-6}" stroke="{C["cream"]}" stroke-opacity=".14"/>')
    mx = max((r["commits"] for r in rows), default=1)
    for i, r in enumerate(rows):
        y = top + i * rowh
        name, kind = label_for(r)
        s.text(cols[0], y + 30, name, "serif", 23, C["cream"])
        s.text(cols[0], y + 48, kind.upper(), "mono", 9.5, C["stone"], spacing=1.2)
        if r["lang"]:
            s.add(f'<circle cx="{cols[1]+5}" cy="{y+30}" r="5" fill="{r["color"] or C["sand"]}"/>')
            s.text(cols[1] + 18, y + 34.5, r["lang"], "sora", 13.5, C["sage"])
        bl = max(3, r["commits"] / mx * 230)
        s.add(f'<rect x="{cols[2]}" y="{y+23}" width="{bl:.1f}" height="12" rx="2" fill="{C["mint"]}" fill-opacity=".85"/>')
        s.text(cols[2] + bl + 10, y + 34, str(r["commits"]), "mono", 12, C["cream"])
        s.text(cols[3], y + 34, ago(r["last"]), "mono", 12, C["sage"])
        if r["private"]:
            pill(s, W - 48 - width("PRIVADO", "mono", 9.5, 1.2) - 20, y + 19, "PRIVADO", C["mute"], 9.5)
        s.add(f'<line x1="48" y1="{y+rowh-4}" x2="{W-48}" y2="{y+rowh-4}" stroke="{C["cream"]}" stroke-opacity=".06"/>')
    s.text(48, H - 26, "repos de clientes aparecem só com o nome já público no portfólio — o código fica privado.",
           "mono", 10.5, C["mute"], spacing=0.6)
    s.add("</g>")
    s.save("now.svg")

# ───────────────────────── stack ─────────────────────────
STACK = [
    ("PRODUTO", ["TypeScript", "Next.js · React", "React Native · Expo", "Tailwind CSS"]),
    ("BACK-END", ["NestJS · Node.js", "Python · FastAPI", "Redis · BullMQ", "REST · Webhooks"]),
    ("DADOS & INFRA", ["PostgreSQL", "Supabase", "AWS S3", "Docker"]),
    ("IA & AUTOMAÇÃO", ["LangGraph · LangChain", "RAG · MCP · tools", "n8n", "Chatwoot · HubSpot"]),
]

def stack():
    W, H = 1200, 320
    s = Svg(W, H, "Stack em produção: " + "; ".join(f"{g}: {', '.join(i)}" for g, i in STACK))
    panel(s, C["paper"], "sc")
    heading(s, 60, "04 — STACK", "O que eu coloco em produção, ", "não o que eu testei uma vez.",
            C["rust2"], C["ink"], C["green"])
    col = (W - 96) / 4
    for i, (group, items) in enumerate(STACK):
        x = 48 + i * col
        s.add(f'<line x1="{x:.1f}" y1="146" x2="{x + col - 24:.1f}" y2="146" stroke="{C["ink"]}" stroke-opacity=".8"/>')
        s.text(x, 172, group, "mono", 10.5, C["taupe"], spacing=1.8)
        for j, item in enumerate(items):
            s.text(x, 206 + j * 27, item, "sora", 15.5, C["ink"])
    s.add("</g>")
    s.save("stack.svg")

# ───────────────────────── rodapé ─────────────────────────
def footer():
    W, H = 1200, 200
    s = Svg(W, H, "Arthur Rangel — arthurrangelh.com.br")
    panel(s, C["green"], "fc")
    s.text(W - 30, H + 34, "Arthur Rangel", "serif-i", 150, C["mint"], anchor="end", opacity=".05")
    s.text(48, 60, "05 — CONTATO", "mono", 11.5, C["mint"], spacing=2)
    s.text(48, 116, "Código, arquitetura ou um problema cabeludo?", "serif", 42, C["cream"], spacing=-0.4)
    s.text(48, 158, "Me chama.", "serif-i", 42, C["mint"], spacing=-0.4)
    s.text(W - 48, 158, "arthurrangelh.com.br  →", "mono", 12, C["sage"], anchor="end", spacing=1.2)
    s.add("</g>")
    s.save("footer.svg")

header(); activity(); rhythm(); now_panel(); stack(); footer()
