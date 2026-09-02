from dataclasses import dataclass
from io import BytesIO
from pypdf import PdfReader
import hashlib
import re

@dataclass
class PdfDocument:
    name: str
    file_id: str
    modified_time: str
    checksum: str
    text: str
    pages: list


def normalize(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_document(name: str, file_id: str, metadata: dict, pdf_bytes: bytes) -> PdfDocument:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = normalize(raw)
        if text:
            pages.append({"pagina": number, "texto": text})

    full_text = "\n\n".join(
        f"[PÁGINA {p['pagina']}]\n{p['texto']}" for p in pages
    )
    checksum = metadata.get("md5Checksum") or hashlib.sha256(pdf_bytes).hexdigest()
    return PdfDocument(
        name=name,
        file_id=file_id,
        modified_time=metadata.get("modifiedTime", ""),
        checksum=checksum,
        text=full_text,
        pages=pages,
    )
