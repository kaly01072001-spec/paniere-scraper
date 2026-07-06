# Panière — scraper automatique

Ce dossier contient tout ce qu'il faut pour que la collecte des prix tourne
automatiquement chaque nuit, gratuitement, sans serveur à gérer.

## Comment ça marche

1. `scraper.py` visite les sites drive des enseignes configurées et note les prix
2. `.github/workflows/scrape.yml` demande à GitHub d'exécuter ce script chaque nuit
3. Les résultats sont sauvegardés dans `data/prices.json` et publiés automatiquement
4. L'application `paniere.html` va chercher ce fichier directement en ligne à chaque
   ouverture, et remplace les prix simulés par les vrais prix dès qu'ils existent

## Étapes de déploiement (à faire une seule fois)

### 1. Créer un compte GitHub (si tu n'en as pas)
Gratuit, sur github.com.

### 2. Créer un nouveau dépôt
- Clique sur "New repository"
- Nom au choix (ex: `paniere-scraper`)
- Coche "Public" (nécessaire pour que l'appli puisse lire le fichier de prix
  gratuitement ensuite)

### 3. Envoyer ces fichiers dans le dépôt
Depuis ton ordinateur, dans le dossier `scraper-auto` :
```bash
git init
git add .
git commit -m "Premier envoi"
git branch -M main
git remote add origin https://github.com/TON-PSEUDO/paniere-scraper.git
git push -u origin main
```

### 4. Remplir les vrais sélecteurs dans scraper.py
C'est l'étape la plus importante et la seule qui demande du travail manuel :
- Ouvre le site drive de chaque enseigne ciblée
- Utilise l'inspecteur du navigateur (clic droit > Inspecter) sur un résultat
  de recherche produit pour trouver les vrais sélecteurs CSS
- Remplace les valeurs marquées "À REMPLIR" dans `CONFIG_ENSEIGNES`
- Ajoute une entrée dans `CONFIG_ENSEIGNES` par magasin que tu veux suivre

Renvoie-moi une capture d'écran de l'inspecteur ouvert sur un vrai site si tu
veux de l'aide pour identifier les bons sélecteurs.

### 5. Vérifier que ça tourne
- Va dans l'onglet "Actions" de ton dépôt GitHub
- Clique sur "Scraper automatique des prix" puis "Run workflow" pour le
  déclencher manuellement une première fois (sans attendre la nuit)
- Vérifie que `data/prices.json` se met à jour avec de vrais prix

### 6. Brancher l'appli sur ces données
Dans `paniere.html`, remplace la constante `URL_PRIX_REELS` (en haut du script)
par :
```
https://raw.githubusercontent.com/TON-PSEUDO/paniere-scraper/main/data/prices.json
```

C'est tout — à partir de là, le scraper tourne seul chaque nuit, et l'appli
affiche automatiquement les prix les plus récents à chaque ouverture.

## Limites à connaître

- Si un site change sa structure de page, le scraper peut se casser
  silencieusement : vérifie de temps en temps l'onglet "Actions" sur GitHub
  pour voir si l'exécution a échoué (croix rouge).
- Les CGU de la plupart des enseignes interdisent le scraping automatisé à
  but commercial. Pour un usage personnel/prototype à faible volume, le risque
  pratique est faible, mais ce n'est pas une garantie juridique.
- GitHub Actions gratuit a une limite de minutes d'exécution par mois pour les
  dépôts publics — largement suffisant pour un scraper qui tourne une fois par
  nuit sur quelques dizaines de produits.
