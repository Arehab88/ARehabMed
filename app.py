# app.py — A-Rehab Med (scheda + esercizi, login disattivato)
import io
from dataclasses import dataclass
from datetime import date
from typing import List
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

st.set_page_config(page_title="A-Rehab Med", page_icon="🦶", layout="wide")

# Logo (usa il file del repo; se non si vede, lascia pure così)
try:
    st.image("https://raw.githubusercontent.com/arehab88/ARehabMed/main/logo_arehab_med.png", width=220)
except Exception:
    pass

st.title("A-Rehab Med — Scheda Podoposturale + Esercizi")
st.caption("Un passo verso la tua salute — versione senza login (semplice e veloce)")

# ---------------- DATI SCHEDA RAPIDA ----------------
col1, col2 = st.columns(2)
with col1:
    nome = st.text_input("Nome")
with col2:
    cognome = st.text_input("Cognome")
vas = st.slider("VAS dolore (0–10)", 0, 10, 3)
motivo = st.text_area("Motivo della visita")
note = st.text_area("Note cliniche / osservazioni")

# ---------------- LIBRERIA ESERCIZI ----------------
@dataclass
class Esercizio:
    categoria: str
    nome: str
    descrizione: str
    dosaggio: str
    progressione: str
    url: str = ""

LIB = [
    Esercizio("Equinismo", "Stretch tricipite surale alla parete",
              "Tallone a terra, ginocchio esteso; bacino in avanti.", "3×30–45''/lato, 2–3/die", "↑ tempo → ginocchio flesso"),
    Esercizio("Equinismo", "Mobilità caviglia in affondo",
              "Porta il ginocchio oltre le dita mantenendo tallone a terra.", "3×12/lato, 1–2/die", "↑ ROM / carico"),
    Esercizio("Pronazione/TP", "Short-foot (attivazione arco)",
              "Solleva attivamente l’arco senza arricciare le dita.", "3×10×5''/die", "↑ tenuta → in stazione"),
    Esercizio("Pronazione/TP", "Heel raise controllato",
              "Salita/discesa lenta, allineamento del retropiede.", "3×12, 3–4/sett", "Unilaterale → step"),
    Esercizio("Stabilità", "Equilibrio monopodalico",
              "Sguardo fisso, microflessione, tronco stabile.", "3×30''/lato, 5–6/sett", "Occhi chiusi / foam"),
    Esercizio("Anca/Core", "Clamshell con elastico",
              "Anca neutra, apertura controllata.", "3×15, 3–4/sett", "↑ tensione elastico"),
]

CATEGORIE = sorted({e.categoria for e in LIB})

st.subheader("Scheda Esercizi")
c1, c2 = st.columns(2)
with c1:
    auto = st.checkbox("Proposta automatica da VAS/Motivo", value=True)
with c2:
    filtri = st.multiselect("Filtra per categoria", CATEGORIE)

def proposta_automatica(vas_val: int, motivo_txt: str) -> List[Esercizio]:
    out = []
    motivo_l = (motivo_txt or "").lower()
    if "polpaccio" in motivo_l or "caviglia" in motivo_l or vas_val >= 6:
        out += [e for e in LIB if e.categoria == "Equinismo"]
    if "piede" in motivo_l or "pronazione" in motivo_l or "arco" in motivo_l:
        out += [e for e in LIB if e.categoria == "Pronazione/TP"]
    out += [e for e in LIB if e.categoria == "Stabilità"]  # base per tutti
    seen = set(); res = []
    for e in out:
        if e.nome not in seen:
            res.append(e); seen.add(e.nome)
    return res[:6]

if st.button("📋 Genera proposta esercizi"):
    if auto:
        st.session_state.es = proposta_automatica(vas, motivo)
    else:
        scelti = [e for e in LIB if not filtri or e.categoria in filtri]
        st.session_state.es = scelti[:6]
    st.success(f"Proposti {len(st.session_state.es)} esercizi.")

# Modifiche personalizzate per ciascun esercizio
if "es" in st.session_state:
    for i, e in enumerate(st.session_state.es, start=1):
        with st.expander(f"{i}. {e.nome} ({e.categoria})"):
            st.write(e.descrizione)
            st.text_input("Dosaggio", value=e.dosaggio, key=f"dos_{i}")
            st.text_input("Progressione", value=e.progressione, key=f"prog_{i}")
            st.text_input("Link (opz.)", value=e.url, key=f"url_{i}")

# ---------------- PDF: SCHEDA CLINICA ----------------
def pdf_scheda(nome, cognome, vas, motivo, note):
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elems = [
        Paragraph("<b>A-Rehab Med</b> — Un passo verso la tua salute", styles["Title"]),
        Spacer(1, 8),
    ]
    data = [
        ["Data", str(date.today())],
        ["Nome", nome],
        ["Cognome", cognome],
        ["VAS dolore", f"{vas}/10"],
        ["Motivo visita", motivo],
        ["Note cliniche", note],
    ]
    t = Table(data, colWidths=[120, 380])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.25,colors.grey),
                           ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
    elems += [t, Spacer(1, 8), Paragraph("© 2025 A-Rehab Med", styles["Normal"])]
    doc.build(elems)
    pdf = buf.getvalue(); buf.close(); return pdf

# ---------------- PDF: SCHEDA ESERCIZI ----------------
def pdf_esercizi(nome, cognome, rows):
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elems = [
        Paragraph("<b>Scheda Esercizi Podoposturali</b>", styles["Title"]),
        Paragraph(f"Paziente: {nome} {cognome}", styles["BodyText"]),
        Spacer(1, 8),
    ]
    tab = [["#", "Esercizio", "Dosaggio", "Progressione", "Link"]]
    for i, r in enumerate(rows, start=1):
        tab.append([str(i), r["nome"], r["dosaggio"], r["progressione"], r["url"]])
    t = Table(tab, colWidths=[20, 180, 140, 140, 100])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.25,colors.grey),
                           ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
    elems += [t, Spacer(1, 8), Paragraph("Eseguire senza dolore (>3/10 = stop).", styles["Italic"])]
    doc.build(elems)
    pdf = buf.getvalue(); buf.close(); return pdf

colA, colB = st.columns(2)
with colA:
    if st.button("📄 Esporta PDF — Scheda Clinica"):
        pdf = pdf_scheda(nome, cognome, vas, motivo, note)
        st.download_button("⬇️ Scarica Scheda Clinica (PDF)", pdf,
                           file_name=f"scheda_{cognome}_{nome}.pdf", mime="application/pdf")
with colB:
    if st.button("📄 Esporta PDF — Scheda Esercizi"):
        rows = []
        if "es" in st.session_state:
            for i, e in enumerate(st.session_state.es, start=1):
                rows.append({
                    "nome": e.nome,
                    "dosaggio": st.session_state.get(f"dos_{i}", e.dosaggio),
                    "progressione": st.session_state.get(f"prog_{i}", e.progressione),
                    "url": st.session_state.get(f"url_{i}", e.url),
                })
        pdf = pdf_esercizi(nome or "", cognome or "", rows)
        st.download_button("⬇️ Scarica Scheda Esercizi (PDF)", pdf,
                           file_name=f"esercizi_{cognome or 'paziente'}_{nome or ''}.pdf", mime="application/pdf")

st.success("✅ Pronto! Genera la proposta, personalizza i campi e scarica i PDF.")
