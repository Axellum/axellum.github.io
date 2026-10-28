#!/usr/bin/env python3
"""Fait les images de partage (1200 × 630, JPG) de chaque page : assets/partage/<langue>-<paire>.jpg.

Une carte par page, dans sa langue : logo, étiquette et titre de la page à gauche, l'image du haut de page à droite.
construire.py les met dans og:image quand elles existent. À relancer quand un titre ou une image du haut change,
puis python construire.py. Outil de poste (pas dans la CI) : il faut Chrome et Pillow.

  python outils/cartes_partage.py
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
import construire  # noqa: E402

from PIL import Image  # noqa: E402

CHROME = next((p for p in (
	Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
	Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
	Path("/usr/bin/google-chrome"),
) if p.exists()), None)
ASSETS = RACINE / "assets"

GABARIT = """<!doctype html><html lang="{langue}"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; width: 1200px; height: 630px; overflow: hidden; position: relative; background: #0e1319; color: #e8ecf1;
	font-family: system-ui, "Segoe UI", Roboto, Arial, sans-serif; -webkit-font-smoothing: antialiased; }}
.fond {{ position: absolute; inset: 0; background:
	radial-gradient(760px 520px at 88% 18%, rgba(240, 164, 111, .20), transparent 62%),
	radial-gradient(620px 420px at 6% 104%, rgba(143, 192, 255, .13), transparent 60%); }}
.texte {{ position: absolute; left: 72px; top: 64px; bottom: 64px; width: {largeur}px; display: flex; flex-direction: column; }}
.marque {{ display: flex; align-items: center; gap: 16px; font-size: 25px; font-weight: 650; color: #c9d2dc; }}
.marque svg, .marque img {{ width: 58px; height: 58px; border-radius: 14px; flex: none; }}
.milieu {{ margin: auto 0; }}
.etiquette {{ display: inline-block; font-size: 17px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #f0a46f;
	background: #33241b; border: 1.5px solid rgba(240, 164, 111, .35); border-radius: 999px; padding: 6px 16px; }}
h1 {{ margin: 22px 0 0; font-size: {taille}px; line-height: 1.07; letter-spacing: -.02em; font-weight: 760; }}
.site {{ font-size: 22px; color: #9aa6b4; letter-spacing: .01em; }}
.site b {{ color: #f0a46f; font-weight: 650; }}
.visuel {{ position: absolute; right: 60px; top: 50%; transform: translateY(-50%); width: 480px; border-radius: 22px; overflow: hidden;
	border: 1px solid #263240; background: #0d1522;
	box-shadow: 0 40px 80px -30px rgba(240, 164, 111, .5), 0 24px 60px rgba(0, 0, 0, .55); }}
.visuel img, .visuel svg {{ display: block; width: 100%; height: auto; }}
.visuel.logo {{ width: 300px; border: 0; background: none; box-shadow: none; right: 130px; }}
</style></head><body><div class="fond"></div>
<div class="texte">
	<div class="marque">{logo}<span>{marque}</span></div>
	<div class="milieu">{etiquette}<h1>{titre}</h1></div>
	<div class="site"><b>auxfilsdesidees.fr</b>{chemin}</div>
</div>
<div class="visuel{classe}">{visuel}</div>
</body></html>"""


def fichier(src: str) -> str:
	"""Adresse /assets/… du site → fichier local, pour que Chrome charge l'image sans serveur."""
	return (ASSETS / src.removeprefix("/assets/")).as_uri()


def carte(page: dict, par_paire: dict) -> str:
	corps = page["corps"]
	projet = construire.projet_de(page, par_paire)
	logo = construire.LOGO
	if projet and projet.get("logo"):
		logo = f'<img src="{fichier(projet["logo"])}" alt="">'
	h1 = re.search(r"<h1[^>]*>(.*?)</h1>", corps, re.S)
	titre = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else page["titre"]
	etiquette = re.search(r'<span class="etiquette">(.*?)</span>', corps)
	# Visuel : le schéma (moteur), sinon l'image principale du haut de page, sinon le logo du site en grand
	schema = re.search(r'<figure class="schema">(.*?)</figure>', corps, re.S)
	haut = re.search(r'<(?:div class="heros"|figure class="un")>.*?<img [^>]*src="([^"]+)"', corps, re.S)
	classe = ""
	if schema:
		visuel = schema.group(1).replace('href="/assets/', f'href="{ASSETS.as_uri()}/')
	elif haut:
		visuel = f'<img src="{fichier(haut.group(1))}" alt="">'
	else:
		visuel, classe = construire.LOGO.replace('class="logo"', ""), " logo"
	return GABARIT.format(
		langue=page["langue"],
		largeur=560,
		taille=60 if len(titre) <= 32 else 52 if len(titre) <= 48 else 46,
		logo=logo,
		marque=html.escape(construire.TEXTES[page["langue"]]["marque"]),
		etiquette=f'<span class="etiquette">{etiquette.group(1)}</span>' if etiquette else "",
		titre=html.escape(titre),
		chemin=html.escape(page["chemin"].rstrip("/")) if page["chemin"] not in ("/", "/en/") else "",
		visuel=visuel,
		classe=classe,
	)


def main() -> int:
	if CHROME is None:
		sys.exit("Chrome introuvable")
	pages = [construire.lire(f, langue) for langue in construire.LANGUES
		for f in sorted((RACINE / "contenu" / langue).glob("*.html"))]
	par_paire: dict[str, dict] = {}
	for page in pages:
		par_paire.setdefault(page["paire"], {})[page["langue"]] = page
	sortie = ASSETS / "partage"
	sortie.mkdir(exist_ok=True)
	with tempfile.TemporaryDirectory() as tmp:
		for page in pages:
			source = Path(tmp) / "carte.html"
			source.write_text(carte(page, par_paire), encoding="utf-8")
			png = Path(tmp) / "carte.png"
			subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
				"--window-size=1200,630", "--virtual-time-budget=3000", f"--screenshot={png}", source.as_uri()],
				check=True, capture_output=True, timeout=60)
			jpg = sortie / f"{page['langue']}-{page['paire']}.jpg"
			Image.open(png).convert("RGB").crop((0, 0, 1200, 630)).save(jpg, "JPEG", quality=84, optimize=True, progressive=True)
			print(jpg.relative_to(RACINE).as_posix(), jpg.stat().st_size // 1024, "Ko")
	return 0


if __name__ == "__main__":
	sys.exit(main())
