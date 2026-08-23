# Aide de l’application Unshiter

Unshiter compare les caractéristiques statistiques de textes littéraires. Les mesures décrivent les textes ; elles ne constituent pas un jugement de qualité littéraire.

## Choisir les textes

Le panneau **Auteurs** permet de déployer ou replier chaque auteur. Les cases à cocher sélectionnent les œuvres affichées dans les graphiques et les tableaux.

Le bouton situé au bas de la liste alterne entre **Tout décocher** et **Tout cocher**. La sélection est conservée dans le navigateur.

## Choisir les mesures

Le panneau **Mesures du radar** contient toutes les mesures disponibles. Les mesures cochées sont utilisées pour le radar, la couverture stylistique, les surfaces et les courbes associées.

Le bouton `↔` inverse le sens d’affichage d’une mesure. Le bouton `?` ouvre sa définition détaillée. Les inversions et les mesures sélectionnées peuvent être enregistrées dans une configuration.

## Radar

Le radar compare les textes sélectionnés. Les limites des axes sont calculées sur l’ensemble du corpus, pas seulement sur la sélection courante. Cliquer sur une entrée de légende la place au premier plan et remplit sa surface.

Les boutons **Limites**, **Auteurs** et **Œuvres** changent le niveau de comparaison : œuvres individuelles, profils moyens des auteurs ou limites du corpus. Les profils d’auteurs utilisent les valeurs médianes dans les tableaux.

## Couverture stylistique

La couverture stylistique est la surface du profil dans le radar. Elle sert à comparer des silhouettes statistiques ; ce n’est pas un score de qualité.

## Courbes de mesures

En mode œuvres, les courbes suivent l’ordre chronologique des dates de publication. En mode auteurs, chaque courbe utilise un profil médian par auteur et trie les auteurs de la valeur affichée la plus faible à la plus forte. Les valeurs sont annotées directement sur les points. Les textes IA sont affichés en gras.

## Voisinage stylistique

La référence peut être une œuvre ou un auteur. Les voisins sont classés par proximité statistique. L’œuvre épinglée est insérée à son rang réel et apparaît en rouge, sans doublon. Le nombre de lignes peut être choisi par pas de cinq ou réglé sur **Tous**.

Le voisinage est calculé à partir des mesures stylistiques standardisées sur tout le corpus. Une proximité statistique ne prouve ni une attribution d’auteur ni une influence.

## Singularité et carte MDS

Les vues **Singularité** et **Carte MDS** sont accessibles en bas de la page. La carte MDS projette les distances stylistiques dans deux dimensions ; ses axes n’ont pas d’interprétation littéraire directe. Les boutons `+`, `−` et **Réinitialiser** contrôlent son zoom.

## Télécharger

Les sélecteurs de téléchargement proposent le format PNG ou SVG pour les graphiques. Le tableau de voisinage possède également son propre téléchargement. Les exports utilisent le titre visible du graphique ou du tableau.

## Configurations

Le bouton **Sauvegarder la configuration** enregistre sous un nom les œuvres sélectionnées, le mode œuvres/auteurs, les mesures cochées, leurs inversions et les paramètres du voisinage. Cliquer sur le nom d’une configuration la recharge. La croix supprime une configuration. **Réinitialiser** revient à la configuration initiale sans supprimer les configurations sauvegardées.

## Données pour analyse

Le bouton **Prompt d’analyse** télécharge le prompt éditable. Le bouton **Données pour analyse** exporte en JSON toutes les mesures disponibles pour les œuvres sélectionnées, leurs définitions, leurs métadonnées et leur couverture stylistique.
