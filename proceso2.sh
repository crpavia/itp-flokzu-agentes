#!/usr/bin/env bash
# Ejecuta agente2.py sobre todos los casos en data/proceso2/caso*/

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
  read -p ">>> PULSE ESPACIO PARA CONTINUAR <<< " -n1 || true
  echo
}

banner() {
  clear
  figlet "Flokzu" || true
  echo
}

# MAIN
banner
pausa

# Detectar casos
echo "[INFO] Buscando casos en data/proceso2 ..."
CASES=()
for d in data/proceso2/caso*/; do
  # solo directorios
  [[ -d "$d" ]] || continue
  CASES+=("$(basename "$d")")
done

if [[ ${#CASES[@]} -eq 0 ]]; then
  echo "[ERROR] No se encontraron subdirectorios de casos en data/proceso2/"
  exit 1
fi

echo "[INFO] Casos encontrados (${#CASES[@]}):"
printf '    %s\n' "${CASES[@]}"
pausa

# Limpiar salidas previas (todas)
echo "[INFO] Borrando JSON de salidas previas..."
rm -f proceso2_*_evaluacion.json || true

# Ejecutar cada caso
for caso in "${CASES[@]}"; do
  raya
  echo "[INFO] Procesando $caso ..."
  # Borrar salida específica por las dudas
  rm -f "proceso2_${caso}_evaluacion.json" || true
  time python3 agente2.py --caso "$caso"
done

raya
pausa
echo
echo "[INFO] Casos procesados:"
printf '    %s\n' "${CASES[@]}"
echo
echo "[INFO] Salidas generadas:"
ls -FAl proceso2_*_evaluacion.json || true

