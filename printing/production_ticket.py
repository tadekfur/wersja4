from fpdf import FPDF
import os
import sys
import webbrowser
import datetime
import re

def format_pdf_value(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value) if value is not None else ""

def orderitem_to_pdf_row(orderitem):
    width = str(getattr(orderitem, "width", getattr(orderitem, "Szerokość", "")))
    height = str(getattr(orderitem, "height", getattr(orderitem, "Wysokość", "")))
    wymiar = f"{width} x {height}" if width and height else width or height
    return [
        wymiar,
        getattr(orderitem, "material", getattr(orderitem, "Rodzaj materiału", "")),
        getattr(orderitem, "roll_length", getattr(orderitem, "nawój/długość", "")),
        getattr(orderitem, "core", getattr(orderitem, "Średnica rdzenia", "")),
        getattr(orderitem, "ordered_quantity", getattr(orderitem, "zam. ilość", "")),
        getattr(orderitem, "quantity_type", getattr(orderitem, "Typ ilości", "")),
        getattr(orderitem, "packaging", getattr(orderitem, "Rodzaj pakowania", "")),
    ]

class ProductionTicketPDF(FPDF):
    def __init__(self):
        # A5 page, portrait, mm
        super().__init__(orientation='P', unit='mm', format='A5')
        self.set_auto_page_break(False)
        self.margin_left = 8
        self.margin_top = 8
        self.page_width = 148
        self.ticket_height = 90  # A6 to 105mm, 2x90 = 180 < 210 (height A5)
        self.ticket_spacing = 8  # space between tickets if needed

        folder = os.path.dirname(__file__)
        font_regular = os.path.join(folder, "DejaVuSans.ttf")
        font_bold = os.path.join(folder, "DejaVuSans-Bold.ttf")
        self.add_font("DejaVu", "", font_regular, uni=True)
        self.add_font("DejaVu", "B", font_bold, uni=True)

    def ticket(self, order, client, order_items, y_offset):
        x = self.margin_left
        y = self.margin_top + y_offset

        # --- HEADER: NR ZAMÓWIENIA + DATY ---
        box_h = 9
        black = (0, 0, 0)
        white = (255, 255, 255)
        blue = (180, 200, 245)
        blue_txt = (40, 80, 160)
        color_border = (180, 180, 200)
        color_grey = (245, 245, 245)
        color_white = (255, 255, 255)

        # NR ZAMÓWIENIA (black box)
        self.set_xy(x, y)
        self.set_fill_color(*black)
        self.set_text_color(*white)
        self.set_font("DejaVu", "B", 10)
        nr_zam = format_pdf_value(getattr(order, "order_number", getattr(order, "Nr zamówienia", "")))
        self.cell(62, box_h, f"Nr zamówienia: {nr_zam}", border=0, align="L", fill=True)

        # Data zam + wysyłki (black boxes)
        self.set_xy(x + 65, y)
        self.set_fill_color(*black)
        self.set_font("DejaVu", "B", 9)
        self.cell(34, box_h, "Data zamówienia:", border=0, align="L", fill=True)
        self.set_xy(x + 100, y)
        self.cell(34, box_h, "Data wysyłki:", border=0, align="L", fill=True)
        # Data values
        self.set_font("DejaVu", "", 9)
        self.set_text_color(0, 0, 0)
        self.set_xy(x + 65, y + box_h)
        self.cell(34, 6, format_pdf_value(getattr(order, "order_date", getattr(order, "Data zamówienia", ""))), border=0, align="L")
        self.set_xy(x + 100, y + box_h)
        self.cell(34, 6, format_pdf_value(getattr(order, "delivery_date", getattr(order, "Data dostawy", ""))), border=0, align="L")

        y += box_h + 8

        # --- DANE KLIENTA / ADRES DOSTAWY ---
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(0, 0, 0)
        self.set_xy(x, y)
        self.cell(45, 5, "Dane klienta", ln=0, align="L")
        self.set_x(x + 68)
        self.cell(0, 5, "Adres dostawy", ln=1, align="L")

        self.set_font("DejaVu", "B", 8)
        y_klient = self.get_y()
        klient_info = [
            ("Firma", getattr(client, 'name', getattr(client, 'Firma', ''))),
            ("Nr klienta", getattr(client, 'client_number', getattr(client, 'Nr klienta', ''))),
            ("Ulica i nr", getattr(client, 'street', getattr(client, 'Ulica i nr', ''))),
            ("Kod pocztowy", getattr(client, 'postal_code', getattr(client, 'Kod pocztowy', ''))),
            ("Miasto", getattr(client, 'city', getattr(client, 'Miasto', '')))
        ]
        for idx, (label, value) in enumerate(klient_info):
            if value:
                self.set_xy(x, y_klient + idx * 5)
                self.set_font("DejaVu", "B", 8)
                self.cell(22, 5, f"{label}:", border=0)
                self.set_font("DejaVu", "", 8)
                self.cell(25, 5, format_pdf_value(value), border=0)
        # Adres dostawy
        self.set_font("DejaVu", "B", 8)
        adres = getattr(order, "delivery_address", getattr(order, "Adres dostawy", {}))
        self.set_xy(x + 68, y_klient)
        firma = adres.get("firma", getattr(client, "delivery_company", ""))
        self.cell(18, 5, "Firma:", border=0)
        self.set_font("DejaVu", "", 8)
        self.cell(35, 5, format_pdf_value(firma if firma else "na adres firmy"), border=0)

        y_table = y_klient + 28

        # --- DANE PRODUKCJI (tabela) ---
        self.set_xy(x, y_table)
        self.set_font("DejaVu", "B", 9)
        self.set_fill_color(*blue)
        self.set_text_color(*blue_txt)
        header = "Dane produkcji"
        self.cell(120, 7, header, fill=True, ln=1)

        self.set_xy(x, y_table + 7)
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(0, 0, 0)
        col_headers = ["Lp.", "Wymiar", "Materiał", "Na rolce", "Rdzeń", "Ilość", "Typ", "Pakow."]
        col_widths = [8, 24, 30, 18, 12, 13, 10, 20]
        for w, h in zip(col_widths, col_headers):
            self.set_fill_color(*blue)
            self.set_draw_color(*color_border)
            self.cell(w, 6, h, border=1, align="C", fill=True)
        self.ln()

        self.set_font("DejaVu", "", 8)
        for i, produkt in enumerate(order_items, 1):
            row = orderitem_to_pdf_row(produkt)
            self.set_x(x)
            bg = color_grey if i % 2 == 0 else color_white
            self.set_fill_color(*bg)
            self.cell(col_widths[0], 5, str(i), border=1, align="C", fill=True)
            for w, cell_val in zip(col_widths[1:], row):
                self.cell(w, 5, str(cell_val), border=1, align="C", fill=True)
            self.ln()
        # Uwagi
        y_uwagi = self.get_y() + 2
        self.set_x(x)
        self.set_font("DejaVu", "B", 8)
        self.cell(0, 5, "Uwagi:", ln=1, align="L")
        self.set_font("DejaVu", "", 7)
        self.set_x(x)
        self.multi_cell(120, 5, format_pdf_value(getattr(order, "notes", getattr(order, "Uwagi", ""))), align="L")

def clean_filename(name):
    # Remove all non-allowed chars for Windows file names
    import re
    return re.sub(r'[^a-zA-Z0-9._-]', '_', name)

def export_production_ticket(order, client, order_items, filename=None):
    # Always save to c:\produkcja
    output_dir = r"c:\produkcja"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    safe_order = clean_filename(str(getattr(order, "order_number", getattr(order, "Nr zamówienia", "zamowienie"))))
    safe_name = clean_filename(str(getattr(client, "name", getattr(client, "Firma", "klient"))))
    if not filename:
        filename = f"{safe_order}_{safe_name}_PRODUKCJA.pdf"
    output_path = os.path.join(output_dir, filename)

    pdf = ProductionTicketPDF()
    pdf.add_page()
    # Pierwszy ticket (górny)
    pdf.ticket(order, client, order_items, y_offset=0)
    # Drugi ticket (dolny) - przesunięcie o wysokość biletu + odstęp
    pdf.ticket(order, client, order_items, y_offset=pdf.ticket_height + pdf.ticket_spacing)

    pdf.output(output_path)

    abs_path = os.path.abspath(output_path)
    if sys.platform.startswith("win"):
        os.startfile(abs_path)
    elif sys.platform.startswith("darwin"):
        os.system(f'open "{abs_path}"')
    else:
        try:
            webbrowser.open(f'file://{abs_path}')
        except Exception:
            os.system(f'xdg-open "{abs_path}"')