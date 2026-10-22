#!/usr/bin/env bash
# Publie la page des projets sur auxfilsdesidees.fr (serveur de Vigie, Caddy) :
#   AFDI_HOST=<adresse> AFDI_SSH_KEY=<clé> ./deploy.sh          # pages, images, robots.txt, sitemap.xml
#   AFDI_HOST=<adresse> AFDI_SSH_KEY=<clé> ./deploy.sh caddy    # + le bloc Caddy, puis redémarre Caddy (une fois)
# GitHub Pages sert le même dépôt sur axellum.github.io ; le robots.txt de la racine est celui de github.io,
# celui de auxfilsdesidees.fr est dans auxfilsdesidees/.
set -euo pipefail
host=${AFDI_HOST:?"AFDI_HOST : adresse du serveur"}
server=vigie@$host
opts=(-o BatchMode=yes)
[ -n "${AFDI_SSH_KEY:-}" ] && opts+=(-i "$AFDI_SSH_KEY")
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/www"
cp -r "$here/index.html" "$here/en" "$here/assets" "$tmp/www/"
cp "$here/auxfilsdesidees/robots.txt" "$here/auxfilsdesidees/sitemap.xml" "$tmp/www/"
tar -czf "$tmp/www.tgz" -C "$tmp/www" .
scp -q "${opts[@]}" "$tmp/www.tgz" "$server:vigie/afdi.tgz"
ssh "${opts[@]}" "$server" 'set -e; d=~/vigie/sites/auxfilsdesidees; rm -rf "$d.new"; mkdir -p "$d.new"
	tar -xzf ~/vigie/afdi.tgz -C "$d.new"; rm ~/vigie/afdi.tgz
	chmod -R a+rX "$d.new"; rm -rf "$d.old"; [ -d "$d" ] && mv "$d" "$d.old"; mv "$d.new" "$d"; rm -rf "$d.old"
	echo "pages installées"'
if [ "${1:-}" = caddy ]; then
	scp -q "${opts[@]}" "$here/auxfilsdesidees/site.caddy" "$server:vigie/sites/auxfilsdesidees.caddy"
	ssh "${opts[@]}" "$server" 'systemctl --user restart caddy.service && sleep 5 && systemctl --user is-active caddy.service'
fi
