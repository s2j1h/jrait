#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verif-dates-exif.py

Parcourt un répertoire (récursivement) et produit un fichier CSV recensant,
pour chaque photo JPG/JPEG, ses trois dates EXIF ainsi qu'un flag indiquant
si la date de prise de vue est cohérente avec le nom du dossier parent.

Convention de nommage attendue pour les dossiers :
    AAAA-MM-JJ_libelle   (ex. 2026-08-09_vacances)
Le dossier « 2026-08-09_... » est censé contenir des photos prises ce jour-là.

Colonnes du CSV produit :
    1. repertoire        : chemin du dossier parent de la photo
    2. fichier           : nom du fichier
    3. date_creation     : DateTimeOriginal (prise de vue)
    4. date_numerisation : CreateDate / DateTimeDigitized
    5. date_modification : ModifyDate / DateTime
    6. coherence         : COHERENT | INCOHERENT | DOSSIER_SANS_DATE
                           | EXIF_SANS_DATE | ERREUR_LECTURE

Dépendance : Pillow  (pip install pillow)

Usage :
    python3 verif-dates-exif.py <repertoire> [fichier_sortie.csv]

Exemples :
    python3 verif-dates-exif.py "/Volumes/homes"
    python3 verif-dates-exif.py "/Volumes/homes" rapport.csv
"""

import csv
import os
import re
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Erreur : Pillow n'est pas installé.  ->  pip install pillow")

# --- Identifiants des tags EXIF utilisés ---------------------------------
TAG_DATETIME          = 0x0132   # 306   -> ModifyDate  (IFD principal)
TAG_EXIF_IFD          = 0x8769   # 34665 -> pointeur vers le sous-IFD Exif
TAG_DATETIME_ORIGINAL = 0x9003   # 36867 -> DateTimeOriginal   (prise de vue)
TAG_DATETIME_DIGITIZED = 0x9004  # 36868 -> DateTimeDigitized   (numérisation)

# Extensions traitées (comparaison insensible à la casse)
EXTENSIONS = (".jpg", ".jpeg")

# Date en tête de nom de dossier : AAAA-MM-JJ suivi de rien, d'un _, - ou espace
RE_DATE_DOSSIER = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[_\-\s].*)?$")

# Format d'une date EXIF brute : "AAAA:MM:JJ HH:MM:SS"
RE_DATE_EXIF = re.compile(r"^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})")


def normaliser_date_exif(valeur):
    """Transforme 'AAAA:MM:JJ HH:MM:SS' en 'AAAA-MM-JJ HH:MM:SS'.
    Renvoie ('', None) si la valeur est absente ou illisible."""
    if not valeur:
        return "", None
    valeur = str(valeur).strip().rstrip("\x00")
    m = RE_DATE_EXIF.match(valeur)
    if not m:
        return valeur, None  # on garde la valeur brute, mais jour inconnu
    annee, mois, jour, h, mn, s = m.groups()
    jour_iso = f"{annee}-{mois}-{jour}"
    return f"{jour_iso} {h}:{mn}:{s}", jour_iso


def lire_dates_exif(chemin):
    """Renvoie un tuple :
        (creation_str, jour_creation, numerisation_str, modification_str, erreur)
    'jour_creation' est la date (AAAA-MM-JJ) issue de DateTimeOriginal, ou None.
    'erreur' vaut True si le fichier n'a pas pu être ouvert/lu."""
    try:
        with Image.open(chemin) as img:
            exif = img.getexif()
    except Exception:
        return "", None, "", "", True

    if not exif:
        return "", None, "", "", False

    # ModifyDate se trouve dans l'IFD principal
    modification = exif.get(TAG_DATETIME)

    # DateTimeOriginal et DateTimeDigitized sont dans le sous-IFD Exif
    creation = numerisation = None
    try:
        sous_ifd = exif.get_ifd(TAG_EXIF_IFD)
    except Exception:
        sous_ifd = {}
    if sous_ifd:
        creation = sous_ifd.get(TAG_DATETIME_ORIGINAL)
        numerisation = sous_ifd.get(TAG_DATETIME_DIGITIZED)

    creation_str, jour_creation = normaliser_date_exif(creation)
    numerisation_str, _ = normaliser_date_exif(numerisation)
    modification_str, _ = normaliser_date_exif(modification)

    return creation_str, jour_creation, numerisation_str, modification_str, False


def date_du_dossier(nom_dossier):
    """Extrait 'AAAA-MM-JJ' d'un nom de dossier comme '2026-08-09_libelle'.
    Renvoie None si le nom ne commence pas par une date valide."""
    m = RE_DATE_DOSSIER.match(nom_dossier)
    if not m:
        return None
    annee, mois, jour = m.groups()
    # contrôle sommaire de validité
    if not (1 <= int(mois) <= 12 and 1 <= int(jour) <= 31):
        return None
    return f"{annee}-{mois}-{jour}"


def evaluer_coherence(jour_creation, jour_dossier, erreur):
    """Détermine la valeur de la colonne 'coherence'."""
    if erreur:
        return "ERREUR_LECTURE"
    if jour_dossier is None:
        return "DOSSIER_SANS_DATE"
    if jour_creation is None:
        return "EXIF_SANS_DATE"
    return "COHERENT" if jour_creation == jour_dossier else "INCOHERENT"


def main():
    if len(sys.argv) < 2:
        sys.exit(
            "Usage : python3 verif-dates-exif.py <repertoire> [fichier_sortie.csv]"
        )

    racine = sys.argv[1]
    sortie = sys.argv[2] if len(sys.argv) > 2 else "dates_exif.csv"

    if not os.path.isdir(racine):
        sys.exit(f"Erreur : le répertoire « {racine} » n'existe pas.")

    print(f"Analyse de : {racine}")
    print(f"Sortie CSV : {sortie}\n")

    compteur = {"total": 0, "COHERENT": 0, "INCOHERENT": 0,
                "DOSSIER_SANS_DATE": 0, "EXIF_SANS_DATE": 0, "ERREUR_LECTURE": 0}

    # utf-8-sig : ajoute un BOM pour qu'Excel affiche correctement les accents
    with open(sortie, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f,delimiter=";")  # séparateur virgule ; passe à delimiter=";" pour Excel FR
        writer.writerow([
            "repertoire", "fichier",
            "date_creation", "date_numerisation", "date_modification",
            "coherence",
        ])

        for dossier, _sous_dossiers, fichiers in os.walk(racine):
            jour_dossier = date_du_dossier(os.path.basename(dossier))
            for nom in sorted(fichiers):
                if not nom.lower().endswith(EXTENSIONS):
                    continue
                chemin = os.path.join(dossier, nom)
                (creation_str, jour_creation, numerisation_str,
                 modification_str, erreur) = lire_dates_exif(chemin)

                coherence = evaluer_coherence(jour_creation, jour_dossier, erreur)

                writer.writerow([
                    dossier, nom,
                    creation_str, numerisation_str, modification_str,
                    coherence,
                ])

                compteur["total"] += 1
                compteur[coherence] = compteur.get(coherence, 0) + 1

    # --- Récapitulatif à l'écran -----------------------------------------
    print(f"{compteur['total']} photo(s) traitée(s).")
    print(f"  COHERENT           : {compteur['COHERENT']}")
    print(f"  INCOHERENT         : {compteur['INCOHERENT']}")
    print(f"  DOSSIER_SANS_DATE  : {compteur['DOSSIER_SANS_DATE']}")
    print(f"  EXIF_SANS_DATE     : {compteur['EXIF_SANS_DATE']}")
    print(f"  ERREUR_LECTURE     : {compteur['ERREUR_LECTURE']}")
    print(f"\nRapport écrit dans : {sortie}")


if __name__ == "__main__":
    main()
