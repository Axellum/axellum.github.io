# axellum.github.io · auxfilsdesidees.fr

La page des projets d'Axel Duviella, en français (`index.html`) et en anglais (`en/`).

- **auxfilsdesidees.fr** : servie par le Caddy du serveur de Vigie. `./deploy.sh` y copie les pages, les images,
  `auxfilsdesidees/robots.txt` et `auxfilsdesidees/sitemap.xml` ; `./deploy.sh caddy` installe aussi
  `auxfilsdesidees/site.caddy` (une fois, puis à chaque changement de ce fichier) et redémarre Caddy.
- **axellum.github.io** : GitHub Pages sert ce dépôt tel quel. Le `robots.txt` de la racine est celui de ce domaine :
  il donne le sitemap du site du Tab5 (`/M5-Tab5-ESPHome-LVGL/`). Les pages y ont leur adresse officielle
  (canonique) sur auxfilsdesidees.fr.
- `googleffef8cbebd0245e5.html` : validation de la propriété `https://axellum.github.io/` dans la Search Console,
  à ne pas supprimer.

Un dossier de ce dépôt ne doit jamais porter le nom d'un autre dépôt publié par GitHub Pages
(`M5-Tab5-ESPHome-LVGL`, …) : il entrerait en conflit avec son site.
