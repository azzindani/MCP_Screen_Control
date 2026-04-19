"""Screenshot capture and image preprocessing."""
import base64
import shutil
from pathlib import Path

import mss
import mss.tools
from PIL import Image

from _sc_helpers import MAX_IMAGE_WIDTH, SCREEN_CURRENT, SCREEN_PREV, TMP_DIR
from shared.platform_utils import get_max_image_width


def capture_screen() -> dict:
    """Grab full screen → save to tmp/screen_current.png → return metadata."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    save_prev_screen()

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        shot = sct.grab(monitor)
        mss.tools.to_png(shot.rgb, shot.size, output=str(SCREEN_CURRENT))
        w, h = shot.size

    return {
        "success": True,
        "path": str(SCREEN_CURRENT),
        "width": w,
        "height": h,
        "token_estimate": 20,
    }


def preprocess_image(path: str | Path, max_width: int | None = None) -> str:
    """Resize image to max_width and return base64-encoded PNG string."""
    if max_width is None:
        max_width = get_max_image_width()

    img = Image.open(path).convert("RGB")
    w, h = img.size
    if w > max_width:
        ratio = max_width / w
        img = img.resize((max_width, int(h * ratio)), Image.LANCZOS)

    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def preprocess_crop(path: str | Path, quadrant: int, max_width: int | None = None) -> str:
    """Crop image to one of four quadrants (0=TL,1=TR,2=BL,3=BR) and preprocess."""
    if max_width is None:
        max_width = get_max_image_width()

    img = Image.open(path).convert("RGB")
    w, h = img.size
    hw, hh = w // 2, h // 2
    boxes = {
        0: (0, 0, hw, hh),
        1: (hw, 0, w, hh),
        2: (0, hh, hw, h),
        3: (hw, hh, w, h),
    }
    cropped = img.crop(boxes.get(quadrant, boxes[0]))
    import io

    buf = io.BytesIO()
    cropped.resize(
        (min(max_width, cropped.width), int(cropped.height * min(max_width, cropped.width) / cropped.width)),
        Image.LANCZOS,
    ).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def save_prev_screen() -> None:
    """Copy current screenshot to tmp/screen_prev.png before new capture."""
    if SCREEN_CURRENT.exists():
        shutil.copy2(SCREEN_CURRENT, SCREEN_PREV)
