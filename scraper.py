import requests
import csv

# Liste mise à jour avec le nouveau domaine internet
URLS_A_TESTER = [
    "https://www.nosparlementaires.fr/deputes/json",
    "https://nosparlementaires.fr/deputes/json",
    "https://www.nosdeputes.fr/deputes/json",
    "https://www.nosdeputes.fr/deputes/enmandat/json"
]

# Filtres pour isoler la Normandie
DEPARTEMENTS_NUMEROS = ["14", "27", "50", "61", "76"]
DEPARTEMENTS_NOMS = ["calvados", "eure", "manche", "orne", "seine-maritime"]

def extraire_liste_globale():
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
                    print(f"-> Succès ! {len(liste)} députés trouvés sur cette URL.")
                    return liste
                else:
                    print("-> Le serveur a répondu, mais la liste est vide. Essai de l'adresse suivante...")
            else:
                print(f"-> Code erreur serveur : {response.status_code}")
        except Exception as e:
            print(f"-> Impossible de joindre cette URL : {e}")
            
    return []

def filtrer_deputes_normands(liste_globale):
    deputes_normands = []

    for item in liste_globale:
        depute = item.get('depute', item) if isinstance(item, dict) else {}
        
        # Récupération de la localisation
        dept_num = str(depute.get('num_deptmap', depute.get('num_departement', ''))).strip()
        dept_nom = str(depute.get('nom_circo', depute.get('departement', ''))).lower().strip()
        
        # On vérifie si le député est normand
        est_normand = (dept_num in DEPARTEMENTS_NUMEROS) or any(nom in dept_nom for nom in DEPARTEMENTS_NOMS)
        
        if est_normand:
            deputes_normands.append({
                'nom': depute.get('nom'),
                'departement': depute.get('nom_circo'),
                'numero_departement': dept_num if dept_num in DEPARTEMENTS_NUMEROS else 'Normandie',
                'circonscription': depute.get('num_circo'),
                'groupe_politique': depute.get('groupe_sigle'),
                'identifiant_api': depute.get('slug'),
                'url_nosdeputes': depute.get('url_nosdeputes')
            })
            
    return deputes_normands

# --- Exécution du traitement ---
liste_brute = extraire_liste_globale()

if not liste_brute:
    raise Exception("Toutes les URLs de l'API ont renvoyé une liste vide ou ont échoué.")

deputes = filtrer_deputes_normands(liste_brute)

if deputes:
    print(f"Filtrage réussi : {len(deputes)} députés normands isolés.")
    nom_fichier = 'deputes_normands.csv'
    colonnes = ['nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique', 'identifiant_api', 'url_nosdeputes']
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes)
    print(f"Le fichier '{nom_fichier}' a été généré avec succès sur votre espace GitHub.")
else:
    print("Erreur : Aucun député de la liste n'a correspondu aux critères normands.")
