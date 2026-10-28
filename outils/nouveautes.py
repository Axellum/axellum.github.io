#!/usr/bin/env python3
"""Met à jour contenu/nouveautes.json avec les versions publiées (releases GitHub, hors préversions) des projets.

construire.py en fait la page Nouveautés, les dernières versions de l'accueil et les flux RSS ; il ne lit que ce
fichier (la CI reste sans réseau). Une version déjà connue garde ce qui a été écrit à la main (titre français,
résumé) ; une nouvelle arrive avec le titre anglais de sa release et sans titre français : le script le signale,
il faut l'écrire dans le fichier (sinon la page française montre le titre anglais). Python 3, sans dépendance.

  python outils/nouveautes.py && python construire.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "contenu" / "nouveautes.json"
# Dépôt → page du projet sur le site (sa « paire » dans contenu/)
DEPOTS = {
	"M5-Tab5-ESPHome-LVGL": "ecran",
	"vigie-api": "vigie",
	"vigie-web": "vigie",
	"vigie-display": "vigie-ecran",
	"vromvrom-engine": "moteur",
}


def releases(depot: str) -> list[dict]:
	entetes = {"Accept": "application/vnd.github+json", "User-Agent": "auxfilsdesidees-nouveautes"}
	if os.environ.get("GITHUB_TOKEN"):
		entetes["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
	requete = urllib.request.Request(f"https://api.github.com/repos/Axellum/{depot}/releases?per_page=100", headers=entetes)
	with urllib.request.urlopen(requete, timeout=30) as reponse:
		return json.load(reponse)


def main() -> int:
	connues = {e["cle"]: e for e in json.loads(DONNEES.read_text(encoding="utf-8"))} if DONNEES.exists() else {}
	toutes = {}
	for depot, projet in DEPOTS.items():
		for r in releases(depot):
			if r["draft"] or r["prerelease"]:
				continue
			cle = f"{depot}@{r['tag_name']}"
			nom = r["name"] or r["tag_name"]
			entree = connues.get(cle, {"cle": cle, "titre": {"en": nom.split(" — ", 1)[1] if " — " in nom else "", "fr": None}})
			entree.update(depot=depot, projet=projet, version=r["tag_name"].removeprefix("v"), date=r["published_at"], url=r["html_url"])
			toutes[cle] = entree
	perdues = sorted(set(connues) - set(toutes))
	liste = sorted(toutes.values(), key=lambda e: e["date"], reverse=True)
	ordre = ("cle", "projet", "depot", "version", "date", "url", "titre", "resume")
	liste = [{k: e[k] for k in ordre if k in e} for e in liste]
	DONNEES.write_text(json.dumps(liste, ensure_ascii=False, indent="\t") + "\n", encoding="utf-8", newline="\n")
	print(f"{len(liste)} versions dans {DONNEES.relative_to(RACINE).as_posix()}")
	for e in liste:
		if e["titre"].get("fr") is None and e["titre"].get("en"):
			print("  titre français à écrire :", e["cle"], "—", e["titre"]["en"])
	for cle in perdues:
		print("  n'existe plus sur GitHub, retirée :", cle)
	return 0


if __name__ == "__main__":
	sys.exit(main())
