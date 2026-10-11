import re
import time
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator
from PIL import Image
from textblob import TextBlob

st.set_page_config(
    page_title="Sentimientos · Daniel Flórez",
    page_icon="💭",
    layout="centered",
    initial_sidebar_state="expanded",
)

# =====================================================================
#  CONTENIDO
# =====================================================================
IMAGEN = "expresiones.jpg"  # si no existe, simplemente no se muestra

EJEMPLOS = {
    "😊 Positivo": (
        "Hoy fue un día maravilloso. Me siento muy feliz y lleno de gratitud, "
        "la presentación salió increíble y todos me felicitaron."
    ),
    "😔 Negativo": (
        "Estoy muy cansado y frustrado. Todo salió mal hoy, el proyecto fracasó "
        "y me siento fatal."
    ),
    "😐 Neutral": (
        "Mañana tengo una reunión a las tres en la oficina. "
        "El informe tiene diez páginas y está en la carpeta compartida."
    ),
}

# nombre -> (código para traducir, código del traductor de respaldo)
IDIOMAS = {
    "Español": ("es", "es-ES"),
    "Inglés": ("en", "en-GB"),
    "Francés": ("fr", "fr-FR"),
    "Portugués": ("pt", "pt-PT"),
    "Italiano": ("it", "it-IT"),
    "Alemán": ("de", "de-DE"),
    "Automático": ("auto", None),
}

UMBRAL_NEUTRAL = 0.05  # entre -0.05 y 0.05 se considera neutral

# Fondo de página tipo cuaderno: (imagen del patrón, tamaño del patrón)
PATRONES = {
    "Puntos": (
        "radial-gradient(circle, rgba(63,113,166,.30) 1.5px, transparent 1.7px)",
        "26px 26px",
    ),
    "Rayas": (
        "linear-gradient(rgba(63,113,166,.20) 1px, transparent 1px)",
        "100% 34px",
    ),
    "Cuadrícula": (
        "linear-gradient(rgba(63,113,166,.16) 1px, transparent 1px), "
        "linear-gradient(90deg, rgba(63,113,166,.16) 1px, transparent 1px)",
        "28px 28px, 28px 28px",
    ),
    "Liso": (None, None),
}

# =====================================================================
#  ESTILO (paleta fría basada en #3f71a6)
# =====================================================================
PRIMARIO = "#3f71a6"
OSCURO = "#1b2f45"
CLARO = "#eaf2f9"
SUAVE = "#a9c7e3"
NEGATIVO = "#5b6fa8"
POSITIVO = "#2b8a9e"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;600&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&family=Playfair+Display:wght@500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    font-size: 1.06rem;
}
.stApp { background-color: #f6fafd; __PATRON__ }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 860px; padding-top: 3rem; padding-bottom: 4rem; }

/* Hero */
.hero { text-align: center; padding: 1rem 0 .5rem 0; }
.hero .etiqueta {
    font-family: 'Caveat', cursive; font-size: 1.8rem; font-weight: 600;
    color: __PRIMARIO__; line-height: 1;
}
.hero h1 {
    font-family: 'Playfair Display', serif; font-size: 3.2rem; color: __OSCURO__;
    margin: .3rem 0 .6rem 0; line-height: 1.1;
}
.hero h1 .marca {
    background: linear-gradient(transparent 62%, rgba(169, 199, 227, .75) 62%);
    padding: 0 .12em;
}
.hero p { color: #4d6479; font-size: 1.2rem; max-width: 600px; margin: 0 auto; }
.linea {
    width: 70px; height: 4px; border-radius: 4px; background: __PRIMARIO__;
    margin: 1.4rem auto;
}
h2, h3 { font-family: 'Playfair Display', serif !important; color: __OSCURO__ !important; }

/* Tarjetas con "cinta washi" (contenedores con key="tarjeta_...") */
[class*="st-key-tarjeta"] {
    position: relative;
    box-sizing: border-box;
    background: #ffffff !important;
    border: 1px solid __SUAVE__99 !important;
    border-radius: 18px !important;
    box-shadow: 0 8px 24px rgba(63, 113, 166, .10);
    padding: 1.4rem 1.5rem 1.3rem 1.5rem !important;
}
[class*="st-key-tarjeta"]::before {
    content: "";
    position: absolute;
    top: -10px; left: 28px;
    width: 80px; height: 20px;
    background: rgba(169, 199, 227, .75);
    border-radius: 2px;
    transform: rotate(-1.5deg);
    box-shadow: 0 1px 2px rgba(27, 47, 69, .10);
    z-index: 2;
}

/* Quita el icono de enlace que Streamlit añade a los títulos */
[data-testid="stHeaderActionElements"] { display: none !important; }

/* Imagen */
[data-testid="stImage"] img {
    border-radius: 18px; max-height: 420px; object-fit: contain;
    box-shadow: 0 10px 28px rgba(27, 47, 69, .14);
}

/* Veredicto */
.veredicto { text-align: center; padding: .4rem 0 1.2rem 0; }
.veredicto .emoji { font-size: 4.2rem; line-height: 1.1; }
.veredicto .titulo {
    font-family: 'Playfair Display', serif; font-size: 1.9rem; font-weight: 600;
    color: __OSCURO__; margin-top: .3rem;
}
.veredicto .detalle { color: #4d6479; margin-top: .3rem; }

/* Medidores */
.medida { margin: 1.1rem 0 1.4rem 0; }
.medida-titulo {
    display: flex; justify-content: space-between; align-items: baseline;
    font-weight: 600; color: __OSCURO__; margin-bottom: 10px;
}
.medida-titulo strong { font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
.pista { position: relative; height: 12px; border-radius: 999px; }
.pista.pol { background: linear-gradient(90deg, __NEGATIVO__ 0%, #dbe7f3 50%, __POSITIVO__ 100%); }
.pista.pol::after {
    content: ""; position: absolute; left: 50%; top: -4px; bottom: -4px;
    width: 2px; background: __SUAVE__;
}
.pista.sub { background: linear-gradient(90deg, #dbe7f3 0%, __PRIMARIO__ 100%); }
.puntero {
    position: absolute; top: 50%; width: 24px; height: 24px; border-radius: 50%;
    background: white; border: 4px solid __OSCURO__;
    transform: translate(-50%, -50%); box-shadow: 0 2px 6px rgba(27, 47, 69, .3); z-index: 1;
}
.extremos {
    display: flex; justify-content: space-between; margin-top: 10px;
    font-size: .82rem; color: #6b8399;
}

/* Filas (oraciones y diario) */
.fila {
    display: flex; align-items: center; gap: 12px;
    padding: 9px 14px; margin: 6px 0;
    background: #f6fafd; border: 1px dashed __SUAVE__; border-radius: 12px;
}
.fila .num {
    font-family: 'IBM Plex Mono', monospace; font-size: .78rem; color: #6b8399; min-width: 34px;
}
.fila .emoji { font-size: 1.3rem; }
.fila .txt { flex: 1; color: __OSCURO__; font-size: .96rem; }
.fila .valor {
    font-family: 'IBM Plex Mono', monospace; font-size: .88rem; color: __OSCURO__;
    min-width: 52px; text-align: right;
}

.nota-ejemplos { color: #6b8399; font-size: .9rem; margin: .2rem 0 .4rem 0; }

/* Botones */
.stButton > button, .stDownloadButton > button {
    background: __PRIMARIO__; color: white; border: 1.5px solid __PRIMARIO__;
    border-radius: 999px; padding: .65rem 1.4rem; font-size: 1.02rem; font-weight: 600;
    transition: all .2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: __OSCURO__; border-color: __OSCURO__; color: white;
    transform: translateY(-2px); box-shadow: 0 8px 18px rgba(27, 47, 69, .25);
}

/* Inputs */
.stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 12px; border: 1px solid __SUAVE__; font-size: 1.04rem;
}
[data-testid="stAlert"] { border-radius: 14px; }

/* Sidebar */
[data-testid="stSidebar"] { background: __OSCURO__; }
[data-testid="stSidebar"] * { color: #e6f0f9 !important; }

#MainMenu, footer { visibility: hidden; }
</style>
"""


def construir_css(patron: str) -> str:
    imagen, tamano = PATRONES[patron]
    base = "linear-gradient(180deg, #f6fafd 0%, #eaf2f9 100%)"
    if imagen:
        fondo = f"background-image: {imagen}, {base}; background-size: {tamano}, 100% 100%;"
    else:
        fondo = f"background-image: {base};"
    css = CSS.replace("__PATRON__", fondo)
    for token, valor in {
        "__PRIMARIO__": PRIMARIO,
        "__OSCURO__": OSCURO,
        "__CLARO__": CLARO,
        "__SUAVE__": SUAVE,
        "__NEGATIVO__": NEGATIVO,
        "__POSITIVO__": POSITIVO,
    }.items():
        css = css.replace(token, valor)
    return css


# =====================================================================
#  LÓGICA
# =====================================================================
def dividir(texto: str, limite: int):
    """Parte el texto en trozos que respeten el límite de cada servicio."""
    partes, actual = [], ""
    for linea in texto.splitlines():
        while len(linea) > limite:
            if actual:
                partes.append(actual)
                actual = ""
            partes.append(linea[:limite])
            linea = linea[limite:]
        if len(actual) + len(linea) + 1 > limite and actual:
            partes.append(actual)
            actual = ""
        actual += linea + "\n"
    if actual.strip():
        partes.append(actual)
    return partes


@st.cache_data(show_spinner=False, ttl=3600)
def traducir_a_ingles(texto: str, idioma: str) -> tuple[str, str]:
    """TextBlob analiza inglés, así que traducimos primero (con reintento y respaldo)."""
    if idioma == "Inglés":
        return texto, "Ninguno"

    codigo, respaldo = IDIOMAS[idioma]
    ultimo_error = None
    for intento in range(2):
        try:
            traductor = GoogleTranslator(source=codigo, target="en")
            partes = [traductor.translate(p) or "" for p in dividir(texto, 4500)]
            return "\n".join(partes).strip(), "Google"
        except Exception as error:
            ultimo_error = error
            time.sleep(1.5)

    if respaldo:
        try:
            traductor = MyMemoryTranslator(source=respaldo, target="en-GB")
            partes = [traductor.translate(p) or "" for p in dividir(texto, 450)]
            return "\n".join(partes).strip(), "MyMemory"
        except Exception:
            pass
    raise ultimo_error


def clasificar(polaridad: float):
    """Devuelve (emoji, etiqueta, intensidad)."""
    magnitud = abs(polaridad)
    if magnitud <= UMBRAL_NEUTRAL:
        return "😐", "neutral", ""
    intensidad = "leve" if magnitud < 0.3 else ("moderado" if magnitud < 0.6 else "fuerte")
    if polaridad > 0:
        return ("😄" if magnitud >= 0.6 else "😊"), "positivo", intensidad
    return ("😢" if magnitud >= 0.6 else "😔"), "negativo", intensidad


def describir_subjetividad(valor: float) -> str:
    if valor < 0.33:
        return "Es un texto más bien objetivo: predominan los hechos."
    if valor < 0.66:
        return "Mezcla hechos con opiniones o emociones."
    return "Es un texto muy subjetivo: predominan las opiniones y las emociones."


def oraciones(texto: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", texto) if s.strip()]


def medidor(valor, minimo, maximo, titulo, izquierda, derecha, clase, signo=False):
    pct = (valor - minimo) / (maximo - minimo) * 100
    pct = max(0, min(100, pct))
    texto_valor = f"{valor:+.2f}" if signo else f"{valor:.2f}"
    return (
        f'<div class="medida"><div class="medida-titulo"><span>{titulo}</span>'
        f"<strong>{texto_valor}</strong></div>"
        f'<div class="pista {clase}"><div class="puntero" style="left:{pct:.1f}%"></div></div>'
        f'<div class="extremos"><span>{izquierda}</span><span>{derecha}</span></div></div>'
    )


# =====================================================================
#  CALLBACKS
# =====================================================================
def cargar_ejemplo(clave: str):
    st.session_state["texto"] = EJEMPLOS[clave]


def borrar_diario():
    st.session_state["diario"] = []


# =====================================================================
#  PÁGINA
# =====================================================================
st.session_state.setdefault("diario", [])

with st.sidebar:
    st.subheader("Cómo usarlo")
    st.markdown(
        "1. Escribe una frase o un párrafo.\n"
        "2. Elige el idioma del texto.\n"
        "3. Pulsa **Analizar sentimiento**."
    )
    st.subheader("Polaridad y subjetividad")
    st.markdown(
        "**Polaridad:** indica si el sentimiento es positivo, negativo o neutral. "
        "Va de **-1** (muy negativo) a **1** (muy positivo); **0** es neutral."
    )
    st.markdown(
        "**Subjetividad:** mide cuánto del texto son opiniones, emociones o creencias "
        "frente a hechos. Va de **0** (objetivo) a **1** (subjetivo)."
    )
    st.subheader("Estilo de la página")
    patron = st.radio(
        "Fondo de cuaderno",
        list(PATRONES),
        horizontal=True,
        label_visibility="collapsed",
    )

st.markdown(construir_css(patron), unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <div class="etiqueta">diario de emociones ✎</div>
        <h1>Análisis de <span class="marca">sentimientos</span></h1>
        <p>Escribe una frase y descubre qué emoción transmite y cuánta opinión contiene.</p>
        <div class="linea"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

ruta_imagen = Path(__file__).parent / IMAGEN
if ruta_imagen.is_file():
    st.image(Image.open(ruta_imagen), use_container_width=True)
    st.write("")

# ---- 1. Texto ----
with st.container(key="tarjeta_texto"):
    st.subheader("1 · Tu texto")
    st.text_area(
        "Texto a analizar",
        key="texto",
        height=150,
        placeholder="Escribe aquí cómo te sientes, una reseña, un comentario...",
        label_visibility="collapsed",
    )

    st.markdown('<div class="nota-ejemplos">¿Sin ideas? Prueba con un ejemplo:</div>', unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    for columna, clave in zip((e1, e2, e3), EJEMPLOS):
        with columna:
            st.button(clave, on_click=cargar_ejemplo, args=(clave,), use_container_width=True)

    c1, c2 = st.columns([1, 1], vertical_alignment="bottom")
    with c1:
        idioma = st.selectbox("Idioma del texto", list(IDIOMAS))
    with c2:
        analizar = st.button("Analizar sentimiento", type="primary", use_container_width=True)

texto = st.session_state.get("texto", "")

if analizar:
    if not texto.strip():
        st.warning("Escribe un texto antes de analizarlo.")
    else:
        try:
            with st.spinner("Analizando..."):
                texto_en, servicio = traducir_a_ingles(texto.strip(), idioma)
                if not texto_en.strip():
                    raise ValueError("La traducción quedó vacía.")
                sentimiento = TextBlob(texto_en).sentiment
                polaridad = round(float(sentimiento.polarity), 2)
                subjetividad = round(float(sentimiento.subjectivity), 2)
                por_oracion = [
                    (frase, round(float(TextBlob(frase).sentiment.polarity), 2))
                    for frase in oraciones(texto_en)
                ]
        except Exception:
            st.error(
                "No se pudo analizar el texto. Los servicios de traducción pueden estar "
                "saturados: espera unos segundos y vuelve a intentarlo."
            )
        else:
            emoji, etiqueta, intensidad = clasificar(polaridad)
            st.session_state["analisis"] = {
                "original": texto.strip(),
                "ingles": texto_en,
                "polaridad": polaridad,
                "subjetividad": subjetividad,
                "por_oracion": por_oracion,
                "servicio": servicio,
            }
            st.session_state["diario"] = (
                st.session_state["diario"]
                + [{"texto": texto.strip(), "polaridad": polaridad, "emoji": emoji}]
            )[-30:]

# ---- 2. Resultado ----
resultado = st.session_state.get("analisis")
if resultado:
    st.write("")
    polaridad = resultado["polaridad"]
    subjetividad = resultado["subjetividad"]
    emoji, etiqueta, intensidad = clasificar(polaridad)
    titulo = f"Sentimiento {etiqueta}" + (f" {intensidad}" if intensidad else "")

    with st.container(key="tarjeta_resultado"):
        st.subheader("2 · Lo que dice tu texto")
        st.markdown(
            f'<div class="veredicto"><div class="emoji">{emoji}</div>'
            f'<div class="titulo">{titulo}</div>'
            f'<div class="detalle">{escape(describir_subjetividad(subjetividad))}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            medidor(polaridad, -1, 1, "Polaridad", "-1 · muy negativo", "+1 · muy positivo", "pol", signo=True)
            + medidor(subjetividad, 0, 1, "Subjetividad", "0 · objetivo", "1 · subjetivo", "sub"),
            unsafe_allow_html=True,
        )

        with st.expander("Ver el texto que lee el análisis (traducido al inglés)"):
            st.write(resultado["ingles"])
            if resultado["servicio"] == "MyMemory":
                st.caption("Traducido con el servicio de respaldo (MyMemory).")
            st.caption(
                "El análisis de TextBlob funciona en inglés, por eso el texto se traduce "
                "antes de medirlo."
            )

        if len(resultado["por_oracion"]) > 1:
            with st.expander("Ver el análisis oración por oración"):
                filas = []
                for i, (frase, valor) in enumerate(resultado["por_oracion"], 1):
                    emoji_frase, _, _ = clasificar(valor)
                    filas.append(
                        f'<div class="fila"><span class="num">#{i:02d}</span>'
                        f'<span class="emoji">{emoji_frase}</span>'
                        f'<span class="txt">{escape(frase)}</span>'
                        f'<span class="valor">{valor:+.2f}</span></div>'
                    )
                st.markdown("".join(filas), unsafe_allow_html=True)

# ---- 3. Diario de la sesión ----
diario = st.session_state["diario"]
if diario:
    st.write("")
    with st.container(key="tarjeta_diario"):
        st.subheader("3 · Diario de esta sesión")
        st.caption("Tus análisis quedan aquí mientras la página esté abierta. No se guardan en ningún servidor.")

        if len(diario) > 1:
            tabla = pd.DataFrame(
                {"Polaridad": [e["polaridad"] for e in diario]},
                index=range(1, len(diario) + 1),
            )
            tabla.index.name = "Entrada"
            st.line_chart(tabla, color=PRIMARIO, height=200)

        filas = []
        for i, entrada in reversed(list(enumerate(diario, 1))):
            resumen = entrada["texto"] if len(entrada["texto"]) <= 80 else entrada["texto"][:80] + "…"
            filas.append(
                f'<div class="fila"><span class="num">#{i:02d}</span>'
                f'<span class="emoji">{entrada["emoji"]}</span>'
                f'<span class="txt">{escape(resumen)}</span>'
                f'<span class="valor">{entrada["polaridad"]:+.2f}</span></div>'
            )
        st.markdown("".join(filas), unsafe_allow_html=True)
        st.button("Borrar el diario", on_click=borrar_diario)

st.write("")
st.caption("Análisis con TextBlob. Traducción con servicios de Google (deep-translator).")
