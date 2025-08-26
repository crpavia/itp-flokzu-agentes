# agent_utils.py

# Core
import os
import sys
import json
import time
import re
from pathlib import Path
import unicodedata

# Data types
from typing import Any, Dict, Iterable, Literal, Mapping, Sequence
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, Field

# Strands
from strands import Agent, tool
from strands.agent import AgentResult
from strands.models import BedrockModel
from strands_tools import file_read

T = TypeVar("T", bound=BaseModel)

__all__ = [
    "clean_json",
    "leer_bytes_pdf",
    "leer_campos_pdf",
    "leer_textos_pdf",
    "get_response_text",
    "get_response_json"
]

def probe(texto):
    """Probar texto."""
    print(f"** {len(texto)} CARACTERES, {len(texto.split("\n"))} LINEAS **")
    if len(texto) < 400:
        print(f"{texto}")
    else:
        print(f"{texto[:200]}")
        print('...')
        print(f"{texto[-200:]}")

def clean_json(response_text: str) -> Optional[str]:
    """
    Extrae un bloque JSON válido de un texto cualquiera.
    - Soporta que venga dentro de marcas ```json ... ``` o mezclado con texto.
    - Devuelve el string JSON (ya validado) o None si no encuentra uno parseable.
    """
    if not response_text:
        return None

    # 1) Si viene en fence ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, flags=re.S)
    candidates: list[str] = []
    if fence:
        candidates.append(fence.group(1))

    # 2) Fallback: primer '{' hasta el último '}' (heurística simple)
    first = response_text.find("{")
    last = response_text.rfind("}")
    if first != -1 and last > first:
        candidates.append(response_text[first : last + 1])

    for cand in candidates:
        try:
            json.loads(cand)
            return cand
        except json.JSONDecodeError:
            continue

    return None

def get_response_text(result: AgentResult) -> str:
    return result.message['content'][0]['text']

def get_response_json(result: AgentResult) -> Optional[str]:
    """Extract and clean JSON from agent result in one step."""
    text = get_response_text(result)
    return clean_json(text)
    
def leer_bytes_pdf(pdf_path: str | Path) -> bytes:
    """
    Lee un archivo PDF desde la ruta especificada y devuelve su contenido como bytes.

    Args:
        pdf_path: Ruta al archivo PDF (string o Path).

    Returns:
        Contenido del PDF en formato bytes.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si la extensión no es .pdf o el archivo está vacío.
    """

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"El archivo no existe: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"El archivo no tiene extensión .pdf: {path}")

    data = path.read_bytes()
    if not data:
        raise ValueError(f"El archivo está vacío: {path}")

    return data

def _sanitize_bedrock_doc_name(p: str | Path) -> str:
    name = Path(p).stem                      # quita .pdf
    name = unicodedata.normalize("NFKD", name).encode("ascii","ignore").decode()
    name = name.replace("_", " ")            # opcional: convierte _ en espacio
    name = re.sub(r"[^A-Za-z0-9\-\(\)\[\]\s]", " ", name)  # deja solo lo permitido
    name = re.sub(r"\s+", " ", name).strip()               # colapsa espacios
    return name or "Document"

def leer_campos_pdf(
    agente: Agent,
    data_model: Type[T],
    pdf_path: str | Path,
    nombre_documento: str | None = None
) -> T:
    """Leer campos de un PDF, especificados en un modelo de datos."""

    prompt = "Extrae los datos del documento, en base a lo especificado en el modelo de datos."
    print("Modelo de lenguaje:", agente.model.get_config()["model_id"])
    print("Prompt:", prompt)
    print("Modelo de datos:", data_model.__name__)
    print("Campos del modelo de datos:")
    for nombre, info in data_model.model_fields.items():
        print(f"  - {nombre} : {info.description}")
    print()        
        
    if not nombre_documento:
        #nombre_documento = _sanitize_bedrock_doc_name(pdf_path)
        nombre_documento = 'Documento'

    print("Nombre del documento:", nombre_documento)
    print("Ubicación del documento:", pdf_path)
    pdf_bytes = leer_bytes_pdf(pdf_path)
    print("Tamaño en bytes:", len(pdf_bytes))
    print()
    print("*** LLAMANDO A MODELO IA ***")
    salida = agente.structured_output(data_model, [
        {"text": prompt},
        {"document": {
            "format": "pdf",
            "name": nombre_documento,         # <- ahora válido para Bedrock
            "source": {"bytes": pdf_bytes}
        }}
    ])
    
    return salida


def leer_texto_pdf(
    pdf_path: str,
    modo: Literal["PLUMBER", "PYPDF", "FITZ"] = "PLUMBER",
    pages: Optional[Iterable[int]] = None,      # 1-based; None = todas
    fix_hyphens: bool = True,                   # junta "palabra-\nsiguiente"
    strip: bool = True                          # .strip() por página
) -> str:
    """
    Lee texto de un PDF usando el backend seleccionado.

    Args:
        pdf_path: Ruta al PDF.
        modo: "PLUMBER" (pdfplumber), "PYPDF" (pypdf), "FITZ" (PyMuPDF).
        pages: Números de página 1-based a extraer (None = todas).
        fix_hyphens: Si True, corrige cortes de palabra por guion al fin de línea.
        strip: Si True, aplica .strip() por página.

    Returns:
        Texto concatenado de las páginas seleccionadas.

    Raises:
        FileNotFoundError: si el PDF no existe.
        ValueError: si el modo no es válido o no hay texto.
        ImportError: si falta la librería del modo elegido.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"No existe el archivo: {pdf_path}")

    tic = time.time()
    partes: list[str] = []

    # Normaliza páginas: pasa a índices 0-based si vienen 1-based
    indices = None
    if pages is not None:
        indices = sorted({p-1 for p in pages if p > 0})

    modo = modo.upper()
    if modo == "PLUMBER":
        try:
            import pdfplumber  # type: ignore
        except Exception as e:
            raise ImportError("Falta 'pdfplumber' (pip install pdfplumber)") from e

        with pdfplumber.open(pdf_path) as pdf:
            sel = indices if indices is not None else range(len(pdf.pages))
            for i in sel:
                t = pdf.pages[i].extract_text() or ""
                partes.append(t.strip() if strip else t)

    elif modo == "PYPDF":
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as e:
            raise ImportError("Falta 'pypdf' (pip install pypdf)") from e

        reader = PdfReader(pdf_path)
        sel = indices if indices is not None else range(len(reader.pages))
        for i in sel:
            t = reader.pages[i].extract_text() or ""
            partes.append(t.strip() if strip else t)

    elif modo == "FITZ":
        try:
            import fitz  # PyMuPDF
        except Exception as e:
            raise ImportError("Falta 'PyMuPDF' (pip install pymupdf)") from e

        doc = fitz.open(pdf_path)
        try:
            sel = indices if indices is not None else range(len(doc))
            for i in sel:
                page = doc.load_page(i)
                t = page.get_text("text") or ""
                partes.append(t.strip() if strip else t)
        finally:
            doc.close()
    else:
        raise ValueError(f"Modo inválido: {modo}. Usa 'PLUMBER', 'PYPDF' o 'FITZ'.")

    texto = "\n\n".join(partes)

    if fix_hyphens and texto:
        # 1) Une palabras cortadas por guion al final de línea: "ejem-\nplo" -> "ejemplo"
        texto = re.sub(r"-\s*\n\s*", "", texto)
        # 2) Limpia saltos múltiples conservando párrafos
        texto = re.sub(r"\n{3,}", "\n\n", texto)

    toc = time.time()
    print(f"PDF procesado en {toc - tic:.2f} seg | modo={modo} | archivo={pdf_path}")

    if not texto.strip():
        raise ValueError("No se extrajo texto del PDF (¿páginas vacías o solo imágenes?).")

    return texto
    
def create_metadata_agent_res(agent: Agent, res: AgentResult, external:Dict={}) -> Dict[str, Dict[str, Any]]:
    """
    Crea un diccionario con metadatos de una interacción de Strands Agents.

    Args:
        agent (Agent): Instancia del agente de Strands que procesó la solicitud.
        res (AgentResult): Resultado devuelto por la ejecución del agente.

    Returns:
        dict: Estructura con tres claves principales:
            - agent (dict): Configuración del modelo usado por el agente.
                * model (dict): Datos devueltos por agent.model.get_config().
            - response (dict): Información sobre la respuesta generada.
                * state (str): Estado final de la ejecución (ej. "success", "error").
                * stop_reason (str | None): Motivo de detención (ej. "stop_sequence", "timeout").
                * message (Any): Mensaje o contenido principal de la respuesta.
                * metrics (dict): Resumen de métricas (tokens, latencia, coste, etc.).
            - external (dict): Espacio reservado para datos de sistemas externos.
    """
    meta: Dict[str, Dict[str, Any]] = {'agent': {}, 'response': {}, 'external': external}
    meta['agent']['model'] = agent.model.get_config()
    meta['response']['state'] = res.state
    meta['response']['stop_reason'] = res.stop_reason
    meta['response']['message'] = res.message
    meta['response']['metrics'] = res.metrics.get_summary()
    # print(json.dumps(meta, indent=2))
    return meta

# FIN