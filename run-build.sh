#!/bin/bash
LOGFILE="/tmp/buildozer-$(date +%Y%m%d-%H%M%S).log"

export JAVA_HOME="${JAVA_HOME:-/home/moi/.jdks/jdk-17.0.12+7}"
export PATH="$JAVA_HOME/bin:$PATH"

# Point pip to local wheels (no network access from host Python 3.14)
export PIP_FIND_LINKS="file:///tmp/pip-wheels"
export PIP_NO_INDEX="1"


cd "$(dirname "$0")"

echo "Démarrage : $(date)" >> "$LOGFILE"
buildozer android debug >> "$LOGFILE" 2>&1
echo "Fin : $(date) - code=$?" >> "$LOGFILE"
echo "Log : $LOGFILE"
