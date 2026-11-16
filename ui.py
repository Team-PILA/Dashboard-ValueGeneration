"""Estilos y piezas HTML del dashboard (paleta azul, morado y plomo).

Sin streamlit: cada función devuelve un string HTML que app.py pinta con st.markdown(..., unsafe_allow_html=True).
Todo texto que venga de datos pasa por html.escape.
"""
from __future__ import annotations

import html

# ---------------------------------------------------------------- paleta
AZUL_OSC, AZUL, AZUL_CLARO = "#1E3A8A", "#2563EB", "#E8EFFD"
MORADO_OSC, MORADO, MORADO_CLARO = "#4C1D95", "#7C3AED", "#F1EBFE"
PLOMO_OSC, PLOMO, PLOMO_CLARO, BORDE = "#334155", "#64748B", "#F4F6F9", "#E2E8F0"
TINTA = "#0F172A"

TONOS = {  # (fondo claro, color de acento)
    "azul": (AZUL_CLARO, AZUL),
    "morado": (MORADO_CLARO, MORADO),
    "plomo": (PLOMO_CLARO, PLOMO),
}
GRADIENTES = {
    "azul": f"linear-gradient(135deg, {AZUL_OSC} 0%, {AZUL} 100%)",
    "morado": f"linear-gradient(135deg, {MORADO_OSC} 0%, {MORADO} 100%)",
    "indigo": f"linear-gradient(135deg, #312E81 0%, #4F46E5 100%)",
    "plomo": f"linear-gradient(135deg, {PLOMO_OSC} 0%, {PLOMO} 100%)",
}

# ---------------------------------------------------------------- íconos (SVG propios, trazo = currentColor)
_SVG = ('<svg viewBox="0 0 24 24" width="{s}" height="{s}" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{p}</svg>')
ICONOS = {
    "diana": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
    "monedas": '<ellipse cx="12" cy="6" rx="7" ry="2.5"/><path d="M5 6v4c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6"/>'
               '<path d="M5 10v4c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-4"/><path d="M5 14v4c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-4"/>',
    "tendencia": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "capas": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    "calendario": '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.8 2.8L16.5 9.5"/>',
    "organigrama": '<rect x="9" y="3" width="6" height="4" rx="1"/><rect x="3" y="17" width="6" height="4" rx="1"/>'
                   '<rect x="15" y="17" width="6" height="4" rx="1"/><path d="M12 7v5M6 17v-5h12v5"/>',
    "personas": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/>'
                '<circle cx="17" cy="9" r="2.5"/><path d="M16 14.2c2.9.4 5 2.8 5 5.8"/>',
    "intercambio": '<path d="M4 8h13l-3-3"/><path d="M20 16H7l3 3"/>',
    "engranaje": '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3'
                 'M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "reloj": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "rayo": '<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>',
    "billete": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/>'
               '<path d="M6 9.5v5M18 9.5v5"/>',
}


def icono(nombre: str, size: int = 26) -> str:
    return _SVG.format(s=size, p=ICONOS.get(nombre, ""))


def _e(t) -> str:
    return html.escape("" if t is None else str(t)).replace("\n", "<br>")


# ---------------------------------------------------------------- CSS
CSS = f"""
<style>
.block-container{{padding-top:2.2rem}}
.vg-head{{display:flex;align-items:center;gap:14px;margin:0 0 4px}}
.vg-head .bar{{width:6px;height:46px;border-radius:3px;background:{GRADIENTES['morado']}}}
.vg-head h1{{font-size:2.1rem;font-weight:800;color:{AZUL_OSC};margin:0;padding:0;line-height:1.1}}
.vg-head p{{margin:2px 0 0;color:{PLOMO};font-size:.95rem}}

.vg-hero{{border-radius:14px;padding:16px 18px;color:#fff;display:flex;gap:14px;align-items:center;
          min-height:150px;box-shadow:0 6px 18px rgba(30,58,138,.18);margin-bottom:14px}}
.vg-hero .ic{{flex:0 0 auto;width:48px;height:48px;border-radius:12px;background:rgba(255,255,255,.16);
              display:flex;align-items:center;justify-content:center}}
.vg-hero .t{{font-size:.8rem;font-weight:700;letter-spacing:.02em;text-transform:uppercase;opacity:.92}}
.vg-hero .v{{font-size:1.9rem;font-weight:800;line-height:1.1;margin-top:2px}}
.vg-hero .s{{font-size:.74rem;opacity:.85;margin-top:4px}}

.vg-hero.big .v{{font-size:2.9rem}}
.vg-hero.big .ic{{width:58px;height:58px}}

.vg-tile{{border-radius:12px;padding:12px 16px;background:{PLOMO_CLARO};border:1px solid {BORDE};
          display:flex;gap:12px;align-items:center;margin-bottom:14px;color:{TINTA};min-height:74px}}
.vg-tile .ic{{color:{AZUL};flex:0 0 auto}}
.vg-tile .t{{font-size:.8rem;font-weight:600;color:{PLOMO_OSC}}}
.vg-tile .v{{font-size:1.45rem;font-weight:800;line-height:1.15}}
.vg-tile .s{{font-size:.72rem;color:{PLOMO}}}

.vg-ger{{border-radius:12px;padding:12px 16px;background:#fff;border:1px solid {BORDE};
         display:flex;gap:12px;align-items:center;margin-bottom:14px;color:{TINTA};min-height:74px}}
.vg-ger .ic{{color:{MORADO};flex:0 0 auto}}
.vg-ger .chips{{display:flex;flex-wrap:wrap;gap:6px}}
.vg-chip{{background:{MORADO_CLARO};color:{MORADO_OSC};border-radius:999px;padding:3px 10px;
          font-size:.82rem;font-weight:700}}

.vg-sec{{display:flex;gap:10px;align-items:center;margin:2px 0 12px}}
.vg-sec .ic{{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center}}
.vg-sec .t{{font-weight:800;color:{TINTA};font-size:1.02rem;line-height:1.2}}
.vg-sec .s{{font-size:.75rem;color:{PLOMO}}}

.vg-met{{border-radius:12px;padding:12px 14px;margin-bottom:10px;display:flex;gap:10px;align-items:center;
         color:{TINTA};min-height:84px}}
.vg-met .ic{{flex:0 0 auto}}
.vg-met .t{{font-size:.78rem;font-weight:700}}
.vg-met .v{{font-size:1.6rem;font-weight:800;line-height:1.15}}
.vg-met .s{{font-size:.72rem;color:{PLOMO}}}
.vg-nota{{font-size:.74rem;text-align:center;color:{PLOMO};margin:0 0 8px}}

.st-key-sec_org, .st-key-sec_inh, .st-key-sec_opt{{border-top-width:5px !important;border-radius:14px !important}}
.st-key-sec_org{{border-top-color:{MORADO} !important}}
.st-key-sec_inh{{border-top-color:{AZUL} !important}}
.st-key-sec_opt{{border-top-color:{PLOMO} !important}}
</style>
"""


# ---------------------------------------------------------------- piezas
def encabezado(titulo: str, subtitulo: str) -> str:
    return (f'<div class="vg-head"><div class="bar"></div><div><h1>{_e(titulo)}</h1>'
            f'<p>{_e(subtitulo)}</p></div></div>')


def hero(titulo: str, valor: str, sub: str | None, ic: str, estilo: str = "azul", grande: bool = False) -> str:
    """Tarjeta principal con fondo degradado y texto blanco."""
    sub_h = f'<div class="s">{_e(sub)}</div>' if sub else ""
    return (f'<div class="vg-hero{" big" if grande else ""}" style="background:{GRADIENTES[estilo]}">'
            f'<div class="ic">{icono(ic, 30 if grande else 26)}</div>'
            f'<div><div class="t">{_e(titulo)}</div><div class="v">{_e(valor)}</div>{sub_h}</div></div>')


def tile(titulo: str, valor: str, sub: str | None, ic: str) -> str:
    """Tarjeta secundaria plomo claro."""
    sub_h = f'<div class="s">{_e(sub)}</div>' if sub else ""
    return (f'<div class="vg-tile"><div class="ic">{icono(ic, 30)}</div>'
            f'<div><div class="t">{_e(titulo)}</div><div class="v">{_e(valor)}</div>{sub_h}</div></div>')


def gerencias(conteo: dict) -> str:
    chips = "".join(f'<span class="vg-chip">{_e(g)}: {int(n)}</span>' for g, n in conteo.items()) \
        or '<span class="vg-chip">Sin gerencias</span>'
    return f'<div class="vg-ger"><div class="ic">{icono("organigrama", 28)}</div><div class="chips">{chips}</div></div>'


def seccion(titulo: str, sub: str, ic: str, tono: str) -> str:
    fondo, acento = TONOS[tono]
    return (f'<div class="vg-sec"><div class="ic" style="background:{fondo};color:{acento}">{icono(ic, 24)}</div>'
            f'<div><div class="t">{_e(titulo)}</div><div class="s">{_e(sub)}</div></div></div>')


def metrica(titulo: str, valor: str, sub: str | None, ic: str, tono: str) -> str:
    fondo, acento = TONOS[tono]
    sub_h = f'<div class="s">{_e(sub)}</div>' if sub else ""
    return (f'<div class="vg-met" style="background:{fondo}"><div class="ic" style="color:{acento}">'
            f'{icono(ic, 30)}</div><div><div class="t" style="color:{acento}">{_e(titulo)}</div>'
            f'<div class="v">{_e(valor)}</div>{sub_h}</div></div>')


def nota(texto: str) -> str:
    return f'<p class="vg-nota">{_e(texto)}</p>'