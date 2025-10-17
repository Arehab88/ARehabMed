# app.py (A-Rehab Med) — versione Streamlit Cloud con tema e login
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

st.set_page_config(page_title="A-Rehab Med", page_icon="🦶", layout="wide")

# Login
auth_ok=True
try:
    USER=st.secrets["auth"]["username"]; PASS=st.secrets["auth"]["password"]
    with st.sidebar:
        st.subheader("🔐 Login")
        u=st.text_input("Utente"); p=st.text_input("Password", type="password")
        if u!=USER or p!=PASS: auth_ok=False; st.warning("Inserisci le credenziali.")
except Exception: pass
if not auth_ok: st.stop()

# --- modello ridotto (per demo) ---
class Scheda(BaseModel):
    data: date = Field(default_factory=date.today)
    nome: str=""; cognome: str=""
    dolore: int=0
    @validator("dolore")
    def v(cls,v):
        if v<0 or v>10: raise ValueError("0-10"); return v

def crea_pdf(nome,cognome,logo_bytes:bytes|None):
    styles=getSampleStyleSheet(); buf=io.BytesIO(); doc=SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36)
    elems=[]; 
    if logo_bytes: elems+=[RLImage(io.BytesIO(logo_bytes),width=140,height=50), Spacer(1,6)]
    elems += [Paragraph("<b>A-Rehab Med</b> — Un passo verso la tua salute", styles["Title"]), Spacer(1,8)]
    elems += [Paragraph(f"Paziente: {nome} {cognome}", styles["BodyText"])]
    doc.build(elems); pdf=buf.getvalue(); buf.close(); return pdf

st.title("A‑Rehab Med — Scheda Podoposturale + Esercizi")

with st.sidebar:
    st.header("Personalizzazione")
    logo_file = st.file_uploader("Logo (PNG/JPG)", type=["png","jpg","jpeg"])

col1,col2=st.columns(2)
with col1:
    nome = st.text_input("Nome")
with col2:
    cognome = st.text_input("Cognome")
dolore = st.slider("VAS dolore",0,10,3)

if st.button("📄 Esporta PDF di prova"):
    logo_bytes = (logo_file.read() if logo_file else open('assets/logo_arehab_med.png','rb').read())
    pdf = crea_pdf(nome, cognome, logo_bytes)
    st.download_button("⬇️ Scarica PDF", data=pdf, file_name=f"arehab_med_demo_{cognome}_{nome}.pdf",
        mime="application/pdf")

st.info("Versione pronta per il deploy. Sostituisci logo in assets/ e usa le credenziali Arehab/Med.")
