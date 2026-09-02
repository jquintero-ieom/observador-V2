from functools import lru_cache
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _credentials():
    # Recomendado: guardar el objeto de credenciales en secrets.toml como una tabla.
    info = dict(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


@lru_cache(maxsize=1)
def _service():
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


class DriveRepository:
    def __init__(self, settings):
        self.settings = settings
        self.service = _service()

    def get_metadata(self, file_id: str) -> dict:
        return self.service.files().get(
            fileId=file_id,
            fields="id,name,mimeType,size,modifiedTime,md5Checksum,webViewLink",
            supportsAllDrives=True,
        ).execute()

    def download_pdf(self, file_id: str) -> bytes:
        request = self.service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True,
        )
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buffer.getvalue()
        if not data.startswith(b"%PDF"):
            raise ValueError("Drive respondió con contenido que no parece ser un PDF válido.")
        return data
