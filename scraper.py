import requests
import csv

# Le vrai site officiel de NosDéputés
API_URL = "https://www.nosdeputes.fr/deputes/enmandat/json"

# Nos 5 départements normands
DEPARTEMENTS_NORMANDS = ["14", "27", "50", "61", "76"]

def get_deputes_normands():
    print("Connexion à l'API NosDéputés.fr...")
    
    # On feint d'être un navigateur classique pour éviter le blocage robot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) JournalismeDonneesNormandie/1.0'
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=20)
        print(f"Réponse du serveur reçue (Code {response.status_code})")
    except Exception as e:
        print(f"Erreur réseau lors de l'accès à NosDéputés : {e}")
        return []
    
    if response.status_code != 200:
        print("Le site NosDéputés a refusé la connexion automatique.")
        return []

    data = response.json()
    deputes_normands = []

    # Extraction des données selon la structure de NosDéputés
    for item in data.get('deputes', []):
        depute = item.get('depute', {})
        
        if str(depute.get('num_deptmap')) in DEPARTEMENTS_NORMANDS:
            deputes_normands.append({
                'nom': depute.get('nom'),
                'departement': depute.get('nom_circo'),
                'numero_departement': depute.get('num_deptmap'),
                'circonscription': depute.get('num_circo'),
                'groupe_politique': depute.get('groupe_sigle'),
                'identifiant_api': depute.get('slug'),
                'url_nosdeputes': depute.get('url_nosdeputes')
            })
            
    return deputes_normands

# --- Lancement du traitement ---
deputes = get_deputes_normands()

if deputes:
    print(f"Succès : {len(deputes)} députés normands récupérés.")
    nom_fichier = 'deputes_normands.csv'
    colonnes = ['nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique', 'identifiant_api', 'url_nosdeputes']
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes)
    print(f"Le fichier '{nom_fichier}' a été créé avec succès sur votre dépôt.")
else:
    raise Exception("L'extraction a échoué. Impossible de générer le fichier CSV.")
