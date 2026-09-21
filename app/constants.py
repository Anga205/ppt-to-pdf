ZIP_HEADER = b"PK\x03\x04"
OLE_HEADER = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

ALLOWED_EXTENSIONS = {".ppt", ".pptx", ".pdf"}
DOCUMENT_ALLOWED_EXTENSIONS = {
    ".doc", ".docx", ".docm", ".dot", ".dotx", ".dotm",
    ".odt", ".ott", ".rtf", ".txt", ".html", ".htm",
}
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
