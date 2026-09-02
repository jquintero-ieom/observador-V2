from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json

@dataclass
class AuditRecord:
    fecha_utc: str
    selected_documents: list
    situacion: str
    modelo: str
    estado: str
    fundamentos: list
    documento: str
    ubicacion: str
    cita_literal: str
    gravedad: str
    texto_observador: str
    acciones: list
    verificaciones: list
    fragmentos: list
    responsable_revision: str = ""
    observaciones_revision: str = ""
    liberacion_humana: str = "PENDIENTE"

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def build_audit_record(situacion, selected_documents, context, result, model, extra=None):
    fragments = [
        {
            "documento": f.document,
            "pagina": f.pagina,
            "score": f.score,
            "texto": f.texto,
        }
        for f in context.fragments
    ]
    record = AuditRecord(
        fecha_utc=datetime.now(timezone.utc).isoformat(),
        selected_documents=selected_documents,
        situacion=situacion,
        modelo=model,
        estado=result.get("estado", "REQUIERE_REVISION"),
        fundamentos=result.get("fundamentos", []),
        documento=result.get("documento", ""),
        ubicacion=result.get("ubicacion", ""),
        cita_literal=result.get("cita_literal", ""),
        gravedad=result.get("gravedad", ""),
        texto_observador=result.get("texto_observador", ""),
        acciones=result.get("acciones", []),
        verificaciones=result.get("verificaciones", []),
        fragmentos=fragments,
    )
    if extra:
        data = asdict(record)
        data.update(extra)
        return AuditRecord(**{k: data[k] for k in AuditRecord.__dataclass_fields__})
    return record
