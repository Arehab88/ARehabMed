# app.py — A-Rehab Med (versione semplificata, login disattivato)
import io
from datetime import date
from typing import List, Optional
from dataclasses import dataclass
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors

st.set_page_config(page_title="A-Rehab Med", page_icon="🦶", layout="wide")

st.image("https://raw.githubusercontent.com/arehab88/ARehabMed/main/logo_arehab_med.png", width=200)
st.title("A-Rehab Med — Scheda Podoposturale + Esercizi")
st.caption("Un passo verso la tua salute — versione semplificata (login disattivato)")

# ---------------- DATI BASE ----------------
nome = st.text_input("Nome")
cognome = st.text_input("Cognome")
dolore_vas = st.slider("VAS dolore (0-10)", 0, 10, 3)
motivo = st.text_area("Motivo della visita")
note = st.text_area("Note cliniche / osservazioni")

# ---------------- PDF EXPORT ----------------
def crea_pdf(nome, cognome, vas, motivo, note):
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    elems = []
    elems.append(Paragraph("<b>A-Rehab Med</b> — Un passo verso la tua salute", styles["Title"]))
    elems.append(Spacer(1, 12))
    data = [
        ["Nome", nome],
        ["Cognome", cognome],
        ["VAS dolore", f"{vas}/10"],
        ["Motivo visita", motivo],
        ["Note cliniche", note],
    ]
    table = Table(data, colWidths=[120, 380])
    table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.25,colors.grey),
        ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)
    ]))
    elems.append(table)
    elems.append(Spacer(1, 12))
    elems.append(Paragraph("© 2025 A-Rehab Med", styles["Normal"]))
    doc.build(elems)
    pdf = buf.getvalue()
    buf.close()
    return pdf

if st.button("📄 Esporta PDF di prova"):
    pdf = crea_pdf(nome, cognome, dolore_vas, motivo, note)
    st.download_button(
        label="⬇️ Scarica Scheda (PDF)",
        data=pdf,
        file_name=f"scheda_{cognome}_{nome}.pdf",
        mime="application/pdf"
    )

st.success("✅ App attiva senza login. Compila e genera PDF.")
