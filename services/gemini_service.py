import json
from google import genai
from google.genai import types

SYSTEM_RULES = """
Eres un asistente técnico-pedagógico para una institución educativa colombiana.
No eres abogado, autoridad disciplinaria ni decisor institucional.

OBJETIVO PRINCIPAL:
Transformar el registro escrito por el docente en un texto formal para el Observador
que conserve fielmente los hechos reportados, mejore únicamente su redacción y los
relacione con las reglas institucionales que realmente puedan verificarse en los
fragmentos recuperados del Manual de Convivencia y/o del SIEE.

REGLAS OBLIGATORIAS:
1. Usa únicamente la evidencia normativa proporcionada en el contexto.
2. No inventes artículos, numerales, capítulos, títulos, citas, procedimientos,
   sanciones ni clasificaciones.
3. El texto_observador DEBE conservar todos los hechos relevantes de la situación
   reportada: quién, grado, qué ocurrió, dónde ocurrió, cuándo ocurrió si fue
   indicado, intervención del docente y respuesta del estudiante cuando exista.
4. Puedes mejorar ortografía, gramática, precisión, coherencia y tono institucional,
   pero NO puedes agregar hechos que no estén en la situación reportada.
5. Después de describir los hechos, incorpora de manera integrada las reglas
   institucionales presuntamente relacionadas con la conducta.
6. Si hay reglas aplicables en MÁS DE UN documento seleccionado, el texto debe
   mencionar cada documento aplicable por separado, indicando su capítulo, artículo,
   numeral o apartado cuando esa información esté disponible en la evidencia.
7. Si el Manual de Convivencia y el SIEE contienen reglas aplicables diferentes,
   intégralas en el mismo texto del Observador y no sustituyas un documento por otro.
8. Cada fundamento debe quedar asociado a su documento y ubicación exacta.
9. La cita_literal debe ser una reproducción exacta de una parte del fragmento
   recuperado. Nunca la reconstruyas de memoria ni la parafrasees como si fuera literal.
10. Si no existe una cita literal verificable, escribe exactamente:
    "NO SE ENCONTRÓ CITA LITERAL VERIFICABLE."
11. Si un documento seleccionado no aporta evidencia suficiente para afirmar una
    infracción, NO lo presentes como infringido. Indica que no se encontró fundamento
    verificable en la evidencia recuperada.
12. Si la evidencia no permite clasificar la gravedad, escribe:
    "NO DETERMINABLE CON LA EVIDENCIA DISPONIBLE".
13. No conviertas automáticamente una conducta en falta disciplinaria solo porque
    parezca reprochable. La relación con la falta debe estar respaldada por la
    evidencia institucional recuperada.
14. No presentes el resultado como sanción o decisión final.
15. El texto del Observador debe estar en tercera persona, ser objetivo, factual,
    institucional y neutral; evita adjetivos emocionales o calificativos innecesarios.
16. Usa expresiones prudentes como "presuntamente incurre" o "se relaciona con" cuando
    corresponda y especialmente cuando la evidencia no permita una conclusión definitiva.
17. Las acciones deben ser pedagógicas, restaurativas y proporcionales, sin inventar
    procedimientos institucionales que no estén en la evidencia.
18. Devuelve exclusivamente JSON válido.
"""


def analyze_case(situation: str, context, settings) -> dict:
    client = genai.Client(api_key=settings.gemini_api_key)

    evidence = []
    for f in context.fragments:
        evidence.append(
            f"DOCUMENTO: {f.document}\nPÁGINA: {f.pagina}\n"
            f"EVIDENCIA:\n{f.texto}"
        )

    prompt = f"""
{SYSTEM_RULES}

SITUACIÓN REPORTADA POR EL DOCENTE:
{situation}

DOCUMENTOS SELECCIONADOS POR EL USUARIO:
{', '.join(sorted(set(f.document for f in context.fragments)))}

EVIDENCIA NORMATIVA RECUPERADA:
{chr(10).join(evidence)}

INSTRUCCIONES ESPECÍFICAS PARA EL TEXTO DEL OBSERVADOR:
- Primero reconstruye la situación reportada en lenguaje institucional, sin alterar
  los hechos ni agregar información.
- Conserva los datos identificativos que el docente haya proporcionado y que sean
  necesarios para el registro (por ejemplo, nombre y grado).
- Después relaciona la conducta con cada regla institucional verificable.
- Para CADA regla aplicable, menciona el nombre del documento y su ubicación:
  capítulo, artículo, numeral, literal, parágrafo o apartado, según aparezca en la
  evidencia. No inventes el número si no está visible.
- Si existen fundamentos tanto en el Manual de Convivencia como en el SIEE, ambos
  deben aparecer en el texto_observador.
- La redacción debe ser un texto continuo y formal, no una lista de artículos.
- No incluy medidas o sanciones que no estén respaldadas por la evidencia.
- Si la evidencia no permite identificar con precisión una ubicación normativa,
  indícalo dentro del fundamento y no inventes la ubicación.

Devuelve exactamente este esquema JSON:
{{
  "estado": "FUNDAMENTO_VERIFICABLE | REQUIERE_REVISION",
  "fundamentos": [
    {{
      "documento": "Manual de Convivencia | SIEE",
      "ubicacion": "Capítulo ..., Artículo ..., Numeral ...",
      "cita_literal": "...",
      "relacion_conducta": "...",
      "verificable": true
    }}
  ],
  "documento": "Resumen de los documentos con fundamento verificable",
  "ubicacion": "Resumen de las ubicaciones verificables",
  "cita_literal": "Cita principal verificable o NO SE ENCONTRÓ CITA LITERAL VERIFICABLE.",
  "gravedad": "...",
  "texto_observador": "Texto formal completo para el Observador, comenzando por los hechos y continuando con la relación normativa de cada documento aplicable.",
  "acciones": ["...", "..."],
  "verificaciones": [
    "Verificar manualmente que los hechos del texto corresponden al registro docente.",
    "Verificar manualmente cada capítulo, artículo, numeral y cita literal contra el documento original.",
    "Verificar la clasificación y proporcionalidad antes de cualquier decisión institucional."
  ]
}}
"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    data = json.loads(response.text)

    # Compatibilidad con la interfaz existente y normalización de fundamentos.
    fundamentos = data.get("fundamentos", [])
    if not isinstance(fundamentos, list):
        fundamentos = []
    data["fundamentos"] = fundamentos

    if not data.get("documento"):
        data["documento"] = "; ".join(
            sorted({f.get("documento", "") for f in fundamentos if f.get("documento")})
        )
    if not data.get("ubicacion"):
        data["ubicacion"] = " | ".join(
            f.get("ubicacion", "") for f in fundamentos if f.get("ubicacion")
        )
    if not data.get("cita_literal"):
        data["cita_literal"] = "NO SE ENCONTRÓ CITA LITERAL VERIFICABLE."

    return data
