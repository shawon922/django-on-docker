import io
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Any

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from .models import Invoice


class POSReceiptProcessor:
    """Extract and parse receipt text into structured invoice data (no DB writes)."""

    def __init__(self, invoice: Invoice):
        self.invoice = invoice
        self.path = invoice.receipt_file.path
        self.file_type = invoice.file_type

    # ---------------- MAIN ENTRY ----------------
    def process(self) -> Dict[str, Any]:
        if self.file_type == 'pdf':
            text, confidence = self._extract_text_from_pdf()
        else:
            text, confidence = self._extract_text_from_image()

        parsed = self._parse_text(text or '')
        result: Dict[str, Any] = {
            'raw_text': text or '',
            'parse_confidence': float(confidence or 0.0),
        }
        result.update(parsed)
        return result

    # ---------------- EXTRACTION ----------------
    def _extract_text_from_pdf(self):
        if pdfplumber is not None:
            try:
                all_text = []
                with pdfplumber.open(self.path) as pdf:
                    for page in pdf.pages:
                        txt = page.extract_text() or ''
                        if txt:
                            all_text.append(txt)
                text = "\n".join(all_text).strip()
                if text:
                    return text, 90.0
            except Exception:
                pass
        return self._ocr_pdf()

    def _ocr_pdf(self):
        if fitz is None or pytesseract is None or Image is None:
            return '', 0.0
        try:
            doc = fitz.open(self.path)
        except Exception:
            return '', 0.0

        parts, confs = [], []
        for i in range(doc.page_count):
            page = doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            mode = 'RGB' if pix.alpha == 0 else 'RGBA'
            try:
                image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            except Exception:
                image = Image.open(io.BytesIO(pix.tobytes()))
            text, conf = self._ocr_image(image)
            if text:
                parts.append(text)
            confs.append(conf)
        doc.close()
        avg = sum(confs) / len(confs) if confs else 0.0
        return "\n".join(parts), avg

    def _extract_text_from_image(self):
        if pytesseract is None or Image is None:
            return '', 0.0
        try:
            image = Image.open(self.path)
        except Exception:
            return '', 0.0
        return self._ocr_image(image)

    def _ocr_image(self, image):
        """Perform OCR with multiple configs to maximize confidence."""
        if pytesseract is None or Image is None:
            raise Exception("OCR libraries not available")

        configs = ['--psm 6', '--psm 4', '--psm 3']
        best_text, best_conf = "", 0.0

        for config in configs:
            try:
                text = pytesseract.image_to_string(image, config=config)
                data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                confs = [int(c) for c in data.get('conf', []) if str(c).isdigit() and int(c) > 0]
                avg_conf = sum(confs) / len(confs) if confs else 0.0
                if avg_conf > best_conf:
                    best_conf, best_text = avg_conf, text
            except Exception:
                continue

        return best_text, best_conf

    # ---------------- PARSING ----------------
    def _parse_text(self, text: str) -> Dict[str, Any]:
        """
        Unified parser entrypoint — uses robust regex-based parsing
        to extract invoice lines and totals.
        """
        parsed = self.parse_invoice_text(text)
        result = {
            'merchant_name': self._guess_merchant(text.splitlines()),
            'invoice_datetime': self._extract_datetime(text.splitlines()),
            'lines': [],
            'subtotal': None,
            'tax_amount': None,
            'total': None,
        }

        # Fill parsed data
        lines = parsed.get('invoice_lines', [])
        totals = parsed.get('totals', {})

        result['lines'] = [
            {
                'description': l.get('name'),
                'quantity': Decimal(l.get('qty') or 1),
                'unit_price': Decimal(str(l.get('unit_price') or 0)),
                'line_total': Decimal(str(l.get('total') or 0)),
            }
            for l in lines
        ]

        result['subtotal'] = totals.get('subtotal') or totals.get('net_total')
        result['tax_amount'] = totals.get('vat')
        result['total'] = totals.get('invoice_total') or totals.get('payment') or totals.get('subtotal')
        return result

    # ---------------- CORE PARSER ----------------
    def parse_invoice_text(self, text: str) -> Dict[str, Any]:
        """Parse messy OCR text into structured invoice dictionary.

        Tuned for POS receipts like the provided Bazooka sample where item lines look like
        "6 Bazooka Golden Sniper 114.00 12" and unit price annotations like "@ 16,52UNP".
        """

        # Normalize whitespace and decimals
        cleaned = text.replace('\u00A0', ' ')
        cleaned = re.sub(r'[^\S\n]+', ' ', cleaned)
        cleaned = cleaned.replace(',', '.')
        cleaned = re.sub(r'(\d)\.[\s]+(\d{2})', r'\1.\2', cleaned)  # 4. 35 -> 4.35
        cleaned = re.sub(r'(\d)[\s]+(\d{2})(?=\s*(?:UNP|\b12\b))', r'\1.\2', cleaned)  # 4 02 -> 4.02

        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]

        invoice_lines: List[Dict[str, Any]] = []
        totals: Dict[str, Decimal] = {}
        current_item: Optional[Dict[str, Any]] = None

        # Item lines with qty, name, line total, 12(VAT)
        pattern_item_endprice = re.compile(r'^\s*(\d+)\s+(.+?)\s+(\d+(?:\.\d{1,2})?)\s+12\b', re.IGNORECASE)
        # Unit price annotation lines like "@ 5.22UNP"
        pattern_unit_price = re.compile(r'@?\s*(\d+(?:\.\d{1,2})?)\s*UNP', re.IGNORECASE)
        # Totals (if present)
        pattern_total = re.compile(r'(Subtotal|Payment|Change|VAT|Net Total|Invoice Total)[:\s]+(?:SAR\s*)?([\d\.]+)', re.IGNORECASE)

        for raw in lines:
            line = raw

            # Item line
            m_item = pattern_item_endprice.match(line)
            if m_item:
                qty = int(m_item.group(1))
                name = m_item.group(2).strip()
                line_total = Decimal(m_item.group(3))
                current_item = {
                    'qty': qty,
                    'name': name,
                    'unit_price': None,
                    'total': line_total,
                }
                invoice_lines.append(current_item)
                continue

            # Unit price line
            m_price = pattern_unit_price.search(line)
            if m_price and current_item is not None:
                try:
                    unit_price = Decimal(m_price.group(1))
                    current_item['unit_price'] = unit_price
                    if not current_item.get('total') and current_item.get('qty'):
                        current_item['total'] = (Decimal(current_item['qty']) * unit_price).quantize(Decimal('0.01'))
                except InvalidOperation:
                    pass
                continue

            # Totals line
            m_total = pattern_total.search(line)
            if m_total:
                key = m_total.group(1).strip().lower().replace(' ', '_')
                try:
                    value = Decimal(m_total.group(2))
                except InvalidOperation:
                    continue
                totals[key] = value
                continue

            # Append short free-text lines to the current item as description addendum
            if current_item is not None and any(ch.isalpha() for ch in line) and not re.search(r'\d+\.\d{2}$', line):
                extra = line[:60]
                current_item['name'] = (current_item['name'] + ' ' + extra).strip()

        # Derive missing line totals
        for item in invoice_lines:
            if (item.get('total') is None) and item.get('qty') and item.get('unit_price'):
                try:
                    item['total'] = (Decimal(item['qty']) * Decimal(item['unit_price'])).quantize(Decimal('0.01'))
                except Exception:
                    item['total'] = None

        # Compute invoice total if missing
        if 'invoice_total' not in totals:
            s = sum((it.get('total') or Decimal('0')) for it in invoice_lines)
            totals['invoice_total'] = s

        return {'invoice_lines': invoice_lines, 'totals': totals}

    # ---------------- HELPERS ----------------
    def _to_decimal(self, s) -> Optional[Decimal]:
        if s is None:
            return None
        
        if isinstance(s, Decimal):
            return s
        
        s = s.replace(',', '')
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return None

    def _guess_merchant(self, lines: List[str]) -> Optional[str]:
        if not lines:
            return None
        for line in lines[:5]:
            if not re.search(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|total|vat|tax|subtotal|cashier|invoice|receipt", line, re.I):
                if not re.search(r"\d+\.\d{2}", line):
                    return line[:255]
        return lines[0][:255]

    def _extract_datetime(self, lines: List[str]):
        dt_regexes = [
            # ISO-like
            r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})[ T]*(\d{1,2}:\d{2}(?::\d{2})?)?\s*(AM|PM)?",
            # D/M/Y
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})[ T]*(\d{1,2}:\d{2}(?::\d{2})?)?\s*(AM|PM)?",
            # 11 Nov'25 14:06 PM
            r"(\d{1,2})\s+([A-Za-z]{3})'?\s*(\d{2,4})\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*(AM|PM)?",
        ]
        from datetime import datetime
        month_map = {m: i for i, m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], start=1)}
        for line in lines[:30]:
            # Month-name pattern
            m = re.search(dt_regexes[2], line)
            if m:
                day = int(m.group(1))
                mon = month_map.get(m.group(2).title(), 1)
                year_str = m.group(3)
                year = int('20' + year_str) if len(year_str) == 2 else int(year_str)
                time_part = m.group(4)
                ampm = (m.group(5) or '').upper()
                try:
                    hh, mm, *rest = time_part.split(':')
                    hour = int(hh)
                    minute = int(mm)
                    sec = int(rest[0]) if rest else 0
                    if ampm == 'PM' and hour < 12:
                        hour += 12
                    if ampm == 'AM' and hour == 12:
                        hour = 0
                    return datetime(year, mon, day, hour, minute, sec)
                except Exception:
                    pass
            # Numeric patterns
            for pat in dt_regexes[:2]:
                m2 = re.search(pat, line)
                if m2:
                    date_part, time_part, ampm = m2.group(1), (m2.group(2) or '00:00:00'), (m2.group(3) or '').upper()
                    fmt_candidates = [
                        ('%Y-%m-%d', '%H:%M:%S'), ('%Y/%m/%d', '%H:%M:%S'),
                        ('%d-%m-%Y', '%H:%M:%S'), ('%d/%m/%Y', '%H:%M:%S'),
                        ('%d-%m-%y', '%H:%M:%S'), ('%d/%m/%y', '%H:%M:%S'),
                    ]
                    for df, tf in fmt_candidates:
                        try:
                            dt = datetime.strptime(f"{date_part} {time_part}", f"{df} {tf}")
                            if ampm:
                                hour = dt.hour
                                if ampm == 'PM' and hour < 12:
                                    hour += 12
                                if ampm == 'AM' and hour == 12:
                                    hour = 0
                                dt = dt.replace(hour=hour)
                            return dt
                        except Exception:
                            continue
        return None
    
    # ---------------- DATA PREPARATION FOR SAVE ----------------
    def prepare_invoice_data(self, parsed: Dict) -> Dict[str, Any]:
        """
        Prepare parsed invoice data into model-ready dicts for Invoice and InvoiceLine creation.
        This does NOT save to the database — only returns clean, validated payloads.
        """

        # --- 1️⃣ Invoice Fields ---
        invoice_data = {
            'merchant_name': parsed.get('merchant_name') or '',
            'invoice_date': parsed.get('invoice_datetime'),
            'currency': 'SAR',  # default from your model
            'subtotal': self._to_decimal(parsed.get('subtotal')),
            'tax_amount': self._to_decimal(parsed.get('tax_amount')),
            'total_amount': self._to_decimal(parsed.get('total')),
            'parse_confidence': parsed.get('parse_confidence', 0.0),
            'raw_text': parsed.get('raw_text', ''),
            'status': 'parsed' if parsed.get('parse_confidence', 0) > 40 else 'draft',  # optional heuristic
        }

        # --- 2️⃣ Invoice Lines ---
        lines_data = []
        for i, line in enumerate(parsed.get('lines', []), start=1):
            try:
                qty = self._to_decimal(line.get('quantity')) or Decimal('1')
                unit_price = self._to_decimal(line.get('unit_price')) or Decimal('0')
                line_total = self._to_decimal(line.get('line_total')) or (qty * unit_price)
            except Exception:
                qty, unit_price, line_total = Decimal('1'), Decimal('0'), Decimal('0')

            lines_data.append({
                'position': i,
                'description': (line.get('description') or '').strip()[:255],
                'quantity': qty,
                'unit_price': unit_price,
                'line_total': line_total,
                'tax_rate': None,
                'product_code': '',  # optional placeholder for later enrichment
            })

        return {'invoice': invoice_data, 'lines': lines_data}
