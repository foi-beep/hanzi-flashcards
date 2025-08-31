
# hanzi_flashcards.py
# Streamlit app to drill Chinese character PDF pages as flashcards.
# Shows only the left half first (character/context), and reveals the right half (pinyin/meaning) on click.
# Usage:
#   streamlit run hanzi_flashcards.py

import random
from typing import Tuple

import streamlit as st

try:
    import fitz  # PyMuPDF
except Exception:
    st.error("PyMuPDF (fitz) is required. Please install with:  pip install pymupdf")
    raise

st.set_page_config(page_title="Hanzi Flashcards (PDF → left/right)", layout="wide")

st.title("🀄 Hanzi Flashcards desde PDF")
st.caption("Sube tu PDF de fichas. El app mostrará **solo el lado izquierdo** primero; haz clic para ver el derecho.")

with st.expander("⚙️ Opciones", expanded=False):
    dpi = st.slider("Resolución de render (DPI)", min_value=120, max_value=300, value=200, step=20,
                    help="Más DPI = imagen más nítida (y más lenta). 200 es un buen balance.")
    no_repeats = st.checkbox("Barajar todas las páginas sin repetición", value=True,
                             help="Recorrerá el PDF aleatoriamente sin repetir hasta agotar todas las páginas.")
    show_page_number = st.checkbox("Mostrar número de página", value=True)
    keep_answer_visible = st.checkbox("Mantener respuesta visible al pasar a la siguiente", value=False,
                                      help="Si se desactiva, cada tarjeta nueva vuelve a ocultar la respuesta.")

uploaded = st.file_uploader("📄 Sube el PDF (cada página contiene izquierda/derecha)", type=["pdf"])

def _render_halves(pdf_bytes: bytes, page_index: int, dpi: int) -> Tuple[bytes, bytes]:
    """Return (left_png_bytes, right_png_bytes) for a given page index."""
    # Open / render inside the function so it stays self-contained for caching.
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc.load_page(page_index)
        rect = page.rect
        mid_x = rect.x0 + rect.width / 2.0
        # Clip rectangles
        left_rect = fitz.Rect(rect.x0, rect.y0, mid_x, rect.y1)
        right_rect = fitz.Rect(mid_x, rect.y0, rect.x1, rect.y1)
        # DPI → matrix scale (PDF uses 72 dpi base)
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        left_pix = page.get_pixmap(matrix=mat, clip=left_rect, alpha=False)
        right_pix = page.get_pixmap(matrix=mat, clip=right_rect, alpha=False)
        return left_pix.tobytes("png"), right_pix.tobytes("png")

@st.cache_data(show_spinner=False)
def get_page_count(pdf_bytes: bytes) -> int:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc.page_count

@st.cache_data(show_spinner=False)
def get_halves_cached(pdf_bytes: bytes, page_index: int, dpi: int) -> Tuple[bytes, bytes]:
    # Cache by (bytes hash, index, dpi) so flipping is instant after first render
    return _render_halves(pdf_bytes, page_index, dpi)

def init_deck(total_pages: int):
    order = list(range(total_pages))
    random.shuffle(order)
    st.session_state.order = order
    st.session_state.pos = 0

def next_index(total_pages: int, no_repeats: bool) -> int:
    if no_repeats:
        if "order" not in st.session_state or st.session_state.get("order_total") != total_pages:
            init_deck(total_pages)
            st.session_state.order_total = total_pages
        if st.session_state.pos >= len(st.session_state.order):
            init_deck(total_pages)
        idx = st.session_state.order[st.session_state.pos]
        st.session_state.pos += 1
        return idx
    else:
        return random.randrange(0, total_pages)

if uploaded:
    pdf_bytes = uploaded.read()
    total = get_page_count(pdf_bytes)
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = next_index(total, no_repeats)
        st.session_state.reveal = False

    # Sidebar info
    with st.sidebar:
        st.success(f"Páginas en el PDF: **{total}**")
        if no_repeats:
            st.info(f"Progreso: {st.session_state.get('pos', 0)} / {total}")
        st.button("🔀 Nueva tarjeta aleatoria", use_container_width=True, type="primary",
                  on_click=lambda: (st.session_state.update({"current_idx": next_index(total, no_repeats)}),
                                    st.session_state.update({"reveal": st.session_state.get("reveal", False) if keep_answer_visible else False})))
        st.button("↩️ Reiniciar baraja", use_container_width=True, on_click=lambda: init_deck(total))

    # Render current page halves
    left_png, right_png = get_halves_cached(pdf_bytes, st.session_state.current_idx, dpi)

    col1, col2 = st.columns(2)
    with col1:
        if show_page_number:
            st.markdown(f"**Página {st.session_state.current_idx + 1} / {total} (IZQUIERDA)**")  # left first
        st.image(left_png, use_column_width=True)
        st.button("👀 Mostrar respuesta (derecha)", key="reveal_btn", type="primary",
                  on_click=lambda: st.session_state.update({"reveal": True}))

    with col2:
        if st.session_state.get("reveal", False):
            if show_page_number:
                st.markdown(f"**Página {st.session_state.current_idx + 1} / {total} (DERECHA)**")
            st.image(right_png, use_column_width=True)
        else:
            st.markdown("<div style='width:100%;height:100%;border:2px dashed #bbb;border-radius:12px;display:flex;align-items:center;justify-content:center;padding:1.5rem;'>"
                        "Haz clic en <b>“Mostrar respuesta”</b> para ver el lado derecho</div>", unsafe_allow_html=True)

    st.divider()
    st.caption("Consejo: activa ‘Barajar sin repetición’ para recorrer todas las páginas una sola vez antes de reiniciar.")
else:
    st.info("Sube un PDF para comenzar. ")
