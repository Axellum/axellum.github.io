# axellum.github.io · auxfilsdesidees.fr

Les pages des projets d'Axel Duviella, en français et en anglais (`/en/…`).

- **Écrire** : le contenu est dans `contenu/fr/` et `contenu/en/` (un fichier par page, en-tête « clé: valeur » puis
  le corps HTML ; voir `construire.py`). `python construire.py` écrit les pages (`index.html`, `vigie/`,
  `en/vigie/`…) et `auxfilsdesidees/sitemap.xml`. Ne pas modifier les pages écrites à la main : la CI
  (`python construire.py --verifier`) échoue si elles diffèrent du contenu.

- **auxfilsdesidees.fr** : servie par le Caddy du serveur de Vigie. `./deploy.sh` y copie toutes les pages, les images,
  `auxfilsdesidees/robots.txt` et `auxfilsdesidees/sitemap.xml` ; `./deploy.sh caddy` installe aussi
  `auxfilsdesidees/site.caddy` (une fois, puis à chaque changement de ce fichier) et redémarre Caddy.
- **axellum.github.io** : GitHub Pages sert ce dépôt tel quel. Le `robots.txt` de la racine est celui de ce domaine :
  il donne le sitemap du site du Tab5 (`/M5-Tab5-ESPHome-LVGL/`). Les pages y ont leur adresse officielle
  (canonique) sur auxfilsdesidees.fr.
- `googleffef8cbebd0245e5.html` : validation de la propriété `https://axellum.github.io/` dans la Search Console,
  à ne pas supprimer.

Un dossier de ce dépôt ne doit jamais porter le nom d'un autre dépôt publié par GitHub Pages
(`M5-Tab5-ESPHome-LVGL`, …) : il entrerait en conflit avec son site.
