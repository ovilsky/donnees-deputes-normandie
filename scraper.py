import requests
import csv
import time

# Configuration de l'API Civix
API_BASE_URL = "https://www.civix.fr/api"

# Filtres géographiques pour cibler la Normandie
DEPARTEMENTS_NORMANDS = ["14", "27", "50", "61", "76"]

def collecter_deputes_civix():
    headers = {
        'User-Agent': 'Mozilla/5.0 JournalismeDonneesNormandie/1.0',
        'Accept': 'application/json'
    }
    
    # 1. Requête vers le point d'accès des parlementaires / députés de Civix
    url = f"{API_BASE_URL}/parlementaires"
    print(f"Connexion à l'API Civix : {url} ...")
    
    try:
        # L'API Civix peut nécessiter de paginer ou de filtrer par type, nous récupérons la liste
        # Note : Si leur documentation spécifie un paramètre de type (ex: ?fonction=depute), il s'ajoute ici
        response = requests.get(url, headers=headers, params={"mandat": "depute"}, timeout=20)
        
        if response.status_code == 200:
            donnees = response.json()
            # Selon la structure standard Civix, les résultats sont souvent dans une clé 'results' ou 'data'
            liste_parlementaires = donnees.get('results', donnees.get('data', donnees))
            print(f"-> {len(liste_parlementaires)} parlementaires trouvés au total.")
            return liste_parlementaires
        else:
            print(f"-> Erreur API Civix (Code {response.status_code})")
            return []
    except Exception as e:
        print(f"-> Échec de la connexion à l'API Civix : {e}")
        return []

def extraire_et_filtrer_normands(liste_globale):
    normands = []
    
    for p in liste_globale:
        # Extraction adaptative selon la structure JSON de l'API Civix
        # Civix sépare généralement l'identité, le mandat (circonscription, département) et les statistiques
        departement_info = p.get('departement', p.get('num_departement', ''))
        
        # Nettoyage du numéro de département (ex: '14' ou '014')
        dept_code = str(departement_info).strip().lstrip('0')
        
        if dept_code in DEPARTEMENTS_NORMANDS:
            # Récupération des statistiques d'activité fournies par Civix
            # Civix agrège souvent ces données sous un objet 'statistiques' ou 'activite'
            stats = p.get('statistiques', p.get('activite', p))
            
            normands.append({
                # État civil & Politique
                'nom': f"{p.get('prenom', '')} {p.get('nom', '')}".strip() or p.get('nom_complet'),
                'departement': p.get('nom_departement', dept_code),
                'numero_departement': dept_code,
                'circonscription': p.get('circonscription', p.get('num_circo')),
                'groupe_politique': p.get('groupe', p.get('groupe_sigle', p.get('parti'))),
                
                # Métriques de présence et assiduité (Standardisées depuis l'API Civix)
                'semaines_presence': stats.get('semaines_presence', stats.get('presence_semaines', 0)),
                'commissions_presences': stats.get('commissions_presences', stats.get('presence_commissions', 0)),
                'interventions_hemicycle': stats.get('interventions', stats.get('prises_de_parole', 0)),
                
                # Travail législatif & amendements
                'amendements_proposes': stats.get('amendements_proposes', stats.get('amendements_deposes', 0)),
                'amendements_signes': stats.get('amendements_cosignes', stats.get('amendements_signes', 0)),
                'amendements_adoptes': stats.get('amendements_adoptes', 0),
                
                # Questions
                'questions_ecrites': stats.get('questions_ecrites', 0),
                'questions_orales': stats.get('questions_orales', 0),
                
                # Identifiant unique Civix pour d'éventuels futurs croisements
                'id_civix': p.get('id')
            })
            
    return normands

# --- Exécution du pipeline Civix ---
liste_brute = collecter_deputes_civix()

if not liste_brute:
    raise Exception("Impossible de récupérer les données depuis l'API Civix.")

deputes_normands = extraire_et_filtrer_normands(liste_brute)

if deputes_normands:
    print(f"Filtrage géographique : {len(deputes_normands)} députés normands extraits avec succès.")
    
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
        
    print(f"Le fichier '{nom_fichier}' mis à jour via Civix est prêt sur votre dépôt GitHub.")
else:
    print("Attention : Aucun député n'a correspondu aux départements normands (14, 27, 50, 61, 76).")
