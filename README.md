# Unshiter — détecteur statistique

Analyse comparative de textes français : rythme, répétitions, structures
syntaxiques, répartition grammaticale et indice IA expérimental.

## Utilisation

Placez les fichiers Markdown à comparer dans `sources/`, puis lancez :

```bash
./stats.sh
```

Le rapport comparatif, les structures et le graphique grammatical sont générés
dans `_output/`.

Pour analyser un fichier précis et produire ses rapports Markdown et JSON :

```bash
./stats.sh sources/lettre1.md
```

## Installation

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

## Organisation

- `script/detector/` : code du détecteur statistique ;
- `assets/` : base Morphalou, mots-outils et notes des mesures ;
- `sources/` : corpus Markdown versionnable ;
- `_output/` : rapports générés, non versionnés ;
- `script/detector/tests/` : tests automatisés du détecteur.

Tous les chemins utilisés par le détecteur sont centralisés dans
`script/detector/config.py`.

## Tests

```bash
PYTHONPATH=script python3 -m unittest discover -s script/detector/tests -v
```
