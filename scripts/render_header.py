"""Export the editable SVG header as a looping GIF.

Install the optional asset tools with: python -m pip install Pillow resvg-py
Then run: python scripts/render_header.py
The SVG is also the static alternative for readers who prefer reduced motion.
"""

from io import BytesIO
import math
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image
import resvg_py


ASSETS = Path(__file__).resolve().parents[1] / "assets"
FRAMES = 72
FRAME_MS = 90


def render_header():
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.fromstring((ASSETS / "header.svg").read_text(encoding="utf-8"))
    ribbons = next(node for node in root.iter() if node.get("id") == "ribbons")
    accent = next(node for node in root.iter() if node.get("id") == "accent")

    # Limit font scanning on Windows; the renderer uses system fonts elsewhere.
    font_paths = [Path("C:/Windows/Fonts") / name for name in
                  ("segoeui.ttf", "segoeuib.ttf", "consola.ttf")]
    font_options = {}
    if all(path.is_file() for path in font_paths):
        font_options = {"skip_system_fonts": True,
                        "font_files": [str(path) for path in font_paths]}

    frames = []
    palette = None
    for index in range(FRAMES):
        phase = math.tau * index / FRAMES
        ribbons.set("transform", f"translate({22 * math.sin(phase):.3f} 0)")
        accent.set("transform", f"translate({246 * (1 - math.cos(phase)):.3f} 0)")
        png = resvg_py.svg_to_bytes(
            svg_string=ET.tostring(root, encoding="unicode"),
            background="#131315", **font_options,
        )
        with Image.open(BytesIO(png)) as rendered:
            frame = rendered.convert("RGB")
        if palette is None:
            palette = frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
        frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))

    destination = ASSETS / "header.gif"
    frames[0].save(destination, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True, disposal=1)
    print(f"Wrote {destination.name}: {FRAMES} frames, "
          f"{FRAMES * FRAME_MS / 1000:.2f}s loop, "
          f"{destination.stat().st_size / 1024:.0f} KiB")


if __name__ == "__main__":
    render_header()
