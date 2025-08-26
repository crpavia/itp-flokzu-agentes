#!/usr/bin/env bash
# Ejecuta agente1.py con distintos casos de facturas

set -euo pipefail

RAYA=$(printf '%.0s*' {1..80})

raya() {
  echo
  echo "$RAYA"
  echo "$RAYA"
  echo "$RAYA"  
  echo
}

pausa() {
  echo
  read -p ">>> PULSE ESPACIO PARA CONTINUAR <<< " -n1
  echo
}

banner() {
	clear
	figlet "Flokzu"
	echo	
}

# MAIN

banner
pausa

# limpiar salidas anteriores
echo "[INFO] Borrando JSON anteriores..."
rm -f proceso1_*_campos.json

echo
echo "[INFO] Documentos a procesar."

FILES=(data/proceso1/*.pdf)
FACTURAS=()
for f in "${FILES[@]}"; do
  FACTURAS+=("$(basename "$f")")
done

echo "[INFO] Se encontraron ${#FACTURAS[@]} documentos:"
printf '    %s\n' "${FACTURAS[@]}"

pausa

# Ejecutar cada caso
for f in "${FACTURAS[@]}"; do
  raya
  echo "[INFO] Procesando $f ..."
  time python3 agente1.py --factura "$f"
done

raya
pausa
echo
echo "[INFO] Documentos procesados:"
ls -FAl data/proceso1/*.pdf
echo
echo "[INFO] Salidas generadas:"
ls -FAl proceso1_*_campos.json
echo
