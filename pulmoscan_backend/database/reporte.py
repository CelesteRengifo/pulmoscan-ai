import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Flowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Paleta ────────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#0A1F5C")
NAVY2   = colors.HexColor("#16337F")
ROJO    = colors.HexColor("#C0392B")
ROJO_BG = colors.HexColor("#FDEDEB")
VERDE   = colors.HexColor("#1A7A4A")
VERDE_BG= colors.HexColor("#E9F7EF")
GRIS    = colors.HexColor("#6B7A99")
GRIS_CL = colors.HexColor("#94A0BC")
OSCURO  = colors.HexColor("#1A2540")
BORDE   = colors.HexColor("#E1E7F2")
FONDO   = colors.HexColor("#F8FAFD")
CHIP_BG = colors.HexColor("#EEF3FF")


# ── Componentes gráficos personalizados ───────────────────────────────────
class BandaEncabezado(Flowable):
    """Franja navy superior con logo de pulmón, marca y código de reporte."""
    def __init__(self, width, estudio_id):
        super().__init__()
        self.width = width
        self.height = 62
        self.estudio_id = estudio_id

    def draw(self):
        c = self.canv
        # Fondo navy
        c.setFillColor(NAVY)
        c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)

        # Logo pulmón (simplificado)
        c.setStrokeColor(colors.white)
        c.setLineWidth(2)
        cx, cy = 26, self.height / 2
        c.line(cx, cy + 12, cx, cy - 6)
        c.bezier(cx, cy - 6, cx - 12, cy - 6, cx - 14, cy + 2, cx - 10, cy - 14)
        c.bezier(cx, cy - 6, cx + 12, cy - 6, cx + 14, cy + 2, cx + 10, cy - 14)

        # Marca
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 17)
        c.drawString(52, self.height / 2 + 2, "PulmoScan AI")
        c.setFillColor(colors.HexColor("#B9C6E8"))
        c.setFont("Helvetica", 8)
        c.drawString(52, self.height / 2 - 12, "Detección automatizada de tuberculosis pulmonar")

        # Código de reporte (derecha)
        c.setFillColor(colors.HexColor("#8FA3D8"))
        c.setFont("Helvetica", 7.5)
        c.drawRightString(self.width - 16, self.height / 2 + 8, "REPORTE N°")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawRightString(self.width - 16, self.height / 2 - 8,
                          f"#{self.estudio_id:05d}")


class BarraProbabilidad(Flowable):
    """Barra de progreso visual para la probabilidad de TB."""
    def __init__(self, width, pct, es_tb):
        super().__init__()
        self.width = width
        self.height = 22
        self.pct = pct
        self.color = ROJO if es_tb else VERDE

    def draw(self):
        c = self.canv
        r = 6
        # Track
        c.setFillColor(colors.HexColor("#EEF1F7"))
        c.roundRect(0, 4, self.width, 10, r, fill=1, stroke=0)
        # Fill
        w = max(self.width * self.pct / 100, 12)
        c.setFillColor(self.color)
        c.roundRect(0, 4, w, 10, r, fill=1, stroke=0)


class SeccionTitulo(Flowable):
    """Título de sección estilo chip con barra lateral."""
    def __init__(self, width, texto):
        super().__init__()
        self.width = width
        self.height = 26
        self.texto = texto

    def draw(self):
        c = self.canv
        # Barra lateral
        c.setFillColor(NAVY)
        c.roundRect(0, 3, 3.5, 18, 1.5, fill=1, stroke=0)
        # Texto
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(12, 8, self.texto.upper())


def _fila_datos(datos, col_widths):
    t = Table(datos, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",      (0, 0), (0, -1),  "Helvetica-Bold"),
        ("FONTNAME",      (2, 0), (2, -1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (0, -1),  GRIS),
        ("TEXTCOLOR",     (2, 0), (2, -1),  GRIS),
        ("TEXTCOLOR",     (1, 0), (1, -1),  OSCURO),
        ("TEXTCOLOR",     (3, 0), (3, -1),  OSCURO),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [FONDO, colors.white]),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _capitalizar_confianza(valor):
    """Convierte 'NivelConfianzaEnum.alta' o 'alta' → 'Alta'."""
    if not valor:
        return "—"
    limpio = str(valor).split(".")[-1]
    return limpio.capitalize()


def generar_reporte_pdf(estudio) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.8 * cm, leftMargin=1.8 * cm,
        topMargin=1.5 * cm, bottomMargin=1.8 * cm
    )
    ancho = doc.width

    styles = getSampleStyleSheet()
    p = estudio.paciente
    r = estudio.resultado
    es_tb = r and r.label == "TB"
    label_res = "TUBERCULOSIS DETECTADA" if es_tb else "SIN HALLAZGOS DE TB"
    sub_res   = "Resultado positivo · TB+" if es_tb else "Resultado negativo · Normal"
    color_res = ROJO if es_tb else VERDE
    bg_res    = ROJO_BG if es_tb else VERDE_BG
    color_hex = "C0392B" if es_tb else "1A7A4A"
    prob_pct  = round((r.prob_tb if r else 0) * 100)

    fecha_carga = estudio.fecha_carga.strftime("%d/%m/%Y · %H:%M") if estudio.fecha_carga else "—"
    emision = datetime.now().strftime("%d/%m/%Y a las %H:%M")
    nombre = f"{p.nombres} {p.apellidos}" if p else "—"
    doc_str = f"{p.tipo_documento}: {p.numero_documento}" if p and p.tipo_documento else "—"
    fecha_nac = str(p.fecha_nacimiento) if p and p.fecha_nacimiento else "—"
    sexo = ("Femenino" if p.sexo == "F" else "Masculino") if p and p.sexo else "—"

    story = []

    # ── Encabezado ────────────────────────────────────────────────────────
    story.append(BandaEncabezado(ancho, estudio.id))
    story.append(Spacer(1, 18))

    # ── Datos del paciente ────────────────────────────────────────────────
    story.append(SeccionTitulo(ancho, "Datos del paciente"))
    story.append(Spacer(1, 4))
    story.append(_fila_datos([
        ["Paciente",   nombre,          "Documento",      doc_str],
        ["Fecha nac.", fecha_nac,       "Sexo",           sexo],
        ["Estudio N°", str(estudio.id), "Fecha análisis", fecha_carga],
    ], [2.6 * cm, 6.5 * cm, 2.8 * cm, ancho - 2.6*cm - 6.5*cm - 2.8*cm]))
    story.append(Spacer(1, 18))

    # ── Resultado ─────────────────────────────────────────────────────────
    story.append(SeccionTitulo(ancho, "Resultado del análisis"))
    story.append(Spacer(1, 6))

    bloque_texto = Paragraph(
        f'<font color="#{color_hex}" size="15"><b>{label_res}</b></font><br/>'
        f'<font color="#{color_hex}" size="9">{sub_res}</font>',
        ParagraphStyle("res", leading=20)
    )
    bloque_prob = Paragraph(
        f'<font color="#{color_hex}" size="26"><b>{prob_pct}%</b></font><br/>'
        f'<font size="7.5" color="#6B7A99">PROBABILIDAD TB</font>',
        ParagraphStyle("prob", leading=26, alignment=TA_RIGHT)
    )

    resultado_table = Table(
        [[bloque_texto, bloque_prob]],
        colWidths=[ancho * 0.62, ancho * 0.38 - 6]
    )
    resultado_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg_res),
        ("LINEBEFORE",    (0, 0), (0, -1),  4, color_res),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (0, -1),  18),
        ("RIGHTPADDING",  (1, 0), (1, -1),  18),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(resultado_table)
    story.append(Spacer(1, 10))
    story.append(BarraProbabilidad(ancho, prob_pct, es_tb))
    story.append(Spacer(1, 18))

    # ── Detalle técnico ───────────────────────────────────────────────────
    if r:
        story.append(SeccionTitulo(ancho, "Detalle técnico del modelo"))
        story.append(Spacer(1, 4))
        story.append(_fila_datos([
            ["Confianza",    _capitalizar_confianza(r.nivel_confianza),
             "Threshold",       str(r.threshold)],
            ["Backbone",     r.backbone or "—",
             "Preprocesado",    r.enhancement_mode or "—"],
            ["Tiempo proc.", f"{r.tiempo_procesamiento_ms:.0f} ms",
             "Versión modelo",  r.version_modelo or "—"],
        ], [2.6 * cm, 6.5 * cm, 2.8 * cm, ancho - 2.6*cm - 6.5*cm - 2.8*cm]))
        story.append(Spacer(1, 18))

        # ── Interpretación ────────────────────────────────────────────────
        if r.interpretacion:
            story.append(SeccionTitulo(ancho, "Interpretación clínica"))
            story.append(Spacer(1, 6))
            interp_table = Table(
                [[Paragraph(r.interpretacion, ParagraphStyle(
                    "interp", fontSize=10, fontName="Helvetica",
                    textColor=OSCURO, leading=17))]],
                colWidths=[ancho]
            )
            interp_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), CHIP_BG),
                ("LINEBEFORE",    (0, 0), (0, -1),  3, NAVY),
                ("TOPPADDING",    (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING",   (0, 0), (-1, -1), 16),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ]))
            story.append(interp_table)
        story.append(Spacer(1, 26))

    # ── Aviso ─────────────────────────────────────────────────────

    story.append(Spacer(1, 20))

    aviso = Table([[Paragraph(
        "Este reporte es generado automáticamente por PulmoScan AI mediante un modelo de "
        "aprendizaje profundo (DenseNet169) y constituye una herramienta de apoyo diagnóstico. "
        "<b>No reemplaza el criterio clínico especializado</b>. Todo hallazgo debe ser confirmado "
        "mediante evaluación médica y pruebas microbiológicas.",
        ParagraphStyle("aviso", fontSize=7.5, fontName="Helvetica",
                       textColor=GRIS, leading=11, alignment=TA_CENTER))]],
        colWidths=[ancho])
    aviso.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), FONDO),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    story.append(aviso)

    doc.build(story)
    buffer.seek(0)
    return buffer