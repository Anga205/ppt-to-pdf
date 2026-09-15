"""Stage 9: Rendering engine wrapper with isolation."""
import logging
from pathlib import Path

from app.services.libreoffice_converter import convert_with_libreoffice, convert_with_libreoffice_generic_only
from app.services.powerpoint_com import convert_with_powerpoint_com
from app.services.unoconv_converter import convert_with_unoconv


def try_engine(engine_name: str, input_path: Path, pdf_path: Path) -> bool:
    try:
        if engine_name == "libreoffice_impress":
            return convert_with_libreoffice(input_path, pdf_path)
        elif engine_name == "libreoffice_generic":
            return convert_with_libreoffice_generic_only(input_path, pdf_path)
        elif engine_name == "unoconv":
            return convert_with_unoconv(input_path, pdf_path)
        elif engine_name == "powerpoint_com":
            return convert_with_powerpoint_com(input_path, pdf_path)
        else:
            return False
    except Exception as exc:
        logging.error("Engine %s crashed: %s", engine_name, exc)
        return False
