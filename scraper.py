import requests
import csv
import time

# URLs de base pour l'annuaire
URLS_ANNUAIRE = [
    "https://www.nosparlementaires.fr/deputes/json",
    "https://www.nosdeputes.fr/deputes/json"
]

# Filtres géographiques pour la Normandie
DEPARTEMENTS_NUMEROS = ["14", "27", "50", "61", "76"]
DEPARTEMENTS_NOMS = ["calvados", "eure", "manche", "orne", "seine-maritime"]

def obtenir_liste_base():
    headers = {'User-Agent': 'Mozilla/5.0 JournalismeDonneesNormandie/1.0'}
    for url in URLS_ANNUAIRE:
        print(f"Extraction de l'annuaire sur : {url} ...")
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200 and len(res.json().get('deputes', [])) > 0:
                return res.json().get('deputes', [])
            print(f"-> URL vide ou code {res.status_code}")
        except Exception as e:
            print(f"-> Erreur sur {url} : {e}")
    return []

# 1. On récupère d'abord l'annuaire global
liste_globale = obtenir_liste_base()
if not liste_globale:
    raise Exception("Impossible de charger l'annuaire des députés.")

# 2. On filtre pour ne garder que les profils de base des Normands
profils_normands = []
for item in liste_globale:
    depute = item.get('depute', item) if isinstance(item, dict) else {}
    dept_num = str(depute.get('num_deptmap', depute.get('num_departement', ''))).strip()
    dept_nom = str(depute.get('nom_circo', depute.get('departement', ''))).lower().strip()
    
    if (dept_num in DEPARTEMENTS_NUMEROS) or any(nom in dept_nom for nom in DEPARTEMENTS_NOMS):
        profils_normands.append({
            'nom': depute.get('nom'),
            'slug': depute.get('slug'),
            'dept_num': dept_num if dept_num in DEPARTEMENTS_NUMEROS else 'Normandie',
            'circo': depute.get('num_circo'),
            'groupe': depute.get('groupe_sigle')
        })

print(f"\n{len(profils_normands)} députés normands identifiés. Début de la collecte des statistiques individuelles...")

# 3. On interroge la page de chaque député normand pour obtenir ses vrais chiffres
donnees_finales = []
headers = {'User-Agent': 'Mozilla/5.0 JournalismeDonneesNormandie/1.0'}

for i, p in enumerate(profils_normands, 1):
    # On teste le domaine principal, sinon le secondaire
    url_fiche = f"https://www.nosparlementaires.fr/{p['slug']}/json"
    print(f"[{i}/{len(profils_normands)}] Récupération de l'activité de : {p['nom']} ...")
    
    try:
        response = requests.get(url_fiche, headers=headers, timeout=15)
        if response.status_code != 200:
            # Sécurité : essai sur l'ancien domaine si le nouveau renvoie une erreur
            url_fiche = f"https://www.nosdeputes.fr/{p['slug']}/json"
            response = requests.get(url_fiche, headers=headers, timeout=15)
            
        if response.status_code == 200:
            data = response.json().get('depute', {})
            
            # On extrait les vraies statistiques d'activité actives
            p['semaines_presence'] = data.get('semaines_presence', 0)
            p['commissions_presences'] = data.get('commissions_presences', 0)
            p['interventions_hemicycle'] = data.get('interventions_longues', 0)
            p['amendements_proposes'] = data.get('amendements_proposes', 0)
            p['amendements_signes'] = data.get('amendements_cosignes', 0)
            p['amendements_adoptes'] = data.get('amendements_adoptes', 0)
            p['questions_ecrites'] = data.get('questions_ecrites', 0)
            p['questions_orales'] = data.get('questions_orales', 0)
            p['url_source'] = f"https://www.nosparlementaires.fr/{p['slug']}"
            donnees_finales.append(p)
        else:
            print(f"  -> Impossible de charger la fiche de {p['nom']} (Code {response.status_code})")
    except Exception as e:
        print(f"  -> Erreur réseau pour {p['nom']} : {e}")
        
    # Une micro-pause de 0.5 seconde entre chaque député pour être un robot poli et éviter les blocages
    time.sleep(0.5)

# 4. Écriture du fichier CSV final complet
if donnees_finales:
    nom_fichier = 'deputes_normands.csv'
    colonnes = [
        'nom', 'slug', 'dept_num', 'circo', 'groupe',
        'semaines_presence', 'commissions_presences', 'interventions_hemicycle',
        'amendements_proposes', 'amendements_signes', 'amendements_adoptes',
        'questions_ecrites', 'questions_orales', 'url_source'
    ]
    
    with open(nom_fichier, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(donnees_finales)
    print(f"\nFélicitations ! Le fichier '{nom_fichier}' contient désormais les profils ET les vrais chiffres d'activité.")
else:
    print("\nErreur : Aucune donnée d'activité n'a pu être collectée.")
