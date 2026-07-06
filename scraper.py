"""
Scraper automatique multi-enseigne pour Panière.

Ce script recherche chaque produit du catalogue sur le site drive de chaque
enseigne configurée, et sauvegarde tous les prix trouvés dans data/prices.json.
Ce fichier est ensuite lu directement par l'application web (voir paniere.html).

Ce script est fait pour être exécuté automatiquement chaque nuit par GitHub
Actions (voir .github/workflows/scrape.yml) — tu n'as rien à lancer toi-même
une fois que c'est en place.

AVANT DE DÉPLOYER : remplis les sélecteurs CSS et l'URL de recherche de chaque
enseigne ci-dessous (CONFIG_ENSEIGNES). Sans ça, le scraper ne trouvera rien.
Voir le README.md du dossier pour la méthode pas à pas.
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout


# ============================================================
# CATALOGUE — doit correspondre exactement aux ids utilisés dans paniere.html
# ============================================================

PRODUITS = [
    {"id": "lait-demi", "nom": "Lait demi-écrémé 1L"},
    {"id": "lait-entier", "nom": "Lait entier 1L"},
    {"id": "yaourt-nat", "nom": "Yaourt nature x8"},
    {"id": "yaourt-fru", "nom": "Yaourt aux fruits x8"},
    {"id": "beurre-doux", "nom": "Beurre doux 250g"},
    {"id": "beurre-sel", "nom": "Beurre demi-sel 250g"},
    {"id": "oeufs", "nom": "Œufs x12"},
    {"id": "fromage-rape", "nom": "Fromage râpé 200g"},
    {"id": "creme", "nom": "Crème fraîche 20cl"},
    {"id": "fromage-blanc", "nom": "Fromage blanc 500g"},
    {"id": "pates-penne", "nom": "Pâtes penne 500g"},
    {"id": "pates-spag", "nom": "Pâtes spaghetti 500g"},
    {"id": "riz", "nom": "Riz long grain 1kg"},
    {"id": "huile-tour", "nom": "Huile de tournesol 1L"},
    {"id": "huile-olive", "nom": "Huile d'olive 500ml"},
    {"id": "sel", "nom": "Sel fin 1kg"},
    {"id": "farine", "nom": "Farine de blé 1kg"},
    {"id": "sauce-tomate", "nom": "Sauce tomate 500g"},
    {"id": "lentilles", "nom": "Lentilles vertes 500g"},
    {"id": "thon", "nom": "Thon au naturel boîte"},
    {"id": "sucre", "nom": "Sucre en poudre 1kg"},
    {"id": "confiture", "nom": "Confiture fraises 370g"},
    {"id": "cafe-moulu", "nom": "Café moulu 250g"},
    {"id": "the", "nom": "Thé infusettes x20"},
    {"id": "chocolat-pdr", "nom": "Chocolat en poudre 400g"},
    {"id": "biscuits", "nom": "Biscuits sablés"},
    {"id": "cereales", "nom": "Céréales muesli 500g"},
    {"id": "miel", "nom": "Miel 250g"},
    {"id": "pain-mie", "nom": "Pain de mie"},
    {"id": "baguette", "nom": "Baguette"},
    {"id": "pain-complet", "nom": "Pain complet"},
    {"id": "croissants", "nom": "Croissants x4"},
    {"id": "brioche", "nom": "Brioche tranchée"},
    {"id": "tomates", "nom": "Tomates 1kg"},
    {"id": "pommes", "nom": "Pommes 1kg"},
    {"id": "bananes", "nom": "Bananes 1kg"},
    {"id": "pdt", "nom": "Pommes de terre 2kg"},
    {"id": "oignons", "nom": "Oignons 1kg"},
    {"id": "carottes", "nom": "Carottes 1kg"},
    {"id": "salade", "nom": "Salade laitue"},
    {"id": "citrons", "nom": "Citrons 500g"},
    {"id": "courgettes", "nom": "Courgettes 1kg"},
    {"id": "poivrons", "nom": "Poivrons 500g"},
    {"id": "poulet", "nom": "Filet de poulet 500g"},
    {"id": "steak-hache", "nom": "Steak haché x4"},
    {"id": "jambon", "nom": "Jambon blanc x4 tranches"},
    {"id": "saucisses", "nom": "Saucisses de Toulouse 400g"},
    {"id": "lardons", "nom": "Lardons 200g"},
    {"id": "dinde", "nom": "Escalope de dinde 400g"},
    {"id": "saumon", "nom": "Filet de saumon 400g"},
    {"id": "cabillaud", "nom": "Cabillaud 400g"},
    {"id": "crevettes", "nom": "Crevettes cuites 200g"},
    {"id": "frites", "nom": "Frites surgelées 1kg"},
    {"id": "legumes-surg", "nom": "Légumes mélangés surgelés 1kg"},
    {"id": "pizza-surg", "nom": "Pizza surgelée"},
    {"id": "glace", "nom": "Glace vanille 1L"},
    {"id": "eau", "nom": "Eau minérale 6x1.5L"},
    {"id": "jus-orange", "nom": "Jus d'orange 1L"},
    {"id": "soda", "nom": "Soda cola 1.5L"},
    {"id": "cafe-grains", "nom": "Café en grains 1kg"},
    {"id": "papier-wc", "nom": "Papier toilette x12"},
    {"id": "vaisselle", "nom": "Liquide vaisselle 500ml"},
    {"id": "lessive", "nom": "Lessive liquide 2L"},
    {"id": "dentifrice", "nom": "Dentifrice"},
    {"id": "gel-douche", "nom": "Gel douche 250ml"},
]


# ============================================================
# CONFIG PAR ENSEIGNE — À REMPLIR (voir README.md)
# ============================================================
# "magasin_id" doit correspondre exactement aux ids définis dans MAGASINS
# côté paniere.html, pour que les prix scrapés retombent sur le bon magasin.

CONFIG_ENSEIGNES = [
    {
        "magasin_id": "auchan-va",
        "enseigne": "Auchan",
        "url_recherche": "https://www.auchan.fr/recherche?text={produit}",  # À VÉRIFIER
        "code_postal_magasin": "59650",
        "selecteur_carte_produit": ".product-thumbnail",       # À REMPLIR
        "selecteur_nom_produit": ".product-thumbnail__title",  # À REMPLIR
        "selecteur_prix": ".product-price",                    # À REMPLIR
        "selecteur_selection_magasin": "#store-picker",        # À REMPLIR
    },
    # Ajoute une entrée par magasin/enseigne ciblé, sur le même modèle.
    # Duplique ce bloc autant de fois que nécessaire.
]

DELAI_ENTRE_REQUETES_SEC = 3


def nettoyer_prix(texte_prix: str) -> float | None:
    if not texte_prix:
        return None
    match = re.search(r"(\d+)[,.](\d{2})", texte_prix)
    if not match:
        return None
    return float(f"{match.group(1)}.{match.group(2)}")


async def selectionner_magasin(page: Page, config: dict) -> bool:
    try:
        await page.click(config["selecteur_selection_magasin"], timeout=5000)
        await page.fill("input[type='text']", config["code_postal_magasin"])
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)
        return True
    except PWTimeout:
        print(f"  [!] Sélection du magasin impossible pour {config['magasin_id']}")
        return False


async def scraper_produit(page: Page, config: dict, produit: dict) -> float | None:
    url = config["url_recherche"].format(produit=produit["nom"].replace(" ", "+"))
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_selector(config["selecteur_carte_produit"], timeout=8000)
    except PWTimeout:
        return None

    premiere_carte = await page.query_selector(config["selecteur_carte_produit"])
    if not premiere_carte:
        return None

    prix_el = await premiere_carte.query_selector(config["selecteur_prix"])
    if not prix_el:
        return None

    prix_brut = (await prix_el.inner_text()).strip()
    return nettoyer_prix(prix_brut)


async def scraper_config(page: Page, config: dict) -> list[dict]:
    print(f"\n[{config['enseigne']}] Magasin : {config['magasin_id']}")
    resultats = []

    ok = await selectionner_magasin(page, config)
    if not ok:
        return resultats

    for produit in PRODUITS:
        prix = await scraper_produit(page, config, produit)
        if prix is not None:
            resultats.append({
                "magasin_id": config["magasin_id"],
                "produit_id": produit["id"],
                "prix": prix,
            })
            print(f"  - {produit['nom']} : {prix} €")
        else:
            print(f"  - {produit['nom']} : non trouvé")
        await asyncio.sleep(DELAI_ENTRE_REQUETES_SEC)

    return resultats


async def main():
    tous_les_prix = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        for config in CONFIG_ENSEIGNES:
            resultats = await scraper_config(page, config)
            tous_les_prix.extend(resultats)

        await browser.close()

    sortie = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prices": tous_les_prix,
    }

    chemin_sortie = Path(__file__).parent / "data" / "prices.json"
    chemin_sortie.parent.mkdir(exist_ok=True)
    chemin_sortie.write_text(json.dumps(sortie, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(tous_les_prix)} prix collectés. Sauvegardé dans {chemin_sortie}")


if __name__ == "__main__":
    asyncio.run(main())
