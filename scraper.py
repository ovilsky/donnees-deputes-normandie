import os
import sys
import zipfile
import urllib.request
import xml.etree.ElementTree as ET
import csv
import json
from pathlib import Path

# Configuration des URLs Open Data de l'Assemblée nationale (17ème Législature)
URL_ACTEURS = "http://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes_divises/AMO40_deputes_actifs_mandats_actifs_organes_divises.json.zip"
URL_SCRUTINS = "http://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.xml.zip"

DIR_DATA = Path("data_assemblee")
DIR_DATA.mkdir(exist_ok=True)

def download_file(url, dest_name):
    """Télécharge un fichier avec un User-Agent pour éviter les blocages de sécurité."""
    dest_path = DIR_DATA / dest_name
    if dest_path.exists():
        print(f"-> {dest_name} déjà présent localement.")
        return dest_path
    
    print(f"Téléchargement de {url}...")
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CitizenScienceBot/1.0'}
    )
    try:
        with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
            out_file.write(response.read())
        print(f"-> Téléchargement réussi : {dest_name}")
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement de {dest_name}: {e}")
        sys.exit(1)
    return dest_path

def build_deputes_database(zip_path):
    """Analyse le fichier JSON des députés actifs pour créer un dictionnaire d'association robuste."""
    deputes_map = {}
    organes_map = {} # Pour retrouver les noms des groupes politiques (ex: PO800538 -> EPR)
    
    print("Extraction et analyse de la base des députés...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        # 1. On commence par charger les organes (groupes politiques)
        organes_file = [f for f in z.namelist() if 'organes' in f.lower() and f.endswith('.json')]
        if organes_file:
            with z.open(organes_file[0]) as f:
                organes_data = json.loads(f.read().decode('utf-8'))
                for org in organes_data.get('organes', {}).get('organe', []):
                    uid = org.get('uid')
                    code = org.get('libelleAbrev') or org.get('libelle')
                    if uid and code:
                        organes_map[uid] = code

        # 2. On charge les acteurs (députés) et leurs mandats actifs
        acteurs_file = [f for f in z.namelist() if 'acteurs' in f.lower() and f.endswith('.json')]
        if not acteurs_file:
            print("❌ Fichier des acteurs introuvable dans le ZIP.")
            sys.exit(1)
            
        with z.open(acteurs_file[0]) as f:
            acteurs_data = json.loads(f.read().decode('utf-8'))
            for acteur in acteurs_data.get('acteurs', {}).get('acteur', []):
                uid = acteur.get('uid', {}).get('#text')
                if not uid:
                    continue
                
                # Récupération de l'identité civile
                civilite = acteur.get('etatCivil', {}).get('ident', {}).get('civ') or ""
                prenom = acteur.get('etatCivil', {}).get('ident', {}).get('prenom') or ""
                nom = acteur.get('etatCivil', {}).get('ident', {}).get('nom') or ""
                nom_complet = f"{prenom} {nom}".strip()
                
                # Analyse des mandats pour trouver sa circonscription, son département et son groupe
                departement = "Inconnu"
                circonscription = "Inconnue"
                groupe = "Non inscrit"
                
                mandats = acteur.get('mandats', {}).get('mandat', [])
                if isinstance(mandats, dict):
                    mandats = [mandats]
                
                for m in mandats:
                    # On ne traite que les mandats parlementaires actifs à l'Assemblée
                    if m.get('typeOrgane') == 'ASSEMBLEE' and m.get('actif') == 'true':
                        # Extraction du département et de la circonscription
                        election = m.get('election', {})
                        lieu = election.get('lieu', {})
                        departement = lieu.get('numDepartement') or lieu.get('departement') or "Inconnu"
                        circonscription = lieu.get('numCirco') or "Inconnue"
                        
                        # Recherche de l'organe du groupe politique associé à ce mandat parlementaire
                        organes_associes = m.get('organes', {}).get('organeRef', [])
                        if isinstance(organes_associes, str):
                            organes_associes = [organes_associes]
                        for ref in organes_associes:
                            if ref.startswith('PO') and ref in organes_map:
                                # Les identifiants de groupes politiques commencent généralement par 'PO'
                                groupe = organes_map[ref]
                
                deputes_map[uid] = {
                    "uid": uid,
                    "nom_complet": nom_complet,
                    "groupe": groupe,
                    "departement": departement,
                    "circonscription": circonscription,
                    "votes_total": 0,
                    "votes_pour": 0,
                    "votes_contre": 0,
                    "abstentions": 0
                }
                
    print(f"-> Base de données de {len(deputes_map)} députés actifs constituée.")
    return deputes_map

def parse_votes_from_scrutins(zip_path, deputes_map):
    """Parcourt tous les scrutins du ZIP officiel et incrémente les votes des députés."""
    print("Analyse des fichiers de scrutins publics...")
    votes_comptabilises = 0
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        xml_files = [f for f in z.namelist() if f.endswith('.xml')]
        total_files = len(xml_files)
        
        for idx, xml_file in enumerate(xml_files):
            if idx % 100 == 0:
                print(f"   Progression : {idx}/{total_files} scrutins analysés...")
                
            with z.open(xml_file) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    
                    # On parcourt les différents groupes de votes du scrutin (pours, contres, abstentions)
                    # Structure AN : scrutin -> ventilationVotes -> extractionGroupes -> groupe -> vote -> votant -> acteurRef
                    ventilation = root.find('.//ventilationVotes')
                    if ventilation is None:
                        continue
                        
                    for group_node in ventilation.findall('.//groupe'):
                        votes_node = group_node.find('.//votes')
                        if votes_node is None:
                            continue
                        
                        # 1. On traite les votes POUR
                        pours = votes_node.find('.//pours')
                        if pours is not None:
                            for votant in pours.findall('.//votant'):
                                act_ref = votant.find('acteurRef')
                                if act_ref is not None and act_ref.text in deputes_map:
                                    deputes_map[act_ref.text]["votes_pour"] += 1
                                    deputes_map[act_ref.text]["votes_total"] += 1
                                    votes_comptabilises += 1
                                    
                        # 2. On traite les votes CONTRE
                        contres = votes_node.find('.//contres')
                        if contres is not None:
                            for votant in contres.findall('.//votant'):
                                act_ref = votant.find('acteurRef')
                                if act_ref is not None and act_ref.text in deputes_map:
                                    deputes_map[act_ref.text]["votes_contre"] += 1
                                    deputes_map[act_ref.text]["votes_total"] += 1
                                    votes_comptabilises += 1
                                    
                        # 3. On traite les ABSTENTIONS
                        abstentions = votes_node.find('.//abstentions')
                        if abstentions is not None:
                            for votant in abstentions.findall('.//votant'):
                                act_ref = votant.find('acteurRef')
                                if act_ref is not None and act_ref.text in deputes_map:
                                    deputes_map[act_ref.text]["abstentions"] += 1
                                    deputes_map[act_ref.text]["votes_total"] += 1
                                    votes_comptabilises += 1
                                    
                except ET.ParseError:
                    print(f"⚠️ Erreur de parsing XML pour le fichier {xml_file}, ignoré.")
                    continue
                    
    print(f"-> Terminé. {votes_comptabilises} votes comptabilisés sur {total_files} scrutins.")

def export_normandie_to_csv(deputes_map, output_filename="votes_deputes_normandie.csv"):
    """Filtre les députés pour la Normandie (14, 27, 50, 61, 76) et exporte un CSV propre."""
    # Codes de départements normands
    normandie_depts = {"14", "27", "50", "61", "76"}
    
    # Filtrage des députés normands (et nettoyage du format de département)
    normandie_deputes = []
    for d in deputes_map.values():
        dep_code = str(d["departement"]).strip()
        if dep_code in normandie_depts:
            normandie_deputes.append(d)
            
    if not normandie_deputes:
        print("⚠️ Aucun député normand trouvé. Sauvegarde globale de secours.")
        normandie_deputes = list(deputes_map.values())

    # Écriture propre du fichier CSV en utilisant le module de confiance de Python
    output_path = Path(output_filename)
    print(f"Génération du fichier CSV : {output_path.resolve()}...")
    
    with open(output_path, mode='w', encoding='utf-8', newline='') as csv_file:
        # Utilisation du point-virgule comme délimiteur (standard français pour Excel)
        writer = csv.writer(csv_file, delimiter=';')
        
        # En-têtes du CSV
        writer.writerow([
            "Identifiant", "Nom Complet", "Groupe", "Département", 
            "Circonscription", "Votes Total", "Votes Pour", 
            "Votes Contre", "Abstentions"
        ])
        
        # Lignes de données
        for d in sorted(normandie_deputes, key=lambda x: (x["departement"], int(x["circonscription"]) if x["circonscription"].isdigit() else 0)):
            writer.writerow([
                d["uid"],
                d["nom_complet"],
                d["groupe"],
                d["departement"],
                d["circonscription"],
                d["votes_total"],
                d["votes_pour"],
                d["votes_contre"],
                d["abstentions"]
            ])
            
    print(f"✅ Succès ! {len(normandie_deputes)} députés normands exportés.")

if __name__ == "__main__":
    print("=== Début du traitement des données parlementaires ===")
    
    # Étape 1 : Téléchargement des archives
    zip_deputes = download_file(URL_ACTEURS, "deputes_actifs.json.zip")
    zip_scrutins = download_file(URL_SCRUTINS, "scrutins.xml.zip")
    
    # Étape 2 : Construction de la base de données relationnelle locale
    db_deputes = build_deputes_database(zip_deputes)
    
    # Étape 3 : Calcul et ventilation des votes individuels
    parse_votes_from_scrutins(zip_scrutins, db_deputes)
    
    # Étape 4 : Filtrage géographique et écriture du CSV normand sécurisé
    export_normandie_to_csv(db_deputes, "votes_deputes_normandie.csv")
    
    print("=== Fin du script avec succès ===")
