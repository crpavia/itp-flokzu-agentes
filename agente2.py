#!/usr/bin/env python3
"""
Agente 2 - Proceso 2: Evaluacion de propuestas
"""

# Core
import os
import sys
import json
import re 
import time
from pathlib import Path
import argparse
# Data types
from typing import Any, Dict, Iterable, Literal, Optional
from pydantic import BaseModel, Field
# Strands
from strands import Agent, tool
from strands.agent import AgentResult
from strands.models import BedrockModel
from strands_tools import file_read
# Internal
from  agent_utils import leer_bytes_pdf, leer_texto_pdf, leer_campos_pdf
from  agent_utils import probe, get_response_json, get_response_text

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:    
    p = argparse.ArgumentParser(description="Procesa archivos de un caso")
    p.add_argument("--data-dir", default="/home/crp/Projects/itp-flokzu/data/proceso2",
                   help="Directorio base de datos (default: %(default)s)")
    p.add_argument("--caso", required=True,
                   help="Subdirectorio del caso")
    p.add_argument("--formulario", default=None,
                   help="Ruta al Formulario.pdf (si no se pasa, se arma con data-dir/caso)")
    p.add_argument("--propuesta", default=None,
                   help="Ruta a Propuesta.pdf (si no se pasa, se arma con data-dir/caso)")
    p.add_argument("--prompt", default=None,
                   help="Ruta a prompt.md (si no se pasa, usa data-dir/prompt1.md)")
    p.add_argument("--categorias", default=None,
                   help="Ruta a categorias.txt (si no se pasa, usa data-dir/categorias.txt)")
    p.add_argument("--salida", default=None,
                   help="Ruta del JSON de salida (si no se pasa, usa proceso2_{caso}_evaluacion.json)")

    # Si no hay argumentos, mostrar help y salir con código de uso (2).
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        p.print_help(sys.stderr)
        sys.exit(2)

    return p.parse_args()

def resolve_paths(a: argparse.Namespace) -> dict:
    data_dir = Path(a.data_dir)
    caso_dir = Path(a.caso)
    base_caso = data_dir / caso_dir
    formulario = Path(a.formulario) if a.formulario else base_caso / "Formulario.pdf"
    propuesta  = Path(a.propuesta)  if a.propuesta  else base_caso / "Propuesta.pdf"
    prompt     = Path(a.prompt)     if a.prompt     else data_dir / "prompt1.md"
    categorias = Path(a.categorias) if a.categorias else data_dir / "categorias.txt"
    salida     = Path(a.salida)     if a.salida     else Path(f"proceso2_{caso_dir.name}_salida.json")
    entrada    = Path(f"proceso2_{caso_dir.name}_entrada.txt")
    return {
        "DATA_DIR": data_dir,
        "CASO_DIR": caso_dir,
        "formulario": formulario,
        "propuesta": propuesta,
        "prompt": prompt,
        "categorias": categorias,
        "salida": salida,
        "entrada": entrada
    }

def assert_exists(p: Path, label: str):
    if not p.exists():
        print(f"[ERROR] No existe {label}: {p}")
        sys.exit(1)

# FAMILIARES
class AltaCentroCostos_Datos(BaseModel):
    """Estructura de datos del formulario Alta de Centro de Costos"""
    nombre_propuesto_servicio: str = Field(description="Nombre propuesto de servicio")    
    servicio_final_esperado: str = Field(description="Producto / Servicio final esperado")
    descripcion_servicio: str = Field(description="Breve descripción del servicio a brindar")
    herramientas_a_utilizar: str = Field(description="Lenguajes / Herramientas a utilizar")
    encargado_indicaciones: str = Field(description="¿Quién es el encargado de dar las indicaciones a los colaboradores?")
    proveedor_herramientas: str = Field(description="¿Quién proporciona las herramientas necesarias a los colaboradores (ej. computadora, email, etc.)?")
    colaborador_percibe_beneficios: str = Field(description="¿El colaborador percibe los beneficios de IT Patagonia?")
    c1: str = Field(description="Se trata de un SaaS")
    c2: str = Field(description="Desarrollo realizado a medida a pedido del cliente")
    c3: str = Field(description="Desarrollo propio comercializable como enlatado")
    c4: str = Field(description="Otorgamiento de servicios de cómputo en la nube")
    c5: str = Field(description="Desarrollo de un software a ser embebido en un hardware")
    c6: str = Field(description="Desarrollo a fin de mejorar la seguridad de equipos y/o redes")
    c7: str = Field(description="Implementación o puesta a punto en el cliente de un producto propio o creado por terceros y de productos registrados")
    c8: str = Field(description="Desarrollo de módulos, rutinas, procedimientos o documentación complementarios o integrables a un software registrable")

    informacion_adicional: str = Field(description="Observaciones información adicional análisis promovido")

def obtener_caracteristica_principal(inst: BaseModel) -> str:
    """
    Revisa campos c1, c2, ...; encuentra la única marcada como afirmativa
    y devuelve su descripción. Lanza ValueError si 0 o >1.
    """
    _PATRON_C = re.compile(r"^c\d+$")
    _VERDADEROS = {"si", "sí", "s", "true", "1", "yes", "y"}
    
    matches: list[str] = []
    data = inst.model_dump()

    for nombre, valor in data.items():
        if not _PATRON_C.match(nombre):
            continue
        v = valor
        es_true = (v is True) or (isinstance(v, (int, float)) and v == 1) \
                  or (isinstance(v, str) and v.strip().lower() in _VERDADEROS)
        if es_true:
            matches.append(nombre)

    if len(matches) == 0:
        raise ValueError("Ninguna opción marcada como afirmativa.")
    if len(matches) > 1:
        raise ValueError(f"Más de una opción afirmativa: {matches}")

    campo = matches[0]
    # Obtener descripción desde la definición del modelo
    field_info = type(inst).model_fields[campo]
    return field_info.description or campo  # fallback por si no hubiera description

def leer_formulario(datos_formulario) -> str:
    """Obtiene los campos relevantes del formulario de Proceso2"""
    formulario = datos_formulario.model_dump()    
    formulario['caracteristica_principal'] = obtener_caracteristica_principal(datos_formulario)
    for i in range(1, 9):
        formulario.pop(f"c{i}", None)
    salida = json.dumps(formulario, indent=2, ensure_ascii=False)
    print()
    print(salida)
    print()
    return salida

# MAIN
args = parse_args()
paths = resolve_paths(args)

categorias = paths['categorias'].read_text().strip()
prompt = paths['prompt'].read_text().strip()
propuesta = leer_texto_pdf(paths['propuesta'])

ag2_camper = Agent(name="pdf_camper", description="Extrae campos de PDF, via DataModel")
formulario_campos = leer_campos_pdf(ag2_camper, AltaCentroCostos_Datos, paths['formulario'])

formulario = leer_formulario(formulario_campos)
prompt_full = (prompt
    .replace('{categorias}', categorias)
    .replace('{formulario}', formulario)
    .replace('{propuesta}', propuesta)
)
probe(prompt_full)
Path(paths['entrada']).write_text(prompt_full)

bm = BedrockModel(maxTokens=16384, temperature=0)
ag2_decisor = Agent(name="Decisor", model=bm)
resultado = ag2_decisor(prompt_full)
salida_json = get_response_json(resultado)
Path(paths['salida']).write_text(salida_json)

# FIN
