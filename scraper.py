import requests
import csv

# URL de l'API Civix pour récupérer les parlementaires
API_URL = "https://api.civix.fr/deputes"

# Les codes des 5 départements normands
DEPARTEMENTS_NORMANDS = ["14", "27", "50", "61", "76"]

def get_deputes_normands_civix():
    print("Connexion à l'API Civix (api.civix.fr)...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DashboardNormandieBot/1.0'
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=15)
        print(f"Statut de la réponse de l'API : {response.status_code}")
    except Exception as e:
        print(f"Erreur de connexion réseau : {e}")
        return []
    
    if response.status_code != 200:
        print("L'API Civix a refusé la connexion ou est en maintenance.")
        return []

    data = response.json()
    deputes_normands = []

    # L'API Civix renvoie généralement une liste directe ou encapsulée
    liste_deputes = data if isinstance(data, list) else data.get('results', data.get('deputes', []))

    for depute in liste_deputes:
        # Civix standardise les codes de départements (ex: "14" ou "014")
        num_dept = str(depute.get('departement_code', depute.get('num_deptmap', '')))
        if num_dept.startswith('0') and len(num_dept) > 2:
            num_dept = num_dept[1:] # On transforme "014" en "14"
            
        if num_dept in DEPARTEMENTS_NORMANDS:
            # Construction du nom complet si découpé
            nom_complet = depute.get('nom_complet')
            if not nom_complet:
                nom_complet = f"{depute.get('prenom', '')} {depute.get('nom', '')}".strip()

            deputes_normands.append({
                'nom': nom_complet,
                'departement': depute.get('departement_nom', depute.get('nom_circo', '')),
                'numero_departement': num_dept,
                'circonscription': depute.get('circonscription_numero', depute.get('num_circo', '')),
                'groupe_politique': depute.get('groupe_sigle', depute.get('groupe', '')),
                'identifiant_api': depute.get('slug', depute.get('id', '')),
                'url_nosdeputes': depute.get('url_nosdeputes', '')
            })
            
    return deputes_normands

# --- Exécution du script ---
deputes = get_deputes_normands_civix()

if deputes:
    print(f"Succès : {len(deputes)} députés normands trouvés.")
    nom_fichier = 'deputes_normands.csv'
    colonnes = ['nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique', 'identifiant_api', 'url_nosdeputes']
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes)
    print(f"Le fichier '{nom_fichier}' a été mis à jour avec succès.")
else:
    raise Exception("L'extraction a échoué. Aucun député normand n'a pu être récupéré.")
