# app.py
# -*- coding: utf-8 -*-
"""
A-Rehab Med — Scheda Podoposturale + Esercizi (versione completa)
- PDF scheda clinica + PDF scheda esercizi con LOGO e SLOGAN
- Suggerimenti automatici in base ai dati clinici
- Condivisione via mailto/WhatsApp + invio e-mail SMTP (allegato PDF)
- Login via secrets (utente: Arehab / password: Med, modificabile in Settings→Secrets)
- Tema consigliato: .streamlit/config.toml (verde/blu)
"""

import io, os, ssl, smtplib
from datetime import date
from typing import Optional, List
from dataclasses import dataclass
import streamlit as st
from pydantic import BaseModel, Field, validator
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
import qrcode
from email.message import EmailMessage

# ---------------- Accesso ----------------
st.set_page_config(page_title="A-Rehab Med", page_icon="🦶", layout="wide")
auth_ok = True
try:
    USER = st.secrets["auth"]["username"]
    PASS = st.secrets["auth"]["password"]
    with st.sidebar:
        st.subheader("🔐 Login")
        u = st.text_input("Utente", value="")
        p = st.text_input("Password", type="password", value="")
        if u != USER or p != PASS:
            auth_ok = False
            st.warning("Inserisci le credenziali corrette per continuare.")
except Exception:
    # Se non sono presenti le secrets, non blocchiamo l'accesso (utile in locale)
    pass
if not auth_ok:
    st.stop()

# ---------------- Modello dati ----------------
class SchedaPodoposturale(BaseModel):
    # Dati anagrafici
    data_compilazione: date = Field(default_factory=date.today)
    nome: str = ""
    cognome: str = ""
    data_nascita: Optional[date] = None
    sesso: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sport: Optional[str] = None
    professione: Optional[str] = None

    # Motivo visita
    motivo: List[str] = Field(default_factory=list)
    dolore_vas: Optional[int] = 0
    insorgenza: Optional[str] = None
    lato: Optional[str] = None

    # Anamnesi
    patologie: Optional[str] = None
    interventi: Optional[str] = None
    farmaci: Optional[str] = None
    allergie: Optional[str] = None
    traumi_pregressi: Optional[str] = None

    # Statica
    appoggio: Optional[str] = None
    retropiede: Optional[str] = None
    avampiede: Optional[str] = None
    arco_plantare: Optional[str] = None
    dismetria: Optional[str] = None
    valgismo_alluce: Optional[str] = None
    dita_martello: Optional[str] = None

    # Dinamica
    cadenza: Optional[str] = None
    lunghezza_passo: Optional[str] = None
    deviazioni: Optional[str] = None

    # Baropodometria
    baro_statico: Optional[str] = None
    baro_dinamico: Optional[str] = None
    pressioni_di_picco: Optional[str] = None

    # Test clinici
    test_equinismo: Optional[str] = None
    test_tibiale_post: Optional[str] = None
    test_flessibilita_arco: Optional[str] = None
    ROM_caviglia: Optional[str] = None
    note_test: Optional[str] = None

    # Posturale globale
    postura: Optional[str] = None
    altri_segmenti: Optional[str] = None

    # Conclusioni / Trattamento
    diagnosi: Optional[str] = None
    obiettivi: Optional[str] = None
    ortesi: Optional[str] = None
    esercizi: Optional[str] = None
    calzature: Optional[str] = None
    educazione: Optional[str] = None
    follow_up_settimane: Optional[int] = 6

    @validator('dolore_vas')
    def vas_range(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError("VAS deve essere 0-10")
        return v

    def suggerimenti_automatici(self) -> List[str]:
        s = []
        if self.appoggio == "pronato" or (self.arco_plantare == "piano"):
            s.append("Valutare plantari con supporto mediale e controllo pronazione.")
        if self.appoggio == "supinato" or (self.arco_plantare == "cavo"):
            s.append("Considerare plantari ammortizzanti con scarico teste metatarsali.")
        if (self.retopiede == "valgo") and (self.dolore_vas and self.dolore_vas >= 5):
            s.append("Inserire wedge mediale nel retropiede per ridurre valgismo.")
        if self.dismetria and str(self.dismetria).lower().startswith("si"):
            s.append("Valutare rialzo controlaterale (progressione 3–5 mm).")
        if self.test_equinismo == "positivo":
            s.append("Stretch tricipite surale + mobilità caviglia.")
        if self.test_tibiale_post == "positivo":
            s.append("Rinforzo tibiale posteriore e controllo pronazione.")
        if self.deviazioni and "intrarotazione" in self.deviazioni.lower():
            s.append("Controllo rotazionale e catena laterale.")
        return s

# ---------------- Libreria esercizi ----------------
@dataclass
class Esercizio:
    categoria: str
    nome: str
    descrizione: str
    dosaggio: str
    progressione: str
    url_demo: str = ""

LIB_ES = [
    Esercizio("Equinismo", "Stretch tricipite surale parete",
              "Tallone a terra, ginocchio esteso, bacino in avanti.", "3×30–45''/lato, 2–3/die", "↑ tempo, poi ginocchio flesso"),
    Esercizio("Equinismo", "Mobilità caviglia in affondo",
              "Ginocchio oltre le dita mantenendo tallone giù.", "3×12/lato, 1–2/die", "↑ ROM, poi carico"),
    Esercizio("Pronazione/TP", "Short-foot (accorciamento arco)",
              "Solleva attivamente l’arco senza arricciare dita.", "3×10×5''/die", "↑ tenuta, poi stazione"),
    Esercizio("Pronazione/TP", "Heel raise controllato",
              "Salita/discesa lenta; allineamento retropiede.", "3×12, 3–4/sett", "Unilaterale, poi step"),
    Esercizio("Stabilità", "Equilibrio monopodalico",
              "Sguardo fisso, microflessione ginocchio.", "3×30''/lato, 5–6/sett", "Occhi chiusi/foam"),
    Esercizio("Metatarsalgia", "Scarico metatarsale con asciugamano",
              "Arriccia asciugamano mantenendo neutro.", "3×12, 4–5/sett", "↑ isometria finale"),
    Esercizio("Anca/Core", "Clamshell con elastico",
              "Anca neutra, apertura controllata.", "3×15, 3–4/sett", "↑ tensione elastico"),
]
CATEGORIE = sorted(set(e.categoria for e in LIB_ES))

def proponi_esercizi(scheda: SchedaPodoposturale):
    proposti = []
    if scheda.test_equinismo == "positivo":
        proposti += [e for e in LIB_ES if e.categoria == "Equinismo"]
    if (scheda.appoggio == "pronato") or (scheda.test_tibiale_post == "positivo") or (scheda.arco_plantare == "piano"):
        proposti += [e for e in LIB_ES if e.categoria == "Pronazione/TP"]
    if scheda.deviazioni and ("instabilità" in scheda.deviazioni.lower() or "basculamento" in scheda.deviazioni.lower()):
        proposti += [e for e in LIB_ES if e.categoria == "Stabilità"]
    if scheda.altri_segmenti and ("anca" in scheda.altri_segmenti.lower()):
        proposti += [e for e in LIB_ES if e.categoria == "Anca/Core"]
    if not proposti:
        proposti += [e for e in LIB_ES if e.categoria in ("Stabilità", "Pronazione/TP")]
    livello = "Base" if (scheda.dolore_vas is None or scheda.dolore_vas >= 4) else "Avanzata"
    visti = set(); out = []
    for e in proposti:
        if e.nome not in visti:
            out.append(e); visti.add(e.nome)
    return out[:6], livello

# ---------------- PDF utils ----------------
def _qr_image_from_text(text: str):
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(text); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO(); img.save(bio, format="PNG"); bio.seek(0); return bio

def crea_pdf_scheda(s, logo_bytes: bytes | None) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elems = []
    # Logo + Slogan
    if logo_bytes:
        try: elems += [RLImage(io.BytesIO(logo_bytes), width=140, height=50), Spacer(1, 4)]
        except Exception: pass
    elems += [Paragraph("<b>A-Rehab Med</b> — Un passo verso la tua salute", styles["Title"]), Spacer(1, 6)]
    # Tabella anagrafica
    dati = [
        ["Data", str(s.data_compilazione)],
        ["Paziente", f"{s.nome} {s.cognome}"],
        ["Nascita", str(s.data_nascita or "")],
        ["Sesso", s.sesso or ""],
        ["Telefono", s.telefono or ""],
        ["Email", s.email or ""],
        ["Sport", s.sport or ""],
        ["Professione", s.professione or ""],
    ]
    t = Table(dati, hAlign='LEFT', colWidths=[100, 380])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.25,colors.grey),
                           ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke),
                           ('VALIGN',(0,0),(-1,-1),'TOP')]))
    elems += [t, Spacer(1, 10)]

    def section(title, body):
        elems.extend([Paragraph(f"<b>{title}</b>", styles["Heading3"]), Spacer(1, 2),
                      Paragraph(body.replace("\n","<br/>"), styles["BodyText"]), Spacer(1, 8)])

    section("Motivo della visita", f"Motivi: {', '.join(s.motivo) if s.motivo else ''}\nVAS: {s.dolore_vas}/10\nInsorgenza: {s.insorgenza or ''} | Lato: {s.lato or ''}")
    section("Anamnesi", f"Patologie: {s.patologie or ''}\nInterventi/Traumi: {s.interventi or ''}\nFarmaci: {s.farmaci or ''}\nAllergie: {s.allergie or ''}")
    section("Esame obiettivo – Statica", f"Appoggio: {s.appoggio or ''} | Retropiede: {s.retopiede or ''} | Avampiede: {s.avampiede or ''}\nArco: {s.arco_plantare or ''} | Dismetria: {s.dismetria or ''}\nValgismo alluce: {s.valgismo_alluce or ''} | Dita a martello: {s.dita_martello or ''}")
    section("Dinamica/Andatura", f"Cadenza: {s.cadenza or ''} | Lunghezza passo: {s.lunghezza_passo or ''}\nDeviazioni: {s.deviazioni or ''}")
    section("Baropodometria", f"Statico: {s.baro_statico or ''}\nDinamico: {s.baro_dinamico or ''}\nPressioni di picco: {s.pessioni_di_picco if hasattr(s,'pessioni_di_picco') else s.pression i_di_picco if False else s.pressioni_di_picco or ''}")
    section("Test clinici", f"Equinismo: {s.test_equinismo or ''} | Tibiale post.: {s.test_tibiale_post or ''} | Flessibilità arco: {s.test_flessibilita_arco or ''}\nROM caviglia: {s.ROM_caviglia or ''}\nNote: {s.note_test or ''}")
    section("Valutazione posturale globale", f"{s.postura or ''}\nAltri segmenti: {s.altri_segmenti or ''}")
    section("Diagnosi / Obiettivi", f"Diagnosi: {s.diagnosi or ''}\nObiettivi: {s.obiettivi or ''}")
    section("Trattamento", f"Ortesi/Plantari: {s.ortesi or ''}\nEsercizi (note generali): {s.esercizi or ''}\nCalzature: {s.calzature or ''}\nEducazione: {s.educazione or ''}\nFollow-up: {s.follow_up_settimane} settimane")

    tips = s.suggerimenti_automatici()
    if tips:
        section("Suggerimenti automatici", "• " + "<br/>• ".join(tips))

    section("Note/Disclaimer", "Documento destinato esclusivamente al paziente indicato. In caso di dolore >3/10 o comparsa di nuovi sintomi, sospendere e contattare il professionista.")
    doc.build(elems); pdf = buf.getvalue(); buf.close(); return pdf

def crea_pdf_esercizi(nome: str, cognome: str, esercizi_rows: List[dict],
                      note_generali: str = "", link_condivisione: str = "",
                      logo_bytes: bytes | None = None) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elems = []
    if logo_bytes:
        try: elems += [RLImage(io.BytesIO(logo_bytes), width=140, height=50), Spacer(1, 4)]
        except Exception: pass
    elems += [Paragraph("<b>Scheda Esercizi Podoposturali</b>", styles["Title"]),
              Paragraph(f"Paziente: {nome} {cognome}", styles["BodyText"]), Spacer(1, 8)]
    rows = [["#", "Esercizio", "Dosaggio", "Progressione", "Link"]]
    for i, r in enumerate(esercizi_rows, start=1):
        rows.append([str(i), r.get('nome',''), r.get('dosaggio',''), r.get('progressione',''), r.get('url','')])
    t = Table(rows, colWidths=[20, 180, 140, 140, 90])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.25,colors.grey),
                           ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke),
                           ('VALIGN',(0,0),(-1,-1),'TOP')]))
    elems += [t, Spacer(1, 8)]
    if note_generali:
        elems += [Paragraph("<b>Note:</b>", styles["Heading3"]), Paragraph(note_generali.replace("\n","<br/>"), styles["BodyText"]), Spacer(1,6)]
    if link_condivisione:
        try:
            qr_bio = _qr_image_from_text(link_condivisione)
            elems += [Paragraph("<b>Apri su smartphone:</b>", styles["Heading3"]),
                      RLImage(qr_bio, width=100, height=100)]
        except Exception: pass
    elems += [Spacer(1,6), Paragraph("Eseguire gli esercizi senza dolore (>3/10 = stop).", styles["Italic"])]
    doc.build(elems); pdf = buf.getvalue(); buf.close(); return pdf

def invia_email_pdf(mittente: str, password_app: str, destinatario: str, oggetto: str, corpo: str,
                     pdf_bytes: bytes, nome_file: str = "scheda.pdf",
                     smtp_host: str = "smtp.gmail.com", smtp_port: int = 465):
    msg = EmailMessage()
    msg["From"] = mittente; msg["To"] = destinatario; msg["Subject"] = oggetto
    msg.set_content(corpo)
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=nome_file)
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context()) as server:
        server.login(mittente, password_app)
        server.send_message(msg)

# ---------------- UI ----------------
st.title("A-Rehab Med — Scheda Podoposturale + Esercizi")

with st.sidebar:
    st.header("Personalizzazione")
    logo_file = st.file_uploader("Logo (PNG/JPG)", type=["png","jpg","jpeg"])
    st.header("Esporta & Condividi")
    st.write("Compila i dati, genera i PDF, condividi.")

# Anagrafica
col1, col2, col3 = st.columns(3)
with col1:
    nome = st.text_input("Nome*")
    cognome = st.text_input("Cognome*")
    data_nascita = st.date_input("Data di nascita", value=None)
    sesso = st.selectbox("Sesso", ["", "M", "F", "Altro"]) or None
    telefono = st.text_input("Telefono")
    email = st.text_input("Email")
with col2:
    sport = st.text_input("Sport")
    professione = st.text_input("Professione")
    motivo = st.multiselect("Motivo della visita", ["Dolore plantare", "Caviglia", "Ginocchio", "Anca", "Schiena", "Instabilità", "Altro"])
    dolore_vas = st.slider("Dolore VAS (0–10)", 0, 10, 0)
    insorgenza = st.selectbox("Insorgenza", ["", "Acuta", "Cronica", "Recidiva"]) or None
    lato = st.selectbox("Lato", ["", "Destro", "Sinistro", "Bilaterale"]) or None
with col3:
    patologie = st.text_area("Patologie note")
    interventi = st.text_area("Interventi/Traumi pregressi")
    farmaci = st.text_input("Farmaci")
    allergie = st.text_input("Allergie")

# Statica
st.subheader("Esame obiettivo – Statica")
s1, s2, s3, s4 = st.columns(4)
with s1:
    appoggio = st.selectbox("Appoggio", ["", "neutro", "pronato", "supinato"]) or None
    retropiede = st.selectbox("Retropiede", ["", "valgo", "varo", "neutro"]) or None
with s2:
    avampiede = st.selectbox("Avampiede", ["", "addotto", "abdotto", "neutro"]) or None
    arco_plantare = st.selectbox("Arco plantare", ["", "cavo", "piano", "normale"]) or None
with s3:
    dismetria = st.text_input("Dismetria", placeholder="no / sì (mm)")
    valgismo_alluce = st.selectbox("Valgismo alluce", ["", "no", "lieve", "moderato", "severo"]) or None
with s4:
    dita_martello = st.selectbox("Dita a martello", ["", "no", "sì"]) or None

# Dinamica
st.subheader("Dinamica / Andatura")
d1, d2, d3 = st.columns(3)
with d1: cadenza = st.text_input("Cadenza (se nota)")
with d2: lunghezza_passo = st.text_input("Lunghezza passo (se nota)")
with d3: deviazioni = st.text_area("Deviazioni osservate")

# Baropodometria
st.subheader("Baropodometria (opzionale)")
b1, b2, b3 = st.columns(3)
with b1: baro_statico = st.text_area("Statico (carichi %)")
with b2: baro_dinamico = st.text_area("Dinamico (COP, picchi)")
with b3: pressioni_di_picco = st.text_area("Pressioni di picco / zone di sovraccarico")

# Test clinici
st.subheader("Test clinici")
t1, t2, t3 = st.columns(3)
with t1: test_equinismo = st.selectbox("Test equinismo", ["", "positivo", "negativo"]) or None
with t2: test_tibiale_post = st.selectbox("Tibiale posteriore", ["", "positivo", "negativo"]) or None
with t3: test_flessibilita_arco = st.selectbox("Flessibilità arco", ["", "buona", "ridotta", "rigido"]) or None
ROM_caviglia = st.text_input("ROM caviglia (°/qualitativo)")
note_test = st.text_area("Note test")

# Valutazione globale
st.subheader("Valutazione posturale globale")
postura = st.text_area("Postura (spalle, bacino, Barré, linee di carico)")
altri_segmenti = st.text_area("Altri segmenti (ginocchia, anca, rachide)")

# Conclusioni e piano
st.subheader("Conclusioni e Piano")
diagnosi = st.text_area("Diagnosi / Ipotesi clinica")
obiettivi = st.text_area("Obiettivi di trattamento")
ortesi = st.text_area("Ortesi/Plantari (materiali, rigidità, wedge, rialzi)")
esercizi_note = st.text_area("Esercizi – note generali")
calzature = st.text_area("Consigli calzaturieri")
educazione = st.text_area("Educazione/Compliance")
follow_up_settimane = st.number_input("Follow-up (settimane)", min_value=2, max_value=24, value=6, step=1)

# Oggetto scheda
scheda = SchedaPodoposturale(
    nome=nome, cognome=cognome, data_nascita=data_nascita or None, sesso=sesso or None,
    telefono=telefono or None, email=email or None, sport=sport or None, professione=professione or None,
    motivo=motivo, dolore_vas=dolore_vas, insorgenza=insorgenza or None, lato=lato or None,
    patologie=patologie or None, interventi=interventi or None, farmaci=farmaci or None, allergie=allergie or None,
    traumi_pregressi=interventi or None, appoggio=appoggio or None, retropiede=retropiede or None, avampiede=avampiede or None,
    arco_plantare=arco_plantare or None, dismetria=dismetria or None, valgismo_alluce=valgismo_alluce or None, dita_martello=dita_martello or None,
    cadenza=cadenza or None, lunghezza_passo=lunghezza_passo or None, deviazioni=deviazioni or None,
    baro_statico=baro_statico or None, baro_dinamico=baro_dinamico or None, pressioni_di_picco=pressioni_di_picco or None,
    test_equinismo=test_equinismo or None, test_tibiale_post=test_tibiale_post or None, test_flessibilita_arco=test_flessibilita_arco or None,
    ROM_caviglia=ROM_caviglia or None, note_test=note_test or None, postura=postura or None, altri_segmenti=altri_segmenti or None,
    diagnosi=diagnosi or None, obiettivi=obiettivi or None, ortesi=ortesi or None, esercizi=esercizi_note or None,
    calzature=calzature or None, educazione=educazione or None, follow_up_settimane=int(follow_up_settimane),
)

# Suggerimenti automatici
if st.button("💡 Suggerimenti automatici"):
    tips = scheda.suggerimenti_automatici()
    st.success("Suggerimenti:\n- " + "\n- ".join(tips) if tips else "Nessun suggerimento specifico.")

# Scheda esercizi
st.subheader("Scheda Esercizi – Riabilitazione Podoposturale")
cat_sel = st.multiselect("Filtra per categoria", CATEGORIE)
proponi = st.checkbox("Proponi automaticamente dagli esiti clinici", value=True)

if st.button("📋 Genera proposta esercizi"):
    elenco, livello = (proponi_esercizi(scheda) if proponi else ([e for e in LIB_ES if (not cat_sel or e.categoria in cat_sel)], "Personalizzato"))
    st.session_state["esercizi_selezionati"] = elenco
    st.success(f"{len(elenco)} esercizi proposti – Livello: {livello}")

if "esercizi_selezionati" in st.session_state:
    for i, e in enumerate(st.session_state["esercizi_selezionati"], start=1):
        with st.expander(f"{i}. {e.nome} ({e.categoria})"):
            st.write(e.descrizione)
            st.text_input("Dosaggio", value=e.dosaggio, key=f"dos_{i}")
            st.text_input("Progressione", value=e.progressione, key=f"prog_{i}")
            st.text_input("Link dimostrativo (opz.)", value=e.url_demo, key=f"url_{i}")

# Export e Condivisione
colA, colB = st.columns(2)
with colA:
    if st.button("📄 Esporta PDF – Scheda Clinica"):
        logo_bytes = None
        try:
            logo_bytes = (logo_file.read() if logo_file else open('assets/logo_arehab_med.png','rb').read())
        except Exception:
            pass
        pdf_bytes = crea_pdf_scheda(scheda, logo_bytes)
        st.download_button("⬇️ Scarica scheda clinica (PDF)", data=pdf_bytes,
                           file_name=f"scheda_podoposturale_{scheda.cognome}_{scheda.nome}.pdf", mime="application/pdf")
with colB:
    if st.button("📄 Esporta PDF – Scheda Esercizi"):
        rows = []
        if "esercizi_selezionati" in st.session_state:
            for i, e in enumerate(st.session_state["esercizi_selezionati"], start=1):
                rows.append({
                    'nome': e.nome,
                    'dosaggio': st.session_state.get(f"dos_{i}", e.dosaggio),
                    'progressione': st.session_state.get(f"prog_{i}", e.progressione),
                    'url': st.session_state.get(f"url_{i}", e.url_demo),
                })
        logo_bytes = None
        try:
            logo_bytes = (logo_file.read() if logo_file else open('assets/logo_arehab_med.png','rb').read())
        except Exception:
            pass
        pdf_bytes_es = crea_pdf_esercizi(nome or "", cognome or "", rows, note_generali=esercizi_note or "", logo_bytes=logo_bytes)
        st.download_button("⬇️ Scarica scheda esercizi (PDF)", data=pdf_bytes_es,
                           file_name=f"esercizi_{(cognome or 'paziente')}_{(nome or '')}.pdf", mime="application/pdf")
        testo = f"Scheda esercizi per {nome} {cognome}. Follow-up tra {follow_up_settimane} settimane."
        st.markdown(f"[✉️ Invia via e-mail](mailto:{email or ''}?subject=Scheda%20esercizi&body={testo.replace(' ', '%20')})  |  [💬 Invia su WhatsApp](https://wa.me/?text={testo.replace(' ', '%20')})")

st.markdown("---")
with st.expander("Invio e-mail diretto con allegato (SMTP – opzionale)"):
    st.write("Per Gmail usa una **password per app** (Google → Sicurezza → Password per le app).")
    mitt = st.text_input("Account mittente (es. yourname@gmail.com)")
    pwd = st.text_input("Password per app", type="password")
    dest = st.text_input("Destinatario", value=email or "")
    ogg = st.text_input("Oggetto", value="Scheda esercizi podoposturali")
    corpo = st.text_area("Messaggio", value=f"Ciao {nome}, in allegato la tua scheda esercizi. A presto.")
    allegato_tipo = st.selectbox("Quale PDF allegare?", ["Esercizi", "Clinica"])
    if st.button("✉️ Invia e-mail ora"):
        try:
            if allegato_tipo == "Esercizi" and "esercizi_selezionati" in st.session_state:
                rows = []
                for i, e in enumerate(st.session_state["esercizi_selezionati"], start=1):
                    rows.append({
                        'nome': e.nome,
                        'dosaggio': st.session_state.get(f"dos_{i}", e.dosaggio),
                        'progressione': st.session_state.get(f"prog_{i}", e.progressione),
                        'url': st.session_state.get(f"url_{i}", e.url_demo),
                    })
                pdf_bytes = crea_pdf_esercizi(nome or "", cognome or "", rows, note_generali=esercizi_note or "")
                nome_file = f"esercizi_{(cognome or 'paziente')}_{(nome or '')}.pdf"
            else:
                pdf_bytes = crea_pdf_scheda(scheda, (logo_file.read() if logo_file else None))
                nome_file = f"scheda_podoposturale_{scheda.cognome}_{scheda.nome}.pdf"
            invia_email_pdf(mitt, pwd, dest, ogg, corpo, pdf_bytes, nome_file=nome_file)
            st.success("E-mail inviata con allegato!")
        except Exception as e:
            st.error(f"Errore invio e-mail: {e}")

st.caption("© 2025 – A-Rehab Med. Questo software non sostituisce il giudizio clinico.")
