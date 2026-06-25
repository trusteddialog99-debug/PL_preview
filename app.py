
import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageOps

try:
    import cairosvg
except Exception:
    cairosvg = None

# ============================================================================
# Exakt vermessene Platzhalter aus template.png
# ============================================================================
# Linker pinker Kreis  : x=83..127,  y=302..347  -> 45x46 px
# Mittleres pinkes Feld: x=651..769, y=291..311  -> 119x21 px
# Rechter pinker Kreis : x=1251..1296, y=330..375 -> 46x46 px
SLOTS = {
    "avatar_links": {
        "kind": "circle",
        "bbox": (83, 302, 127, 347),
        "label": "Avatar links (GMX / WEB.DE / 1&1)",
    },
    "logo_mitte": {
        "kind": "rect",
        "bbox": (651, 291, 769, 311),
        "label": "Logo Mitte (Telekom Mail / Freenet Mail)",
    },
    "avatar_rechts": {
        "kind": "circle",
        "bbox": (1251, 330, 1296, 375),
        "label": "Avatar rechts (Darkmode / GMX Android)",
    },
}

ALLOWED_TYPES = ["png", "jpg", "jpeg", "webp", "svg"]


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_template() -> Image.Image:
    path = script_dir() / "template.png"
    if not path.exists():
        st.error("template.png wurde nicht gefunden. Bitte im selben Ordner wie app.py ablegen.")
        st.stop()
    return Image.open(path).convert("RGBA")


def read_uploaded_image(uploaded_file) -> Image.Image:
    suffix = Path(uploaded_file.name).suffix.lower()
    data = uploaded_file.getvalue()

    if suffix == ".svg":
        if cairosvg is None:
            st.error(
                "SVG-Upload benötigt das Python-Paket 'cairosvg'. Bitte in deiner Umgebung installieren: pip install cairosvg"
            )
            st.stop()
        png_data = cairosvg.svg2png(bytestring=data)
        return Image.open(io.BytesIO(png_data)).convert("RGBA")

    return Image.open(io.BytesIO(data)).convert("RGBA")


def bbox_size(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = bbox
    return (x1 - x0 + 1, y1 - y0 + 1)


def fit_cover(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """Füllt die Zielgröße vollständig (wie CSS object-fit: cover)."""
    return ImageOps.fit(image.convert("RGBA"), target_size, method=Image.LANCZOS, centering=(0.5, 0.5))


def fit_contain(image: Image.Image, target_size: tuple[int, int], padding: int = 0) -> Image.Image:
    """Skaliert proportional in die Zielbox (wie CSS object-fit: contain)."""
    target_w, target_h = target_size
    inner_w = max(1, target_w - 2 * padding)
    inner_h = max(1, target_h - 2 * padding)

    src = image.convert("RGBA")
    src.thumbnail((inner_w, inner_h), Image.LANCZOS)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    x = (target_w - src.width) // 2
    y = (target_h - src.height) // 2
    canvas.paste(src, (x, y), src)
    return canvas


def make_circle_overlay(image: Image.Image, bbox: tuple[int, int, int, int]) -> Image.Image:
    size = bbox_size(bbox)
    overlay = fit_cover(image, size)

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)

    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(overlay, (0, 0), mask)
    return result


def make_rect_overlay(image: Image.Image, bbox: tuple[int, int, int, int], padding: int = 0) -> Image.Image:
    size = bbox_size(bbox)
    return fit_contain(image, size, padding=padding)


def paste_into_bbox(base: Image.Image, overlay: Image.Image, bbox: tuple[int, int, int, int]) -> None:
    x0, y0, _, _ = bbox
    base.paste(overlay, (x0, y0), overlay)


def build_result(
    template: Image.Image,
    avatar_left: Image.Image | None,
    logo_middle: Image.Image | None,
    avatar_right: Image.Image | None,
    logo_padding: int = 0,
) -> Image.Image:
    result = template.copy()

    if avatar_left is not None:
        overlay = make_circle_overlay(avatar_left, SLOTS["avatar_links"]["bbox"])
        paste_into_bbox(result, overlay, SLOTS["avatar_links"]["bbox"])

    if logo_middle is not None:
        overlay = make_rect_overlay(logo_middle, SLOTS["logo_mitte"]["bbox"], padding=logo_padding)
        paste_into_bbox(result, overlay, SLOTS["logo_mitte"]["bbox"])

    if avatar_right is not None:
        overlay = make_circle_overlay(avatar_right, SLOTS["avatar_rechts"]["bbox"])
        paste_into_bbox(result, overlay, SLOTS["avatar_rechts"]["bbox"])

    return result


def png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def show_debug_overlay(template: Image.Image) -> Image.Image:
    preview = template.copy()
    draw = ImageDraw.Draw(preview)

    colors = {
        "circle": (0, 255, 255, 255),
        "rect": (255, 255, 0, 255),
    }

    for slot in SLOTS.values():
        bbox = slot["bbox"]
        color = colors[slot["kind"]]
        if slot["kind"] == "circle":
            draw.ellipse(bbox, outline=color, width=2)
        else:
            draw.rectangle(bbox, outline=color, width=2)
    return preview


def main() -> None:
    st.set_page_config(page_title="Template Editor", layout="wide")
    st.title("Template Editor – pixelgenaue Platzierung in template.png")
    st.caption("Unterstützt PNG, JPG, WEBP und SVG. SVG-Dateien werden beim Upload sauber in PNG umgewandelt.")

    template = load_template()

    with st.sidebar:
        st.header("Uploads")
        avatar_left_file = st.file_uploader(
            SLOTS["avatar_links"]["label"],
            type=ALLOWED_TYPES,
            key="avatar_left_file",
        )
        logo_middle_file = st.file_uploader(
            SLOTS["logo_mitte"]["label"],
            type=ALLOWED_TYPES,
            key="logo_middle_file",
        )
        avatar_right_file = st.file_uploader(
            SLOTS["avatar_rechts"]["label"],
            type=ALLOWED_TYPES,
            key="avatar_right_file",
        )

        st.header("Feintuning")
        logo_padding = st.slider(
            "Innenabstand Logo (px)",
            min_value=0,
            max_value=10,
            value=0,
            help="Nur falls ein Logo minimal mehr Luft im pinken Rechteck braucht. Standard ist 0 für maximale Flächennutzung.",
        )
        show_debug = st.checkbox("Platzhalter-Konturen anzeigen", value=False)

    avatar_left = read_uploaded_image(avatar_left_file) if avatar_left_file else None
    logo_middle = read_uploaded_image(logo_middle_file) if logo_middle_file else None
    avatar_right = read_uploaded_image(avatar_right_file) if avatar_right_file else None

    result = build_result(
        template=template,
        avatar_left=avatar_left,
        logo_middle=logo_middle,
        avatar_right=avatar_right,
        logo_padding=logo_padding,
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Template / Debug")
        st.image(show_debug_overlay(template) if show_debug else template, use_container_width=True)
        st.markdown(
            f"""**Verwendete Slots:**  
- Avatar links: `{SLOTS['avatar_links']['bbox']}` → Größe `{bbox_size(SLOTS['avatar_links']['bbox'])}` px  
- Logo Mitte: `{SLOTS['logo_mitte']['bbox']}` → Größe `{bbox_size(SLOTS['logo_mitte']['bbox'])}` px  
- Avatar rechts: `{SLOTS['avatar_rechts']['bbox']}` → Größe `{bbox_size(SLOTS['avatar_rechts']['bbox'])}` px"""
        )

    with col2:
        st.subheader("Ergebnis")
        st.image(result, use_container_width=True)
        st.download_button(
            "PNG herunterladen",
            data=png_bytes(result),
            file_name="template_composite.png",
            mime="image/png",
            use_container_width=True,
        )

    with st.expander("Wichtige Hinweise"):
        st.markdown(
            """
- **Avatare** werden per `cover` in den Kreis eingesetzt. Dadurch füllt das Motiv den kompletten Kreis ohne Verzerrung.
- **Logos** werden per `contain` in das Rechteck eingesetzt. Dadurch bleibt das Seitenverhältnis erhalten und nichts wird abgeschnitten.
- Wenn du für das mittlere Logo lieber eine harte Verzerrung auf exakt 119×21 px willst, kann ich dir alternativ noch einen `stretch`-Modus einbauen.
            """
        )


if __name__ == "__main__":
    main()
