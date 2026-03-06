import logging
import platform
from pathlib import Path

from app.utils.file_ops import file_has_content


def _is_windows_platform():
    return platform.system().lower() == "windows"


def _import_win32_client():
    try:
        import win32com.client  # type: ignore

        return win32com.client
    except Exception as exc:
        logging.error("PowerPoint COM unavailable: %s", exc)
        return None


def _close_presentation(presentation):
    try:
        if presentation is not None:
            presentation.Close()
    except Exception:
        pass


def _quit_powerpoint_app(app_obj):
    try:
        if app_obj is not None:
            app_obj.Quit()
    except Exception:
        pass


def convert_with_powerpoint_com(input_path: Path, pdf_path: Path):
    if not _is_windows_platform():
        logging.info("Skipping PowerPoint COM conversion on non-Windows platform")
        return False

    win32_client = _import_win32_client()
    if win32_client is None:
        return False

    app_obj = None
    presentation = None
    try:
        app_obj = win32_client.Dispatch("PowerPoint.Application")
        app_obj.Visible = 1
        app_obj.DisplayAlerts = 0
        presentation = app_obj.Presentations.Open(str(input_path), False, False, False)
        presentation.SaveAs(str(pdf_path), FileFormat=32)
        if file_has_content(pdf_path):
            logging.info("PowerPoint COM conversion succeeded")
            return True
        logging.error("PowerPoint COM ran but output PDF was not created")
        return False
    except Exception as exc:
        logging.error("PowerPoint COM conversion failed: %s", exc)
        return False
    finally:
        _close_presentation(presentation)
        _quit_powerpoint_app(app_obj)
