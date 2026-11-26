"""Gera assets/track.svg: o gráfico de contribuições vira um circuito e um GT3 RS dá voltas nele,
fazendo drift nas curvas (frenagem, escorregada da traseira, contraesterço, fumaça e marcas de pneu).

Uso: python scripts/track.py [usuario] [--demo]
"""
import base64
import math
import random
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = next((a for a in sys.argv[1:] if not a.startswith("-")), "RaphaLima38")
OUT = Path(__file__).resolve().parent.parent / "assets" / "track.svg"
AMBER = "#f5a524"  # destaque âmbar (luz do túnel)
RED = "#e3170a"
SILVER = "#e8e4dc"
FONT = "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono','Fira Code',Consolas,monospace"
LEVELS = ["#1a1612", "#4a3212", "#8a5a14", "#d08a1c", "#ffc46b"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def fetch():
    req = urllib.request.Request(f"https://github.com/users/{USER}/contributions",
                                 headers={"User-Agent": "profile-track-generator"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    days = []
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        d = re.search(r'data-date="([\d-]+)"', tag)
        lv = re.search(r'data-level="(\d)"', tag)
        if d and lv:
            days.append((date.fromisoformat(d.group(1)), int(lv.group(1))))
    total = re.search(r"([\d,.]+)\s+contributions?\s+in the last year", html)
    if not days:
        raise RuntimeError("calendário de contribuições não encontrado")
    return sorted(days), int(re.sub(r"\D", "", total.group(1))) if total else None


def demo():
    end = date.today(); start = end - timedelta(days=364 + (end.weekday() + 1) % 7)
    r = random.Random(38)
    return [(start + timedelta(i), r.choice([0, 0, 0, 1, 1, 2, 3, 4])) for i in range((end - start).days + 1)], None


def smooth(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def periodic(t0, TT, stages):
    """Keyframes de uma animação periódica (duração TT) de algo que nasce em t0.
    stages: [(idade_s, {attr: valor})]; fora da vida usa o último estágio (invisível)."""
    pts = sorted(((t0 + age) % TT, vals) for age, vals in stages)
    first, last = pts[0], pts[-1]
    span = first[0] + TT - last[0]
    f = (TT - last[0]) / span if span else 0
    edge = {k: last[1][k] + (first[1][k] - last[1][k]) * f for k in first[1]}
    pts = [(0.0, edge)] + pts + [(TT, edge)]
    keys = ";".join(f"{x / TT:.4f}" for x, _ in pts)
    return keys, {k: ";".join(f"{v[k]:.2f}" for _, v in pts) for k in edge}


def puff(x, y, t0, TT, wx, wy, strength):
    life = 5.5
    ages = [0, .12, .9, 2.4, 4.0, life]
    ops = [0, .5, .34, .17, .06, 0]
    rs = [2, 4.5, 9, 15, 20, 24]
    stages = [(a, {"cx": x + wx * a, "cy": y + wy * a, "r": r, "opacity": o * strength}) for a, r, o in zip(ages, rs, ops)]
    stages.append((life + .01, {"cx": x, "cy": y, "r": 2, "opacity": 0}))
    keys, vals = periodic(t0, TT, stages)
    anim = "".join(f'<animate attributeName="{k}" values="{v}" keyTimes="{keys}" dur="{TT:.2f}s" repeatCount="indefinite"/>' for k, v in vals.items())
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="0" opacity="0">{anim}</circle>'


class Track:
    """Circuito fechado amostrado a cada `ds` px: posição, direção, curvas."""

    def __init__(self, ds=2.0):
        self.ds, self.pts, self.turns, self.x, self.y = ds, [], [], None, None

    def move(self, x, y):
        self.x, self.y = x, y
        self.pts.append((x, y))

    def line(self, x, y):
        n = max(1, int(math.hypot(x - self.x, y - self.y) / (self.ds * 3)))
        for i in range(1, n + 1):
            self.pts.append((self.x + (x - self.x) * i / n, self.y + (y - self.y) * i / n))
        self.x, self.y = x, y

    def arc(self, cx, cy, r, a0, a1, drift):
        s0 = len(self.pts) - 1
        n = max(2, int(abs(math.radians(a1 - a0)) * r / self.ds))
        for i in range(1, n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            self.pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.x, self.y = self.pts[-1]
        self.turns.append(dict(i0=s0, i1=len(self.pts) - 1, sign=1 if a1 > a0 else -1, drift=drift,
                               cx=cx, cy=cy, r=r, a0=a0, a1=a1))


def build(days, total):
    C, SX, SY = 14, 18, 28                  # célula, passo horizontal, passo entre faixas
    first = days[0][0]
    offset = (first.weekday() + 1) % 7    # domingo = 0
    cells = [((i + offset) // 7, (i + offset) % 7, d, lv) for i, (d, lv) in enumerate(days)]
    cols = cells[-1][0] + 1
    E, RH, R2 = 10, SY / 2, 14
    X0, Y0 = 84, 72
    xs, xe = X0 + C / 2, X0 + (cols - 1) * SX + C / 2
    yr = lambda r: Y0 + r * SY + SY / 2
    ybot = yr(6) + SY + 8
    xl = xs - E - RH - 20
    W, H = int(xe + E + RH + 40), int(ybot + 52)

    # ---------- traçado: 7 retas (dias da semana) com grampos + retorno por fora ----------
    T = Track()
    T.move(xs - E, yr(0))
    for r in range(7):
        right = r % 2 == 0
        T.line(xe + E if right else xs - E, yr(r))
        if r < 6:
            if right:
                T.arc(xe + E, yr(r) + RH, RH, -90, 90, 48)
            else:
                T.arc(xs - E, yr(r) + RH, RH, -90, -270, 48)
    T.arc(xe + E, yr(6) + R2, R2, -90, 0, 32)
    T.line(xe + E + R2, ybot - R2)
    T.arc(xe + E, ybot - R2, R2, 0, 90, 32)
    T.line(xl + R2, ybot)
    T.arc(xl + R2, ybot - R2, R2, 90, 180, 32)
    T.line(xl, yr(0) + R2)
    T.arc(xl + R2, yr(0) + R2, R2, 180, 270, 32)
    T.line(xs - E, yr(0))
    P = T.pts
    n = len(P)
    S = [0.0]
    for i in range(1, n):
        S.append(S[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    L = S[-1]
    head = [math.degrees(math.atan2(P[min(i + 1, n - 1)][1] - P[max(i - 1, 0)][1], P[min(i + 1, n - 1)][0] - P[max(i - 1, 0)][0])) for i in range(n)]
    for t in T.turns:
        t["s0"], t["s1"] = S[t["i0"]], S[t["i1"]]

    # ---------- dinâmica: perfil de velocidade com aceleração e frenagem limitadas ----------
    VMAX, A_ACC, A_BRK = 290.0, 140.0, 360.0          # px/s e px/s²
    m = n - 1                                          # P[n-1] == P[0] (circuito fechado)
    dd = lambda i: math.hypot(P[i % m][0] - P[(i - 1) % m][0], P[i % m][1] - P[(i - 1) % m][1])
    v = [VMAX] * m
    for t in T.turns:
        vt = 78.0 if t["drift"] > 30 else 120.0
        for i in range(t["i0"], t["i1"] + 1):
            v[i % m] = min(v[i % m], vt)
    for _ in range(2):                                 # aceleração (passada para frente)
        for i in range(m):
            v[i] = min(v[i], math.sqrt(v[(i - 1) % m] ** 2 + 2 * A_ACC * dd(i)))
    for _ in range(2):                                 # frenagem (passada para trás)
        for i in range(m - 1, -1, -1):
            j = (i + 1) % m
            v[i] = min(v[i], math.sqrt(v[j] ** 2 + 2 * A_BRK * dd(j)))
    v.append(v[0])
    tm = [0.0]
    for i in range(1, n):
        tm.append(tm[-1] + dd(i) * 2 / (v[i] + v[i - 1]))
    TT = tm[-1]
    brake = [v[min(i + 1, n - 1)] < v[i] - .02 for i in range(n)]

    def slip(s):
        a = 0.0
        for t in T.turns:
            ln = t["s1"] - t["s0"]
            rise = smooth(t["s0"] - 22, t["s0"] + .45 * ln, s)
            out = smooth(t["s1"] - 4, t["s1"] + 55, s)
            back = smooth(t["s1"] + 55, t["s1"] + 130, s)
            a += t["sign"] * t["drift"] * (rise * (1 - out) + out * (1 - back) * -.3)
        return a
    SL = [slip(x) for x in S]

    def at_s(s):
        i = min(n - 1, max(0, int(s / L * (n - 1))))
        while i < n - 1 and S[i + 1] < s:
            i += 1
        while i > 0 and S[i] > s:
            i -= 1
        return i

    # ---------- keyframes (a cada ~8 px) ----------
    K = list(range(0, n, 4)) + ([n - 1] if (n - 1) % 4 else [])
    kt = ";".join(f"{tm[i] / TT:.5f}" for i in K)
    kp = ";".join(f"{S[i] / L:.5f}" for i in K)
    ksl = ";".join(f"{SL[i]:.1f}" for i in K)
    kbr = ";".join("1" if brake[i] else ".25" for i in K)
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in P) + " Z"
    dur = f"{TT:.2f}s"

    # ---------- células acendem quando o carro passa ----------
    rects = []
    for c, r, d, lv in cells:
        cx, cy = X0 + c * SX + C / 2, yr(r)
        i = min(range(0, n, 2), key=lambda j: (P[j][0] - cx) ** 2 + (P[j][1] - cy) ** 2) if False else None
        # posição exata na reta da linha r
        base = 0.0
        for rr in range(r):
            base += 0  # calculado abaixo
        rects.append((c, r, d, lv, cx, cy))
    # s de cada célula: procura o ponto mais próximo na reta da sua linha
    row_idx = {}
    for i, (x, y) in enumerate(P):
        for r in range(7):
            if abs(y - yr(r)) < .01 and xs - E - .1 <= x <= xe + E + .1:
                row_idx.setdefault(r, []).append(i)
    out_rects = []
    for c, r, d, lv, cx, cy in rects:
        ids = row_idx[r]
        i = min(ids, key=lambda j: abs(P[j][0] - cx))
        t = tm[i] / TT
        out_rects.append(
            f'<rect x="{cx - C / 2:.0f}" y="{cy - C / 2:.0f}" width="{C}" height="{C}" rx="3" fill="{LEVELS[lv]}" opacity=".35">'
            f'<title>{d.strftime("%d/%m/%Y")}</title><animate attributeName="opacity" values=".35;.35;1;1" '
            f'keyTimes="0;{t:.4f};{min(t + .002, 1):.4f};1" dur="{dur}" repeatCount="indefinite"/></rect>')

    # ---------- fumaça, marcas de pneu, zebras ----------
    WX, WY = 7.0, -4.5                                 # vento (px/s): leva a fumaça para cima/direita
    smoke, skids, kerbs = [], [], []
    for t in T.turns:
        j0, j1 = at_s(t["s0"] - 4), at_s(min(L, t["s1"] + 40))
        rl, rr_ = [], []
        for i in range(j0, j1 + 1):
            th = math.radians(head[i] + SL[i])
            bx, by = P[i][0] - math.cos(th) * 10, P[i][1] - math.sin(th) * 10
            nx, ny = -math.sin(th) * 4.5, math.cos(th) * 4.5
            rl.append((bx + nx, by + ny)); rr_.append((bx - nx, by - ny))
        ta, tb = tm[j0] / TT, tm[j1] / TT
        for pts in (rl, rr_):
            ln = sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]) for k in range(1, len(pts)))
            d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
            skids.append(f'<path d="{d}" fill="none" stroke="#050403" stroke-opacity=".7" stroke-width="2.2" stroke-linecap="butt" '
                         f'stroke-dasharray="{ln:.1f}" stroke-dashoffset="{ln:.1f}"><animate attributeName="stroke-dashoffset" '
                         f'values="{ln:.1f};{ln:.1f};0;0" keyTimes="0;{ta:.4f};{tb:.4f};1" dur="{dur}" repeatCount="indefinite"/></path>')
        rnd = random.Random(int(t["s0"]))
        for i in range(at_s(t["s0"] + 4), at_s(t["s1"] + 60), 3):
            th = math.radians(head[i] + SL[i])
            if abs(SL[i]) < 8:
                continue
            px, py = P[i][0] - math.cos(th) * 12, P[i][1] - math.sin(th) * 12
            k = .8 + rnd.random() * .5
            smoke.append(puff(px, py, tm[i], TT, WX * k, WY * k, min(1, abs(SL[i]) / t["drift"])))
        ro = t["r"] + 15
        a0, a1 = math.radians(t["a0"]), math.radians(t["a1"])
        large = 1 if abs(t["a1"] - t["a0"]) > 180 else 0
        sweep = 1 if t["a1"] > t["a0"] else 0
        d = (f'M{t["cx"] + ro * math.cos(a0):.1f} {t["cy"] + ro * math.sin(a0):.1f} '
             f'A{ro} {ro} 0 {large} {sweep} {t["cx"] + ro * math.cos(a1):.1f} {t["cy"] + ro * math.sin(a1):.1f}')
        kerbs.append(f'<path d="{d}" fill="none" stroke="{SILVER}" stroke-width="4"/>'
                     f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="4" stroke-dasharray="5 5"/>')

    # ---------- textos ----------
    months, last = [], None
    for c, r, d, _ in cells:
        if r == 0 and d.month != last:
            last = d.month
            if c < cols - 2:
                months.append(f'<text x="{X0 + c * SX}" y="{Y0 - 6}" font-family="{MONO}" font-size="11" fill="#6b6359">{MESES[d.month - 1]}</text>')
    chk = "".join(f'<rect x="{xs - E - 4 + (i % 2) * 4}" y="{yr(0) - 12 + (i // 2) * 4}" width="4" height="4" fill="{SILVER if (i + i // 2) % 2 == 0 else "#14110e"}"/>'
                  for i in range(12))
    legend = "".join(f'<rect x="{W - 60 - 5 * 17 + i * 17}" y="{H - 30}" width="13" height="13" rx="3" fill="{col}"/>' for i, col in enumerate(LEVELS))
    car_img = base64.b64encode((OUT.parent / "car-top.webp").read_bytes()).decode()
    beams = ('<g filter="url(#shd)" opacity=".9"><path d="M15 -5 L88 -24 Q95 -11 88 1 Z" fill="url(#beam)"/>'
             '<path d="M15 5 L88 24 Q95 11 88 -1 Z" fill="url(#beam)"/></g>'
             '<circle cx="15.5" cy="-4.6" r="1.6" fill="#fff8e8"/><circle cx="15.5" cy="4.6" r="1.6" fill="#fff8e8"/>')
    car = (f'<g><g>{beams}<ellipse cx="0" cy="0" rx="17" ry="8" fill="#000" opacity=".55" filter="url(#shd)"/>'
           f'<image x="-16" y="-7.1" width="32" height="14.2" href="data:image/webp;base64,{car_img}"/>'
           f'<g fill="{RED}"><rect x="-16.5" y="-5.6" width="2" height="3.2" rx="1"/><rect x="-16.5" y="2.4" width="2" height="3.2" rx="1"/>'
           f'<ellipse cx="-17" cy="0" rx="6" ry="7" opacity=".55" filter="url(#shd)"/>'
           f'<animate attributeName="opacity" values="{kbr}" keyTimes="{kt}" calcMode="discrete" dur="{dur}" repeatCount="indefinite"/></g>'
           f'<animateTransform attributeName="transform" type="rotate" values="{ksl}" keyTimes="{kt}" dur="{dur}" repeatCount="indefinite"/></g>'
           f'<animateMotion dur="{dur}" repeatCount="indefinite" rotate="auto" keyPoints="{kp}" keyTimes="{kt}" calcMode="linear"><mpath href="#trk"/></animateMotion></g>')
    titulo = f"{total} contribuições no último ano" if total is not None else "Contribuições no último ano"
    body = f"""
<defs><filter id="smk" x="0" y="0" filterUnits="userSpaceOnUse" width="{W}" height="{H}"><feTurbulence type="fractalNoise" baseFrequency=".045" numOctaves="3" seed="7" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="16" xChannelSelector="R" yChannelSelector="G" result="d"/><feGaussianBlur in="d" stdDeviation="2.4"/></filter>
<linearGradient id="beam" gradientUnits="userSpaceOnUse" x1="15" y1="0" x2="92" y2="0"><stop offset="0" stop-color="#fff4dc" stop-opacity=".75"/><stop offset=".35" stop-color="#ffe9c0" stop-opacity=".32"/><stop offset="1" stop-color="#ffe9c0" stop-opacity="0"/></linearGradient>
<filter id="shd" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.5"/></filter>
<path id="trk" d="{path}"/></defs>
<rect width="{W}" height="{H}" rx="14" fill="#14110e" stroke="#2a241d"/>
<text x="26" y="34" font-family="{MONO}" font-size="14" font-weight="700" fill="{AMBER}" letter-spacing="3">PISTA DE CONTRIBUIÇÕES</text>
<text x="{W - 26}" y="34" text-anchor="end" font-family="{FONT}" font-size="14" fill="#9c9387">{titulo}</text>
{"".join(months)}
<use href="#trk" fill="none" stroke="#2a241d" stroke-width="27" stroke-linejoin="round"/>
<use href="#trk" fill="none" stroke="#1b1611" stroke-width="24" stroke-linejoin="round"/>
{"".join(kerbs)}{chk}
{"".join(out_rects)}
{"".join(skids)}<g fill="#d6cfc4" filter="url(#smk)">{"".join(smoke)}</g>
{car}
<text x="{xl - 6}" y="{H - 18}" font-family="{MONO}" font-size="11" fill="#5a5249">atualizado em {date.today().strftime("%d/%m/%Y")} · volta de {TT:.0f} s</text>
<text x="{W - 60 - 5 * 17 - 8}" y="{H - 19}" text-anchor="end" font-family="{MONO}" font-size="11" fill="#5a5249">menos</text>{legend}
<text x="{W - 54}" y="{H - 19}" font-family="{MONO}" font-size="11" fill="#5a5249">mais</text>"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{titulo}: um GT3 RS dá voltas no gráfico de contribuições fazendo drift nas curvas"><title>{titulo}</title>{body}</svg>\n')


if __name__ == "__main__":
    days, total = demo() if "--demo" in sys.argv else fetch()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build(days, total), encoding="utf-8")
    print(f"{OUT} gerado ({len(days)} dias, total={total})")
