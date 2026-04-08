import anthropic
import smtplib
import requests 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configuration
CLE_API = "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"
EMAIL = "antoine.huber13@gmail.com"
MOT_DE_PASSE_GMAIL = "wmox zfvh nizg cahh"
DESTINATAIRE = "antoine.huber13@gmail.com"

client = anthropic.Anthropic(api_key=CLE_API)

def recuperer_ao_boamp():
    from datetime import datetime
    import json

    url = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
    params = {
    "limit": 20,
    "order_by": "dateparution desc",
    "where": "(code_departement='67' or code_departement='68' or code_departement='57') and (objet like '%voirie%' or objet like '%VRD%' or objet like '%terrassement%' or objet like '%réseau%' or objet like '%assainissement%' or objet like '%chaussée%')"
}
    reponse = requests.get(url, params=params)
    data = reponse.json()

    aos = []
    for record in data["results"]:
        # Calcul du délai réel
        date_limite = record.get("datelimitereponse", "")
        if date_limite:
            date_limite_dt = datetime.fromisoformat(date_limite[:10])
            delai = (date_limite_dt - datetime.now()).days
        else:
            delai = 21

        # Extraction du budget depuis donnees
        budget = 1000000
        donnees = record.get("donnees", {})
        if isinstance(donnees, str):
            try:
                donnees = json.loads(donnees)
            except:
                donnees = {}
        try:
            valeur = donnees.get("MAPA", {}).get("initial", {}).get("caracteristiques", {}).get("variantes", {}).get("principales", [{}])
            if isinstance(valeur, list) and len(valeur) > 0:
                montant = valeur[0].get("duree", {}).get("nbMois", "")
        except:
            pass

        aos.append({
            "titre": record.get("objet", "Sans titre")[:100],
            "type": record.get("famille_libelle", "Inconnu"),
            "zone": record.get("code_departement", "Inconnu"),
            "budget": budget,
            "delai": max(delai, 0)
        })
    return aos

profil_entreprise = {
    "metiers": ["VRD", "terrassement", "aménagement urbain"],
    "zone": "Alsace",
    "budget_min": 500000,
    "budget_max": 2000000,
    "delai_min": 15
}

appels_offres = recuperer_ao_boamp()

def scorer(ao):
    score = 0

    # On laisse Claude juger le type de travaux
    reponse = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"Est-ce que ce chantier correspond aux métiers VRD, terrassement ou aménagement urbain ? Réponds uniquement par OUI ou NON : {ao['titre']}"
        }]
    )
    if "OUI" in reponse.content[0].text.upper():
        score += 40

    if ao["zone"] in ["67", "68", "57"]:
        score += 30

    if profil_entreprise["budget_min"] <= ao["budget"] <= profil_entreprise["budget_max"]:
        score += 20

    if ao["delai"] >= profil_entreprise["delai_min"]:
        score += 10

    return score

def analyser(ao):
    reponse = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"En 3 lignes maximum, analyse cet AO pour une PME de VRD en Alsace : {ao['titre']}, budget {ao['budget']}€, délai {ao['delai']} jours. Points forts et points de vigilance."
        }]
    )
    return reponse.content[0].text

def generer_html(resultats):
    html = """
    <html><head><meta charset="UTF-8"><style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; background: #f5f5f5; }
        h1 { color: #2C2C2A; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .score { font-size: 24px; font-weight: bold; float: right; width: 50px; height: 50px; border-radius: 50%; text-align: center; line-height: 50px; }
        .score-high { background: #E1F5EE; color: #085041; }
        .score-low { background: #FCEBEB; color: #791F1F; }
        .titre { font-size: 16px; font-weight: bold; margin-bottom: 5px; }
        .analyse { font-size: 13px; color: #5F5E5A; line-height: 1.6; border-left: 3px solid #ddd; padding-left: 10px; margin-top: 10px; }
    </style></head><body>
    <h1>Rapport AO du jour</h1>
    """
    for r in resultats:
        ao = r["ao"]
        score = r["score"]
        if score >= 70:
            priorite = "🟢 À étudier en priorité"
            cls = "score-high"
        elif score >= 40:
            priorite = "🟡 À regarder si disponibilité"
            cls = "score-high"
        else:
            priorite = "🔴 Non pertinent"
            cls = "score-low"
        analyse = analyser(ao) if score >= 40 else "AO non pertinent."
        html += f"""
        <div class="card">
            <div class="score {cls}">{score}</div>
            <div class="titre">{ao['titre']}</div>
            <div>{priorite}</div>
            <div class="analyse">{analyse}</div>
        </div>"""
    html += "</body></html>"
    return html

def envoyer_email(contenu_html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Rapport AO du jour"
    msg["From"] = EMAIL
    msg["To"] = DESTINATAIRE
    msg.attach(MIMEText(contenu_html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(EMAIL, MOT_DE_PASSE_GMAIL)
        serveur.sendmail(EMAIL, DESTINATAIRE, msg.as_string())
        print("Email envoyé !")

# Lancement
resultats = []
for ao in appels_offres:
    resultats.append({"ao": ao, "score": scorer(ao)})
resultats = sorted(resultats, key=lambda x: x["score"], reverse=True)

html = generer_html(resultats)
envoyer_email(html)
print("Agent terminé !")