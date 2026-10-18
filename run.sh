#!/bin/sh
# Avvia KogitechHub dalla cartella del progetto (senza installazione).
cd "$(dirname "$0")" && PYTHONPATH=src exec python3 -m kogitechhub "$@"
