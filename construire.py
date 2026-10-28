#!/usr/bin/env python3
"""Construit les pages du site à partir de contenu/<langue>/*.html (Python 3.11+, sans dépendance).

Chaque fichier de contenu commence par un en-tête « clé: valeur » terminé par une ligne « --- », puis le corps HTML.
Clés : chemin (adresse de la page, ex. /vigie/), paire (identifiant commun à la page FR et à la page EN),
titre (balise <title>), description, image (partage, sous /assets/), fil (nom dans le fil d'Ariane, absent sur
l'accueil), ordre (place dans la navigation, absent = hors navigation), menu (nom dans la navigation),
parent (paire de la page du projet : la page est alors une sous-page, rangée par « ordre » dans le menu de gauche).
Menu du haut : les projets. Menu de gauche : les pages du projet et les sections (<h2 id>) de la page ouverte.
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
		"presentation": "Présentation",
		"cote": "Pages du projet",
		"sommaire": "Sur cette page",
		"evitement": "Aller au contenu",
		"projets": "Projets",
		"ailleurs": "Ailleurs",
		"doc_tab5": "Doc du Tab5",
		"devise": "Des écrans et des outils pour la maison, faits avec l'IA et partagés au cas où.",
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
		"presentation": "Overview",
		"cote": "Project pages",
		"sommaire": "On this page",
		"evitement": "Skip to content",
		"projets": "Projects",
		"ailleurs": "Elsewhere",
		"doc_tab5": "Tab5 docs",
		"devise": "Screens and tools for the home, made with AI and shared in case they help.",
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
# Monogramme : un fil qui relie trois idées. Repris en ligne dans l'en-tête et le pied de page.
LOGO = (
	'<svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
	'<path d="M5 24C10 10 15 9 18 16s8 9 9-8" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>'
	'<circle cx="5" cy="24" r="3"/><circle cx="18" cy="16" r="3"/><circle cx="27" cy="8" r="3"/></svg>'
)
# Script de la page (progression de lecture, sommaire, apparitions, agrandissement des images), mis en ligne
# dans chaque page : moins de 2 Ko, aucune requête de plus.
SCRIPT = (ICI / "gabarits" / "site.js").read_text(encoding="utf-8").strip()
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


def projet_de(page: dict, par_paire: dict) -> dict | None:
	"""Page du projet auquel appartient une page (elle-même, son parent, ou rien pour l'accueil)."""
	if page.get("parent"):
		return par_paire[page["parent"]][page["langue"]]
	return page if page.get("ordre") else None


def entete_navigation(page: dict, pages: list[dict], autre: dict, projet: dict | None) -> str:
	t = TEXTES[page["langue"]]
	accueil = "/" if page["langue"] == "fr" else "/en/"
	liens = []
	projets = (p for p in pages if p["langue"] == page["langue"] and p.get("ordre") and not p.get("parent"))
	for p in sorted(projets, key=lambda p: int(p["ordre"])):
		courant = ' aria-current="page"' if p is page else (' class="courant"' if p is projet else "")
		liens.append(f'<li><a href="{p["chemin"]}"{courant}>{html.escape(p.get("menu") or p["fil"])}</a></li>')
	autre_langue = "en" if page["langue"] == "fr" else "fr"
	return (
		f'<a class="evitement" href="#contenu">{t["evitement"]}</a>\n'
		'<header class="haut">\n'
		'\t<div class="page ligne">\n'
		f'\t\t<a class="marque" href="{accueil}">{LOGO}<span>{t["marque"]}</span></a>\n'
		f'\t\t<nav class="menu" aria-label="{t["navigation"]}"><ul>{"".join(liens)}</ul></nav>\n'
		f'\t\t<a class="langue" href="{autre["chemin"]}" hreflang="{autre_langue}" lang="{autre_langue}">{t["autre"]}</a>\n'
		'\t</div>\n'
		'\t<div class="progression" aria-hidden="true"><span></span></div>\n'
		'</header>'
	)


def onglets(page: dict, pages: list[dict], projet: dict | None) -> str:
	"""Onglets du projet sous le fil d'Ariane : la page du projet (« Présentation ») et ses sous-pages.
	Rien pour l'accueil ni pour un projet d'une seule page."""
	if projet is None:
		return ""
	sous = sorted((p for p in pages if p.get("parent") == projet["paire"] and p["langue"] == page["langue"]),
		key=lambda p: int(p["ordre"]))
	if not sous:
		return ""
	t = TEXTES[page["langue"]]
	liens = []
	for p in [projet, *sous]:
		nom = t["presentation"] if p is projet else (p.get("menu") or p["fil"])
		courant = ' aria-current="page"' if p is page else ""
		liens.append(f'<li><a href="{p["chemin"]}"{courant}>{html.escape(nom)}</a></li>')
	return (
		f'<nav class="onglets" aria-label="{t["cote"]}"><span class="onglets-projet">'
		f'{html.escape(projet.get("menu") or projet["fil"])}</span><ul>{"".join(liens)}</ul></nav>\n'
	)


def sommaire(page: dict, projet: dict | None) -> tuple[str, str]:
	"""Sommaire de la page (ses <h2 id>) : colonne de droite sur grand écran, pastille flottante qui l'ouvre ailleurs.
	La section en cours de lecture est allumée par gabarits/site.js."""
	sections = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', page["corps"])
	if projet is None or len(sections) < 2:
		return "", ""
	t = TEXTES[page["langue"]]
	liste = "".join(f'<li><a href="#{ancre}">{texte}</a></li>' for ancre, texte in sections)
	colonne = (
		f'<aside class="sommaire"><nav aria-label="{t["sommaire"]}"><p class="sommaire-titre">{t["sommaire"]}</p>'
		f'<ul>{liste}</ul></nav></aside>\n'
	)
	pastille = (
		f'<button class="sommaire-bouton" type="button" popovertarget="sommaire-mobile" aria-label="{t["sommaire"]}">'
		f'<span>{t["sommaire"]}</span></button>\n'
		f'<nav id="sommaire-mobile" class="sommaire-mobile" popover aria-label="{t["sommaire"]}">'
		f'<p class="sommaire-titre">{t["sommaire"]}</p><ul>{liste}</ul></nav>\n'
	)
	return colonne, pastille


def pied(page: dict, pages: list[dict]) -> str:
	t = TEXTES[page["langue"]]
	accueil = "/" if page["langue"] == "fr" else "/en/"
	projets = sorted((p for p in pages if p["langue"] == page["langue"] and p.get("ordre") and not p.get("parent")),
		key=lambda p: int(p["ordre"]))
	liens = "".join(f'<li><a href="{p["chemin"]}">{html.escape(p.get("menu") or p["fil"])}</a></li>' for p in projets)
	return (
		'<footer class="bas">\n'
		'\t<div class="page">\n'
		'\t\t<div class="bas-haut">\n'
		f'\t\t\t<div><a class="marque" href="{accueil}">{LOGO}<span>{t["marque"]}</span></a><p>{t["devise"]}</p></div>\n'
		f'\t\t\t<nav aria-label="{t["projets"]}"><p class="bas-titre">{t["projets"]}</p><ul>{liens}</ul></nav>\n'
		f'\t\t\t<nav aria-label="{t["ailleurs"]}"><p class="bas-titre">{t["ailleurs"]}</p><ul>'
		'<li><a href="https://github.com/Axellum">GitHub</a></li>'
		'<li><a href="https://vigie.auxfilsdesidees.fr/">Vigie</a></li>'
		'<li><a href="https://axellum.github.io/M5-Tab5-ESPHome-LVGL/">' + t["doc_tab5"] + '</a></li></ul></nav>\n'
		'\t\t</div>\n'
		f'\t\t{t["pied"]}\n'
		'\t</div>\n'
		'</footer>'
	)


def fil_ariane(page: dict, projet: dict | None) -> tuple[str, dict | None]:
	if not page.get("fil"):
		return "", None
	t = TEXTES[page["langue"]]
	accueil = "/" if page["langue"] == "fr" else "/en/"
	etapes = [(t["accueil"], accueil)]
	if projet is not None and projet is not page:
		etapes.append((projet["fil"], projet["chemin"]))
	liens = "".join(f'<a href="{lien}">{html.escape(nom)}</a> <span aria-hidden="true">›</span> ' for nom, lien in etapes)
	visible = (
		f'<nav class="fil" aria-label="{t["fil"]}">{liens}'
		f'<span aria-current="page">{html.escape(page["fil"])}</span></nav>\n'
	)
	etapes.append((page["fil"], page["chemin"]))
	ld = {
		"@type": "BreadcrumbList",
		"itemListElement": [
			{"@type": "ListItem", "position": i, "name": nom, "item": SITE + lien}
			for i, (nom, lien) in enumerate(etapes, 1)
		],
	}
	return visible, ld


def rendre(page: dict, pages: list[dict], par_paire: dict) -> str:
	t = TEXTES[page["langue"]]
	fr, en = par_paire[page["paire"]]["fr"], par_paire[page["paire"]]["en"]
	autre = en if page["langue"] == "fr" else fr
	url = SITE + page["chemin"]
	image = SITE + "/assets/" + (page.get("image") or "partage.jpg")
	projet = projet_de(page, par_paire)
	visible, ld_fil = fil_ariane(page, projet)
	colonne, pastille = sommaire(page, projet)
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
<meta name="theme-color" content="#0e1319" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f7f6f2" media="(prefers-color-scheme: light)">
<link rel="icon" href="/assets/icone.svg" type="image/svg+xml">
<link rel="stylesheet" href="{STYLE}">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
{entete_navigation(page, pages, autre, projet)}

<div class="page{" avec-sommaire" if colonne else ""}">
<main id="contenu">
{visible}{onglets(page, pages, projet)}{page["corps"]}
</main>
{colonne}</div>
{pastille}
{pied(page, pages)}
<script>
{SCRIPT}
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
