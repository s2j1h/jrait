# verif-dates-exif

Outils pour vérifier la cohérence entre les dates EXIF des photos JPEG et le nom du dossier qui les contient.

## Contexte

Ce dépôt part d'une convention de rangement des photos par dossiers datés :

```
AAAA-MM-JJ_libelle   (ex. 2026-08-09_vacances)  -> photos prises ce jour-là
AAAA-MM_libelle      (ex. 2026-08_vacances)     -> photos prises ce mois-là
```

Le but est de détecter les photos mal classées, c'est-à-dire dont la date de prise de vue (EXIF) ne correspond pas à la date indiquée par le dossier parent. Quand le dossier ne précise que l'année et le mois, seule la correspondance année-mois est vérifiée (le jour n'est pas contraint).

Le dépôt contient deux outils indépendants :

| Fichier | Rôle |
|---|---|
| [verif-dates-exif.py](verif-dates-exif.py) | Parcourt un répertoire, compare les dates EXIF au nom du dossier, produit un rapport CSV avec un statut de cohérence par photo. |
| [ajoute-dates-exif.py](ajoute-dates-exif.py) | Force les trois dates EXIF de toutes les photos d'un répertoire à une même date donnée en paramètre (écrase les dates existantes ou les crée). |
| [verif-dates-exif.sh](verif-dates-exif.sh) | Affiche rapidement les trois dates EXIF de chaque photo d'un répertoire, sans analyse de cohérence (basé sur `exiftool`). |
| [dates_exif.csv](dates_exif.csv) | Exemple de rapport généré par le script Python. |

## Installation

Les scripts Python nécessitent Python 3 et les dépendances listées dans [requirements.txt](requirements.txt) (`pillow` pour `verif-dates-exif.py`, `piexif` pour `ajoute-dates-exif.py`). Dans un environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## verif-dates-exif.py

### Dépendances

- Python 3
- [Pillow](https://python-pillow.org/) : `pip install pillow`

### Usage

```bash
python3 verif-dates-exif.py <repertoire> [fichier_sortie.csv]
```

- `repertoire` : dossier à analyser (parcouru récursivement).
- `fichier_sortie.csv` : optionnel, `dates_exif.csv` par défaut.

Exemples :

```bash
python3 verif-dates-exif.py "/Volumes/homes"
python3 verif-dates-exif.py "/Volumes/homes" rapport.csv
```

### Fonctionnement

Pour chaque fichier `.jpg` / `.jpeg` rencontré lors du parcours :

1. Lecture des tags EXIF via Pillow :
   - `DateTimeOriginal` (date de prise de vue)
   - `DateTimeDigitized` (date de numérisation)
   - `DateTime` (date de dernière modification)
2. Extraction de la date en tête du nom du dossier parent :
   - d'abord au format `AAAA-MM-JJ` (regex `^(\d{4})-(\d{2})-(\d{2})(?:[_\-\s].*)?$`) → comparaison au jour près ;
   - à défaut, au format `AAAA-MM` (regex `^(\d{4})-(\d{2})(?:[_\-\s].*)?$`) → comparaison au mois près uniquement.
   Dans les deux cas, un contrôle sommaire vérifie que le mois (et le jour, le cas échéant) sont dans une plage valide.
3. Comparaison entre la date de prise de vue et la date du dossier (jour exact ou année-mois selon le format détecté) pour déterminer un statut de cohérence.

### Colonnes du CSV produit

Séparateur `;`, encodage `utf-8-sig` (BOM pour un affichage correct des accents dans Excel).

| Colonne | Description |
|---|---|
| `repertoire` | Chemin du dossier parent de la photo |
| `fichier` | Nom du fichier |
| `date_creation` | `DateTimeOriginal` normalisée (`AAAA-MM-JJ HH:MM:SS`) |
| `date_numerisation` | `DateTimeDigitized` normalisée |
| `date_modification` | `DateTime` (ModifyDate) normalisée |
| `coherence` | Voir ci-dessous |

### Valeurs de la colonne `coherence`

| Valeur | Signification |
|---|---|
| `COHERENT` | La date de prise de vue correspond à la date du dossier (jour exact, ou année-mois si le dossier ne précise pas le jour) |
| `INCOHERENT` | La date de prise de vue diffère de la date du dossier |
| `DOSSIER_SANS_DATE` | Le nom du dossier ne commence pas par une date `AAAA-MM-JJ` ou `AAAA-MM` valide |
| `EXIF_SANS_DATE` | Le dossier a une date, mais `DateTimeOriginal` est absent/illisible dans l'EXIF |
| `ERREUR_LECTURE` | Le fichier n'a pas pu être ouvert (image corrompue, format invalide, etc.) |

### Progression

Pendant le traitement, une ligne est mise à jour en place (sans défiler) indiquant le nombre de photos traitées et le dossier en cours d'analyse, rafraîchie au maximum 5 fois par seconde pour ne pas ralentir le script sur de gros volumes.

### Récapitulatif console

À la fin de l'exécution, le script affiche le nombre total de photos traitées et la répartition par statut de cohérence.

## ajoute-dates-exif.py

Force les trois dates EXIF (prise de vue, numérisation, modification) de toutes les photos JPG/JPEG d'un répertoire à une seule et même date, donnée en paramètre. Utile pour dater un lot de photos qui n'en ont pas (scans, exports sans métadonnées) ou pour corriger un lot mal daté.

- Si le fichier a déjà des dates EXIF, elles sont **écrasées**.
- S'il n'en a aucune, elles sont **créées**.
- Les autres métadonnées EXIF (appareil photo, GPS, etc.) sont conservées telles quelles.
- Seul le bloc de métadonnées est réécrit : l'image n'est **pas réencodée**, ses pixels restent identiques (pas de perte de qualité JPEG).

### Dépendances

- Python 3
- [piexif](https://github.com/hMatoba/Piexif) : `pip install piexif`

### Usage

```bash
python3 ajoute-dates-exif.py <repertoire> <date> [--dry-run]
```

- `repertoire` : dossier à traiter (parcouru récursivement).
- `date` : date à appliquer, au format `AAAA-MM-JJ` ou `"AAAA-MM-JJ HH:MM:SS"` (heure omise → `00:00:00`).
- `--dry-run` : n'écrit rien, affiche seulement les fichiers qui seraient modifiés.

Exemples :

```bash
python3 ajoute-dates-exif.py "/Volumes/homes/2026-08-09_vacances" 2026-08-09
python3 ajoute-dates-exif.py "/Volumes/homes/2026-08-09_vacances" "2026-08-09 14:30:00"
python3 ajoute-dates-exif.py "/Volumes/homes/2026-08-09_vacances" 2026-08-09 --dry-run
```

### Tags EXIF renseignés

| Tag | IFD | Rôle |
|---|---|---|
| `DateTime` (0x0132) | IFD0 | Date de modification |
| `DateTimeOriginal` (0x9003) | Exif | Date de prise de vue |
| `DateTimeDigitized` (0x9004) | Exif | Date de numérisation |

Les trois sont réglés à la même valeur, celle passée en paramètre.

### Progression et résumé

Comme `verif-dates-exif.py`, une ligne de progression est affichée pendant le traitement (mise à jour en place, rafraîchie au maximum 5x/seconde), suivie d'un résumé indiquant le nombre de photos traitées et, le cas échéant, la liste des fichiers en erreur.

## verif-dates-exif.sh

Complément rapide en ligne de commande, sans génération de CSV ni analyse de cohérence : affiche une ligne par photo avec ses trois dates EXIF.

### Dépendance

- [exiftool](https://exiftool.org/) : `brew install exiftool`

### Usage

```bash
./verif-dates-exif.sh [repertoire] [-r]
```

- `repertoire` : dossier à analyser (par défaut, le répertoire courant).
- `-r` : parcours récursif des sous-dossiers.

Exemples :

```bash
./verif-dates-exif.sh ~/Photos
./verif-dates-exif.sh ~/Photos -r
```

Pour chaque photo, affiche : `chemin | Créé: ... | Numér.: ... | MàJ: ...` (valeurs manquantes affichées comme `(absente)`).
