#!/usr/bin/env python3
"""Construit les pages du site à partir de contenu/<langue>/*.html (Python 3.11+, sans dépendance).

Chaque fichier de contenu commence par un en-tête « clé: valeur » terminé par une ligne « --- », puis le corps HTML.
Clés : chemin (adresse de la page, ex. /vigie/), paire (identifiant commun à la page FR et à la page EN),
titre (balise <title>, 60 caractères au plus : Google coupe au-delà), description (155 au plus), maj (date de la
dernière vraie mise à jour, AAAA-MM-JJ : <lastmod> du sitemap), image (image principale, sous /assets/ ; l'image de
partage est assets/partage/<langue>-<paire>.jpg si elle existe, faite par outils/cartes_partage.py), fil (nom dans le fil d'Ariane, absent sur
l'accueil), ordre (place dans la navigation, absent = hors navigation), menu (nom dans la navigation),
parent (paire de la page du projet : la page est alors une sous-page, rangée par « ordre » dans le menu de gauche),
logo (page d'un projet : son logo sous /assets/, montré devant le nom du projet au-dessus des onglets).
Menu du haut : les projets. Sous le fil d'Ariane : les onglets du projet ; à droite, le sommaire (<h2 id>) de la page.
Un bloc <!--ld … ld--> dans le corps est un objet JSON-LD de plus, ajouté au graphe de la page.
Nouveautés : contenu/nouveautes.json (versions publiées, tenu à jour par outils/nouveautes.py). Dans un corps,
<!--nouveautes--> devient la liste complète par mois, <!--nouveautes 3--> les trois dernières ; la page de paire
« nouveautes » porte aussi le flux RSS de sa langue (rss.xml dans son dossier).

  python construire.py            # écrit les pages, les flux RSS et auxfilsdesidees/sitemap.xml
  python construire.py --verifier # échoue si une page écrite diffère de ce que le contenu produit (CI)
"""
from __future__ import annotations

import datetime
import email.utils
import hashlib
import html
import itertools
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
		"nouveautes": "Nouveautés",
		"notes": "Notes de version",
		"flux": "Flux RSS",
		"flux_titre": "Nouveautés · Aux fils des idées",
		"flux_description": "Les versions publiées des projets d'Axel Duviella : l'écran Home Assistant, Vigie et le moteur IA.",
		"deux_points": " : ",
		"mois": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
			"novembre", "décembre"),
		"mois_court": ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."),
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
		"nouveautes": "What's new",
		"notes": "Release notes",
		"flux": "RSS feed",
		"flux_titre": "What's new · Aux fils des idées",
		"flux_description": "Released versions of Axel Duviella's projects: the Home Assistant display, Vigie and the AI engine.",
		"deux_points": ": ",
		"mois": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
			"November", "December"),
		"mois_court": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
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
# Empreinte de la feuille de style et de l'icône dans leur adresse : /assets/ est gardé 7 jours en cache par les
# navigateurs (Caddy), un fichier modifié doit changer d'adresse pour être rechargé. Lu en texte pour que
# l'empreinte ne dépende pas des fins de ligne (Windows ou CI).
def empreinte(nom):
	return f"/assets/{nom}?v=" + hashlib.sha256((ICI / "assets" / nom).read_text(encoding="utf-8").encode()).hexdigest()[:10]


STYLE = empreinte("style.css")
ICONE = empreinte("icone.svg")
# Logo du site (choisi par Axel le 28/10/2026) : un fil qui se divise en arbre, chaque branche finit sur une idée.
# Même dessin que l'icône d'onglet (assets/icone.svg), repris en ligne dans l'en-tête et le pied de page.
LOGO = (
	'<svg class="logo" viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
	'<rect width="64" height="64" rx="14" fill="#10151c"/>'
	'<path d="M30 55V41C30 33 23 29 20 21M30 41C30 35 35 31 39 29" fill="none" stroke="#f0a46f" stroke-width="4.8" stroke-linecap="round"/>'
	'<path d="M39 29C40.5 24.5 41.5 20 43 15.5M39 29C43 28 47 28 50.5 25.5" fill="none" stroke="#f0a46f" stroke-width="3.8" stroke-linecap="round"/>'
	'<circle cx="19.2" cy="18.6" r="5" fill="#8fc0ff"/><circle cx="43.6" cy="13.2" r="4.4" fill="#f0a46f"/>'
	'<circle cx="52.2" cy="24.4" r="4.2" fill="#e8ecf1"/></svg>'
)
# Script de la page (progression de lecture, sommaire, apparitions, agrandissement des images), mis en ligne
# dans chaque page : environ 3 Ko (1,4 Ko compressé), aucune requête de plus.
SCRIPT = (ICI / "gabarits" / "site.js").read_text(encoding="utf-8").strip()
PERSONNE = {
	"@type": "Person",
	"@id": f"{SITE}/#axel",
	"name": "Axel Duviella",
	"url": f"{SITE}/",
	"sameAs": ["https://github.com/Axellum"],
}
NOUVEAUTES = json.loads((ICI / "contenu" / "nouveautes.json").read_text(encoding="utf-8"))
# Nom d'un dépôt dans les nouveautés, quand ce n'est pas celui de la page de son projet
NOMS_DEPOTS = {"vigie-api": "Vigie API", "vigie-web": "Vigie Web", "vigie-display": "Vigie display"}
FLUX = "rss.xml"


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
	for cle, limite in (("titre", 60), ("description", 155)):
		if len(page[cle]) > limite:
			sys.exit(f"{fichier} : « {cle} » de {len(page[cle])} caractères, {limite} au plus (Google coupe au-delà)")
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
	logo = f'<img src="/assets/{projet["logo"]}" width="26" height="26" alt="">' if projet.get("logo") else ""
	return (
		f'<nav class="onglets" aria-label="{t["cote"]}"><span class="onglets-projet">{logo}'
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
	nouveautes = next(p for p in pages if p["paire"] == "nouveautes" and p["langue"] == page["langue"])
	liens += f'<li><a href="{nouveautes["chemin"]}">{t["nouveautes"]}</a></li>'
	return (
		'<footer class="bas">\n'
		'\t<div class="page">\n'
		'\t\t<div class="bas-haut">\n'
		f'\t\t\t<div><a class="marque" href="{accueil}">{LOGO}<span>{t["marque"]}</span></a><p>{t["devise"]}</p></div>\n'
		f'\t\t\t<nav aria-label="{t["projets"]}"><p class="bas-titre">{t["projets"]}</p><ul>{liens}</ul></nav>\n'
		f'\t\t\t<nav aria-label="{t["ailleurs"]}"><p class="bas-titre">{t["ailleurs"]}</p><ul>'
		'<li><a href="https://github.com/Axellum">GitHub</a></li>'
		'<li><a href="https://vigie.auxfilsdesidees.fr/">Vigie</a></li>'
		'<li><a href="https://axellum.github.io/M5-Tab5-ESPHome-LVGL/">' + t["doc_tab5"] + '</a></li>'
		f'<li><a href="{nouveautes["chemin"]}{FLUX}">{t["flux"]}</a></li></ul></nav>\n'
		'\t\t</div>\n'
		f'\t\t{t["pied"]}\n'
		'\t</div>\n'
		'</footer>'
	)


def nom_version(e: dict, langue: str, par_paire: dict) -> tuple[str, str, dict]:
	"""(« Écran Home Assistant 3.9.0 », titre dans la langue ou à défaut en anglais, page du projet)."""
	projet = par_paire[e["projet"]][langue]
	nom = NOMS_DEPOTS.get(e["depot"], projet.get("menu") or projet["fil"])
	return f'{nom} {e["version"]}', e["titre"].get(langue) or e["titre"]["en"], projet


def nouveaute(e: dict, langue: str, par_paire: dict) -> str:
	t = TEXTES[langue]
	nom, titre, projet = nom_version(e, langue, par_paire)
	annee, mois, jour = e["date"][:10].split("-")
	langue_titre = "" if e["titre"].get(langue) else ' lang="en"'
	resume = f'\t\t\t\t<p{langue_titre}>{html.escape(titre)}</p>\n' if titre else ""
	return (
		'\t\t<li>\n'
		f'\t\t\t<time datetime="{e["date"][:10]}">{int(jour)} {t["mois_court"][int(mois) - 1]} {annee}</time>\n'
		'\t\t\t<div>\n'
		f'\t\t\t\t<strong><a href="{projet["chemin"]}">{html.escape(nom.rsplit(" ", 1)[0])}</a> {e["version"]}</strong>\n{resume}'
		f'\t\t\t\t<a href="{e["url"]}">{t["notes"]}</a>\n'
		'\t\t\t</div>\n'
		'\t\t</li>\n'
	)


def deplier_nouveautes(corps: str, langue: str, par_paire: dict) -> str:
	"""<!--nouveautes 3--> : les trois dernières versions ; <!--nouveautes--> : toutes, une section par mois."""
	t = TEXTES[langue]

	def liste(m: re.Match) -> str:
		if m.group(1):
			return "<ul>\n" + "".join(nouveaute(e, langue, par_paire) for e in NOUVEAUTES[:int(m.group(1))]) + "\t</ul>"
		sections = []
		for mois, groupe in itertools.groupby(NOUVEAUTES, key=lambda e: e["date"][:7]):
			annee, numero = mois.split("-")
			nom = f'{t["mois"][int(numero) - 1].capitalize()} {annee}'
			sections.append(
				f'<section class="bloc journal" aria-labelledby="m-{mois}">\n\t<h2 id="m-{mois}">{nom}</h2>\n\t<ul>\n'
				+ "".join(nouveaute(e, langue, par_paire) for e in groupe) + "\t</ul>\n</section>"
			)
		return "\n\n".join(sections)

	return re.sub(r"<!--nouveautes(?: (\d+))?-->", liste, corps)


def flux_rss(langue: str, par_paire: dict) -> str:
	"""Flux RSS 2.0 des versions publiées, dans une langue ; daté de la dernière version (stable d'une construction à l'autre)."""
	t = TEXTES[langue]
	page = par_paire["nouveautes"][langue]
	x = html.escape

	def date822(iso: str) -> str:
		return email.utils.format_datetime(datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")), usegmt=True)

	articles = []
	for e in NOUVEAUTES:
		nom, titre, _ = nom_version(e, langue, par_paire)
		articles.append(
			"    <item>\n"
			f"      <title>{x(nom + (t['deux_points'] + titre if titre else ''))}</title>\n"
			f"      <link>{e['url']}</link>\n"
			f"      <guid isPermaLink=\"true\">{e['url']}</guid>\n"
			f"      <pubDate>{date822(e['date'])}</pubDate>\n"
			f"      <category>{x(nom.rsplit(' ', 1)[0])}</category>\n"
			f"      <description>{x(titre or nom)}</description>\n"
			"    </item>"
		)
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
		"  <channel>\n"
		f"    <title>{x(t['flux_titre'])}</title>\n"
		f"    <link>{SITE}{page['chemin']}</link>\n"
		f'    <atom:link href="{SITE}{page["chemin"]}{FLUX}" rel="self" type="application/rss+xml"/>\n'
		f"    <description>{x(t['flux_description'])}</description>\n"
		f"    <language>{langue}</language>\n"
		f"    <lastBuildDate>{date822(NOUVEAUTES[0]['date'])}</lastBuildDate>\n"
		+ "\n".join(articles) + "\n"
		"  </channel>\n"
		"</rss>\n"
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
	carte = f"partage/{page['langue']}-{page['paire']}.jpg"
	if (ICI / "assets" / carte).exists():
		partage = (f'<meta property="og:image" content="{SITE}/assets/{carte}">\n'
			'<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
			f'<meta property="og:image:alt" content="{html.escape(page["titre"])}">')
	else:
		partage = f'<meta property="og:image" content="{image}">'
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
	if page.get("maj"):
		graphe[-1]["dateModified"] = page["maj"]
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
<link rel="alternate" type="application/rss+xml" title="{e(t["flux_titre"])}" href="{par_paire["nouveautes"][page["langue"]]["chemin"]}{FLUX}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{t["locale"]}">
<meta property="og:locale:alternate" content="{autre_locale}">
<meta property="og:site_name" content="{t["marque"]}">
<meta property="og:title" content="{e(page["titre"])}">
<meta property="og:description" content="{e(page["description"])}">
<meta property="og:url" content="{url}">
{partage}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0e1319" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f7f6f2" media="(prefers-color-scheme: light)">
<link rel="icon" href="{ICONE}" type="image/svg+xml">
<link rel="stylesheet" href="{STYLE}">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
{entete_navigation(page, pages, autre, projet)}

<div class="page{" avec-sommaire" if colonne else ""}">
<main id="contenu">
{visible}{onglets(page, pages, projet)}{deplier_nouveautes(page["corps"], page["langue"], par_paire)}
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
		if page.get("maj"):
			lignes.append(f"    <lastmod>{page['maj']}</lastmod>")
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
	# Une page qui montre les nouveautés est à jour de la dernière version publiée
	for page in pages:
		if "<!--nouveautes" in page["corps"]:
			page["maj"] = max(page.get("maj", ""), NOUVEAUTES[0]["date"][:10])
	attendu = {sortie(p["chemin"]): rendre(p, pages, par_paire) for p in pages}
	attendu[ICI / "auxfilsdesidees" / "sitemap.xml"] = sitemap(pages, par_paire)
	for langue in LANGUES:
		attendu[ICI / par_paire["nouveautes"][langue]["chemin"].strip("/") / FLUX] = flux_rss(langue, par_paire)
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
