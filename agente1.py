#!/usr/bin/env python3
"""
Agente 1 - Proceso1, Etapa 1: Extracción de datos de facturas PDF a salida JSON.
"""

# Core
import sys
import time
from pathlib import Path

# Other
import argparse
from pydantic import BaseModel, Field
from strands import Agent
from status_icons import icon_status
from agent_utils import leer_campos_pdf

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Procesa facturas")
    p.add_argument("--data-dir", default="/home/crp/Projects/itp-flokzu/data/proceso1",
                   help="Directorio base de datos (default: %(default)s)")
    p.add_argument("--factura", required=True,
                   help="Ruta a la factura en PDF")
    p.add_argument("--salida", default=None,
                   help="Ruta del JSON de salida (si no se pasa, usa proceso1_{factura}_campos.json)")

    if len(sys.argv) == 1:
        p.print_help(sys.stderr)
        sys.exit(1)

    return p.parse_args()

def resolve_paths(a: argparse.Namespace) -> dict:
    data_dir = Path(a.data_dir)
    factura = data_dir / a.factura
    salida  = Path(a.salida) if a.salida else Path(f"proceso1_{factura.stem}_campos.json")
    return {
        "factura": factura,
        "salida": salida
    }


class Factura_Data_Model(BaseModel):
    """Estructura de datos para facturas"""
    tipo_comprobante: str = Field(
        description="Código AFIP del comprobante (ej: '01' para Factura A, '06' para Factura B)"
    )
    fecha_emision: str = Field(
        description="Fecha de emisión en formato dd/mm/aaaa"
    )
    numero_factura: str = Field(
        description="Número de factura en formato X-00000-00000000 (letra comprobante, 5 dígitos punto venta, 8 dígitos número)"
    )
    fecha_vencimiento: str = Field(
        description="Fecha de vencimiento en formato dd/mm/aaaa"
    )
    monto: str = Field(
        description="Monto en formato NNNNNNN,NN (número decimal con coma sin separador de miles)"
    )

# MAIN

try:
    args = parse_args()
    paths = resolve_paths(args)
    #print(paths)
    #print("paths['factura']", paths['factura'])

    icon_status("wait", f"Procesando: {paths['factura'].name} ...")
    tic = time.time()
    agente = Agent()
    campos = leer_campos_pdf(agente, Factura_Data_Model, paths['factura'])
    toc = time.time()
    
    icon_status("ok", "JSON OBTENIDO.")
    salida = campos.model_dump_json(indent=2)
    print(f"Procesado en {toc-tic:.2f} segundos.")
    paths['salida'].write_text(salida)
    
except Exception as e:
    icon_status("Error", f"{e}")

# FIN
