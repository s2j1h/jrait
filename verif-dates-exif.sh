#!/bin/bash
#
# verif-dates-exif.sh
# Affiche, pour chaque photo d'un répertoire, sur une seule ligne :
#   - la date de création    (DateTimeOriginal)
#   - la date de numérisation (CreateDate)
#   - la date de mise à jour  (ModifyDate)
# Le chemin (répertoire + nom de fichier) est affiché pour chaque photo.
#
# Usage :
#   ./verif-dates-exif.sh [répertoire] [-r]
#
#   [répertoire]  Répertoire à analyser (par défaut : répertoire courant)
#   -r            Parcours récursif des sous-répertoires
#
# Exemples :
#   ./verif-dates-exif.sh ~/Photos
#   ./verif-dates-exif.sh ~/Photos -r
#

# --- Vérification qu'exiftool est installé ---
if ! command -v exiftool >/dev/null 2>&1; then
    echo "Erreur : exiftool n'est pas installé."
    echo "Installe-le avec : brew install exiftool"
    exit 1
fi

# --- Analyse des arguments ---
REP="."
RECURSIF=""

for arg in "$@"; do
    if [ "$arg" = "-r" ]; then
        RECURSIF="-r"
    else
        REP="$arg"
    fi
done

# --- Vérification que le répertoire existe ---
if [ ! -d "$REP" ]; then
    echo "Erreur : le répertoire « $REP » n'existe pas."
    exit 1
fi

echo "Analyse de : $REP"
[ -n "$RECURSIF" ] && echo "(parcours récursif activé)"
echo

# --- Extraction des dates, une ligne par fichier ---
#   $directory/$filename  : chemin complet (répertoire visible)
#   Créé   = DateTimeOriginal
#   Numér. = CreateDate
#   MàJ    = ModifyDate
# Les valeurs manquantes sont remplacées par "(absente)".
exiftool $RECURSIF -ext jpg -ext jpeg \
    -d "%Y-%m-%d %H:%M:%S" \
    -p '$directory/$filename | Créé: ${DateTimeOriginal;$_ or $_="(absente)"} | Numér.: ${CreateDate;$_ or $_="(absente)"} | MàJ: ${ModifyDate;$_ or $_="(absente)"}' \
    -q -m "$REP"

echo
echo "Terminé."
