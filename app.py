import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw

# Feste Platzhalterkoordinaten für die Vorlage
AVATAR_POSITION = (100, 120)
AVATAR_SIZE = (180, 180)
LOGO_POSITION = (400, 100)
LOGO_SIZE = (220, 120)

# Optional: Erweiterbar für mehrere Avatare/Logos
AVATAR_CONFIGS = [
    {"position": AVATAR_POSITION, "size": AVATAR_SIZE},
]
LOGO_CONFIGS = [
    {"position": LOGO_POSITION, "size": LOGO_SIZE},
]


def load_template(path: str | None = None) -> Image.Image:
    """Lädt das statische Hintergrundbild unverändert."""
    script_dir = Path(__file__).resolve().parent
    default_path = script_dir / "template.png"
    alt_path = Path.cwd() / "template.png"

    if path is None:
        path = default_path
        if not path.exists() and alt_path.exists():
            path = alt_path

    template_path = Path(path)
    if not template_path.exists():
        raise FileNotFoundError(
            "Die Template-Datei wurde nicht gefunden. Erwartete Orte:\n"
            f"- {default_path}\n"
            f"- {alt_path}"
        )
    template = Image.open(template_path).convert("RGBA")
    return template


def create_circular_avatar(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Erzeugt ein kreisförmiges Avatarbild mit exakter Zielgröße."""
    target_width, target_height = size
    image = image.convert("RGBA")
    image = image.resize((target_width, target_height), Image.LANCZOS)

    mask = Image.new("L", (target_width, target_height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([(0, 0), (target_width, target_height)], fill=255)

    avatar = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    avatar.paste(image, (0, 0), mask=mask)
    return avatar


def create_logo(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Skaliert das Logo proportional und zentriert es in einer festen Zielgröße."""
    max_width, max_height = size
    image = image.convert("RGBA")

    src_width, src_height = image.size
    ratio = min(max_width / src_width, max_height / src_height)
    target_width = int(src_width * ratio)
    target_height = int(src_height * ratio)

    logo_resized = image.resize((target_width, target_height), Image.LANCZOS)
    logo = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
    offset_x = (max_width - target_width) // 2
    offset_y = (max_height - target_height) // 2
    logo.paste(logo_resized, (offset_x, offset_y), mask=logo_resized)
    return logo


def place_image(base: Image.Image, overlay: Image.Image, position: tuple[int, int]) -> None:
    """Fügt das Overlay-Bild pixelgenau in das Basisbild ein."""
    base.paste(overlay, position, mask=overlay)


def image_to_bytes(image: Image.Image) -> bytes:
    """Gibt das Bild als PNG-Bytes zurück für den Download."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_composite(
    template: Image.Image,
    avatar_image: Image.Image | None,
    logo_image: Image.Image | None,
) -> Image.Image:
    """Erzeugt das finale Bild basierend auf dem statischen Template."""
    result = template.copy()

    if avatar_image is not None:
        avatar_overlay = create_circular_avatar(avatar_image, AVATAR_SIZE)
        place_image(result, avatar_overlay, AVATAR_POSITION)

    if logo_image is not None:
        logo_overlay = create_logo(logo_image, LOGO_SIZE)
        place_image(result, logo_overlay, LOGO_POSITION)

    return result


def main() -> None:
    st.set_page_config(page_title="Pixel-perfect Template Editor", layout="wide")
    st.title("Pixel-perfekter Bild-Editor mit statischem Template")
    st.write(
        "Dieses Tool verwendet `template.png` als unverändertes Hintergrundbild und ersetzt nur definierte Bereiche."
    )

    try:
        template_image = load_template()
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    with st.sidebar:
        st.header("Uploads")
        avatar_file = st.file_uploader("Avatar hochladen", type=["png", "jpg", "jpeg"])
        logo_file = st.file_uploader("Logo hochladen", type=["png", "jpg", "jpeg"])
        st.markdown("---")
        st.caption("Nur die definierten Platzhalter werden dynamisch ersetzt.")

    avatar_image = Image.open(avatar_file) if avatar_file is not None else None
    logo_image = Image.open(logo_file) if logo_file is not None else None

    final_image = render_composite(template_image, avatar_image, logo_image)

    st.subheader("Vorschau")
    st.image(final_image, use_column_width=False)

    png_bytes = image_to_bytes(final_image)
    st.download_button(
        label="Download as PNG",
        data=png_bytes,
        file_name="output.png",
        mime="image/png",
    )

    st.markdown("---")
    st.write("Konfiguration der festen Platzhalter:")
    st.code(
        f"AVATAR_POSITION = {AVATAR_POSITION}\nAVATAR_SIZE = {AVATAR_SIZE}\nLOGO_POSITION = {LOGO_POSITION}\nLOGO_SIZE = {LOGO_SIZE}",
        language="python",
    )


if __name__ == "__main__":
    main()
