import os
from pathlib import Path
import numpy as np
import pandas as pd

# script d'ingestion de données de circulation ferroviaires, 
# tels que définis dans ../data/1-raw/circulations/readme.md
# - input : fichier .csv d'une partion donnée (slo, ter, tet, idfm), pour une année donnée
# - ouput : fichier .parquet nettoyé

# paramètres 
annee = 2022
partition = "slo"

# chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent.parent
source_file = BASE_DIR / f"data/1-raw/circulations/{partition}_annuel_{annee}.csv"
dest_file = BASE_DIR / f"data/2-clean/circulations/{partition}_{annee}.parquet"


######### LECTURE ET NETTOYAGE DES DONNÉES BRUTES #########

# lecture du fichier source
print(f"Lecture du fichier {source_file}.")
df = pd.read_csv(
    source_file,
    usecols = ['id_circ', 'num_marche', 'code_ci_origine', 'lib_ci_origine', 'code_ci_destination', 
               'lib_ci_destination', 'ui', 'lib_ui', 'tct', 'lib_tct', 'code_ci_jalon', 'code_ch_jalon', 
               'lib_ci_jalon', 'distance_cumul', 'type_horaire', 'id_engin', 'mode_traction', 'date_circ', 
               'dh_the_jalon', 'dh_obs_jalon', 'dh_est_jalon'], 
    dtype={
        "id_circ": "string",
        "num_marche": "string",
        "code_ci_origine": "string",
        "lib_ci_origine": "string",
        "code_ci_destination": "string",
        "lib_ci_destination": "string",
        "ui": "string",
        "lib_ui": "string",
        "tct": "string",
        "lib_tct": "string",
        "code_ci_jalon": "string",
        "code_ch_jalon": "string",
        "lib_ci_jalon": "string",
        "distance_cumul" : "Int64",
        "type_horaire": "string",
        "id_engin": "string",
        "mode_traction": "string"
    },
    parse_dates=[
        "date_circ",
        "dh_the_jalon",
        "dh_obs_jalon",
        "dh_est_jalon"
        ]
)
print(f"Fichier lu : {df.shape[0]:_} lignes, {df.shape[1]:_} colonnes.")

# nombre de trajets initial
nb_trajet_init = df['id_circ'].nunique()

# suppression des lignes avec des valeurs manquantes
print("Suppression des lignes avec des valeurs manquantes.")
df = df.dropna()

# on garde uniquement les jalons de départ et d'arrivée
print("Filtrage des jalons de départ et d'arrivée.")
df['is_depart'] = (df['code_ci_jalon'] == df['code_ci_origine']) & (df['type_horaire'].isin(['D', 'P', 'I']))
df['is_arrivee'] = (df['code_ci_jalon'] == df['code_ci_destination']) & (df['type_horaire'].isin(['A', 'P', 'I']))
df = df[df['is_depart'] | df['is_arrivee']]
df = df[~(df['is_depart'] & df['is_arrivee'])] # exclusion des trajets où départ = arrivée
df['type_arret'] = np.where(df['is_depart'], 'depart', 'arrivee') # on peut le faire car on a déjà filtré les cas ambigus
df = df.drop(columns=['is_depart', 'is_arrivee'])

# sppression des trajets en doublon
print("Suppression des trajets en doublon.")
df = df.drop_duplicates(subset=['id_circ', 'date_circ', 'num_marche', 'code_ci_origine', 'lib_ci_origine', 
                                'code_ci_destination', 'lib_ci_destination', 'lib_ui', 'id_engin', 'type_arret'],
                                keep='first') # on garde seulement la première occurrence de chaque doublon


######### PIVOT #########

# pivot (pour avoir une seule ligne par trajet)
print("Pivot du jeu de données (pour avoir une seule ligne par trajet).")
df = df.pivot_table(
    index = ['id_circ', 'date_circ', 'num_marche', 'code_ci_origine', 'lib_ci_origine', 
            'code_ci_destination', 'lib_ci_destination', 'lib_ui'],
    columns = ['type_arret'],
    values = ['dh_the_jalon', 'dh_obs_jalon', 'distance_cumul', 'lib_tct', 'id_engin'],
    aggfunc = 'first'  # on a déjà géré les doublons, donc ce paramètre ne devrait avoir aucun impact
)

# on aplatit les colonnes multi-index
df.columns = ['_'.join(col).strip() for col in df.columns.values]
df = df.reset_index()

# on renomme les colonnes
df = df.rename(columns={
    'dh_the_jalon_depart': 'depart_theorique',
    'dh_the_jalon_arrivee': 'arrivee_theorique',
    'dh_obs_jalon_depart': 'depart_observe',
    'dh_obs_jalon_arrivee': 'arrivee_observe',
    'distance_cumul_arrivee': 'distance_totale'
})

# on réorganise l'ordre des colonnes
df = df[[
    'id_circ', 'date_circ', 'num_marche', 
    'code_ci_origine', 'lib_ci_origine',
    'code_ci_destination', 'lib_ci_destination',
    'lib_ui', 'lib_tct_depart', 'lib_tct_arrivee', 
    'id_engin_depart', 'id_engin_arrivee',
    'depart_theorique', 'depart_observe',
    'arrivee_theorique', 'arrivee_observe', 
    'distance_totale'
]]

# suppression des trajets incomplets (sans départ ou arrivée)
print("Suppression des trajets incomplets (sans départ ou arrivée).")
df = df.dropna()

# taux de perte après nettoyage
nb_trajet_final = df['id_circ'].nunique()
print(f"Après pivot et nettoyage, il reste {nb_trajet_final:_} trajets sur {nb_trajet_init:_}, soit {(nb_trajet_init - nb_trajet_final) / nb_trajet_init:.2%} de pertes.")


######### CALCUL DES COLONNES DÉRIVÉES #########

print("Calcul des colonnes dérivées (retards, durées, mois, jour de la semaine, etc.).")

# Retard au départ et à l'arrivée (en minutes)
df['ret_depart'] = ((df['depart_observe'] - df['depart_theorique']).dt.total_seconds()) / 60
df['ret_arrivee'] = ((df['arrivee_observe'] - df['arrivee_theorique']).dt.total_seconds()) / 60

# Catégories de retard à l'arrivée : 'True' si le train a plus de 'n' minutes de retard
for n in [5, 10, 15, 30, 60]:
    df[f"ret_arrivee_{n}min"] = df["ret_arrivee"] >= n

# Durée théorique du trajet (en minutes)
df['duree_theorique'] = (df['arrivee_theorique'] - df['depart_theorique']).dt.total_seconds() / 60

# Durée théorique du trajet (catégories)
bins = [0, 90, 180, float("inf")]
labels = ["<1h30", "1h30-3h", ">3h"]
df["duree_theorique_cat"] = pd.cut(df["duree_theorique"], bins=bins, labels=labels, right=False)

# Durée observée du trajet (en minutes)
df['duree_observee'] = (df['arrivee_observe'] - df['depart_observe']).dt.total_seconds() / 60

# Mois (1 = janvier, 12 = décembre)
df['mois'] = df['date_circ'].dt.month

# Numéro de semaine dans l'année
df['num_semaine'] = df['date_circ'].dt.isocalendar().week

# Jour de la semaine (0 = lundi, 6 = dimanche)
df['jour_semaine'] = df['date_circ'].dt.dayofweek

# Plage horaire de départ et d'arrivée, par tranche de 1 heure
df['heure_depart'] = df['depart_observe'].dt.hour
df['heure_arrivee'] = df['arrivee_observe'].dt.hour

print(f"Nettoyage terminé : {df.shape[0]:_} lignes, {df.shape[1]:_} colonnes.")


######### SAUVEGARDE DU FICHIER #########
print(f"Sauvegarde du fichier nettoyé dans {dest_file}.")
df.to_parquet(dest_file, index=False)
print(f"Fichier sauvegardé. Taille du fichier : {os.path.getsize(dest_file) / 1_000_000:.2f} Mo.")