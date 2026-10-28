/* Aux fils des idées : progression de lecture, sommaire qui suit la lecture, apparitions au défilement,
   agrandissement des images. Sans bibliothèque ; rien ne bouge si le système demande moins d'animations. */
(() => {
	const d = document, h = d.documentElement, calme = matchMedia("(prefers-reduced-motion: reduce)").matches;
	h.classList.add("js");
	const liens = [...d.querySelectorAll(".sommaire a, .sommaire-mobile a")];
	const titres = [...new Set(liens.map(a => a.hash))].map(x => d.getElementById(x.slice(1))).filter(Boolean);
	const pastille = d.querySelector(".sommaire-bouton span");
	let actif = null, attente = false;
	const maj = () => {
		attente = false;
		const max = h.scrollHeight - innerHeight;
		h.style.setProperty("--p", max > 0 ? Math.min(scrollY / max, 1) : 0);
		h.classList.toggle("defile", scrollY > 240);
		let courant = null;
		for (const t of titres) if (t.getBoundingClientRect().top < innerHeight * 0.32) courant = t;
		if (courant !== actif) {
			actif = courant;
			for (const a of liens) a.classList.toggle("actif", !!courant && a.hash === "#" + courant.id);
			if (pastille) pastille.textContent = courant ? courant.textContent : pastille.dataset.vide;
		}
	};
	if (pastille) pastille.dataset.vide = pastille.textContent;
	addEventListener("scroll", () => { if (!attente) { attente = true; requestAnimationFrame(maj); } }, { passive: true });
	addEventListener("resize", maj);
	maj();
	d.getElementById("sommaire-mobile")?.addEventListener("click", e => e.target.closest("a") && e.currentTarget.hidePopover());
	if (!calme && "IntersectionObserver" in window) {
		const vu = new IntersectionObserver(es => es.forEach(e => {
			if (e.isIntersecting) {
				const x = e.target;
				x.classList.add("vu");
				vu.unobserve(x);
				setTimeout(() => x.style.transitionDelay = "", 900);
			}
		}), { rootMargin: "0px 0px -6% 0px" });
		d.querySelectorAll("main > section > :not(.grille, .cartes), main > .faits, .grille > *, .cartes > *, .journal li").forEach(x => {
			if (x.getBoundingClientRect().top < innerHeight) return;
			const rang = [...x.parentElement.children].indexOf(x);
			if (x.parentElement.matches(".grille, .cartes, .journal ul")) x.style.transitionDelay = Math.min(rang, 4) * 70 + "ms";
			x.classList.add("revele");
			vu.observe(x);
		});
	}
	const loupe = d.createElement("dialog");
	loupe.className = "loupe";
	loupe.innerHTML = '<img alt="">';
	loupe.setAttribute("aria-label", h.lang === "fr" ? "Image agrandie" : "Enlarged image");
	loupe.addEventListener("click", () => loupe.close());
	d.body.append(loupe);
	d.querySelectorAll("main figure img").forEach(img => {
		if (img.closest(".diaporama, .collage")) return;
		img.classList.add("agrandir");
		img.addEventListener("click", () => {
			const grande = loupe.firstChild;
			grande.src = img.currentSrc || img.src;
			grande.alt = img.alt;
			loupe.showModal();
		});
	});
})();
