import streamlit as st
import anthropic
import smtplib
import requests
import json
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os
CLE_API = os.environ.get("ANTHROPIC_API_KEY", "")
EMAIL = os.environ.get("EMAIL", "")
MOT_DE_PASSE_GMAIL = os.environ.get("GMAIL_PASSWORD", "")

client = anthropic.Anthropic(api_key=CLE_API)

FICHIER_PROFIL = "profil.json"
FICHIER_HISTORIQUE = "historique.json"

def charger_profil():
    if os.path.exists(FICHIER_PROFIL):
        with open(FICHIER_PROFIL, "r") as f:
            return json.load(f)
    return None

def sauvegarder_profil(profil):
    with open(FICHIER_PROFIL, "w") as f:
        json.dump(profil, f)

def charger_historique():
    if os.path.exists(FICHIER_HISTORIQUE):
        with open(FICHIER_HISTORIQUE, "r") as f:
            return json.load(f)
    return []

def sauvegarder_historique(ids):
    with open(FICHIER_HISTORIQUE, "w") as f:
        json.dump(ids, f)

profil_sauvegarde = charger_profil()

st.title("🏗️ Agent AO — Appels d'offres BTP")
st.subheader("Configurez votre profil entreprise")

email_entreprise = st.text_input(
    "Votre email",
    value=profil_sauvegarde["email"] if profil_sauvegarde else "",
    placeholder="contact@entreprise.fr"
)

metiers = st.multiselect(
    "Vos corps de métier",
    ["VRD", "Terrassement", "Aménagement urbain", "Gros œuvre", "Génie civil", "Fondations spéciales", "Réseaux"],
    default=profil_sauvegarde["metiers"] if profil_sauvegarde else ["VRD", "Terrassement"]
)

zones = st.multiselect(
    "Votre zone géographique",
    [
        "67 — Bas-Rhin", "68 — Haut-Rhin", "57 — Moselle",
        "75 — Paris", "69 — Rhône", "13 — Bouches-du-Rhône",
        "31 — Haute-Garonne", "33 — Gironde", "44 — Loire-Atlantique",
        "59 — Nord", "76 — Seine-Maritime", "38 — Isère",
        "34 — Hérault", "06 — Alpes-Maritimes"
    ],
    default=profil_sauvegarde["zones"] if profil_sauvegarde else ["67 — Bas-Rhin", "68 — Haut-Rhin"]
)

budget_min, budget_max = st.slider(
    "Budget cible (€)",
    min_value=100000,
    max_value=5000000,
    value=(
        profil_sauvegarde["budget_min"] if profil_sauvegarde else 500000,
        profil_sauvegarde["budget_max"] if profil_sauvegarde else 2000000
    ),
    step=100000,
    format="%d €"
)

delai_min = st.slider(
    "Délai minimum de réponse (jours)",
    min_value=5,
    max_value=60,
    value=profil_sauvegarde["delai_min"] if profil_sauvegarde else 15
)

if profil_sauvegarde:
    st.success("✅ Profil chargé automatiquement !")

if st.button("🚀 Lancer l'analyse et envoyer le rapport"):
    if not email_entreprise:
        st.error("Veuillez entrer votre email !")
    elif not metiers:
        st.error("Veuillez sélectionner au moins un métier !")
    elif not zones:
        st.error("Veuillez sélectionner au moins une zone !")
    else:
        sauvegarder_profil({
            "email": email_entreprise,
            "metiers": metiers,
            "zones": zones,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "delai_min": delai_min
        })

        with st.spinner("Analyse des AO en cours..."):

            profil = {
                "metiers": metiers,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "delai_min": delai_min
            }

            historique = charger_historique()

            codes = [z.split(" — ")[0] for z in zones]
            filtre_zone = " or ".join([f"code_departement='{c}'" for c in codes])

            url = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
            params = {
                "limit": 20,
                "order_by": "dateparution desc",
                "where": f"({filtre_zone}) and (objet like '%voirie%' or objet like '%VRD%' or objet like '%terrassement%' or objet like '%réseau%' or objet like '%assainissement%' or objet like '%chaussée%' or objet like '%travaux publics%' or objet like '%enrobés%' or objet like '%canalisations%' or objet like '%réhabilitation%' or objet like '%aménagement%' or objet like '%drainage%' or objet like '%trottoir%' or objet like '%bitume%')"
            }
            data = requests.get(url, params=params).json()

            aos = []
            nouveaux_ids = []
            for record in data["results"]:
                id_ao = record.get("id", "")
                if id_ao in historique:
                    continue

                date_limite = record.get("datelimitereponse", "")
                date_parution = record.get("dateparution", "")
                if date_limite:
                    delai = (datetime.fromisoformat(date_limite[:10]) - datetime.now()).days
                else:
                    delai = 21
                if date_parution:
                    parution = datetime.fromisoformat(date_parution[:10]).strftime("%d/%m/%Y")
                else:
                    parution = "Inconnue"

                aos.append({
                    "id": id_ao,
                    "titre": record.get("objet", "Sans titre")[:100],
                    "zone": record.get("code_departement", ""),
                    "acheteur": record.get("nomacheteur", ""),
                    "url": record.get("url_avis", ""),
                    "budget": 1000000,
                    "delai": max(delai, 0),
                    "parution": parution
                })
                nouveaux_ids.append(id_ao)

            if not aos:
                st.info("Aucun nouvel AO depuis la dernière analyse !")
            else:
                def scorer(ao):
                    score = 0
                    reponse = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=10,
                        messages=[{"role": "user", "content": f"Est-ce que ce chantier correspond aux métiers {', '.join(profil['metiers'])} ? Réponds uniquement OUI ou NON : {ao['titre']}"}]
                    )
                    if "OUI" in reponse.content[0].text.upper():
                        score += 40
                    if profil["budget_min"] <= ao["budget"] <= profil["budget_max"]:
                        score += 20
                    if ao["delai"] >= profil["delai_min"]:
                        score += 10
                    score += 30
                    return score

                def analyser(ao):
                    reponse = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=250,
                        messages=[{"role": "user", "content": f"En 3 lignes, analyse cet AO pour une entreprise de {', '.join(profil['metiers'])} : {ao['titre']}, délai {ao['delai']} jours. Estime le montant probable du marché en euros. Points forts et vigilance."}]
                    )
                    return reponse.content[0].text

                resultats = []
                for ao in aos:
                    score = scorer(ao)
                    resultats.append({"ao": ao, "score": score})
                resultats = sorted(resultats, key=lambda x: x["score"], reverse=True)

                sauvegarder_historique(historique + nouveaux_ids)

                prioritaires = len([r for r in resultats if r["score"] >= 70])
                a_regarder = len([r for r in resultats if 40 <= r["score"] < 70])
                non_pertinents = len([r for r in resultats if r["score"] < 40])

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🟢 Prioritaires", prioritaires)
                with col2:
                    st.metric("🟡 À regarder", a_regarder)
                with col3:
                    st.metric("🔴 Non pertinents", non_pertinents)

                st.divider()

                for r in resultats:
                    ao = r["ao"]
                    score = r["score"]

                    if score >= 70:
                        couleur = "🟢"
                        badge = f'<span style="background:#E1F5EE;color:#085041;padding:4px 12px;border-radius:20px;font-weight:bold">{score}/100</span>'
                    elif score >= 40:
                        couleur = "🟡"
                        badge = f'<span style="background:#FAEEDA;color:#633806;padding:4px 12px;border-radius:20px;font-weight:bold">{score}/100</span>'
                    else:
                        couleur = "🔴"
                        badge = f'<span style="background:#FCEBEB;color:#791F1F;padding:4px 12px;border-radius:20px;font-weight:bold">{score}/100</span>'

                    st.markdown(f"### {couleur} {ao['titre']}")
                    st.markdown(badge, unsafe_allow_html=True)
                    st.markdown(f"🏢 **{ao['acheteur']}** | 📅 Délai : **{ao['delai']} jours** | 📆 Publié le : **{ao['parution']}** | [📄 Voir l'AO]({ao['url']})")

                    if score >= 40:
                        analyse = analyser(ao)
                        st.info(analyse)
                    st.divider()