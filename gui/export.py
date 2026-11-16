"""Image export of the display (File menu): a PNG of the current frame and a short animated GIF.

The GIF is rendered offscreen at a fixed time step, so it never stutters: for each of its frames the canvas's
animation is stepped `60 / fps` times (the timer is paused meanwhile) and the widget is drawn into a QImage, which
is scaled to `width` px.  GIF writing needs Pillow, which is optional and not in requirements.txt
(`pip install Pillow`); it is imported inside `export_gif`, and the menu explains how to install it when missing.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

STEPS_PER_SECOND = 60


def grab_frame(canvas) -> QImage:
    """The canvas as it is drawn now (any renderer)."""
    img = QImage(max(1, canvas.width()), max(1, canvas.height()), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    canvas.render(img)
    return img


def save_frame(canvas, path: str) -> bool:
    return grab_frame(canvas).save(path, "PNG")


def gif_frames(canvas, seconds: float = 5.0, fps: int = 15, width: int = 480) -> list:
    """QImages (RGB888, `width` px wide) of the next `seconds` of the show, stepped at a fixed rate."""
    steps = max(1, round(STEPS_PER_SECOND / fps))
    height = max(1, round(width * canvas.height() / max(1, canvas.width())))
    running = canvas.timer.isActive()
    canvas.timer.stop()
    frames = []
    try:
        for _ in range(int(seconds * fps)):
            for _ in range(steps):
                canvas.update_animation()
            img = grab_frame(canvas).scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            frames.append(img.convertToFormat(QImage.Format.Format_RGB888))
    finally:
        if running:
            canvas.timer.start()
    return frames


def export_gif(canvas, path: str, seconds: float = 5.0, fps: int = 15, width: int = 480) -> int:
    """Write an animated GIF; returns the number of frames.  Raises ImportError without Pillow."""
    from PIL import Image  # optional dependency: pip install Pillow

    pics = []
    for img in gif_frames(canvas, seconds, fps, width):
        w, h, bpl = img.width(), img.height(), img.bytesPerLine()
        data = bytes(img.constBits().asstring(img.sizeInBytes()))
        pics.append(Image.frombuffer("RGB", (w, h), data, "raw", "RGB", bpl, 1).copy())
    if not pics:
        return 0
    pics[0].save(path, save_all=True, append_images=pics[1:], duration=round(1000 / fps), loop=0, optimize=False)
    return len(pics)


# --- menu actions ---------------------------------------------------------------------------------------------
def save_frame_dialog(parent, canvas) -> None:
    path, _ = QFileDialog.getSaveFileName(parent, "Save Frame as PNG", "fireworks.png", "PNG image (*.png)")
    if path:
        if not path.lower().endswith(".png"):
            path += ".png"
        if not save_frame(canvas, path):
            QMessageBox.warning(parent, "Save Frame", f"Could not write {path}.")


def export_gif_dialog(parent, canvas) -> None:
    try:
        import PIL  # noqa: F401
    except ImportError:
        QMessageBox.information(parent, "Export GIF",
                                "GIF export needs the Pillow package.\n\nInstall it with:\n    pip install Pillow")
        return
    path, _ = QFileDialog.getSaveFileName(parent, "Export GIF", "fireworks.gif", "GIF animation (*.gif)")
    if not path:
        return
    if not path.lower().endswith(".gif"):
        path += ".gif"
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        n = export_gif(canvas, path)
    except OSError as e:
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(parent, "Export GIF", f"Could not write {path}:\n{e}")
        return
    QApplication.restoreOverrideCursor()
    if hasattr(parent, "statusBar"):
        parent.statusBar().showMessage(f"Saved {n} frames to {path}", 5000)
