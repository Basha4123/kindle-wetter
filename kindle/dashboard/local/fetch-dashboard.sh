#!/usr/bin/env sh
# Lädt das aktuelle Wetterbild nach "$1".
# DEIN-GITHUB-NAME durch deinen GitHub-Benutzernamen ersetzen!
"$(dirname "$0")/../xh" -d -q -o "$1" get "https://DEIN-GITHUB-NAME.github.io/kindle-wetter/wetter.png"
