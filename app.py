import base64
import json
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw
import streamlit.components.v1 as components


# ============================================================================
# Exakt vermessene Platzhalter aus dem aktuellen template.png
# ============================================================================

SLOTS = {
    "avatar_links": {
        "kind": "circle",
        "bbox": (83, 301, 127, 346),
        "label": "Avatar links (GMX / WEB.DE / 1&1)",
    },
    "logo_mitte": {
        "kind": "rect",
        "bbox": (665, 290, 786, 311),
        "label": "Logo Mitte (Telekom Mail / Freenet Mail)",
    },
    "avatar_rechts": {
        "kind": "circle",
        "bbox": (1219, 333, 1264, 377),
        "label": "Avatar rechts (Darkmode / GMX Android)",
    },
}

# Ohne CairoSVG:
# SVGs werden nicht serverseitig in Python konvertiert,
# sondern direkt im Browser gerendert.
ALLOWED_TYPES = ["svg", "png", "jpg", "jpeg", "webp"]


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def template_path() -> Path:
    return script_dir() / "template.png"


def load_template_size() -> tuple[int, int]:
    path = template_path()

    if not path.exists():
        st.error("template.png wurde nicht gefunden. Bitte im selben Ordner wie app.py ablegen.")
        st.stop()

    with Image.open(path) as img:
        return img.size


def load_template_as_data_url() -> str:
    path = template_path()

    if not path.exists():
        st.error("template.png wurde nicht gefunden. Bitte im selben Ordner wie app.py ablegen.")
        st.stop()

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def bbox_size(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = bbox
    return x1 - x0 + 1, y1 - y0 + 1


def file_to_data_url(uploaded_file) -> str | None:
    """
    Gibt eine Data-URL zurück.

    SVG wird bewusst NICHT serverseitig konvertiert,
    sondern als image/svg+xml direkt an den Browser übergeben.
    """
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower().replace(".", "")
    raw = uploaded_file.getvalue()

    if suffix == "svg":
        mime = "image/svg+xml"
    elif suffix in ("jpg", "jpeg"):
        mime = "image/jpeg"
    elif suffix == "webp":
        mime = "image/webp"
    else:
        mime = "image/png"

    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def make_debug_overlay_data_url() -> str:
    """
    Erzeugt eine PNG-Vorschau mit pinken Platzhalterrahmen.
    Das nutzt weiterhin Pillow, aber nur für template.png.
    SVG-Konvertierung ist nicht nötig.
    """
    path = template_path()
    img = Image.open(path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    for slot in SLOTS.values():
        bbox = slot["bbox"]

        if slot["kind"] == "circle":
            draw.ellipse(bbox, outline=(255, 0, 255, 255), width=3)
        else:
            draw.rectangle(bbox, outline=(255, 0, 255, 255), width=3)

    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_canvas_component(
    template_data_url: str,
    uploads: dict,
    controls: dict,
    template_width: int,
    template_height: int,
) -> str:
    """
    Baut eine HTML/JS-Komponente, die template.png plus die hochgeladenen Grafiken
    direkt im Browser auf ein Canvas rendert.

    Vorteil:
    - kein CairoSVG
    - keine lokale Installation
    - SVGs bleiben im Browser sauber skalierbar
    """

    payload = {
        "template": template_data_url,
        "templateWidth": template_width,
        "templateHeight": template_height,
        "slots": SLOTS,
        "uploads": uploads,
        "controls": controls,
    }

    payload_json = json.dumps(payload)

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #262730;
    }}

    .wrap {{
      width: 100%;
    }}

    .canvas-wrap {{
      width: 100%;
      border: 1px solid #e6e6e6;
      border-radius: 10px;
      overflow: hidden;
      background: #f7f7f7;
    }}

    canvas {{
      display: block;
      width: 100%;
      height: auto;
    }}

    .actions {{
      display: flex;
      gap: 10px;
      margin-top: 12px;
      align-items: center;
      flex-wrap: wrap;
    }}

    button {{
      border: 0;
      border-radius: 8px;
      background: #ff4b4b;
      color: #fff;
      padding: 0.65rem 0.9rem;
      font-weight: 600;
      cursor: pointer;
    }}

    button:hover {{
      background: #e43f3f;
    }}

    .hint {{
      font-size: 13px;
      color: #666;
    }}
  </style>
</head>

<body>
  <div class="wrap">
    <div class="canvas-wrap">
      <canvas id="resultCanvas"></canvas>
    </div>

    <div class="actions">
      <button id="downloadBtn">PNG herunterladen</button>
      <span class="hint">SVGs werden direkt im Browser gerendert – ohne CairoSVG.</span>
    </div>
  </div>

<script>
const DATA = {payload_json};

const canvas = document.getElementById("resultCanvas");
const ctx = canvas.getContext("2d");

canvas.width = DATA.templateWidth;
canvas.height = DATA.templateHeight;

function loadImage(src) {{
  return new Promise((resolve, reject) => {{
    if (!src) {{
      resolve(null);
      return;
    }}

    const img = new Image();

    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  }});
}}

function bboxSize(bbox) {{
  const [x0, y0, x1, y1] = bbox;

  return {{
    w: x1 - x0 + 1,
    h: y1 - y0 + 1
  }};
}}

function drawCover(img, bbox, scalePx, offsetX, offsetY, circular) {{
  if (!img) return;

  const [x0, y0] = bbox;
  const size = bboxSize(bbox);

  const baseScale = Math.max(
    size.w / img.naturalWidth,
    size.h / img.naturalHeight
  );

  let drawW = img.naturalWidth * baseScale + 2 * scalePx;
  let drawH = img.naturalHeight * baseScale + 2 * scalePx;

  drawW = Math.max(1, drawW);
  drawH = Math.max(1, drawH);

  const dx = x0 + (size.w - drawW) / 2 + offsetX;
  const dy = y0 + (size.h - drawH) / 2 + offsetY;

  ctx.save();

  if (circular) {{
    ctx.beginPath();
    ctx.ellipse(
      x0 + size.w / 2,
      y0 + size.h / 2,
      size.w / 2,
      size.h / 2,
      0,
      0,
      Math.PI * 2
    );
    ctx.clip();
  }} else {{
    ctx.beginPath();
    ctx.rect(x0, y0, size.w, size.h);
    ctx.clip();
  }}

  ctx.drawImage(img, dx, dy, drawW, drawH);

  ctx.restore();
}}

function drawContain(img, bbox, padding, scalePx, offsetX, offsetY) {{
  if (!img) return;

  const [x0, y0] = bbox;
  const size = bboxSize(bbox);

  const innerW = Math.max(1, size.w - 2 * padding);
  const innerH = Math.max(1, size.h - 2 * padding);

  const baseScale = Math.min(
    innerW / img.naturalWidth,
    innerH / img.naturalHeight
  );

  let drawW = img.naturalWidth * baseScale + 2 * scalePx;
  let drawH = img.naturalHeight * baseScale + 2 * scalePx;

  drawW = Math.max(1, drawW);
  drawH = Math.max(1, drawH);

  const dx = x0 + (size.w - drawW) / 2 + offsetX;
  const dy = y0 + (size.h - drawH) / 2 + offsetY;

  ctx.save();

  ctx.beginPath();
  ctx.rect(x0, y0, size.w, size.h);
  ctx.clip();

  ctx.drawImage(img, dx, dy, drawW, drawH);

  ctx.restore();
}}

async function render() {{
  const templateImg = await loadImage(DATA.template);
  const avatarLeft = await loadImage(DATA.uploads.avatar_links);
  const logoMiddle = await loadImage(DATA.uploads.logo_mitte);
  const avatarRight = await loadImage(DATA.uploads.avatar_rechts);

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.drawImage(templateImg, 0, 0, canvas.width, canvas.height);

  drawCover(
    avatarLeft,
    DATA.slots.avatar_links.bbox,
    DATA.controls.avatar_links.scale,
    DATA.controls.avatar_links.offsetX,
    DATA.controls.avatar_links.offsetY,
    true
  );

  drawContain(
    logoMiddle,
    DATA.slots.logo_mitte.bbox,
    DATA.controls.logo_mitte.padding,
    DATA.controls.logo_mitte.scale,
    DATA.controls.logo_mitte.offsetX,
    DATA.controls.logo_mitte.offsetY
  );

  drawCover(
    avatarRight,
    DATA.slots.avatar_rechts.bbox,
    DATA.controls.avatar_rechts.scale,
    DATA.controls.avatar_rechts.offsetX,
    DATA.controls.avatar_rechts.offsetY,
    true
  );
}}

render().catch(err => {{
  console.error(err);
  alert("Beim Rendern ist ein Fehler aufgetreten. Bitte prüfe, ob die SVG-Datei valide ist.");
}});

document.getElementById("downloadBtn").addEventListener("click", () => {{
  const link = document.createElement("a");

  link.download = "template_composite.png";
  link.href = canvas.toDataURL("image/png");

  link.click();
}});
</script>
</body>
</html>
"""


def main() -> None:
    st.set_page_config(page_title="Template Editor", layout="wide")

    st.title("Template Editor – SVG-Upload ohne CairoSVG")
    st.caption(
        "SVG-Dateien werden direkt im Browser gerendert. "
        "Du musst lokal nichts zusätzlich installieren."
    )

    template_width, template_height = load_template_size()

    col1, col2 = st.columns([1, 1.4], gap="large")

    with col1:
        st.subheader("Uploads")

        avatar_left_file = st.file_uploader(
            SLOTS["avatar_links"]["label"],
            type=ALLOWED_TYPES,
            key="avatar_left",
        )

        st.markdown("#### Avatar links feinjustieren")

        avatar_left_scale = st.slider(
            "Avatar links Größe proportional ändern (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
            help="Negative Werte verkleinern die Grafik, positive Werte vergrößern sie proportional.",
        )

        avatar_left_x = st.slider(
            "Avatar links horizontal verschieben (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
        )

        avatar_left_y = st.slider(
            "Avatar links vertikal verschieben (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
        )

        st.divider()

        logo_middle_file = st.file_uploader(
            SLOTS["logo_mitte"]["label"],
            type=ALLOWED_TYPES,
            key="logo_middle",
        )

        st.markdown("#### Logo Mitte feinjustieren")

        logo_padding = st.slider(
            "Innenabstand Logo Mitte (px)",
            min_value=-5,
            max_value=20,
            value=0,
            step=1,
            help="Negative Werte vergrößern das Logo leicht, positive Werte geben mehr Innenabstand.",
        )

        logo_middle_scale = st.slider(
            "Logo Mitte zusätzlich proportional ändern (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
            help="Feinjustierung zusätzlich zum Innenabstand.",
        )

        logo_middle_x = st.slider(
            "Logo Mitte horizontal verschieben (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
        )

        logo_middle_y = st.slider(
            "Logo Mitte vertikal verschieben (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
        )

        st.divider()

        avatar_right_file = st.file_uploader(
            SLOTS["avatar_rechts"]["label"],
            type=ALLOWED_TYPES,
            key="avatar_right",
        )

        st.markdown("#### Avatar rechts feinjustieren")

        avatar_right_scale = st.slider(
            "Avatar rechts Größe proportional ändern (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
            help="Negative Werte verkleinern die Grafik, positive Werte vergrößern sie proportional.",
        )

        avatar_right_x = st.slider(
            "Avatar rechts horizontal verschieben (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
        )

        avatar_right_y = st.slider(
            "Avatar rechts vertikal verschieben (px)",
            min_value=-5,
            max_value=5,
            value=0,
            step=1,
        )

        st.divider()

        show_debug = st.checkbox("Nur Platzhalter anzeigen", value=False)

        st.markdown("### Platzhaltergrößen")

        st.markdown(
            f"""
- **Avatar links:** `{SLOTS["avatar_links"]["bbox"]}` → Größe `{bbox_size(SLOTS["avatar_links"]["bbox"])} px`
- **Logo Mitte:** `{SLOTS["logo_mitte"]["bbox"]}` → Größe `{bbox_size(SLOTS["logo_mitte"]["bbox"])} px`
- **Avatar rechts:** `{SLOTS["avatar_rechts"]["bbox"]}` → Größe `{bbox_size(SLOTS["avatar_rechts"]["bbox"])} px`
"""
        )

    uploads = {
        "avatar_links": file_to_data_url(avatar_left_file),
        "logo_mitte": file_to_data_url(logo_middle_file),
        "avatar_rechts": file_to_data_url(avatar_right_file),
    }

    controls = {
        "avatar_links": {
            "scale": avatar_left_scale,
            "offsetX": avatar_left_x,
            "offsetY": avatar_left_y,
        },
        "logo_mitte": {
            "padding": logo_padding,
            "scale": logo_middle_scale,
            "offsetX": logo_middle_x,
            "offsetY": logo_middle_y,
        },
        "avatar_rechts": {
            "scale": avatar_right_scale,
            "offsetX": avatar_right_x,
            "offsetY": avatar_right_y,
        },
    }

    if show_debug:
        template_data_url = make_debug_overlay_data_url()
        uploads_for_component = {
            "avatar_links": None,
            "logo_mitte": None,
            "avatar_rechts": None,
        }
    else:
        template_data_url = load_template_as_data_url()
        uploads_for_component = uploads

    with col2:
        st.subheader("Ergebnis")

        component_html = build_canvas_component(
            template_data_url=template_data_url,
            uploads=uploads_for_component,
            controls=controls,
            template_width=template_width,
            template_height=template_height,
        )

        component_height = min(900, max(520, int(template_height * 0.72)))

        components.html(
            component_html,
            height=component_height,
            scrolling=False,
        )

        with st.expander("Wichtige Hinweise"):
            st.markdown(
                """
- **Kein CairoSVG nötig:** SVGs werden nicht in Python konvertiert, sondern direkt im Browser auf ein Canvas gerendert.
- **Download:** Der Download-Button befindet sich direkt unter der Vorschau und erzeugt clientseitig eine PNG-Datei.
- **Avatare:** Avatare werden per `cover` in den Kreis eingesetzt und kreisförmig maskiert.
- **Logo Mitte:** Das Logo wird per `contain` in das Rechteck eingesetzt. Das Seitenverhältnis bleibt erhalten.
- **Feinjustierung:** Größe, X- und Y-Verschiebung können jeweils im Bereich `-5 bis +5 px` angepasst werden.
- **Innenabstand Logo:** Beim mittleren Logo kann der Innenabstand zusätzlich von `-5 bis 20 px` angepasst werden.
- **SVG-Dateien:** Am stabilsten sind SVGs, bei denen Formen/Pfade direkt eingebettet sind. Externe Bild- oder Font-Referenzen innerhalb der SVG können je nach Browser blockiert oder anders dargestellt werden.
"""
            )


if __name__ == "__main__":
    main()
