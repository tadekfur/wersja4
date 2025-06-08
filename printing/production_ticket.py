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

def format_cena(cena, cena_typ):
    if not cena:
        return ""
    cena_str = str(cena)
    typ = str(cena_typ).lower()
    typ = typ.replace(".", "").replace(" ", "")
    typ = (typ.replace("ę", "e")
              .replace("ł", "l")
              .replace("ó", "o")
              .replace("ą", "a")
              .replace("ś", "s")
              .replace("ć", "c")
              .replace("ń", "n")
              .replace("ź", "z")
              .replace("ż", "z"))
    if "rol" in typ:
        return f"{cena_str} /rolka"
    elif "tys" in typ or "tyś" in typ:
        return f"{cena_str} /tyś"
    else:
        return cena_str

def get_dynamic_col_widths(pdf, headers, rows, total_width, min_width=10, max_width=70, padding=1):
    # max_width zwiększony, aby tabela mogła się rozciągać do marginesów!
    n = len(headers)
    col_widths = [min_width] * n
    for i, header in enumerate(headers):
        w = pdf.get_string_width(str(header)) + 2 * padding
        col_widths[i] = max(col_widths[i], min(w, max_width))
    for row in rows:
        for i, val in enumerate(row):
            w = pdf.get_string_width(str(val)) + 2 * padding
            col_widths[i] = max(col_widths[i], min(w, max_width))
    sum_width = sum(col_widths)
    # Skalowanie aby suma szerokości = total_width
    if sum_width != total_width:
        scale = total_width / sum_width if sum_width > 0 else 1
        col_widths = [w * scale for w in col_widths]
        # Korekta błędu zaokrąglenia: suma kolumn musi być dokładnie total_width
        diff = total_width - sum(col_widths)
        if col_widths:
            col_widths[-1] += diff
    return col_widths

def orderitem_to_pdf_row(orderitem):
    width = str(getattr(orderitem, "width", getattr(orderitem, "Szerokość", "")))
    height = str(getattr(orderitem, "height", getattr(orderitem, "Wysokość", "")))
    wymiar = f"{width}x{height}" if width and height else width or height
    material = getattr(orderitem, "material", getattr(orderitem, "Rodzaj materiału", ""))
    roll_length = getattr(orderitem, "roll_length", getattr(orderitem, "nawój/długość", ""))
    core = getattr(orderitem, "core", getattr(orderitem, "Średnica rdzenia", ""))
    ordered_quantity = getattr(orderitem, "ordered_quantity", getattr(orderitem, "zam. ilość", ""))
    miara = getattr(orderitem, "quantity_type", getattr(orderitem, "Typ ilości", ""))
    zam_rolki = getattr(orderitem, "zam. rolki", getattr(orderitem, "zam_rolki", ""))
    cena = getattr(orderitem, "Cena", getattr(orderitem, "price", ""))
    cena_typ = getattr(orderitem, "price_type", getattr(orderitem, "CenaTyp", ""))
    cena_sufix = format_cena(cena, cena_typ)
    return [
        wymiar, material, roll_length, core, ordered_quantity, miara, zam_rolki, cena_sufix
    ]

class ProductionTicketPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A5')
        self.set_auto_page_break(False)
        self.margin_left = 6
        self.margin_top = 6
        self.page_width = 148
        self.page_height = 210
        self.ticket_height = 90
        self.ticket_spacing = 6

        folder = os.path.dirname(__file__)
        font_regular = os.path.join(folder, "DejaVuSans.ttf")
        font_bold = os.path.join(folder, "DejaVuSans-Bold.ttf")
        self.add_font("DejaVu", "", font_regular, uni=True)
        self.add_font("DejaVu", "B", font_bold, uni=True)

    def draw_cut_mark(self):
        y_cut = self.page_height / 2
        x1 = self.margin_left
        x2 = self.page_width - self.margin_left
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.6)
        self.line(x1, y_cut, x2, y_cut)
        self.set_text_color(120, 120, 120)
        self.set_font("DejaVu", "", 8)
        self.set_xy(x2 - 20, y_cut - 4)
        self.cell(20, 5, "--- cięcie ---", border=0, align="R")
        self.set_text_color(0, 0, 0)

    def ticket(self, order, client, order_items, y_offset, table_full_width=False):
        x = self.margin_left
        # Dodaj przesunięcie o 0.5cm od linii cięcia dla drugiego zamówienia (y_offset > 0)
        if y_offset > 0:
            y = self.margin_top + y_offset + 10
        else:
            y = self.margin_top + y_offset

        box_h = 8
        black = (0, 0, 0)
        white = (255, 255, 255)
        blue = (180, 200, 245)
        blue_txt = (40, 80, 160)
        color_border = (180, 180, 200)
        color_grey = (245, 245, 245)
        color_white = (255, 255, 255)

        # --- Górny czarny pasek i bloki dat ---
        self.set_xy(x, y)
        self.set_fill_color(*black)
        self.set_text_color(*white)
        self.set_font("DejaVu", "B", 9)
        self.cell(56, box_h, f"Nr zamówienia: {format_pdf_value(getattr(order, 'order_number', getattr(order, 'Nr zamówienia', '')))}", border=0, align="L", fill=True)

        # Tło pod "Data zamówienia:" – dokładnie pod tekst
        self.set_font("DejaVu", "B", 8)
        date_order_label = "Data zamówienia:"
        date_order_label_w = self.get_string_width(date_order_label) + 6  # +6mm margines
        date_order_x = x + 58
        date_order_y = y
        self.set_fill_color(*black)
        self.rect(date_order_x, date_order_y, date_order_label_w, box_h, style='F')
        self.set_xy(date_order_x, date_order_y)
        self.set_text_color(*white)
        self.cell(date_order_label_w, box_h, date_order_label, border=0, align="L", fill=0)

        # Tło pod "Data wysyłki:" – przesunięte o 1,5cm w prawo
        wysylka_label = "Data wysyłki:"
        wysylka_label_w = self.get_string_width(wysylka_label) + 6
        wysylka_x = date_order_x + date_order_label_w + 15  # 1,5 cm dalej
        wysylka_y = y
        self.set_fill_color(*black)
        self.rect(wysylka_x, wysylka_y, wysylka_label_w, box_h, style='F')
        self.set_xy(wysylka_x, wysylka_y)
        self.set_text_color(*white)
        self.cell(wysylka_label_w, box_h, wysylka_label, border=0, align="L", fill=0)

        # Daty (pod spodem, czarny na białym):
        self.set_text_color(0, 0, 0)
        self.set_font("DejaVu", "", 8)
        self.set_xy(date_order_x, y + box_h)
        self.cell(date_order_label_w, 5, format_pdf_value(getattr(order, "order_date", getattr(order, "Data zamówienia", ""))), border=0, align="L")
        self.set_xy(wysylka_x, y + box_h)
        self.cell(wysylka_label_w, 5, format_pdf_value(getattr(order, "delivery_date", getattr(order, "Data dostawy", ""))), border=0, align="L")

        y += box_h + 5

        self.set_font("DejaVu", "B", 8)
        self.set_text_color(0, 0, 0)
        self.set_xy(x, y)
        self.cell(40, 4, "Dane klienta", ln=0, align="L")
        self.set_x(x + 60)
        self.cell(0, 4, "Adres dostawy", ln=1, align="L")

        self.set_font("DejaVu", "B", 7)
        y_klient = self.get_y()
        nazwa_skrocona = getattr(client, 'short_name', getattr(client, 'Nazwa skrócona', ''))
        klient_info = [
            ("Firma", nazwa_skrocona if nazwa_skrocona else getattr(client, 'name', getattr(client, 'Firma', ''))),
            ("Nr klienta", getattr(client, 'client_number', getattr(client, 'Nr klienta', ''))),
            ("Ulica i nr", getattr(client, 'street', getattr(client, 'Ulica i nr', ''))),
            ("Kod poczt.", getattr(client, 'postal_code', getattr(client, 'Kod pocztowy', ''))),
            ("Miasto", getattr(client, 'city', getattr(client, 'Miasto', '')))
        ]
        for idx, (label, value) in enumerate(klient_info):
            if value:
                self.set_xy(x, y_klient + idx * 4)
                self.set_font("DejaVu", "B", 7)
                self.cell(18, 4, f"{label}:", border=0)
                self.set_font("DejaVu", "", 7)
                self.cell(20, 4, format_pdf_value(value), border=0)
        self.set_font("DejaVu", "B", 7)
        adres = getattr(order, "delivery_address", getattr(order, "Adres dostawy", {}))
        self.set_xy(x + 60, y_klient)
        firma = adres.get("firma", getattr(client, "delivery_company", ""))
        self.cell(14, 4, "Firma:", border=0)
        self.set_font("DejaVu", "", 7)
        self.cell(25, 4, format_pdf_value(firma if firma else "na adres firmy"), border=0)

        y_table = y_klient + 22

        filtered_items = [item for item in order_items if str(getattr(item, "width", getattr(item, "Szerokość", ""))).strip() != ""]
        if filtered_items:
            col_headers = ["Lp.", "Wymiar", "Materiał", "Na rolce", "Rdzeń", "Ilość", "Miara", "zam. rolki", "Cena"]
            rows = []
            for i, produkt in enumerate(filtered_items, 1):
                row = orderitem_to_pdf_row(produkt)
                row_new = [str(i)] + row
                rows.append(row_new)
            # Rozciągamy TYLKO tabelę do szerokości marginesów
            total_width = self.page_width - 2 * self.margin_left
            self.set_font("DejaVu", "B", 7)
            # max_width duży, by kolumny mogły być szerokie, min_width mały, padding mały
            col_widths = get_dynamic_col_widths(self, col_headers, rows, total_width, min_width=10, max_width=70, padding=1)

            table_x = x
            table_y = y_table + 5

            self.set_xy(table_x, y_table)
            self.set_fill_color(180, 200, 245)
            self.set_text_color(40, 80, 160)
            self.set_font("DejaVu", "B", 8)
            self.cell(sum(col_widths), 6, "Dane produkcji", ln=1, fill=True)

            self.set_xy(table_x, table_y)
            self.set_font("DejaVu", "B", 7)
            self.set_text_color(0, 0, 0)
            for w, h in zip(col_widths, col_headers):
                self.set_fill_color(180, 200, 245)
                self.set_draw_color(*color_border)
                self.cell(w, 5, h, border=1, align="C", fill=True)
            self.ln()

            self.set_font("DejaVu", "", 7)
            for i, row in enumerate(rows):
                self.set_x(table_x)
                bg = color_grey if i % 2 == 1 else color_white
                self.set_fill_color(*bg)
                for w, cell_val in zip(col_widths, row):
                    self.cell(w, 5, str(cell_val), border=1, align="C", fill=True)
                self.ln()
            y_uwagi = self.get_y() + 1
        else:
            y_uwagi = y_table

        self.set_x(x)
        self.set_font("DejaVu", "B", 7)
        self.cell(0, 4, "Uwagi:", ln=1, align="L")
        self.set_font("DejaVu", "", 6)
        self.set_x(x)
        self.multi_cell(110, 4, format_pdf_value(getattr(order, "notes", getattr(order, "Uwagi", ""))), align="L")

def clean_filename(name):
    import re
    return re.sub(r'[^a-zA-Z0-9._-]', '_', name)

def export_production_ticket(order, client, order_items, filename=None):
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
    # Pierwszy bilet - zwyczajnie
    pdf.ticket(order, client, order_items, y_offset=0)
    pdf.draw_cut_mark()
    # Drugi bilet - przesuwamy w dół o 0,5 cm (5mm)
    pdf.ticket(order, client, order_items, y_offset=pdf.ticket_height + pdf.ticket_spacing, table_full_width=True)

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