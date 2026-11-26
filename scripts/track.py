"""Gera assets/track.svg: o gráfico de contribuições vira uma pista e um GT3 RS percorre os dias.

Uso: python scripts/track.py [usuario] [--demo]
"""
import random
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = next((a for a in sys.argv[1:] if not a.startswith("-")), "RaphaLima38")
OUT = Path(__file__).resolve().parent.parent / "assets" / "track.svg"
RED = "#e10600"
FONT = "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono','Fira Code',Consolas,monospace"
LEVELS = ["#161618", "#4a0d0d", "#85100f", "#c0120e", "#ff2a1f"]
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


def build(days, total):
    S, C = 16, 12  # passo e tamanho da célula
    X0, Y0 = 64, 62
    first = days[0][0]
    offset = (first.weekday() + 1) % 7  # domingo = 0
    cells = []
    for i, (d, lv) in enumerate(days):
        k = i + offset
        cells.append((k // 7, k % 7, d, lv))
    cols = cells[-1][0] + 1
    W = X0 + cols * S + 56
    H = Y0 + 7 * S + 58
    # percurso em serpentina: desce numa coluna, sobe na seguinte
    order = sorted(cells, key=lambda c: (c[0], c[1] if c[0] % 2 == 0 else -c[1]))
    pts = [(X0 + c * S + C / 2, Y0 + r * S + C / 2) for c, r, _, _ in order]
    path = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in pts)
    n = len(order); dur = max(20, n * .075); drive = .9
    when = {(c, r): drive * i / (n - 1) for i, (c, r, _, _) in enumerate(order)}

    rects = []
    for c, r, d, lv in cells:
        t = when[(c, r)]
        rects.append(
            f'<rect x="{X0 + c * S}" y="{Y0 + r * S}" width="{C}" height="{C}" rx="2.5" fill="{LEVELS[lv]}" opacity=".3">'
            f'<title>{d.strftime("%d/%m/%Y")}</title>'
            f'<animate attributeName="opacity" values=".3;.3;1;1" keyTimes="0;{t:.4f};{min(t + .003, 1):.4f};1" '
            f'dur="{dur:.1f}s" repeatCount="indefinite"/></rect>')
    months, last = [], None
    for c, r, d, _ in cells:
        if r == 0 and d.month != last:
            last = d.month
            if c < cols - 2:
                months.append(f'<text x="{X0 + c * S}" y="{Y0 - 10}" font-family="{MONO}" font-size="10" fill="#6b6b70">{MESES[d.month - 1]}</text>')
    dias = "".join(f'<text x="{X0 - 10}" y="{Y0 + r * S + 10}" text-anchor="end" font-family="{MONO}" font-size="9" fill="#55555a">{n_}</text>'
                   for r, n_ in [(1, "seg"), (3, "qua"), (5, "sex")])
    flag = "".join(f'<rect x="{X0 - 6 + (i % 2) * 3}" y="{Y0 + i * 3 - 2}" width="3" height="3" fill="{"#e6e6e6" if i % 2 == 0 else "#0b0b0c"}"/>'
                   for i in range(7 * S // 3 + 1))
    finish = "".join(f'<rect x="{X0 + cols * S + 2 + (i % 2) * 3}" y="{Y0 + i * 3 - 2}" width="3" height="3" fill="{"#e6e6e6" if i % 2 == 0 else "#0b0b0c"}"/>'
                     for i in range(7 * S // 3 + 1))
    legend = "".join(f'<rect x="{W - 56 - 5 * 16 + i * 16}" y="{H - 28}" width="12" height="12" rx="2.5" fill="{col}"/>' for i, col in enumerate(LEVELS))
    car = (f'<g><g transform="translate(-13 -6.5)">'
           f'<rect x="2" y="0" width="24" height="13" rx="5" fill="#1c1c1e" stroke="#4a4a4e" stroke-width=".8"/>'
           f'<rect x="0" y="-.5" width="4" height="14" rx="1" fill="{RED}"/>'
           f'<rect x="13" y="2.5" width="6" height="8" rx="1.5" fill="#0c0d10"/>'
           f'<rect x="7" y="3" width="5" height="7" rx="1" fill="#2a2a2d"/>'
           f'<rect x="24" y="1.5" width="2" height="3" fill="#f2f2f2"/><rect x="24" y="8.5" width="2" height="3" fill="#f2f2f2"/></g>'
           f'<animateMotion dur="{dur:.1f}s" repeatCount="indefinite" rotate="auto" keyPoints="0;1;1" keyTimes="0;{drive};1" '
           f'calcMode="linear" path="{path}"/></g>')
    titulo = f"{total} contribuições no último ano" if total is not None else "Contribuições no último ano"
    body = f"""
<rect width="{W}" height="{H}" rx="14" fill="#0b0b0c" stroke="#1f1f22"/>
<text x="24" y="30" font-family="{MONO}" font-size="13" fill="{RED}" letter-spacing="3">PISTA DE CONTRIBUIÇÕES</text>
<text x="{W - 24}" y="30" text-anchor="end" font-family="{FONT}" font-size="13" fill="#a3a3a8">{titulo}</text>
{"".join(months)}{dias}{flag}{finish}
{"".join(rects)}{legend}
<path d="{path}" stroke="#ffffff" stroke-opacity=".04" fill="none" stroke-width="2"/>
{car}
<text x="{X0}" y="{H - 18}" font-family="{MONO}" font-size="10" fill="#55555a">atualizado em {date.today().strftime("%d/%m/%Y")}</text>
<text x="{W - 56 - 5 * 16 - 8}" y="{H - 18}" text-anchor="end" font-family="{MONO}" font-size="10" fill="#55555a">menos</text>
<text x="{W - 52}" y="{H - 18}" font-family="{MONO}" font-size="10" fill="#55555a">mais</text>"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{titulo}: um GT3 RS percorre o gráfico de contribuições"><title>{titulo}</title>{body}</svg>\n')


if __name__ == "__main__":
    days, total = demo() if "--demo" in sys.argv else fetch()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build(days, total), encoding="utf-8")
    print(f"{OUT} gerado ({len(days)} dias, total={total})")
