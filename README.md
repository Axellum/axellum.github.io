# axellum.github.io · auxfilsdesidees.fr

Les pages des projets d'Axel Duviella, en français et en anglais (`/en/…`).

- **Écrire** : le contenu est dans `contenu/fr/` et `contenu/en/` (un fichier par page, en-tête « clé: valeur » puis
  le corps HTML ; voir `construire.py`). `python construire.py` écrit les pages (`index.html`, `vigie/`,
  `en/vigie/`…) et `auxfilsdesidees/sitemap.xml`. Ne pas modifier les pages écrites à la main : la CI
  (`python construire.py --verifier`) échoue si elles diffèrent du contenu.

  Titre 60 caractères au plus, description 155 au plus : `construire.py` refuse au-delà.
- **Images de partage** : `python outils/cartes_partage.py` (Chrome et Pillow, sur le poste) refait
  `assets/partage/<langue>-<paire>.jpg` (1200 × 630) à partir du titre et de l'image du haut de chaque page ; à relancer
  quand l'un des deux change, puis `python construire.py`.
- **Nouveautés** : après une release GitHub d'un projet, `python outils/nouveautes.py` met à jour
  `contenu/nouveautes.json` (versions publiées, hors préversions) ; écrire le titre français qu'il signale, puis
  `python construire.py` refait la page `/nouveautes/` (`/en/news/`), les trois dernières versions de l'accueil et les
  flux RSS (`rss.xml` dans le dossier de chaque page). La CI ne lit que le fichier, jamais GitHub.
- **Exemples de configuration** : `exemples/fr/` et `exemples/en/` (même code, commentaires et textes traduits).
  `<!--exemple nom-->` dans un corps les met en bloc de code (bouton « Copier »). Les valider avant de publier :
  `esphome config`, et `esphome compile` avec ESPHome 2026.9.1 au moins (pour les essais, un `name:` à part pour ne
  pas écraser le dossier de build d'un appareil) ; la CI ne le fait pas.
- **Anciennes adresses** : `REDIRECTIONS` dans `construire.py` écrit à l'ancienne adresse une page qui renvoie vers la
  nouvelle (`/ecran-vigie/` depuis le 28/10/2026). Ne pas en retirer une : des liens extérieurs peuvent y mener.

- **auxfilsdesidees.fr** : servie par le Caddy du serveur de Vigie. `./deploy.sh` y copie toutes les pages, les images,
  `auxfilsdesidees/robots.txt`, la clé IndexNow (`auxfilsdesidees/<clé>.txt`) et `auxfilsdesidees/sitemap.xml` ;
  `./deploy.sh caddy` installe aussi `auxfilsdesidees/site.caddy` (une fois, puis à chaque changement de ce fichier) et
  redémarre Caddy. Après un déploiement, `python outils/indexnow.py` signale les pages du sitemap à Bing et aux autres
  moteurs IndexNow.
- **axellum.github.io** : GitHub Pages sert ce dépôt tel quel. Le `robots.txt` de la racine est celui de ce domaine :
  il donne le sitemap du site du Tab5 (`/M5-Tab5-ESPHome-LVGL/`). Les pages y ont leur adresse officielle
  (canonique) sur auxfilsdesidees.fr.
- `googleffef8cbebd0245e5.html` : validation de la propriété `https://axellum.github.io/` dans la Search Console,
  à ne pas supprimer.

Un dossier de ce dépôt ne doit jamais porter le nom d'un autre dépôt publié par GitHub Pages
(`M5-Tab5-ESPHome-LVGL`, …) : il entrerait en conflit avec son site.
