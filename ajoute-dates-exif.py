#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ajoute-dates-exif.py

Force les trois dates EXIF d'une photo (date de prise de vue, de
numérisation et de modification) à une même date donnée en paramètre,
pour tous les fichiers JPG/JPEG d'un répertoire (parcouru récursivement).

Si le fichier a déjà des dates EXIF, elles sont écrasées. S'il n'en a
aucune, elles sont créées. Les autres métadonnées EXIF (appareil photo,
GPS, etc.) et l'image elle-même ne sont pas modifiées : seul le bloc de
métadonnées date est réécrit, sans réencodage des pixels.

Tags EXIF renseignés :
    - DateTime           (0x0132, IFD0)        -> date de modification
    - DateTimeOriginal   (0x9003, sous-IFD Exif) -> date de prise de vue
    - DateTimeDigitized  (0x9004, sous-IFD Exif) -> date de numérisation

Dépendance : piexif  (pip install piexif)

Usage :
    python3 ajoute-dates-exif.py <repertoire> <date> [--dry-run]

<date> au format AAAA-MM-JJ ou "AAAA-MM-JJ HH:MM:SS"
       (heure omise -> 00:00:00).

Exemples :
    python3 ajoute-dates-exif.py "/Volumes/homes/2026-08-09_vacances" 2026-08-09
    python3 ajoute-dates-exif.py "/Volumes/homes/2026-08-09_vacances" "2026-08-09 14:30:00"
    python3 ajoute-dates-exif.py "/Volumes/homes/2026-08-09_vacances" 2026-08-09 --dry-run
"""

import argparse
import os
import re
import sys
import time

try:
    import piexif
except ImportError:
    sys.exit("Erreur : piexif n'est pas installé.  ->  pip install piexif")

# Extensions traitées (comparaison insensible à la casse)
EXTENSIONS = (".jpg", ".jpeg")

# Date en paramètre : AAAA-MM-JJ, éventuellement suivie de HH:MM:SS
RE_DATE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}):(\d{2}))?$"
)


def parser_date(valeur):
    """Convertit 'AAAA-MM-JJ' ou 'AAAA-MM-JJ HH:MM:SS' en date EXIF
    'AAAA:MM:JJ HH:MM:SS'. Lève ValueError si le format est invalide."""
    m = RE_DATE.match(valeur.strip())
    if not m:
        raise ValueError(
            f"« {valeur} » (format attendu : AAAA-MM-JJ ou "
            "\"AAAA-MM-JJ HH:MM:SS\")"
        )
    annee, mois, jour, h, mn, s = m.groups()
    h, mn, s = h or "00", mn or "00", s or "00"
    # contrôle sommaire de validité
    if not (1 <= int(mois) <= 12 and 1 <= int(jour) <= 31):
        raise ValueError(f"« {valeur} » : mois ou jour hors plage")
    return f"{annee}:{mois}:{jour} {h}:{mn}:{s}"


def forcer_date_exif(chemin, date_exif):
    """Écrase (ou crée) les dates EXIF du fichier avec 'date_exif'
    (format 'AAAA:MM:JJ HH:MM:SS'), sans toucher aux pixels de l'image
    ni aux autres métadonnées EXIF déjà présentes."""
    try:
        exif_dict = piexif.load(chemin)
    except Exception:
        # Pas de segment EXIF exploitable : on repart d'une structure vide.
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    date_bytes = date_exif.encode("ascii")
    exif_dict["0th"][piexif.ImageIFD.DateTime] = date_bytes
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_bytes
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_bytes

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, chemin)


def afficher_progression(total, chemin_courant, termine=False):
    """Affiche une ligne de progression mise à jour en place (sans retour
    à la ligne), avec le nombre de photos traitées et le fichier en cours."""
    if termine:
        print(f"\r{' ' * 100}\r", end="")
        return
    ligne = f"\r{total} photo(s) traitée(s)... {chemin_courant}"
    largeur_terminal = os.get_terminal_size().columns if sys.stdout.isatty() else 200
    ligne = ligne[:largeur_terminal - 1]
    print(f"{ligne}{' ' * (largeur_terminal - 1 - len(ligne))}", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Force les dates EXIF des photos JPG/JPEG d'un répertoire à une date donnée."
    )
    parser.add_argument("repertoire", help="Répertoire à traiter (parcouru récursivement)")
    parser.add_argument(
        "date",
        help='Date à appliquer : AAAA-MM-JJ ou "AAAA-MM-JJ HH:MM:SS"',
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="N'écrit rien, affiche seulement les fichiers qui seraient modifiés",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.repertoire):
        sys.exit(f"Erreur : le répertoire « {args.repertoire} » n'existe pas.")

    try:
        date_exif = parser_date(args.date)
    except ValueError as e:
        sys.exit(f"Erreur : date invalide {e}")

    print(f"Répertoire     : {args.repertoire}")
    print(f"Date appliquée : {date_exif}")
    if args.dry_run:
        print("(mode simulation : aucun fichier ne sera modifié)")
    print()

    total = 0
    erreurs = []
    dernier_affichage = 0.0

    for dossier, _sous_dossiers, fichiers in os.walk(args.repertoire):
        for nom in sorted(fichiers):
            if not nom.lower().endswith(EXTENSIONS):
                continue
            chemin = os.path.join(dossier, nom)

            if not args.dry_run:
                try:
                    forcer_date_exif(chemin, date_exif)
                except Exception as e:
                    erreurs.append((chemin, str(e)))
                    continue

            total += 1

            maintenant = time.monotonic()
            if maintenant - dernier_affichage >= 0.2:
                afficher_progression(total, chemin)
                dernier_affichage = maintenant

    afficher_progression(total, "", termine=True)

    print(f"{total} photo(s) traitée(s) avec succès.")
    if erreurs:
        print(f"\n{len(erreurs)} erreur(s) :")
        for chemin, message in erreurs:
            print(f"  [ERREUR] {chemin} : {message}")


if __name__ == "__main__":
    main()
