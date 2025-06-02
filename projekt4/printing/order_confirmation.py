from fpdf import FPDF
import os
import sys
import webbrowser
import datetime

def orderitem_to_pdf_dict(orderitem):
    if isinstance(orderitem, dict):
        width = str(orderitem.get("Szerokość", orderitem.get("width", "")))
        height = str(orderitem.get("Wysokość", orderitem.get("height", "")))
        wymiar = f"{width} x {height}" if width and height else width or height
        return {
            "Wymiar": wymiar,
            "Rodzaj materiału": orderitem.get("Rodzaj materiału", orderitem.get("material", "")),
            "Ilość na rolce": orderitem.get("nawój/długość", orderitem.get("roll_length", "")),
            "Średnica rdzenia": orderitem.get("Średnica rdzenia", orderitem.get("core", "")),
            "Ilość": orderitem.get("zam. ilość", orderitem.get("ordered_quantity", "")),
            "Typ ilości": orderitem.get("Typ ilości", orderitem.get("quantity_type", "")),
            "Rodzaj pakowania": orderitem.get("Rodzaj pakowania", orderitem.get("packaging", "")),
        }
    else:
        width = str(getattr(orderitem, "Szerokość", getattr(orderitem, "width", "")))
        height = str(getattr(orderitem, "Wysokość", getattr(orderitem, "height", "")))
        wymiar = f"{width} x {height}" if width and height else width or height
        return {
            "Wymiar": wymiar,
            "Rodzaj materiału": getattr(orderitem, "Rodzaj materiału", getattr(orderitem, "material", "")),
            "Ilość na rolce": getattr(orderitem, "nawój_długość", getattr(orderitem, "roll_length", "")),
            "Średnica rdzenia": getattr(orderitem, "Średnica rdzenia", getattr(orderitem, "core", "")),
            "Ilość": getattr(orderitem, "zam_ilość", getattr(orderitem, "ordered_quantity", "")),
            "Typ ilości": getattr(orderitem, "Typ ilości", getattr(orderitem, "quantity_type", "")),
            "Rodzaj pakowania": getattr(orderitem, "Rodzaj pakowania", getattr(orderitem, "packaging", "")),
        }

def client_to_pdf_dict(client):
    if isinstance(client, dict):
        return client
    return {
        "Firma": getattr(client, "company_name", getattr(client, "name", "")),
        "Nr klienta": getattr(client, "client_number", ""),
        "Osoba kontakt.": getattr(client, "contact_person", ""),  # zmiana etykiety
        "Nr telefonu": getattr(client, "phone", ""),
        "E-mail": getattr(client, "email", ""),
        "Ulica i nr": getattr(client, "street", ""),
        "Kod pocztowy": getattr(client, "postal_code", ""),
        "Miasto": getattr(client, "city", ""),
        "NIP": getattr(client, "nip", ""),
        "delivery_company": getattr(client, "delivery_company", ""),
        "delivery_street": getattr(client, "delivery_street", ""),
        "delivery_postal_code": getattr(client, "delivery_postal_code", ""),
        "delivery_city": getattr(client, "delivery_city", ""),
    }

def format_pdf_value(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value) if value is not None else ""

class PDFGenerator:
    def __init__(self, order):
        self.order = order

    def generate_pdf(self, filename="output.pdf"):
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        folder = os.path.dirname(__file__)
        font_regular = os.path.join(folder, "DejaVuSans.ttf")
        font_bold = os.path.join(folder, "DejaVuSans-Bold.ttf")
        pdf.add_font("DejaVu", "", font_regular, uni=True)
        pdf.add_font("DejaVu", "B", font_bold, uni=True)

        color_accent = (77, 144, 254)
        color_header_bg = (0, 0, 0)
        color_white = (255, 255, 255)
        color_grey = (245, 245, 245)
        color_border = (180, 180, 200)

        left_margin = 15

        # --- Dane firmy Termedia (wyrównane do lewej) ---
        pdf.set_xy(left_margin, 15)
        pdf.set_font("DejaVu", "B", 13.5)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 7, "TERMEDIA", ln=1, align="L")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_x(left_margin)
        pdf.cell(0, 4, "ul. Przemysłowa 60", ln=1, align="L")
        pdf.set_x(left_margin)
        pdf.cell(0, 4, "43-110 Tychy", ln=1, align="L")
        pdf.set_x(left_margin)
        pdf.cell(0, 4, "bok@termedialabels.pl", ln=1, align="L")
        pdf.set_x(left_margin)
        pdf.cell(0, 4, "www.termedialabels.pl", ln=1, align="L")
        pdf.set_x(left_margin)
        pdf.cell(0, 4, "+48 503 179 658", ln=1, align="L")
        pdf.ln(1)

        # --- Blok "Zamówienie" i nr zamówienia (przesunięcie w prawo o 2cm względem lewej, tło krótsze o 1cm z prawej) ---
        blok_x = left_margin + 60  # 6cm = 60mm w prawo od lewego marginesu
        blok_y = 15
        ramka_w = 120  # zmniejszone tło o 1 cm (10mm) z prawej
        ramka_h = 11
        pdf.set_xy(blok_x, blok_y)
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(blok_x, blok_y, ramka_w, ramka_h, style='F')
        pdf.set_xy(blok_x + 4, blok_y + 1.5)
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(45, 8, "Zamówienie", ln=0, align="L")
        nr_zamowienia = format_pdf_value(self.order.get('Nr zamówienia', ''))
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_xy(blok_x + 52, blok_y + 1.5)
        pdf.cell(0, 8, f"Nr zamówienia: {nr_zamowienia}", ln=0, align="L")

        # --- Ramki pod daty, dane klienta i tabela przesunięte w dół o 2cm (20mm) ---
        przesuniecie_dol = 20  # 2cm

        # Daty
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_fill_color(0, 0, 0)
        # Data zamówienia
        pdf.set_xy(left_margin, 33 + przesuniecie_dol)
        pdf.cell(64, 8, "Data zamówienia:", ln=0, align="L", fill=True)
        # Data wysyłki (było: dostawy)
        pdf.set_xy(left_margin + 68, 33 + przesuniecie_dol)
        pdf.cell(64, 8, "Data wysyłki:", ln=0, align="L", fill=True)
        # Wartości dat
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(left_margin, 41 + przesuniecie_dol)
        data_zamowienia = format_pdf_value(self.order.get("Data zamówienia", ""))
        pdf.cell(64, 7, data_zamowienia, ln=0, align="L")
        pdf.set_xy(left_margin + 68, 41 + przesuniecie_dol)
        data_dostawy = format_pdf_value(self.order.get("Data dostawy", ""))  # zachowujemy klucz, zmieniamy tylko label
        pdf.cell(64, 7, data_dostawy, ln=0, align="L")
        pdf.ln(14)

        # Dane klienta (lewo) przesunięte o 0.5cm w prawo
        klient_x = left_margin + 5
        pdf.set_xy(klient_x, 51 + przesuniecie_dol)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 7, "Dane klienta", ln=0, align="L")

        # Adres dostawy (przesunięcie w lewo o 2cm względem oryginału)
        adres_blok_x = left_margin + 90 - 20  # 2cm = 20mm w lewo
        pdf.set_x(adres_blok_x)
        pdf.cell(0, 7, "Adres dostawy", ln=1, align="L")

        # Dane klienta
        klient_info = [
            (u"Firma", self.order.get('Firma', '')),
            (u"Nr klienta", self.order.get('Nr klienta', '')),
            (u"Osoba kontakt.", self.order.get('Osoba kontakt.', self.order.get('Osoba kontaktowa', ''))),  # zmiana etykiety i obsługa starego klucza
            (u"Nr telefonu", self.order.get('Nr telefonu', '')),
            (u"E-mail", self.order.get('E-mail', '')),
            (u"Ulica i nr", self.order.get('Ulica i nr', '')),
            (u"Kod pocztowy", self.order.get('Kod pocztowy', '')),
            (u"Miasto", self.order.get('Miasto', '')),
            (u"NIP", self.order.get('NIP', '')),
        ]
        y_klient = pdf.get_y()
        for idx, (label, value) in enumerate(klient_info):
            if value:
                pdf.set_xy(klient_x + 3, y_klient + idx * 6)
                pdf.set_font("DejaVu", "B", 8)
                pdf.cell(30, 6, f"{label}:", border=0)
                pdf.set_font("DejaVu", "", 8)
                pdf.cell(0, 6, format_pdf_value(value), ln=0, align="L")
        # Adres dostawy (przesunięty blok)
        adres = self.order.get("Adres dostawy", {})
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_xy(adres_blok_x + 3, y_klient)
        adres_labels = [
            ("Firma", "firma"),  # było "Nazwa firmy"
            ("Ulica i nr", "ulica"),
            ("Kod pocztowy", "kod_pocztowy"),
            ("Miejscowość", "miejscowość"),
        ]
        for idx, (lab, key) in enumerate(adres_labels):
            val = adres.get(key, "")
            if val:
                pdf.set_xy(adres_blok_x + 3, y_klient + idx * 6)
                pdf.set_font("DejaVu", "B", 8)
                pdf.cell(36, 6, f"{lab}:", border=0)
                pdf.set_font("DejaVu", "", 8)
                pdf.cell(0, 6, format_pdf_value(val), ln=0, align="L")
        # Przesuń całą sekcję produkcji niżej o 2cm:
        pdf.ln(74)

        # Dane produkcji (wyrównane do lewej, wyświetlaj tylko jeśli wypełniona szerokość)
        pdf.set_x(left_margin)
        pdf.set_font("DejaVu", "B", 10.5)
        prod_title_width = pdf.get_string_width("Dane produkcji") + 10
        pdf.set_fill_color(180, 200, 245)
        pdf.set_text_color(40, 80, 160)
        pdf.cell(prod_title_width, 9, "Dane produkcji", ln=1, fill=True)
        pdf.ln(1)

        produkty = self.order.get("Dane produkcji", [])
        produkty = [
            produkt for produkt in produkty
            if (produkt.get("Wymiar", "") or produkt.get("width", "") or produkt.get("Szerokość", ""))
            and (str(produkt.get("Wymiar", "")) != "" or str(produkt.get("width", "")) != "" or str(produkt.get("Szerokość", "")) != "")
        ]
        pdf.set_x(left_margin)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("DejaVu", "B", 7.5)
        table_headers = [
            "Lp.", "Wymiar", "Materiał", "Na rolce", "Rdzeń", "Ilość", "Typ", "Pakow."
        ]
        col_widths = [9, 28, 37, 22, 14, 16, 13, 32]

        pdf.set_x(left_margin)
        for w, h in zip(col_widths, table_headers):
            pdf.set_fill_color(180, 200, 245)
            pdf.set_draw_color(*color_border)
            pdf.cell(w, 6.5, h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("DejaVu", "", 7.5)
        for i, produkt in enumerate(produkty, 1):
            wymiar = format_pdf_value(produkt.get("Wymiar", ""))
            material = format_pdf_value(produkt.get("Rodzaj materiału", ""))
            na_rolce = format_pdf_value(produkt.get("Ilość na rolce", ""))
            rdzen = format_pdf_value(produkt.get("Średnica rdzenia", ""))
            ilosc = format_pdf_value(produkt.get("Ilość", ""))
            typ_ilosci = format_pdf_value(produkt.get("Typ ilości", ""))
            pakowanie = format_pdf_value(produkt.get("Rodzaj pakowania", ""))
            row = [
                str(i),
                wymiar,
                material,
                na_rolce,
                rdzen,
                ilosc,
                typ_ilosci,
                pakowanie,
            ]
            pdf.set_x(left_margin)
            bg = color_grey if i % 2 == 0 else color_white
            pdf.set_fill_color(*bg)
            for w, cell_val in zip(col_widths, row):
                pdf.cell(w, 6, str(cell_val), border=1, align="C", fill=True)
            pdf.ln()

        # Uwagi pod tabelą
        pdf.ln(3)
        pdf.set_x(left_margin)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 7, "Uwagi:", ln=1, align="L")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_x(left_margin)
        uwagi = self.order.get("Uwagi", "")
        pdf.multi_cell(176, 6, format_pdf_value(uwagi), align="L")
        pdf.ln(10)

        # Stopka
        pdf.set_font("DejaVu", "", 4)
        pdf.set_text_color(130, 130, 130)
        pdf.set_y(277)
        center_text = "Wygenerowano automatycznie przez LabelOrderManager"
        text_width = pdf.get_string_width(center_text)
        page_center = 105
        pdf.set_x(page_center - text_width / 2)
        pdf.cell(text_width, 3, center_text, align="C")

        pdf.output(filename)

        abs_path = os.path.abspath(filename)
        # Usunięto drugi wydruk! Teraz tylko jeden raz jest otwierany plik
        if sys.platform.startswith("win"):
            os.startfile(abs_path)
        elif sys.platform.startswith("darwin"):
            os.system(f'open "{abs_path}"')
        else:
            try:
                webbrowser.open(f'file://{abs_path}')
            except Exception:
                os.system(f'xdg-open "{abs_path}"')

def export_order_to_pdf(order, client, order_items, filename):
    output_dir = os.path.dirname(filename)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    client_dict = client_to_pdf_dict(client) if client else {}
    order_items_dicts = [orderitem_to_pdf_dict(item) for item in (order_items or [])]
    order_data = dict(order) if isinstance(order, dict) else {}

    if "Nr zamówienia" not in order_data:
        if "order_number" in order_data:
            order_data["Nr zamówienia"] = order_data["order_number"]
        elif hasattr(order, "order_number"):
            order_data["Nr zamówienia"] = getattr(order, "order_number", "")
    if "Data zamówienia" not in order_data:
        if "order_date" in order_data:
            order_data["Data zamówienia"] = order_data["order_date"]
        elif hasattr(order, "order_date"):
            order_data["Data zamówienia"] = getattr(order, "order_date", "")
    if "Data dostawy" not in order_data:
        if "delivery_date" in order_data:
            order_data["Data dostawy"] = order_data["delivery_date"]
        elif hasattr(order, "delivery_date"):
            order_data["Data dostawy"] = getattr(order, "delivery_date", "")

    # UWAGI - zawsze zmapuj pole notes (obiekt/order) na klucz "Uwagi"
    if "Uwagi" not in order_data:
        if "notes" in order_data:
            order_data["Uwagi"] = order_data["notes"]
        elif hasattr(order, "notes"):
            order_data["Uwagi"] = getattr(order, "notes", "")

    order_data.update(client_dict)
    if order_items_dicts:
        order_data['Dane produkcji'] = order_items_dicts

    # ADRES DOSTAWY: budujemy na podstawie pól z klienta/orderu, jeśli nie istnieje
    if "Adres dostawy" not in order_data or not order_data["Adres dostawy"]:
        adres_dostawy = {
            "firma": order_data.get("delivery_company", ""),
            "ulica": order_data.get("delivery_street", ""),
            "kod_pocztowy": order_data.get("delivery_postal_code", ""),
            "miejscowość": order_data.get("delivery_city", "")
        }
        adres_dostawy = {k: v for k, v in adres_dostawy.items() if v}
        order_data["Adres dostawy"] = adres_dostawy

    for key in ["Data zamówienia", "Data dostawy"]:
        if key in order_data and isinstance(order_data[key], (datetime.date, datetime.datetime)):
            order_data[key] = order_data[key].strftime("%Y-%m-%d")

    pdfgen = PDFGenerator(order_data)
    pdfgen.generate_pdf(filename)