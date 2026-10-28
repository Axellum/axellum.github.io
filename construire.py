#!/usr/bin/env python3
"""Construit les pages du site à partir de contenu/<langue>/*.html (Python 3.11+, sans dépendance).

Chaque fichier de contenu commence par un en-tête « clé: valeur » terminé par une ligne « --- », puis le corps HTML.
Clés : chemin (adresse de la page, ex. /vigie/), paire (identifiant commun à la page FR et à la page EN),
titre (balise <title>), description, image (partage, sous /assets/), fil (nom dans le fil d'Ariane, absent sur
l'accueil), ordre (place dans la navigation, absent = hors navigation), menu (nom dans la navigation),
groupe (nom d'un sous-menu : les pages du même groupe sont rangées dessous, à la place de la première).
Un bloc <!--ld … ld--> dans le corps est un objet JSON-LD de plus, ajouté au graphe de la page.

  python construire.py            # écrit les pages et auxfilsdesidees/sitemap.xml
  python construire.py --verifier # échoue si une page écrite diffère de ce que le contenu produit (CI)
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
SITE = "https://auxfilsdesidees.fr"
LANGUES = ("fr", "en")
TEXTES = {
	"fr": {
		"marque": "Aux fils des idées",
		"accueil": "Accueil",
		"navigation": "Navigation principale",
		"fil": "Fil d'Ariane",
		"autre": "English",
		"locale": "fr_FR",
		"pied": (
			"<p>Projets personnels, non commerciaux, faits avec l'aide de l'IA et testés surtout chez moi. "
			"Retours bienvenus sur <a href=\"https://github.com/Axellum\">GitHub</a>.</p>\n"
			"\t<p>Éditeur : Axel Duviella, particulier, à titre non professionnel (France). Contact : "
			"<a href=\"https://github.com/Axellum\">github.com/Axellum</a>. Hébergeur : OVH SAS, 2 rue Kellermann, "
			"59100 Roubaix, France (<a href=\"https://www.ovhcloud.com/fr/\">ovhcloud.com</a>). Ce site ne dépose aucun "
			"cookie et ne mesure pas ses visites.</p>"
		),
	},
	"en": {
		"marque": "Aux fils des idées",
		"accueil": "Home",
		"navigation": "Main navigation",
		"fil": "Breadcrumb",
		"autre": "Français",
		"locale": "en_US",
		"pied": (
			"<p>Personal, non-commercial projects, made with the help of AI and tested mostly at home. "
			"Feedback welcome on <a href=\"https://github.com/Axellum\">GitHub</a>.</p>\n"
			"\t<p>Publisher: Axel Duviella, private individual, non-professional (France). Contact: "
			"<a href=\"https://github.com/Axellum\">github.com/Axellum</a>. Host: OVH SAS, 2 rue Kellermann, "
			"59100 Roubaix, France (<a href=\"https://www.ovhcloud.com/en/\">ovhcloud.com</a>). This site sets no "
			"cookies and does not measure its visits.</p>"
		),
	},
}
# Empreinte de la feuille de style dans son adresse : /assets/ est gardé 7 jours en cache par les navigateurs
# (Caddy), une feuille modifiée doit changer d'adresse pour être rechargée.
STYLE = "/assets/style.css?v=" + hashlib.sha256((ICI / "assets" / "style.css").read_text(encoding="utf-8").encode()).hexdigest()[:10]
PERSONNE = {
	"@type": "Person",
	"@id": f"{SITE}/#axel",
	"name": "Axel Duviella",
	"url": f"{SITE}/",
	"sameAs": ["https://github.com/Axellum"],
}


def lire(fichier: Path, langue: str) -> dict:
	brut = fichier.read_text(encoding="utf-8")
	tete, separateur, corps = brut.partition("\n---\n")
	if not separateur:
		sys.exit(f"{fichier} : en-tête sans ligne « --- »")
	page = {"langue": langue, "source": fichier}
	for ligne in tete.splitlines():
		cle, _, valeur = ligne.partition(":")
		page[cle.strip()] = valeur.strip()
	for cle in ("chemin", "paire", "titre", "description"):
		if not page.get(cle):
			sys.exit(f"{fichier} : clé « {cle} » manquante")
	page["ld"] = [json.loads(bloc) for bloc in re.findall(r"<!--ld(.*?)ld-->", corps, re.S)]
	page["corps"] = re.sub(r"\s*<!--ld.*?ld-->\s*", "\n", corps, flags=re.S).strip("\n")
	return page


def sortie(chemin: str) -> Path:
	return ICI / chemin.strip("/") / "index.html" if chemin != "/" else ICI / "index.html"


def entete_navigation(page: dict, pages: list[dict], autre: dict) -> str:
	t = TEXTES[page["langue"]]
	accueil = "/" if page["langue"] == "fr" else "/en/"
	liens, groupes = [], {}
	for p in sorted((p for p in pages if p["langue"] == page["langue"] and p.get("ordre")), key=lambda p: int(p["ordre"])):
		courant = ' aria-current="page"' if p is page else ""
		lien = f'<li><a href="{p["chemin"]}"{courant}>{html.escape(p.get("menu") or p["fil"])}</a></li>'
		if not p.get("groupe"):
			liens.append(lien)
			continue
		if p["groupe"] not in groupes:
			groupes[p["groupe"]] = []
			liens.append(p["groupe"])
		groupes[p["groupe"]].append((lien, p is page))
	for i, lien in enumerate(liens):
		if lien in groupes:
			sous = groupes[lien]
			classe = "groupe courant" if any(c for _, c in sous) else "groupe"
			liens[i] = (
				f'<li class="{classe}"><details><summary>{html.escape(lien)}</summary>'
				f'<ul>{"".join(l for l, _ in sous)}</ul></details></li>'
			)
	autre_langue = "en" if page["langue"] == "fr" else "fr"
	return (
		'<header class="haut">\n'
		'\t<div class="ligne">\n'
		f'\t\t<a class="marque" href="{accueil}">{t["marque"]}</a>\n'
		f'\t\t<a class="langue" href="{autre["chemin"]}" hreflang="{autre_langue}" lang="{autre_langue}">{t["autre"]}</a>\n'
		'\t</div>\n'
		f'\t<nav class="menu" aria-label="{t["navigation"]}"><ul>{"".join(liens)}</ul></nav>\n'
		'</header>'
	)


def fil_ariane(page: dict) -> tuple[str, dict | None]:
	if not page.get("fil"):
		return "", None
	t = TEXTES[page["langue"]]
	accueil = "/" if page["langue"] == "fr" else "/en/"
	visible = (
		f'<nav class="fil" aria-label="{t["fil"]}"><a href="{accueil}">{t["accueil"]}</a>'
		f' <span aria-hidden="true">›</span> <span aria-current="page">{html.escape(page["fil"])}</span></nav>\n'
	)
	ld = {
		"@type": "BreadcrumbList",
		"itemListElement": [
			{"@type": "ListItem", "position": 1, "name": t["accueil"], "item": SITE + accueil},
			{"@type": "ListItem", "position": 2, "name": page["fil"], "item": SITE + page["chemin"]},
		],
	}
	return visible, ld


def rendre(page: dict, pages: list[dict], par_paire: dict) -> str:
	t = TEXTES[page["langue"]]
	fr, en = par_paire[page["paire"]]["fr"], par_paire[page["paire"]]["en"]
	autre = en if page["langue"] == "fr" else fr
	url = SITE + page["chemin"]
	image = SITE + "/assets/" + (page.get("image") or "partage.jpg")
	visible, ld_fil = fil_ariane(page)
	graphe = [
		{
			"@type": "WebSite",
			"@id": f"{SITE}/#site",
			"url": f"{SITE}/",
			"name": t["marque"],
			"inLanguage": ["fr", "en"],
			"publisher": {"@id": f"{SITE}/#axel"},
		},
		PERSONNE,
		{
			"@type": "WebPage",
			"@id": url + "#page",
			"url": url,
			"name": page["titre"],
			"description": page["description"],
			"inLanguage": page["langue"],
			"isPartOf": {"@id": f"{SITE}/#site"},
			"primaryImageOfPage": image,
		},
	]
	if ld_fil:
		graphe.append(ld_fil)
	for objet in page["ld"]:
		objet.setdefault("author", {"@id": f"{SITE}/#axel"})
		graphe.append(objet)
	ld = json.dumps({"@context": "https://schema.org", "@graph": graphe}, ensure_ascii=False, indent="\t")
	e = html.escape
	autre_locale = TEXTES["en" if page["langue"] == "fr" else "fr"]["locale"]
	return f"""<!doctype html>
<html lang="{page["langue"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(page["titre"])}</title>
<meta name="description" content="{e(page["description"])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{SITE}{fr["chemin"]}">
<link rel="alternate" hreflang="en" href="{SITE}{en["chemin"]}">
<link rel="alternate" hreflang="x-default" href="{SITE}{en["chemin"]}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{t["locale"]}">
<meta property="og:locale:alternate" content="{autre_locale}">
<meta property="og:site_name" content="{t["marque"]}">
<meta property="og:title" content="{e(page["titre"])}">
<meta property="og:description" content="{e(page["description"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#10151c" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f6f5f1" media="(prefers-color-scheme: light)">
<link rel="icon" href="/assets/icone.svg" type="image/svg+xml">
<link rel="stylesheet" href="{STYLE}">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
<div class="page">
{entete_navigation(page, pages, autre)}

<main>
{visible}{page["corps"]}
</main>

<footer class="bas">
	{t["pied"]}
</footer>
</div>
<script>
/* Sous-menus : fermés par un clic ailleurs ou la touche Échap. */
document.addEventListener("click", e => document.querySelectorAll("nav.menu details[open]").forEach(d => d.contains(e.target) || d.removeAttribute("open")));
document.addEventListener("keydown", e => e.key === "Escape" && document.querySelectorAll("nav.menu details[open]").forEach(d => d.removeAttribute("open")));
</script>
</body>
</html>
"""


def sitemap(pages: list[dict], par_paire: dict) -> str:
	lignes = [
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" '
		'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
	]
	for page in pages:
		paire = par_paire[page["paire"]]
		lignes.append("  <url>")
		lignes.append(f"    <loc>{SITE}{page['chemin']}</loc>")
		for langue in LANGUES:
			lignes.append(f'    <xhtml:link rel="alternate" hreflang="{langue}" href="{SITE}{paire[langue]["chemin"]}"/>')
		lignes.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{paire["en"]["chemin"]}"/>')
		images = dict.fromkeys(re.findall(r'<img[^>]+src="(/assets/[^"]+)"', page["corps"]))
		for image in images:
			lignes.append(f"    <image:image><image:loc>{SITE}{image}</image:loc></image:image>")
		lignes.append("  </url>")
	lignes.append("</urlset>")
	return "\n".join(lignes) + "\n"


def main() -> int:
	verifier = "--verifier" in sys.argv
	pages = [lire(f, langue) for langue in LANGUES for f in sorted((ICI / "contenu" / langue).glob("*.html"))]
	par_paire: dict[str, dict] = {}
	for page in pages:
		par_paire.setdefault(page["paire"], {})[page["langue"]] = page
	for paire, versions in par_paire.items():
		if set(versions) != set(LANGUES):
			sys.exit(f"page « {paire} » : il manque une langue ({', '.join(sorted(versions))})")
	attendu = {sortie(p["chemin"]): rendre(p, pages, par_paire) for p in pages}
	attendu[ICI / "auxfilsdesidees" / "sitemap.xml"] = sitemap(pages, par_paire)
	ecarts = []
	for fichier, texte in attendu.items():
		actuel = fichier.read_text(encoding="utf-8") if fichier.exists() else None
		if actuel == texte:
			continue
		if verifier:
			ecarts.append(fichier.relative_to(ICI).as_posix())
		else:
			fichier.parent.mkdir(parents=True, exist_ok=True)
			fichier.write_text(texte, encoding="utf-8", newline="\n")
			print("écrit", fichier.relative_to(ICI).as_posix())
	if ecarts:
		print("pages à reconstruire (python construire.py) :", *ecarts, sep="\n  ")
		return 1
	print(f"{len(pages)} pages à jour")
	return 0


if __name__ == "__main__":
	sys.exit(main())
