import requests
import csv

# On reprend les URLs exactes qui ont fonctionné à l'étape précédente !
URLS_A_TESTER = [
    "https://www.nosparlementaires.fr/deputes/json",
    "https://nosparlementaires.fr/deputes/json",
    "https://www.nosdeputes.fr/deputes/json"
]

# Filtres pour la Normandie
DEPARTEMENTS_NUMEROS = ["14", "27", "50", "61", "76"]
DEPARTEMENTS_NOMS = ["calvados", "eure", "manche", "orne", "seine-maritime"]

def extraire_donnees_globales():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) JournalismeDonneesNormandie/1.0'
    }
    
    for url in URLS_A_TESTER:
        print(f"Tentative de connexion à : {url} ...")
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                liste = data.get('deputes', [])
                
                if len(liste) > 0:
                    print(f"-> Succès ! Fichier trouvé avec {len(liste)} députés.")
                    return liste
                else:
                    print("-> Serveur joint, mais liste vide. Essai de l'adresse suivante...")
            else:
                print(f"-> Code erreur serveur : {response.status_code}")
        except Exception as e:
            print(f"-> Impossible de joindre cette URL : {e}")
            
    return []

def filtrer_et_extraire_stats(liste_globale):
    deputes_normands = []

    for item in liste_globale:
        depute = item.get('depute', item) if isinstance(item, dict) else {}
        
        # Identification géographique
        dept_num = str(depute.get('num_deptmap', depute.get('num_departement', ''))).strip()
        dept_nom = str(depute.get('nom_circo', depute.get('departement', ''))).lower().strip()
        
        est_normand = (dept_num in DEPARTEMENTS_NUMEROS) or any(nom in dept_nom for nom in DEPARTEMENTS_NOMS)
        
        if est_normand:
            # Extraction combinée du profil ET des stats d'activité présentes dans le flux
            deputes_normands.append({
                # Profil
                'nom': depute.get('nom'),
                'departement': depute.get('nom_circo'),
                'numero_departement': dept_num if dept_num in DEPARTEMENTS_NUMEROS else 'Normandie',
                'circonscription': depute.get('num_circo'),
                'groupe_politique': depute.get('groupe_sigle'),
                
                # Activité & Présence (Sécurisé avec .get(..., 0) si la métrique est absente)
                'semaines_presence': depute.get('semaines_presence', 0),
                'commissions_presences': depute.get('commissions_presences', 0),
                'interventions_hemicycle': depute.get('interventions_longues', depute.get('interventions_hemicycle', 0)),
                
                # Travail législatif
                'amendements_proposes': depute.get('amendements_proposes', 0),
                'amendements_signes': depute.get('amendements_cosignes', depute.get('amendements_signes', 0)),
                'amendements_adoptes': depute.get('amendements_adoptes', 0),
                
                # Prises de parole
                'questions_ecrites': depute.get('questions_ecrites', 0),
                'questions_orales': depute.get('questions_orales', 0),
                
                # Liens
                'identifiant_api': depute.get('slug'),
                'url_nosdeputes': depute.get('url_nosdeputes')
            })
            
    return deputes_normands

# --- Lancement du traitement ---
liste_brute = extraire_donnees_globales()

if not liste_brute:
    raise Exception("Toutes les URLs ont échoué. Impossible de récupérer les profils.")

deputes = filtrer_et_extraire_stats(liste_brute)

if deputes:
    print(f"Filtrage réussi : {len(deputes)} députés normands isolés avec leurs statistiques.")
    nom_fichier = 'deputes_normands.csv'
    
    colonnes = [
        'nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique',
        'semaines_presence', 'commissions_presences', 'interventions_hemicycle',
        'amendements_proposes', 'amendements_signes', 'amendements_adoptes',
        'questions_ecrites', 'questions_orales', 'identifiant_api', 'url_nosdeputes'
    ]
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes)
        
    print(f"Le fichier complet '{nom_fichier}' a été sauvegardé sur votre espace GitHub.")
else:
    print("Erreur : Aucun député n'a correspondu aux critères normands.")
