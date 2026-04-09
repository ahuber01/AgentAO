import streamlit as st
import anthropic
import smtplib
import requests
import json
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configuration — fonctionne en local ET sur Streamlit Cloud
CLE_API = st.secrets.get("ANTHROPIC_API_KEY", "")
EMAIL = st.secrets.get("EMAIL", "antoine.huber13@gmail.com")
MOT_DE_PASSE_GMAIL = st.secrets.get("GMAIL_PASSWORD", "") 

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

# Sources AO
def recuperer_boamp(codes_dep, mots_cles):
    from datetime import datetime, timedelta
    date_limite = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    filtre_zone = " or ".join([f"code_departement='{c}'" for c in codes_dep])
    filtre_mots = " or ".join([f"objet like '%{m}%'" for m in mots_cles])
    url = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
    params = {
        "limit": 20,
        "order_by": "dateparution desc",
        "where": f"({filtre_zone}) and ({filtre_mots}) and dateparution >= '{date_limite}'"
    }
    try:
        data = requests.get(url, params=params, timeout=10).json()
        aos = []
        for record in data.get("results", []):
            date_limite_rep = record.get("datelimitereponse", "")
            date_parution = record.get("dateparution", "")
            delai = (datetime.fromisoformat(date_limite_rep[:10]) - datetime.now()).days if date_limite_rep else 21
            parution = datetime.fromisoformat(date_parution[:10]).strftime("%d/%m/%Y") if date_parution else "Inconnue"
            aos.append({
                "id": record.get("id", ""),
                "titre": record.get("objet", "Sans titre")[:120],
                "acheteur": record.get("nomacheteur", ""),
                "url": record.get("url_avis", ""),
                "source": "BOAMP",
                "delai": max(delai, 0),
                "parution": parution
            })
        return aos
    except:
        return []

def recuperer_ao_attribues(codes_dep, mots_cles):
    from datetime import datetime, timedelta
    date_limite = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    filtre_zone = " or ".join([f"code_departement='{c}'" for c in codes_dep])
    filtre_mots = " or ".join([f"objet like '%{m}%'" for m in mots_cles])
    url = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
    params = {
        "limit": 10,
        "order_by": "dateparution desc",
        "where": f"({filtre_zone}) and ({filtre_mots}) and dateparution >= '{date_limite}' and type_avis like '%10%'"
    }
    try:
        data = requests.get(url, params=params, timeout=10).json()
        attribues = []
        for record in data.get("results", []):
            donnees = record.get("donnees", {})
            montant = "Non communiqué"
            titulaire = "Non communiqué"
            try:
                if isinstance(donnees, dict):
                    titulaires = donnees.get("ATTRIBUTION", {}).get("titulaires", [])
                    if titulaires and len(titulaires) > 0:
                        titulaire = titulaires[0].get("denomination", "Non communiqué")
                    valeur = donnees.get("ATTRIBUTION", {}).get("valeur", {})
                    if valeur:
                        montant = f"{valeur.get('montant', 'Non communiqué')} €"
            except:
                pass
            attribues.append({
                "titre": record.get("objet", "Sans titre")[:120],
                "acheteur": record.get("nomacheteur", ""),
                "titulaire": titulaire,
                "montant": montant,
                "url": record.get("url_avis", ""),
                "parution": record.get("dateparution", "")[:10]
            })
        return attribues
    except:
        return []

def recuperer_aws_achat(mots_cles):
    try:
        mot = mots_cles[0] if mots_cles else "travaux"
        url = f"https://www.aws-achat.com/flux/rss?q={mot}&type=AO"
        import xml.etree.ElementTree as ET
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        aos = []
        for item in root.findall(".//item")[:10]:
            titre = item.find("title")
            lien = item.find("link")
            date = item.find("pubDate")
            if titre is not None:
                aos.append({
                    "id": lien.text if lien is not None else titre.text,
                    "titre": titre.text[:120] if titre.text else "Sans titre",
                    "acheteur": "AWS Achat",
                    "url": lien.text if lien is not None else "",
                    "source": "AWS Achat",
                    "delai": 21,
                    "parution": date.text[:10] if date is not None else "Inconnue"
                })
        return aos
    except:
        return []

def recuperer_ted(mots_cles):
    try:
        mot = "+".join(mots_cles[:2]) if mots_cles else "travaux"
        url = f"https://ted.europa.eu/api/v3.0/notices/search?q={mot}&scope=3&fields=title,url,publicationDate,buyer&pageSize=10&page=1"
        data = requests.get(url, timeout=10).json()
        aos = []
        for notice in data.get("notices", []):
            aos.append({
                "id": notice.get("id", ""),
                "titre": notice.get("title", {}).get("fr", notice.get("title", {}).get("en", "Sans titre"))[:120],
                "acheteur": notice.get("buyer", {}).get("name", "Europe"),
                "url": f"https://ted.europa.eu/udl?uri=TED:NOTICE:{notice.get('id', '')}:TEXT:FR:HTML",
                "source": "TED Europe",
                "delai": 30,
                "parution": notice.get("publicationDate", "")[:10]
            })
        return aos
    except:
        return []

profil_sauvegarde = charger_profil()

# Interface
if os.path.exists("LOGO_AHead_BTP.png"):
    st.image("LOGO_AHead_BTP.png", width=250)
else:
    st.title("🏗️ AHead BTP")
st.subheader("Votre radar d'appels d'offres — Détectez. Analysez. Remportez.")
st.divider()

email_entreprise = st.text_input(
    "Votre email",
    value=profil_sauvegarde.get("email", "") if profil_sauvegarde else "",
    placeholder="contact@entreprise.fr"
)

st.markdown("**Vos corps de métier**")
col1, col2 = st.columns(2)

metiers_tp = [
    "Voirie / VRD", "Terrassement", "Assainissement",
    "Réseaux eau potable", "Aménagement urbain", "Génie civil",
    "Fondations spéciales", "Démolition", "Enrobés / chaussées",
    "Espaces verts", "Drainage / bassins"
]
metiers_bat = [
    "Gros œuvre / maçonnerie", "Électricité / courants forts",
    "Plomberie / sanitaires", "Chauffage / CVC",
    "Menuiserie / charpente", "Peinture / revêtements",
    "Carrelage / sols", "Couverture / toiture",
    "Isolation / étanchéité", "Serrurerie / métallerie"
]

metiers_selectionnes = profil_sauvegarde.get("metiers", []) if profil_sauvegarde else []

with col1:
    st.markdown("*Travaux publics & génie civil*")
    metiers_tp_choisis = [m for m in metiers_tp if st.checkbox(m, value=m in metiers_selectionnes, key=f"tp_{m}")]

with col2:
    st.markdown("*Bâtiment & second œuvre*")
    metiers_bat_choisis = [m for m in metiers_bat if st.checkbox(m, value=m in metiers_selectionnes, key=f"bat_{m}")]

metiers = metiers_tp_choisis + metiers_bat_choisis

mots_cles_libres = st.text_input(
    "Mots-clés techniques supplémentaires (séparés par des virgules)",
    value=profil_sauvegarde.get("mots_cles_libres", "") if profil_sauvegarde else "",
    placeholder="micro-pieux, paroi berlinoise, béton désactivé..."
)

zones = st.multiselect(
    "Zone géographique",
    [
        "67 — Bas-Rhin", "68 — Haut-Rhin", "57 — Moselle",
        "75 — Paris", "69 — Rhône", "13 — Bouches-du-Rhône",
        "31 — Haute-Garonne", "33 — Gironde", "44 — Loire-Atlantique",
        "59 — Nord", "76 — Seine-Maritime", "38 — Isère",
        "34 — Hérault", "06 — Alpes-Maritimes", "54 — Meurthe-et-Moselle",
        "67 — Bas-Rhin", "25 — Doubs", "90 — Territoire de Belfort"
    ],
    default=profil_sauvegarde.get("zones", ["67 — Bas-Rhin", "68 — Haut-Rhin"]) if profil_sauvegarde else ["67 — Bas-Rhin", "68 — Haut-Rhin"]
)

type_moa = st.multiselect(
    "Type de maître d'ouvrage",
    ["Commune / Mairie", "Département", "Région", "État / Ministère", "Bailleur social", "Établissement public", "Tous types"],
    default=profil_sauvegarde.get("type_moa", ["Tous types"]) if profil_sauvegarde else ["Tous types"]
)

variantes = st.radio(
    "Variantes acceptées dans l'AO ?",
    ["Indifférent", "Oui — je veux des AO qui autorisent les variantes", "Non — je veux des AO sans variantes"],
    index=profil_sauvegarde.get("variantes_index", 0) if profil_sauvegarde else 0
)

duree_min, duree_max = st.slider(
    "Durée du chantier (mois)",
    min_value=1,
    max_value=24,
    value=(
        profil_sauvegarde.get("duree_min", 1) if profil_sauvegarde else 1,
        profil_sauvegarde.get("duree_max", 12) if profil_sauvegarde else 12
    )
)

budget_min, budget_max = st.slider(
    "Budget cible (€)",
    min_value=50000,
    max_value=10000000,
    value=(
        profil_sauvegarde.get("budget_min", 500000) if profil_sauvegarde else 500000,
        profil_sauvegarde.get("budget_max", 2000000) if profil_sauvegarde else 2000000
    ),
    step=50000,
    format="%d €"
)

delai_min = st.slider(
    "Délai minimum de réponse (jours)",
    min_value=5,
    max_value=60,
    value=profil_sauvegarde.get("delai_min", 15) if profil_sauvegarde else 15
)

sources = st.multiselect(
    "Sources AO à surveiller",
    ["BOAMP", "AWS Achat", "TED Europe"],
    default=profil_sauvegarde.get("sources", ["BOAMP"]) if profil_sauvegarde else ["BOAMP"]
)

if profil_sauvegarde:
    st.success("✅ Profil chargé automatiquement !")

if st.button("🚀 Lancer l'analyse"):
    if not email_entreprise:
        st.error("Veuillez entrer votre email !")
    elif not metiers and not mots_cles_libres:
        st.error("Veuillez sélectionner au moins un métier ou entrer des mots-clés !")
    elif not zones:
        st.error("Veuillez sélectionner au moins une zone !")
    else:
        sauvegarder_profil({
            "email": email_entreprise,
            "metiers": metiers,
            "mots_cles_libres": mots_cles_libres,
            "zones": zones,
            "type_moa": type_moa,
            "variantes_index": ["Indifférent", "Oui — je veux des AO qui autorisent les variantes", "Non — je veux des AO sans variantes"].index(variantes),
            "duree_min": duree_min,
            "duree_max": duree_max,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "delai_min": delai_min,
            "sources": sources
        })

        with st.spinner("Analyse des AO en cours..."):

            profil = {
                "metiers": metiers,
                "mots_cles_libres": [m.strip() for m in mots_cles_libres.split(",") if m.strip()],
                "budget_min": budget_min,
                "budget_max": budget_max,
                "delai_min": delai_min,
                "duree_min": duree_min,
                "duree_max": duree_max,
                "variantes": variantes,
                "type_moa": type_moa
            }

            codes = [z.split(" — ")[0] for z in zones]
            mots_recherche = metiers + profil["mots_cles_libres"]
            if not mots_recherche:
                mots_recherche = ["travaux"]

            historique = charger_historique()
            aos = []

            if "BOAMP" in sources:
                aos += recuperer_boamp(codes, mots_recherche)
            if "AWS Achat" in sources:
                aos += recuperer_aws_achat(mots_recherche)
            if "TED Europe" in sources:
                aos += recuperer_ted(mots_recherche)

            aos = [ao for ao in aos if ao["id"] not in historique]
            nouveaux_ids = [ao["id"] for ao in aos]

            if not aos:
                st.info("Aucun nouvel AO depuis la dernière analyse !")
            else:
                def scorer(ao):
                    score = 0
                    tous_mots = profil["metiers"] + profil["mots_cles_libres"]
                    reponse = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=10,
                        messages=[{"role": "user", "content": f"Est-ce que ce chantier correspond aux metiers ou techniques suivants : {', '.join(tous_mots)} ? Reponds uniquement OUI ou NON : {ao['titre']}".encode('utf-8', errors='ignore').decode('utf-8')}]
                    )
                    if "OUI" in reponse.content[0].text.upper():
                        score += 40
                    if profil["budget_min"] <= 1000000 <= profil["budget_max"]:
                        score += 20
                    if ao["delai"] >= profil["delai_min"]:
                        score += 10
                    score += 30
                    return score

                def analyser(ao):
                    tous_mots = profil["metiers"] + profil["mots_cles_libres"]
                    contexte_variantes = ""
                    if profil["variantes"] != "Indifférent":
                        contexte_variantes = f" L'entreprise {'cherche des AO qui autorisent les variantes' if 'Oui' in profil['variantes'] else 'préfère des AO sans variantes'}."
                    reponse = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=250,
                        messages=[{"role": "user", "content": f"En 3 lignes, analyse cet AO pour une entreprise spécialisée en {', '.join(tous_mots)} : {ao['titre']}, délai {ao['delai']} jours.{contexte_variantes} Estime le montant probable. Points forts et vigilance."}]
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
                    st.markdown(f"🏢 **{ao['acheteur']}** | 📅 Délai : **{ao['delai']} jours** | 📆 Publié le : **{ao['parution']}** | 🔗 Source : **{ao['source']}** | [📄 Voir l'AO]({ao['url']})")

                    if score >= 40:
                        analyse = analyser(ao)
                        st.info(analyse)
                    st.divider()
                    # Section AO attribués
                    st.divider()
                    st.subheader("📋 Marchés récemment attribués dans votre zone")
                    st.caption("Suivez la concurrence — qui remporte quoi près de chez vous")

                    attribues = recuperer_ao_attribues(codes, mots_recherche)

                    if not attribues:
                        st.info("Aucun marché attribué récemment dans votre zone.")
                    else:
                        for a in attribues:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**{a['titre']}**")
                                st.caption(f"🏢 Acheteur : {a['acheteur']} | 🏆 Attribué à : **{a['titulaire']}** | 💰 Montant : **{a['montant']}**")
                                st.markdown(f"[Voir le marché]({a['url']})")
                            with col2:
                                st.caption(f"📆 {a['parution']}")
                            st.divider()