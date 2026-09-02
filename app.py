import streamlit as st
import streamlit.components.v1 as components
import json
from services.config import load_settings
from services.drive import DriveRepository
from services.pdf_service import extract_pdf_document
from services.rag import build_relevant_context
from services.gemini_service import analyze_case
from services.audit import build_audit_record
from dataclasses import asdict

def copiar_portapapeles(texto, key, etiqueta="📋 Copiar"):
    """Botón HTML/JS para copiar texto directamente al portapapeles."""
    texto = str(texto or "")
    safe_key = "".join(ch if ch.isalnum() else "_" for ch in str(key))
    datos_js = json.dumps(texto, ensure_ascii=False).replace("</", "<\\/")

    components.html(
        f"""
        <div style="font-family:sans-serif;padding:2px 0 8px 0;">
          <button id="btn-{safe_key}"
            style="padding:8px 14px;border:1px solid #b8c0ca;border-radius:7px;
                   background:white;cursor:pointer;font-weight:600;color:#243447;">
            {etiqueta}
          </button>
          <span id="estado-{safe_key}" style="font-size:12px;color:#555;margin-left:10px;"></span>
        </div>
        <script>
        const texto_{safe_key} = {datos_js};
        const btn_{safe_key} = document.getElementById('btn-{safe_key}');
        const estado_{safe_key} = document.getElementById('estado-{safe_key}');

        async function copiar_{safe_key}() {{
          try {{
            if (navigator.clipboard && window.isSecureContext) {{
              await navigator.clipboard.writeText(texto_{safe_key});
            }} else {{
              const area = document.createElement('textarea');
              area.value = texto_{safe_key};
              area.style.position = 'fixed';
              area.style.left = '-9999px';
              document.body.appendChild(area);
              area.focus();
              area.select();
              document.execCommand('copy');
              area.remove();
            }}
            estado_{safe_key}.textContent = '✓ Copiado al portapapeles';
          }} catch (e) {{
            estado_{safe_key}.textContent = 'No fue posible copiar automáticamente';
          }}
        }}
        btn_{safe_key}.addEventListener('click', copiar_{safe_key});
        </script>
        """,
        height=48,
        scrolling=False,
    )


def copiar_evidencia(documento, ubicacion, cita, key):
    """Muestra botones para copiar evidencia normativa."""
    documento = str(documento or "Documento no determinado")
    ubicacion = str(ubicacion or "Ubicación no determinada")
    cita = str(cita or "NO SE ENCONTRÓ CITA LITERAL VERIFICABLE.")

    texto_ubicacion = f"{documento} — {ubicacion}"
    texto_completo = (
        f"De acuerdo con el {documento}, {ubicacion}, se establece lo siguiente: "
        f'"{cita}"'
    )

    copiar_portapapeles(cita, f"{key}_cita", "📋 Copiar cita")
    copiar_portapapeles(texto_ubicacion, f"{key}_ubicacion", "📍 Copiar ubicación")
    copiar_portapapeles(texto_completo, f"{key}_completo", "📝 Copiar al Observador")


st.set_page_config(
    page_title="Sistema Observador",
    page_icon="🧑🏽‍💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

settings = load_settings()

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "audit_record" not in st.session_state:
    st.session_state.audit_record = None

st.title(" 🧑🏽‍💻Sistema Observador")
st.caption("Análisis asistido por IA con trazabilidad, citas verificables y revisión humana")

##with st.sidebar:
    ##st.header("⚙️ Configuración")
    ##st.write(f"**Modelo:** `{settings.gemini_model}`")
    ##st.write(f"**Manual:** `{settings.manual_file_id[:10]}…`" if settings.manual_file_id else "**Manual:** no configurado")
    ##st.write(f"**SIEE:** `{settings.siee_file_id[:10]}…`" if settings.siee_file_id else "**SIEE:** no configurado")
    ##if st.button("🔄 Limpiar caché de documentos", use_container_width=True):
   ##     st.cache_data.clear()
  ##      st.success("Caché limpiado. Vuelve a ejecutar el análisis.")
##
col_left, col_right = st.columns([0.95, 1.05])

with col_left:
    st.subheader("📥 Registro de la situación")

    documentos = st.multiselect(
        "Documentos a contrastar",
        ["Manual de Convivencia", "SIEE"],
        default=["Manual de Convivencia"],
    )

    situacion = st.text_area(
        "Describa la situación presentada",
        height=260,
        placeholder=(
            "Describa únicamente los hechos observables, contexto, grado y demás "
            "información necesaria para el análisis. Evite incluir datos sensibles "
            "innecesarios."
        ),
    )

    analizar = st.button("🚀 Analizar caso", type="primary", use_container_width=True)

with col_right:
    st.subheader("🔍 Resultado")

    if analizar:
        if not situacion.strip():
            st.error("Debe describir la situación.")
            st.stop()
        if not documentos:
            st.error("Seleccione al menos un documento.")
            st.stop()

        repository = DriveRepository(settings)
        documents = []
        errors = []

        with st.spinner("Accediendo a Google Drive y verificando documentos…"):
            selected = []
            if "Manual de Convivencia" in documentos:
                selected.append(("Manual de Convivencia", settings.manual_file_id))
            if "SIEE" in documentos:
                selected.append(("SIEE", settings.siee_file_id))

            for name, file_id in selected:
                try:
                    metadata = repository.get_metadata(file_id)
                    pdf_bytes = repository.download_pdf(file_id)
                    document = extract_pdf_document(name, file_id, metadata, pdf_bytes)
                    if not document.text.strip():
                        raise ValueError(
                            "El PDF no contiene texto extraíble. Si es un PDF escaneado, "
                            "debe habilitarse un flujo OCR."
                        )
                    documents.append(document)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")

        if errors:
            for error in errors:
                st.error(error)

        if not documents:
            st.warning("No fue posible cargar ningún documento válido.")
            st.stop()

        with st.spinner("Buscando únicamente los fragmentos normativos relevantes…"):
            context = build_relevant_context(situacion, documents, settings)

        if not context.fragments:
            st.warning(
                "No se encontró un fragmento normativo suficientemente relevante. "
                "El sistema no generará una norma inventada."
            )
            st.session_state.analysis_result = None
            st.stop()

        with st.spinner("Generando análisis estructurado con Gemini…"):
            try:
                result = analyze_case(situacion, context, settings)
                st.session_state.analysis_result = result
                st.session_state.audit_record = build_audit_record(
                    situacion=situacion,
                    selected_documents=[d.name for d in documents],
                    context=context,
                    result=result,
                    model=settings.gemini_model,
                )
            except Exception as exc:
                st.error(f"Error al consultar Gemini: {exc}")
                st.stop()

    result = st.session_state.analysis_result
    audit = st.session_state.audit_record

    if result:
        status = result.get("estado", "REQUIERE_REVISION")
        if status == "FUNDAMENTO_VERIFICABLE":
            st.success("Fundamento normativo localizado y presentado para revisión humana.")
        else:
            st.warning("No se obtuvo un fundamento normativo plenamente verificable.")

        st.markdown("### 1. Fundamento normativo")
        fundamentos = result.get("fundamentos", [])
        if fundamentos:
            for i, fundamento in enumerate(fundamentos, start=1):
                st.markdown(f"**Fundamento {i} — {fundamento.get('documento', 'Documento no determinado')}**")
                ubicacion = fundamento.get('ubicacion', 'No determinada')
                cita = fundamento.get("cita_literal", "NO SE ENCONTRÓ CITA LITERAL VERIFICABLE.")
                documento = fundamento.get('documento', 'Documento no determinado')
                st.write(f"**Ubicación:** {ubicacion}")
                st.write(f"**Relación con la conducta:** {fundamento.get('relacion_conducta', 'No determinada')}")
                st.write("**Cita literal verificable:**")
                st.info(cita)
                copiar_evidencia(documento, ubicacion, cita, f"fundamento-{i}")
        else:
            documento = result.get('documento', 'No determinado')
            ubicacion = result.get('ubicacion', 'No determinada')
            cita = result.get("cita_literal", "NO SE ENCONTRÓ CITA LITERAL VERIFICABLE.")
            st.write(f"**Documento:** {documento}")
            st.write(f"**Ubicación:** {ubicacion}")
            st.write("**Cita literal verificable:**")
            st.info(cita)
            copiar_evidencia(documento, ubicacion, cita, "fundamento-unico")
        st.write(f"**Gravedad:** {result.get('gravedad', 'No determinada')}")

        st.markdown("### 2. Texto sugerido para el Observador")
        texto_observador = result.get("texto_observador", "No generado.")
        st.markdown(texto_observador)

        # Copia el texto completo, conservando saltos de línea, directamente al portapapeles.
        copiar_portapapeles(
            texto_observador,
            "texto_observador",
            "📋 Copiar texto completo al portapapeles",
        )

        st.markdown("### 3. Acciones correctivas y pedagógicas")
        for action in result.get("acciones", []):
            st.markdown(f"- {action}")

        st.markdown("### 4. Control de verificación")
        for item in result.get("verificaciones", []):
            st.markdown(f"- {item}")

        st.markdown("### 5. Evidencia normativa recuperada")
        fragmentos_audit = audit.fragmentos if hasattr(audit, "fragmentos") else audit.get("fragmentos", [])
        for fragment in fragmentos_audit:
            with st.expander(
                f"{fragment['documento']} — página {fragment['pagina']} — puntuación {fragment['score']}"
            ):
                st.write(fragment["texto"])

        st.divider()
        st.subheader("✍️ Liberación humana")
        st.warning(
            "La IA no aprueba ni decide la medida institucional. El responsable debe "
            "verificar la cita, la ubicación, la clasificación y la proporcionalidad "
            "antes de incorporar el texto al Observador."
        )

        
    ##    responsable = st.text_input("Responsable de la revisión")
    ##    observaciones = st.text_area("Observaciones de la revisión", height=120)
    ##    aprobado = st.checkbox("He verificado manualmente el fundamento y la cita literal.")

    ##    if st.button("📋 Generar acta de liberación", use_container_width=True):
    ##        if not responsable.strip() or not aprobado:
    ##            st.error("Indique el responsable y confirme la verificación manual.")
    ##        else:
    ##            final_audit = asdict(audit)
    ##            final_audit["responsable_revision"] = responsable
    ##            final_audit["observaciones_revision"] = observaciones
    ##            final_audit["liberacion_humana"] = "APROBADO PARA REVISIÓN/USO INSTITUCIONAL"
    ##            audit_final = build_audit_record(
    ##                situacion=situacion,
    ##                selected_documents=final_audit["selected_documents"],
    ##                context=context,
    ##                result=result,
    ##                model=settings.gemini_model,
    ##                extra=final_audit,
    ##            )
    ##           st.session_state.audit_record = audit_final
    ##            st.download_button(
    ##                "⬇️ Descargar acta JSON",
    ##                data=audit_final.to_json(),
    ##                file_name="acta_observador.json",
    ##                mime="application/json",
    ##                use_container_width=True,
    ##            )
            