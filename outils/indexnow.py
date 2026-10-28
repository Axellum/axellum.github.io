#!/usr/bin/env python3
"""Signale les pages du sitemap à IndexNow (Bing, Yandex, Seznam, Naver…) après un déploiement (Python 3, sans dépendance).

La clé est le fichier auxfilsdesidees/<clé>.txt, servi à la racine de auxfilsdesidees.fr par deploy.sh : elle est publique
par principe (le moteur vérifie qu'elle est bien sur le site), ce n'est pas un secret. Le script vérifie d'abord qu'elle
est en ligne, puis envoie toutes les adresses du sitemap en une requête.

  python outils/indexnow.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SITE = "https://auxfilsdesidees.fr"


def main() -> int:
	cles = [f for f in (RACINE / "auxfilsdesidees").glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", f.stem)]
	if len(cles) != 1:
		sys.exit(f"il faut une seule clé auxfilsdesidees/<32 hexa>.txt, trouvé {len(cles)}")
	cle = cles[0].stem
	en_ligne = urllib.request.urlopen(f"{SITE}/{cle}.txt", timeout=20).read().decode().strip()
	if en_ligne != cle:
		sys.exit(f"{SITE}/{cle}.txt ne contient pas la clé : lancer deploy.sh d'abord")
	adresses = re.findall(r"<loc>([^<]+)</loc>", (RACINE / "auxfilsdesidees" / "sitemap.xml").read_text(encoding="utf-8"))
	corps = json.dumps({"host": "auxfilsdesidees.fr", "key": cle, "keyLocation": f"{SITE}/{cle}.txt", "urlList": adresses}).encode()
	requete = urllib.request.Request("https://api.indexnow.org/indexnow", data=corps,
		headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
	with urllib.request.urlopen(requete, timeout=30) as reponse:
		# 200 : reçu ; 202 : reçu, clé en cours de vérification
		print(f"IndexNow : HTTP {reponse.status}, {len(adresses)} adresses envoyées")
	return 0


if __name__ == "__main__":
	sys.exit(main())
