#!/bin/bash

ISTIO_DIR=./istio
ISTIO_VERSION="1.26.1"

# Funktion zum Herunterladen und Extrahieren der Istio Release
download_istio() {
    echo "--- Lade Istio $ISTIO_VERSION Release herunter ---"

    echo "Verwende Istio Version: $ISTIO_VERSION"
    istio_release_url="https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/istio-${ISTIO_VERSION}-linux-amd64.tar.gz"
    echo "Lade von: $istio_release_url"

    mkdir -p "$ISTIO_DIR"
    curl -L "$istio_release_url" | tar xz --strip-components=1 -C "$ISTIO_DIR"
    if [ $? -ne 0 ]; then
        echo "Fehler beim Herunterladen oder Extrahieren von Istio. Beende Skript."
        rm -rf "$ISTIO_DIR"
        exit 1
    fi
    echo "Istio erfolgreich heruntergeladen und nach $ISTIO_DIR extrahiert."
    export PATH=$PWD/$ISTIO_DIR/bin:$PATH # Füge istioctl zum PATH hinzu
    echo "Istio-Binärdateien zum PATH hinzugefügt."
}

download_istio
