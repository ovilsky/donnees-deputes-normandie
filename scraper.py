import requests
import csv

# URL de l'API pour les députés actuellement en mandat
API_URL = "https://www.nosdeputes.fr/deputes/enmandat/json"

# Les codes des 5 départements de la Normandie
DEPARTEMENTS_NORMANDS = ["14", "27", "50", "61", "76"]

def get_deputes_normands():
    print("Connexion à l'API NosDéputés.fr en cours...")
    response = requests.get(API_URL)
    
    if response.status_code != 200:
        print(f"Erreur de connexion (Code {response.status_code})")
        return []

    data = response.json()
    deputes_normands = []

    # L'API renvoie une liste dans la clé 'deputes'
    for item in data.get('deputes', []):
        depute = item.get('depute', {})
        
        # Le champ 'num_deptmap' contient le numéro du département
        if depute.get('num_deptmap') in DEPARTEMENTS_NORMANDS:
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

# --- Exécution du script ---
deputes = get_deputes_normands()

if deputes:
    print(f"\nSuccès : {len(deputes)} députés normands trouvés.\n")
    
    # Affichage d'un aperçu dans la console
    for d in deputes[:5]:  # Affiche seulement les 5 premiers pour l'exemple
        print(f"- {d['nom']} ({d['departement']}, {d['circonscription']}e circo) | Groupe : {d['groupe_politique']}")
    print("...")

    # Exportation des données en CSV pour votre dashboard
    nom_fichier = 'deputes_normands.csv'
    colonnes = ['nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique', 'identifiant_api', 'url_nosdeputes']
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes)
        
    print(f"\nLes données ont été sauvegardées avec succès dans le fichier '{nom_fichier}'.")
    print("Ce fichier CSV est prêt à être importé dans votre base de données ou votre outil de BI.")
else:
    print("Aucun député trouvé ou erreur lors de l'extraction.")
