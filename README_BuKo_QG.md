# BuKo QG — langage, application Android et site officiel

Ce dépôt unique contient plusieurs fichiers spécialisés : on ne met pas tout le code dans un seul fichier Python.

## Arborescence à conserver

- `main.py` : interface prototype Android écrite en Python/Kivy.
- `buko_engine_v0_6.py` : moteur du langage BuKo utilisé par l'application.
- `buildozer.spec` : configuration de compilation de l'application Android.
- `.github/workflows/build-android.yml` : compilation automatique d'un APK de test sur GitHub Actions.
- `docs/index.html` et `docs/style.css` : site officiel statique, modifiable depuis GitHub.

## Ajouter les fichiers depuis un téléphone

1. Crée un dépôt GitHub public nommé `buko-language`.
2. Dans le dépôt, utilise **Add file → Upload files** et envoie le contenu du dossier du projet en gardant exactement les chemins indiqués ci-dessus.
3. Assure-toi que `.github/workflows/build-android.yml` existe bien à la racine du dépôt. Le dossier `.github` peut être caché dans le gestionnaire de fichiers.
4. Pour compiler l'APK, va dans **Actions → Build BuKo Android APK → Run workflow**. À la fin, ouvre l'exécution et télécharge l'artifact `buko-studio-mobile-debug-apk`.
5. Pour publier le site, va dans **Settings → Pages**, choisis **Deploy from a branch**, branche `main`, dossier `/docs`, puis **Save**. GitHub affichera l'adresse publique du site dans cette section.

## Modifier le site directement sur GitHub

Ouvre `docs/index.html` pour modifier les textes et sections. Ouvre `docs/style.css` pour changer les couleurs, espacements et présentation. Appuie sur le crayon pour éditer, puis **Commit changes**. Après activation de GitHub Pages, les changements du site seront publiés automatiquement après un court délai.

## Limites actuelles

- L'application Android est un prototype Kivy, pas encore un IDE complet.
- Le dépôt contient les sources, pas un APK précompilé.
- Le site est une page statique. Il n'exécute pas encore de code BuKo dans le navigateur et ne contient pas encore d'éditeur de site intégré.
- La compilation Android doit être réellement exécutée dans GitHub Actions et son résultat testé sur un appareil.
