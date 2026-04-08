import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL = "antoine.huber13@gmail.com"
MOT_DE_PASSE = "wmox zfvh nizg cahh"
DESTINATAIRE = "antoine.huber13@gmail.com"

def envoyer_rapport(contenu_html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Rapport AO du jour"
    msg["From"] = EMAIL
    msg["To"] = DESTINATAIRE

    partie_html = MIMEText(contenu_html, "html")
    msg.attach(partie_html)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(EMAIL, MOT_DE_PASSE)
        serveur.sendmail(EMAIL, DESTINATAIRE, msg.as_string())
        print("Email envoyé avec succès !")

with open("rapport_ao.html", "r", encoding="utf-8") as f:
    contenu = f.read()

envoyer_rapport(contenu)