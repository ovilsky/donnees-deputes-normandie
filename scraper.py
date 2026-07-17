import requests
import csv

# URL officielle de l'API
API_URL = "https://www.nosdeputes.fr/deputes/enmandat/json"

# Nos filtres pour la Normandie
DEPARTEMENTS_NUMEROS = ["14", "27", "50", "61", "76"]
DEPARTEMENTS_NOMS = ["calvados", "eure", "manche", "orne", "seine-maritime"]

def get_deputes_normands():
    print("Connexion à l'API NosDéputés.fr...")
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
        return []

    data = response.json()
    
    # --- BLOC DE DÉBOGAGE (Pour inspecter la structure en cas de souci) ---
    print(f"Type de données racine : {type(data)}")
    if isinstance(data, dict):
        print(f"Clés trouvées à la racine du JSON : {list(data.keys())}")
        liste_globale = data.get('deputes', [])
    else:
        liste_globale = data if isinstance(data, list) else []
        
    print(f"Nombre total de députés dans l'API nationale : {len(liste_globale)}")
    if len(liste_globale) > 0:
        print(f"Structure brute du premier élément pour vérification : {liste_globale[0]}")
    # ---------------------------------------------------------------------

    deputes_normands = []

    for item in liste_globale:
        # On extrait la fiche du député, qu'elle soit encapsulée ou directe
        depute = item.get('depute', item) if isinstance(item, dict) else {}
        
        # Récupération des informations de localisation
        dept_num = str(depute.get('num_deptmap', depute.get('num_departement', ''))).strip()
        dept_nom = str(depute.get('nom_circo', depute.get('departement', ''))).lower().strip()
        
        # Le député est-il normand ? (Vérification par numéro OU par nom)
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

# --- Lancement du traitement ---
deputes = get_deputes_normands()

if deputes:
    print(f"Succès : {len(deputes)} députés normands trouvés.")
    nom_fichier = 'deputes_normands.csv'
    colonnes = ['nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique', 'identifiant_api', 'url_nosdeputes']
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes)
    print(f"Le fichier '{nom_fichier}' a été créé avec succès.")
else:
    print("Erreur : Aucun député n'a correspondu aux critères normands.")
    raise Exception("L'extraction a échoué. La liste filtrée est vide.")
