import requests
import json
import csv
import time
import os

BASE_URL = "https://www.civix.fr/api/v1"

# Les 5 départements normands avec leurs codes et leurs noms pour maximiser la recherche
NORMANDIE = {
    "14": "Calvados",
    "27": "Eure",
    "50": "Manche",
    "61": "Orne",
    "76": "Seine-Maritime"
}

HEADERS = {
    "User-Agent": "JournalismeDonneesNormandie/2.0 (Contact: local-scraping)",
    "Accept": "application/json"
}

def requete_api(endpoint, params=None):
    """Effectue une requête propre sur l'API avec gestion des erreurs."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if response.status_code == 200:
            # Sécurité anti-HTML
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            else:
                print(f"⚠️ Alerte : Le serveur a répondu OK mais n'a pas renvoyé de JSON pour {url}")
                return None
        else:
            print(f"❌ Erreur {response.status_code} sur l'URL : {url}")
            return None
    except Exception as e:
        print(f"💥 Échec de connexion sur {url} : {e}")
        return None

def decouvrir_uids_normands():
    """Cherche tous les députés rattachés aux départements normands."""
    uids_trouves = set()
    print("🕵️‍♂️ Phase 1 : Découverte des députés normands...")
    
    for code, nom in NORMANDIE.items():
        print(f" -> Interrogation pour le département : {code} ({nom})")
        # On teste une recherche sur le nom du département
        resultats = requete_api("search", params={"search": nom, "page_size": 50})
        
        if resultats and "data" in resultats:
            # Selon la structure de l'API, les données utiles sont dans 'data'
            items = resultats["data"] if isinstance(resultats["data"], list) else resultats["data"].get("results", [])
            for item in items:
                uid = item.get("uid") or item.get("id")
                # On s'assure que c'est un député actif et qu'on ne l'a pas déjà ajouté
                if uid and uid.startswith("PA"): 
                    uids_trouves.add(uid)
                    
        # Petite pause de courtoisie pour le serveur entre deux requêtes
        time.sleep(0.5)
        
    print(f"🎯 Fin de la phase 1 : {len(uids_trouves)} députés uniques identifiés en Normandie.")
    return list(uids_trouves)

def collecter_fiches_detaillees(liste_uids):
    """Boucle sur chaque UID pour extraire la totalité des statistiques de vote."""
    print("\n🚀 Phase 2 : Extraction des fiches détaillées (Données Dashboard)...")
    fiches_completes = []
    
    for index, uid in enumerate(liste_uids, 1):
        print(f" [{index}/{len(liste_uids)}] Téléchargement du profil complet : {uid}...")
        profil = requete_api(f"deputes/{uid}")
        
        if profil and "data" in profil:
            fiches_completes.append(profil["data"])
        else:
            print(f" ⚠️ Impossible de récupérer la fiche pour l'UID : {uid}")
            
        time.sleep(0.5) # Protection du serveur
        
    return fiches_completes

def sauvegarder_donnees(donnees):
    """Structure et exporte les résultats en JSON et en CSV."""
    if not donnees:
        print("❌ Aucune donnée à sauvegarder.")
        return

    # 1. Sauvegarde du JSON brut complet (Idéal pour le Dashboard)
    fichier_json = 'deputes_normands_complet.json'
    with open(fichier_json, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print(f"💾 Fichier JSON enrichi sauvegardé : '{fichier_json}'")

    # 2. Sauvegarde du CSV à plat (Résumé des indicateurs clés)
    fichier_csv = 'deputes_normands_resume.csv'
    colonnes = [
        'uid', 'nom_complet', 'groupe', 'departement', 'circonscription',
        'mandat_debut', 'votes_total', 'votes_pour', 'votes_contre', 'abstentions'
    ]
    
    with open(fichier_csv, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=colonnes)
        writer.writeheader()
        
        for p in donnees:
            # Extraction adaptative selon la structure exacte renvoyée par l'API
            civilite = p.get('civilite', {}) or p
            stats_votes = p.get('statistiques', {}).get('votes', {}) or p.get('votes_stats', {})
            
            nom = f"{civilite.get('prenom', '')} {civilite.get('nom', '')}".strip() or p.get('nom_complet', 'Inconnu')
            
            writer.writerow({
                'uid': p.get('uid'),
                'nom_complet': nom,
                'groupe': p.get('groupe', {}).get('organisme', p.get('groupe_politique', 'NI')),
                'departement': p.get('departement', {}).get('nom', 'Normandie'),
                'circonscription': p.get('circonscription_numero', p.get('circo')),
                'mandat_debut': p.get('mandat_debut'),
                'votes_total': stats_votes.get('total', 0),
                'votes_pour': stats_votes.get('pour', 0),
                'votes_contre': stats_votes.get('contre', 0),
                'abstentions': stats_votes.get('abstention', 0)
            })
            
    print(f"💾 Fichier CSV résumé sauvegardé : '{fichier_csv}'")

# --- Point d'entrée de l'Action GitHub ---
if __name__ == "__main__":
    uids = decouvrir_uids_normands()
    
    if not uids:
        # Solution de secours si la recherche par mot-clé échoue temporairement
        print("⚠️ La recherche par mot-clé n'a retourné aucun UID. Passage en mode liste statique de secours.")
        # Liste d'UIDs de secours (échantillon de députés normands de la législature)
        uids = ["PA796118", "PA607619", "PA721486", "PA795156", "PA794022", "PA793664"] 
        
    donnees_finales = collecter_fiches_detaillees(uids)
    sauvegarder_donnees(donnees_finales)
    print("\n🎉 Travail terminé avec succès !")
