Ce dossier contient les données brutes au format csv, utilisées comme source initiale avant transformation et optimisation.
- **gares-de-voyageurs.csv** : liste des gares. source : https://www.data.gouv.fr/datasets/gares-de-voyageurs-1
- **circulations_ferroviaires** : dataset contenant l'ensemble des circulations ferroviaires entre 2017 et 2024. source : https://ftp.autorite-transports.fr/circulations_ferroviaires.zip
	- circulations_ferroviaire_readme.md : documentation fournie par l'ART, expliquant les fichiers et colonnes du jeu de données.
	- referentiel_tct-ui.csv : liste des entreprises ferroviaires.
	- les autres fichiers du dataset étant très volumineux (144Go), ils ne sont pas inclus dans le dépôt Git. Si besoin, vous pouvez les télécharger via le lien ci-dessus. Ces fichiers incluent notamment :
		- slo_annuel_2024.csv : liste des circulations ferroviaires "librement organisées", incluant notamment les TAGV (Trains à grande vitesse) comme InOui, Ouigo, Thalys, etc.