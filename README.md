# Sistema Observador — versión profesional

Aplicación Streamlit para contrastar una situación reportada con el Manual de Convivencia y/o SIEE, recuperando evidencia normativa desde Google Drive y generando un borrador asistido por Gemini con trazabilidad y revisión humana.

## Arquitectura

`Streamlit → Google Drive API → PDF/pypdf → recuperación de fragmentos → Gemini → revisión humana → acta JSON`

## 1. Crear entorno

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configurar Google Drive

1. En Google Cloud crea/selecciona un proyecto.
2. Habilita Google Drive API.
3. Crea una Service Account.
4. Descarga sus credenciales JSON.
5. Comparte cada PDF con el `client_email` de la Service Account como lector.
6. No hagas públicos los PDFs.
7. Coloca los datos de la Service Account en `.streamlit/secrets.toml` usando `secrets.toml.example` como plantilla.

Si los archivos están en Shared Drive, la cuenta de servicio debe tener acceso al archivo o al Shared Drive.

## 3. Configurar Gemini

Crea una nueva API Key de Gemini y colócala en `GEMINI_API_KEY` dentro de `secrets.toml`.

## 4. Ejecutar

```powershell
streamlit run app.py
```

## 5. Seguridad

- Revoca cualquier API Key que haya sido expuesta en código, capturas o chats.
- No subas `.streamlit/secrets.toml` al repositorio.
- No uses URLs públicas de Drive para documentos institucionales.
- El sistema no debe considerarse un decisor disciplinario.
- La liberación final requiere verificación humana.

## 6. Limitación actual

`pypdf` extrae texto de PDFs que contienen texto digital. Un PDF compuesto exclusivamente por imágenes requiere un módulo OCR antes de entrar al buscador normativo.

## 7. Principio de no invención

Si el sistema no recupera evidencia suficiente, debe devolver `REQUIERE_REVISION` y no fabricar una cita, artículo, numeral o clasificación.

## Regla de redacción del Observador

El texto sugerido conserva los hechos registrados por el docente, mejora su redacción institucional y, a continuación, relaciona la conducta con **cada fundamento normativo verificable** recuperado de los documentos seleccionados. Si existen fundamentos tanto en el Manual de Convivencia como en el SIEE, ambos se incorporan al mismo texto indicando documento y ubicación (capítulo, artículo, numeral o apartado) cuando estén disponibles.

La IA no debe inventar ubicaciones ni citas. La cita literal debe verificarse contra el documento original antes de liberar el registro.
