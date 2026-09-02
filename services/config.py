from dataclasses import dataclass
import streamlit as st

@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    manual_file_id: str
    siee_file_id: str
    top_k: int = 6
    chunk_size: int = 1400
    chunk_overlap: int = 220


def load_settings() -> Settings:
    return Settings(
        gemini_api_key=st.secrets["GEMINI_API_KEY"],
        gemini_model=st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash"),
        manual_file_id=st.secrets.get("MANUAL_FILE_ID", ""),
        siee_file_id=st.secrets.get("SIEE_FILE_ID", ""),
        top_k=int(st.secrets.get("TOP_K", 6)),
        chunk_size=int(st.secrets.get("CHUNK_SIZE", 1400)),
        chunk_overlap=int(st.secrets.get("CHUNK_OVERLAP", 220)),
    )
