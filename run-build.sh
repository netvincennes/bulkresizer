#!/bin/bash
LOGFILE="/tmp/buildozer-$(date +%Y%m%d-%H%M%S).log"
export JAVA_HOME=/home/moi/.jdks/jdk-17.0.12+7
export PATH="/home/moi/.local/cmake/bin:/home/moi/.local/bin:$JAVA_HOME/bin:$PATH"

# Local HTTP PyPI mirror (no SSL needed)
python3 -m http.server 8765 --bind 127.0.0.1 &> /tmp/pypi-http-mirror.log &
export PIP_INDEX_URL=http://127.0.0.1:8765/simple
export PIP_FIND_LINKS=file:///tmp/local-pypi
export PIP_TRUSTED_HOST=127.0.0.1
export PIP_RETRIES=0

cd /home/moi/mydev/seccgardian_cleaner_android

echo "Démarrage : $(date)" >> "$LOGFILE"
buildozer android debug >> "$LOGFILE" 2>&1
echo "Fin : $(date) - code=$?" >> "$LOGFILE"
