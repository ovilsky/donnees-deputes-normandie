import requests
import json
import csv
import time

BASE_URL = "https://www.civix.fr/api/v1"

# Cartographie stricte des 28 députés normands (Législature actuelle)
# Classés par département pour faciliter le filtrage ultérieur de votre Dashboard
DEPUTES_NORMANDS_CONFIG = {
    # CALVADOS (14)
    "PA796118": {"departement": "Calvados", "circo": 1},
    "PA607619": {"departement": "Calvados", "circo": 2},
    "PA721486": {"departement": "Calvados", "circo": 3},
    "PA795156": {"departement": "Calvados", "circo": 4},
    "PA794022": {"departement": "Calvados", "circo": 5},
    "PA793664": {"departement": "Calvados", "circo": 6},
    
    # EURE (27)
    "PA793992": {"departement": "Eure", "circo": 1},
    "PA793912": {"departement": "Eure", "circo": 2},
    "PA793744": {"departement": "Eure", "circo": 3},
    "PA793394": {"departement": "Eure", "circo": 4},
    "PA721246": {"departement": "Eure", "circo": 5},
    
    # MANCHE (50)
    "PA720728": {"departement": "Manche", "circo": 1},
    "PA795058": {"departement": "Manche", "circo": 2},
    "PA606171": {"departement": "Manche", "circo": 3},
    "PA795228": {"departement": "Manche", "circo": 4},
    
    # ORNE (61)
    "PA721006": {"departement": "Orne", "circo": 1},
    "PA795438": {"departement": "Orne", "circo": 2},
    "PA719024": {"departement": "Orne", "circo": 3},
    
    # SEINE-MARITIME (76)
    "PA795168": {"departement": "Seine-Maritime", "circo": 1},
    "PA795684": {"departement": "Seine-Maritime", "circo": 2},
    "PA795778": {"departement": "Seine-Maritime", "circo": 3},
    "PA795808": {"departement": "Seine-Maritime", "circo": 4},
    "PA795270": {"departement": "Seine-Maritime", "circo": 5},
    "PA794838": {"departement": "Seine-Maritime", "circo": 6},
    "PA794146": {"departement": "Seine-Maritime", "circo": 7},
    "PA795244": {"departement": "Seine-Maritime", "circo": 8},
    "PA794442": {"departement": "Seine-Maritime", "circo": 9},
    "PA721328": {"departement": "Seine-Maritime", "circo": 10}
}

HEADERS = {
    "User-Agent": "JournalismeDonneesNormandie/2.5 (Contact: local-scraping)",
    "Accept": "application/json"
}

def collecter_fiches_detaillees():
    """Parcourt la liste fixe des députés normands pour extraire l'essentiel."""
    print("🚀 Extraction des profils officiels depuis CIVIX...")
    fiches_completes = []
    
    for index, (uid, meta) in enumerate(DEPUTES_NORMANDS_CONFIG.items(), 1):
        url = f"{BASE_URL}/deputes/{uid}"
        print(f" [{index}/{len(DEPUTES_NORMANDS_CONFIG)}] Extraction : {uid} ({meta['departement']})")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
                json_data = response.json()
                
                # CIVIX encapsule généralement ses réponses dans une clé 'data' ou à la racine
                bloc_depute = json_data.get("data", json_data)
                
                if bloc_depute:
                    # On injecte nos métadonnées géographiques locales pour enrichir le JSON
                    bloc_depute["meta_departement"] = meta["departement"]
                    bloc_depute["meta_circonscription"] = meta["circo"]
                    fiches_completes.append(bloc_depute)
            else:
                print(f" ⚠️ Réponse invalide ou absente pour {uid} (Status: {response.status_code})")
        except Exception as e:
            print(f" 💥 Erreur de connexion pour {uid} : {e}")
            
        time.sleep(0.4) # Respect du serveur
        
    return fiches_completes

def sauvegarder_donnees(donnees):
    """Structure et exporte proprement les résultats."""
    if not donnees:
        print("❌ Aucune donnée collectée. Export annulé.")
        return

    # 1. Export JSON complet (Idéal pour les structures imbriquées complexes du Dashboard)
    fichier_json = 'deputes_normands_complet.json'
    with open(fichier_json, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print(f"💾 Fichier JSON enrichi sauvegardé : '{fichier_json}'")

    # 2. Export CSV plat (Résumé analytique)
    fichier_csv = 'deputes_normands_resume.csv'
    colonnes = [
        'uid', 'nom_complet', 'groupe', 'departement', 'circonscription',
        'votes_total', 'votes_pour', 'votes_contre', 'abstentions'
    ]
    
    with open(fichier_csv, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=colonnes)
        writer.writeheader()
        
        for p in donnees:
            # Sécurité de lecture adaptative selon la structure interne de la fiche de l'élu
            civilite = p.get('civilite', {}) or p
            prenom = civilite.get('prenom', p.get('prenom', ''))
            nom_famille = civilite.get('nom', p.get('nom', ''))
            nom_complet = f"{prenom} {nom_famille}".strip() or p.get('nom_complet', 'Identité non lue')
            
            # Parsing des statistiques de votes
            stats = p.get('statistiques', {}).get('votes', {}) or p.get('votes_stats', {})
            
            # Identification du groupe parlementaire
            groupe_bloc = p.get('groupe', {}) or {}
            groupe_nom = groupe_bloc.get('organisme', p.get('groupe_politique', 'Non inscrit'))
            
            writer.writerow({
                'uid': p.get('uid') or p.get('id'),
                'nom_complet': nom_complet,
                'groupe': groupe_nom,
                'departement': p.get('meta_departement'),
                'circonscription': p.get('meta_circonscription'),
                'votes_total': stats.get('total', stats.get('total_votes', 0)),
                'votes_pour': stats.get('pour', 0),
                'votes_contre': stats.get('contre', 0),
                'abstentions': stats.get('abstention', stats.get('abstentions', 0))
            })
            
    print(f"💾 Fichier CSV résumé sauvegardé : '{fichier_csv}'")

if __name__ == "__main__":
    donnees_finales = collecter_fiches_detaillees()
    sauvegarder_donnees(donnees_finales)
    print("\n🎉 Nettoyage et structuration terminés avec succès !")
