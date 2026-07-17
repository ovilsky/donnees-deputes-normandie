import requests
import csv

# Configuration de l'API Civix
API_BASE_URL = "https://www.civix.fr/api"
DEPARTEMENTS_NORMANDS = ["14", "27", "50", "61", "76"]

def collecter_deputes_civix():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) JournalismeDonneesNormandie/1.0',
        'Accept': 'application/json'
    }
    
    url = f"{API_BASE_URL}/parlementaires"
    print(f"Connexion à l'API Civix : {url} ...")
    
    try:
        response = requests.get(url, headers=headers, params={"mandat": "depute"}, timeout=20)
        print(f"-> Code statut reçu : {response.status_code}")
        print(f"-> Type de contenu déclaré par le serveur : {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            try:
                donnees = response.json()
                liste_parlementaires = donnees.get('results', donnees.get('data', donnees))
                return liste_parlementaires
            except ValueError as json_err:
                print("\n" + "!"*20 + " DIAGNOSTIC SERVEUR " + "!"*20)
                print("Le serveur a renvoyé du texte ou de l'HTML au lieu de données JSON.")
                print("Voici les 500 premiers caractères de la réponse pour identifier le problème :")
                print("-" * 60)
                print(response.text[:500])
                print("-" * 60)
                print("!"*60 + "\n")
                return []
        else:
            print(f"-> Erreur API Civix (Code {response.status_code})")
            return []
    except Exception as e:
        print(f"-> Échec critique de la connexion : {e}")
        return []

def extraire_et_filtrer_normands(liste_globale):
    normands = []
    for p in liste_globale:
        if not isinstance(p, dict):
            continue
        departement_info = p.get('departement', p.get('num_departement', ''))
        dept_code = str(departement_info).strip().lstrip('0')
        
        if dept_code in DEPARTEMENTS_NORMANDS:
            stats = p.get('statistiques', p.get('activite', p))
            normands.append({
                'nom': f"{p.get('prenom', '')} {p.get('nom', '')}".strip() or p.get('nom_complet'),
                'departement': p.get('nom_departement', dept_code),
                'numero_departement': dept_code,
                'circonscription': p.get('circonscription', p.get('num_circo')),
                'groupe_politique': p.get('groupe', p.get('groupe_sigle', p.get('parti'))),
                'semaines_presence': stats.get('semaines_presence', 0),
                'commissions_presences': stats.get('commissions_presences', 0),
                'interventions_hemicycle': stats.get('interventions', 0),
                'amendements_proposes': stats.get('amendements_proposes', 0),
                'amendements_signes': stats.get('amendements_cosignes', 0),
                'amendements_adoptes': stats.get('amendements_adoptes', 0),
                'questions_ecrites': stats.get('questions_ecrites', 0),
                'questions_orales': stats.get('questions_orales', 0),
                'id_civix': p.get('id')
            })
    return normands

# --- Exécution ---
liste_brute = collecter_deputes_civix()

if not liste_brute:
    raise Exception("L'API n'a pas renvoyé l'objet JSON attendu. Regardez le bloc DIAGNOSTIC SERVEUR ci-dessus dans les logs.")

deputes_normands = extraire_et_filtrer_normands(liste_brute)

if deputes_normands:
    nom_fichier = 'deputes_normands.csv'
    colonnes = [
        'nom', 'departement', 'numero_departement', 'circonscription', 'groupe_politique',
        'semaines_presence', 'commissions_presences', 'interventions_hemicycle',
        'amendements_proposes', 'amendements_signes', 'amendements_adoptes',
        'questions_ecrites', 'questions_orales', 'id_civix'
    ]
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(deputes_normands)
    print(f"Le fichier '{nom_fichier}' a été mis à jour.")
