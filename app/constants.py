ZIP_HEADER = b"PK\x03\x04"
OLE_HEADER = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

ALLOWED_EXTENSIONS = {".ppt", ".pptx"}
JUNK_BASENAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}

LIBREOFFICE_CANDIDATES = ("soffice", "libreoffice")
LIBREOFFICE_FLAGS = (
    "--headless",
    "--norestore",
    "--nolockcheck",
    "--nodefault",
    "--invisible",
)

COMMAND_TIMEOUT_SECONDS = 240
