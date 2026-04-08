import anthropic

client = anthropic.Anthropic(api_key="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")

profil_entreprise = {
    "metiers": ["VRD", "terrassement", "aménagement urbain"],
    "zone": "Alsace",
    "budget_min": 500000,
    "budget_max": 2000000,
    "delai_min": 15
}

appels_offres = [
    {
        "titre": "Réhabilitation voirie - Strasbourg",
        "type": "VRD",
        "zone": "Alsace",
        "budget": 1200000,
        "delai": 28
    },
    {
        "titre": "Charpente métallique - Lyon",
        "type": "charpente métallique",
        "zone": "Rhône-Alpes",
        "budget": 4000000,
        "delai": 10
    },
    {
        "titre": "Terrassement - Colmar",
        "type": "terrassement",
        "zone": "Alsace",
        "budget": 800000,
        "delai": 12
    }
]

def scorer(appel_offre):
    score = 0
    if appel_offre["type"] in profil_entreprise["metiers"]:
        score += 40
    if appel_offre["zone"] == profil_entreprise["zone"]:
        score += 30
    if profil_entreprise["budget_min"] <= appel_offre["budget"] <= profil_entreprise["budget_max"]:
        score += 20
    if appel_offre["delai"] >= profil_entreprise["delai_min"]:
        score += 10
    return score

def analyser_avec_claude(appel_offre):
    reponse = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": f"En 3 lignes maximum, analyse cet AO pour une PME de VRD en Alsace : {appel_offre['titre']}, budget {appel_offre['budget']}€, délai {appel_offre['delai']} jours. Points forts et points de vigilance."
            }
        ]
    )
    return reponse.content[0].text

print("\n=== RAPPORT DU JOUR ===\n")

resultats = []
for ao in appels_offres:
    score = scorer(ao)
    resultats.append({"ao": ao, "score": score})

resultats = sorted(resultats, key=lambda x: x["score"], reverse=True)

for r in resultats:
    ao = r["ao"]
    score = r["score"]

    if score >= 70:
        priorite = "🟢 À étudier en priorité"
    elif score >= 40:
        priorite = "🟡 À regarder si disponibilité"
    else:
        priorite = "🔴 Non pertinent"

    print(f"--- {ao['titre']} ---")
    print(f"Score : {score}/100 — {priorite}")

    if score >= 40:
        print("Analyse Claude :")
        print(analyser_avec_claude(ao))
    else:
        print("Analyse : AO non pertinent, pas d'analyse détaillée.")
    print()

html = """
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; background: #f5f5f5; }
        h1 { color: #2C2C2A; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .score { font-size: 24px; font-weight: bold; float: right; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .score-high { background: #E1F5EE; color: #085041; }
        .score-low { background: #FCEBEB; color: #791F1F; }
        .titre { font-size: 16px; font-weight: bold; margin-bottom: 5px; }
        .priorite { font-size: 13px; margin-bottom: 10px; }
        .analyse { font-size: 13px; color: #5F5E5A; line-height: 1.6; border-left: 3px solid #ddd; padding-left: 10px; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Rapport AO du jour</h1>
"""

for r in resultats:
    ao = r["ao"]
    score = r["score"]
    if score >= 70:
        priorite = "🟢 À étudier en priorité"
        score_class = "score-high"
    elif score >= 40:
        priorite = "🟡 À regarder si disponibilité"
        score_class = "score-high"
    else:
        priorite = "🔴 Non pertinent"
        score_class = "score-low"

    analyse = analyser_avec_claude(ao) if score >= 40 else "AO non pertinent."

    html += f"""
    <div class="card">
        <div class="score {score_class}">{score}</div>
        <div class="titre">{ao['titre']}</div>
        <div class="priorite">{priorite}</div>
        <div class="analyse">{analyse}</div>
    </div>
"""

html += "</body></html>"

with open("rapport_ao.html", "w", encoding="utf-8") as f:
    f.write(html)

print("\nRapport HTML généré ! Ouvre le fichier rapport_ao.html dans ton navigateur.")