def crea_pdf_scheda(s, logo_bytes: bytes | None) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elems = []

    # Logo + Slogan
    if logo_bytes:
        try:
            elems += [RLImage(io.BytesIO(logo_bytes), width=140, height=50), Spacer(1, 4)]
        except Exception:
            pass

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
    t.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.25,colors.grey),
        ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke),
        ('VALIGN',(0,0),(-1,-1),'TOP')
    ]))
    elems += [t, Spacer(1, 10)]

    def section(title, body):
        elems.extend([
            Paragraph(f"<b>{title}</b>", styles["Heading3"]),
            Spacer(1, 2),
            Paragraph(body.replace("\n","<br/>"), styles["BodyText"]),
            Spacer(1, 8)
        ])

    # Sezioni
    section("Motivo della visita", f"Motivi: {', '.join(s.motivo) if s.motivo else ''}\nVAS: {s.dolore_vas}/10\nInsorgenza: {s.insorgenza or ''} | Lato: {s.lato or ''}")
    section("Anamnesi", f"Patologie: {s.patologie or ''}\nInterventi/Traumi: {s.interventi or ''}\nFarmaci: {s.farmaci or ''}\nAllergie: {s.allergie or ''}")
    section("Esame obiettivo – Statica", f"Appoggio: {s.appoggio or ''} | Retropiede: {s.retopiede or ''} | Avampiede: {s.avampiede or ''}\nArco: {s.arco_plantare or ''} | Dismetria: {s.dismetria or ''}\nValgismo alluce: {s.valgismo_alluce or ''} | Dita a martello: {s.dita_martello or ''}")
    section("Dinamica/Andatura", f"Cadenza: {s.cadenza or ''} | Lunghezza passo: {s.lunghezza_passo or ''}\nDeviazioni: {s.deviazioni or ''}")

    # 🔹 CORRETTO — sezione Baropodometria
    section("Baropodometria",
            f"Statico: {s.baro_statico or ''}\n"
            f"Dinamico: {s.baro_dinamico or ''}\n"
            f"Pressioni di picco: {s.pressioni_di_picco or ''}")

    section("Test clinici", f"Equinismo: {s.test_equinismo or ''} | Tibiale post.: {s.test_tibiale_post or ''} | Flessibilità arco: {s.test_flessibilita_arco or ''}\nROM caviglia: {s.ROM_caviglia or ''}\nNote: {s.note_test or ''}")
    section("Valutazione posturale globale", f"{s.postura or ''}\nAltri segmenti: {s.altri_segmenti or ''}")
    section("Diagnosi / Obiettivi", f"Diagnosi: {s.diagnosi or ''}\nObiettivi: {s.obiettivi or ''}")
    section("Trattamento", f"Ortesi/Plantari: {s.ortesi or ''}\nEsercizi (note generali): {s.esercizi or ''}\nCalzature: {s.calzature or ''}\nEducazione: {s.educazione or ''}\nFollow-up: {s.follow_up_settimane} settimane")

    tips = s.suggerimenti_automatici()
    if tips:
        section("Suggerimenti automatici", "• " + "<br/>• ".join(tips))

    section("Note/Disclaimer", "Documento destinato esclusivamente al paziente indicato. In caso di dolore >3/10 o comparsa di nuovi sintomi, sospendere e contattare il professionista.")

    doc.build(elems)
    pdf = buf.getvalue()
    buf.close()
    return pdf
