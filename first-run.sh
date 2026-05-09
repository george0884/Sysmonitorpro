#!/bin/bash
# scripts/first-run.sh
mkdir -p ~/.config/sysmonitorpro
if [ ! -f ~/.config/sysmonitorpro/config.json ]; then
    cp config/default.json ~/.config/sysmonitorpro/config.json
    echo "Configuración creada en ~/.config/sysmonitorpro/config.json"
fi
