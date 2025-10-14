import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Tuple, Optional, Union
import logging

# OCR and PDF processing imports
try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import camelot
except ImportError:
    camelot = None

try:
    import tabula
except ImportError:
    tabula = None

from django.conf import settings
from .models import ProcessingLog

logger = logging.getLogger(__name__)


class BankStatementProcessor:
    """Main class for processing bank statements from PDF and image files"""
    
    def __init__(self, statement_instance):
        self.statement = statement_instance
        self.file_path = statement_instance.file.path
        self.file_type = statement_instance.file_type
        
    def process(self) -> List[Dict]:
        """Main processing method that routes to appropriate processor"""
        try:
            if self.file_type == 'pdf':
                return self._process_pdf()
            else:
                return self._process_image()
        except Exception as e:
            self._log_error(f"Processing failed: {str(e)}")
            raise
    
    def _process_pdf(self) -> List[Dict]:
        """Process PDF files using multiple extraction methods"""
        self._log_info("Starting PDF processing")
        
        # Try different PDF processing methods in order of preference
        methods = [
            self._extract_with_pdfplumber,
            self._extract_with_pymupdf,
            self._extract_with_camelot,
            self._extract_with_tabula
        ]
        
        for method in methods:
            try:
                if method.__name__ == '_extract_with_pdfplumber' and pdfplumber is None:
                    continue
                if method.__name__ == '_extract_with_pymupdf' and fitz is None:
                    continue
                if method.__name__ == '_extract_with_camelot' and camelot is None:
                    continue
                if method.__name__ == '_extract_with_tabula' and tabula is None:
                    continue
                    
                self._log_info(f"Trying {method.__name__}")
                transactions = method()
                if transactions:
                    self._log_info(f"Successfully extracted {len(transactions)} transactions using {method.__name__}")
                    return transactions
            except Exception as e:
                self._log_warning(f"{method.__name__} failed: {str(e)}")
                continue
        
        raise Exception("All PDF processing methods failed")
    
    def _process_image(self) -> List[Dict]:
        """Process image files using OCR"""
        if pytesseract is None or Image is None:
            raise Exception("OCR libraries not available")
        
        self._log_info("Starting image OCR processing")
        
        try:
            # Open and preprocess image
            image = Image.open(self.file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Perform OCR with different configurations
            configs = [
                '--psm 6',  # Uniform block of text
                '--psm 4',  # Single column of text
                '--psm 3',  # Fully automatic page segmentation
            ]
            
            best_text = ""
            best_confidence = 0
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                    # Get confidence data
                    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_text = text
                        
                except Exception as e:
                    self._log_warning(f"OCR config {config} failed: {str(e)}")
                    continue
            
            if not best_text.strip():
                raise Exception("No text extracted from image")
            
            self._log_info(f"OCR completed with confidence: {best_confidence:.2f}%")
            
            # Parse the extracted text
            transactions = self._parse_text_to_transactions(best_text, best_confidence)
            return transactions
            
        except Exception as e:
            self._log_error(f"Image processing failed: {str(e)}")
            raise
    
    def _extract_with_pdfplumber(self) -> List[Dict]:
        """Extract text using pdfplumber"""
        transactions = []
        
        with pdfplumber.open(self.file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                # Try to extract tables first
                tables = page.extract_tables()
                words = page.extract_words()
                
                if tables:
                    header = self._generate_header_from_words(words)
                    for table in tables:
                        table_transactions = self._parse_table_to_transactions([header] + table)
                        transactions.extend(table_transactions)
                
                # Extract text as fallback
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            
            # If no tables found, parse text
            if not transactions and full_text:
                transactions = self._parse_text_to_transactions(full_text)
        
        return transactions
    
    def _extract_with_pymupdf(self) -> List[Dict]:
        """Extract text using PyMuPDF"""
        doc = fitz.open(self.file_path)
        full_text = ""
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            full_text += text + "\n"
        
        doc.close()
        
        if not full_text.strip():
            raise Exception("No text extracted from PDF")
        
        return self._parse_text_to_transactions(full_text)
    
    def _extract_with_camelot(self) -> List[Dict]:
        """Extract tables using Camelot"""
        tables = camelot.read_pdf(self.file_path, pages='all')
        transactions = []
        
        for table in tables:
            df = table.df
            table_transactions = self._parse_dataframe_to_transactions(df)
            transactions.extend(table_transactions)
        
        return transactions
    
    def _extract_with_tabula(self) -> List[Dict]:
        """Extract tables using Tabula"""
        dfs = tabula.read_pdf(self.file_path, pages='all', multiple_tables=True)
        transactions = []
        
        for df in dfs:
            table_transactions = self._parse_dataframe_to_transactions(df)
            transactions.extend(table_transactions)
        
        return transactions
    
    def _parse_table_to_transactions(self, table: List[List]) -> List[Dict]:
        """Parse table data to transactions"""
        if not table or len(table) < 2:
            return []
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(table[1:], columns=table[0])
        return self._parse_dataframe_to_transactions(df)
    
    def _parse_dataframe_to_transactions(self, df: pd.DataFrame) -> List[Dict]:
        """Parse DataFrame to transactions"""
        transactions = []
        
        # Identify key columns
        date_col = self._find_date_column(df)
        desc_col = self._find_description_column(df)
        debit_col = self._find_amount_column(df, 'debit')
        credit_col = self._find_amount_column(df, 'credit')
        balance_col = self._find_amount_column(df, 'balance')
        
        # Require at least date and description columns
        if not date_col or not desc_col:
            return transactions
        
        # Parse each row into a transaction
        for _, row in df.iterrows():
            tx = self._parse_row_to_transaction(row, date_col, desc_col, debit_col, credit_col, balance_col)
            if tx:
                transactions.append(tx)
        
        return transactions
    
    def _parse_line_to_transaction(self, line: str, confidence: float = 100.0) -> Optional[Dict]:
        """Parse a single line to transaction"""
        # Common patterns for bank statement lines
        patterns = [
            # DD/MM/YYYY Description Amount Balance
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})$',
            # DD/MM/YYYY Description Debit Credit Balance
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\d+[.,]\d{2})?\s+(\d+[.,]\d{2})?\s+(\d+[.,]\d{2})$',
            # More flexible pattern
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([\d,]+[.]\d{2}).*?([\d,]+[.]\d{2})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                
                # Parse date
                date_str = groups[0]
                transaction_date = self._parse_date(date_str)
                if not transaction_date:
                    continue
                
                # Parse description
                description = groups[1].strip()
                if not description:
                    continue
                
                # Parse amounts
                amounts = [self._parse_amount(g) for g in groups[2:] if g]
                amounts = [a for a in amounts if a is not None]
                
                if len(amounts) >= 2:
                    # Determine debit/credit based on context
                    debit_amount = None
                    credit_amount = None
                    balance = amounts[-1]  # Last amount is usually balance
                    
                    # Simple heuristic: if description suggests debit, first amount is debit
                    if any(keyword in description.lower() for keyword in ['withdrawal', 'debit', 'charge', 'fee', 'atm']):
                        debit_amount = amounts[0] if len(amounts) > 1 else None
                    else:
                        credit_amount = amounts[0] if len(amounts) > 1 else None
                    
                    return {
                        'transaction_date': transaction_date,
                        'description': description,
                        'raw_description': line,
                        'debit_amount': debit_amount,
                        'credit_amount': credit_amount,
                        'balance': balance,
                        'confidence_score': confidence / 100.0
                    }
        
        return None
    
    def _parse_row_to_transaction(self, row, date_col, desc_col, debit_col, credit_col, balance_col) -> Optional[Dict]:
        """Parse DataFrame row to transaction"""
        try:
            # Parse date
            date_value = row[date_col] if date_col else None
            transaction_date = self._parse_date(str(date_value)) if date_value else None
            
            if not transaction_date:
                return None
            
            # Parse description
            description = str(row[desc_col]).strip() if desc_col else ''
            if not description or description == 'nan':
                return None
            
            # Parse amounts
            debit_amount = self._parse_amount(str(row[debit_col])) if debit_col else None
            credit_amount = self._parse_amount(str(row[credit_col])) if credit_col else None
            balance = self._parse_amount(str(row[balance_col])) if balance_col else None
            
            return {
                'transaction_date': transaction_date,
                'description': description,
                'raw_description': ' '.join([str(v) for v in row.values]),
                'debit_amount': debit_amount if debit_amount > 0 else None,
                'credit_amount': credit_amount if credit_amount > 0 else None,
                'balance': balance,
                'confidence_score': 1.0
            }
        except Exception as e:
            self._log_warning(f"Error parsing row: {str(e)}")
            return None
    
    def _find_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the date column in DataFrame"""
        date_keywords = ['date', 'transaction date', 'value date', 'posting date']
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in date_keywords):
                return col
        
        # Check first few rows for date patterns
        for col in df.columns:
            sample_values = df[col].head(5).astype(str)
            date_count = sum(1 for val in sample_values if self._parse_date(val))
            if date_count >= 2:  # At least 2 valid dates
                return col
        
        return None
    
    def _find_description_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the description column in DataFrame"""
        desc_keywords = ['description', 'narration', 'particulars', 'details', 'transaction details']
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in desc_keywords):
                return col
        
        # Find column with longest average text length
        text_lengths = {}
        for col in df.columns:
            try:
                # Convert to string and calculate average length
                col_series = df[col].astype(str)
                avg_length = col_series.str.len().mean()
                text_lengths[col] = avg_length
            except (AttributeError, TypeError):
                # Skip columns that can't be processed
                text_lengths[col] = 0
        
        if text_lengths:
            return max(text_lengths, key=text_lengths.get)
        
        return None
    
    def _find_amount_column(self, df: pd.DataFrame, amount_type: str) -> Optional[str]:
        """Find amount columns (debit, credit, balance) in DataFrame"""
        keywords = {
            'debit': ['debit', 'withdrawal', 'dr', 'debit amount'],
            'credit': ['credit', 'deposit', 'cr', 'credit amount'],
            'balance': ['balance', 'closing balance', 'running balance']
        }
        
        target_keywords = keywords.get(amount_type, [])
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in target_keywords):
                return col
        
        return None
    
    def _generate_header_from_words(self, words: List[Dict], y_tolerance: float = 3.0) -> List[str]:
        """
        Generate table header list from pdfplumber 'words' output.

        Args:
            words: list of word dicts from pdfplumber.extract_words()
            y_tolerance: vertical grouping tolerance (higher if text lines not perfectly aligned)

        Returns:
            List of header column names (left-to-right order)
        """
        import itertools
        
        if not words:
            return []

        # Sort words by vertical position (top)
        words_sorted = sorted(words, key=lambda w: float(w.get('top', 0.0)))

        # --- Step 1: group words by y position (header lines) ---
        lines = []
        for _, group in itertools.groupby(words_sorted, key=lambda w: round(w["top"] / y_tolerance)):
            line_words = sorted(list(group), key=lambda w: w["x0"])
            lines.append(line_words)

        # --- Step 2: find the header line ---
        # Heuristic: the line containing "Date", "Debit", "Credit", or "Balance" is likely the header
        header_line = None
        for line in lines:
            texts = [w["text"] for w in line]
            if any(t.lower() in ["date", "debit", "credit", "balance", "transaction"] for t in texts):
                header_line = line
                break

        if not header_line:
            # fallback: take the line with the most words near the top
            header_line = max(lines, key=lambda l: len(l))

        # --- Step 3: merge adjacent words that belong to same column header ---
        merged_headers = []
        current_text = header_line[0]["text"]
        prev_x1 = header_line[0]["x1"]

        for word in header_line[1:]:
            if word["x0"] - prev_x1 < 8:  # merge words close together
                current_text += " " + word["text"]
            else:
                merged_headers.append(current_text.strip())
                current_text = word["text"]
            prev_x1 = word["x1"]

        merged_headers.append(current_text.strip())

        return merged_headers

    def _generate_ordered_header_from_word_objects(self, words: List[Dict]) -> List[str]:
        """Generate normalized header names in left-to-right order from a list of word objects.
        Each word object is expected to contain at least 'text', 'top', and 'x0' keys.
        """
        if not words:
            return []
        
        # Cluster words into lines by their 'top' coordinate (tolerance in PDF points)
        tol = 2.0
        sorted_words = sorted(words, key=lambda w: float(w.get('top', 0.0)))
        lines: List[Dict] = []
        for w in sorted_words:
            t = float(w.get('top', 0.0))
            if not lines or abs(t - float(lines[-1]['top'])) > tol:
                lines.append({'top': t, 'words': [w]})
            else:
                lines[-1]['words'].append(w)
        
        # Define header keyword synonyms
        keywords: Dict[str, List[str]] = {
            'date': ['date', 'transaction date', 'value date', 'posting date'],
            'description': ['description', 'narration', 'particulars', 'details', 'transaction details'],
            'debit': ['debit', 'withdrawal', 'dr', 'debit amount'],
            'credit': ['credit', 'deposit', 'cr', 'credit amount'],
            'amount': ['amount', 'transaction amount'],
            'balance': ['balance', 'closing balance', 'running balance']
        }
        
        def _line_score(line_words: List[Dict]) -> int:
            toks = [str(w.get('text', '')).strip().lower() for w in line_words if str(w.get('text', '')).strip()]
            score = 0
            for i in range(len(toks)):
                uni = toks[i]
                if any(k in uni for kws in keywords.values() for k in kws):
                    score += 1
                if i + 1 < len(toks):
                    bi = f"{toks[i]} {toks[i+1]}"
                    if any(k in bi for kws in keywords.values() for k in kws):
                        score += 1
                if i + 2 < len(toks):
                    tri = f"{toks[i]} {toks[i+1]} {toks[i+2]}"
                    if any(k in tri for kws in keywords.values() for k in kws):
                        score += 1
            return score
        
        # Pick the best candidate line that likely contains the header
        best_line = max(lines, key=lambda L: _line_score(L['words'])) if lines else None
        if not best_line:
            return []
        
        # Sort selected line's words left-to-right
        selected_words = sorted(best_line['words'], key=lambda w: float(w.get('x0', 0.0)))
        toks = [str(w.get('text', '')).strip().lower() for w in selected_words if str(w.get('text', '')).strip()]
        
        # Build ordered normalized headers by scanning trigrams -> bigrams -> unigrams
        header: List[str] = []
        i = 0
        while i < len(toks):
            matched_name: Optional[str] = None
            matched_len = 1
            # Try trigram
            if i + 2 < len(toks):
                tri = f"{toks[i]} {toks[i+1]} {toks[i+2]}"
                for name, kws in keywords.items():
                    if any(k in tri for k in kws):
                        matched_name = name
                        matched_len = 3
                        break
            # Try bigram
            if matched_name is None and i + 1 < len(toks):
                bi = f"{toks[i]} {toks[i+1]}"
                for name, kws in keywords.items():
                    if any(k in bi for k in kws):
                        matched_name = name
                        matched_len = 2
                        break
            # Try unigram
            if matched_name is None:
                uni = toks[i]
                for name, kws in keywords.items():
                    if any(k in uni for k in kws):
                        matched_name = name
                        matched_len = 1
                        break
            
            if matched_name is not None and matched_name not in header:
                header.append(matched_name)
                i += matched_len
            else:
                i += 1
        
        return header
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str or date_str.lower() in ['nan', 'none', '']:
            return None
        
        # Common date formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
            '%Y-%m-%d', '%Y/%m/%d',
            '%m/%d/%Y', '%m-%d-%Y',
            '%d %b %Y', '%d %B %Y',
            '%b %d, %Y', '%B %d, %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """Parse amount string to Decimal"""
        if not amount_str or amount_str.lower() in ['nan', 'none', '']:
            return None
        
        # Clean the amount string
        amount_str = str(amount_str).strip()
        amount_str = re.sub(r'[^\d.,\-]', '', amount_str)  # Remove non-numeric chars except .,- 
        
        if not amount_str:
            return None
        
        # Handle different decimal separators
        if ',' in amount_str and '.' in amount_str:
            # Assume comma is thousands separator
            amount_str = amount_str.replace(',', '')
        elif ',' in amount_str and amount_str.count(',') == 1 and len(amount_str.split(',')[1]) == 2:
            # Comma as decimal separator
            amount_str = amount_str.replace(',', '.')
        
        try:
            return Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return None
    
    def _log_info(self, message: str):
        """Log info message"""
        logger.info(message)
        ProcessingLog.objects.create(
            statement=self.statement,
            level='info',
            message=message
        )
    
    def _log_warning(self, message: str):
        """Log warning message"""
        logger.warning(message)
        ProcessingLog.objects.create(
            statement=self.statement,
            level='warning',
            message=message
        )
    
    def _log_error(self, message: str):
        """Log error message"""
        logger.error(message)
        ProcessingLog.objects.create(
            statement=self.statement,
            level='error',
            message=message
        )


class DataCleaner:
    """Class for cleaning and validating extracted transaction data"""
    
    @staticmethod
    def clean_description(description: str) -> str:
        """Clean and normalize transaction description text"""
        if description is None:
            return ""
        # Remove control characters
        desc = re.sub(r'[\r\n\t]', ' ', str(description))
        # Collapse multiple spaces
        desc = re.sub(r'\s+', ' ', desc)
        # Trim
        desc = desc.strip()
        return desc

    @staticmethod
    def validate_transaction(transaction_data: Dict) -> Tuple[bool, List[str]]:
        """Validate a single transaction dict and return (is_valid, errors)"""
        errors: List[str] = []

        # Validate date
        if not transaction_data.get('transaction_date'):
            errors.append('Transaction date is required')

        # Validate description
        description = transaction_data.get('description', '')
        if not description or str(description).strip() == '':
            errors.append('Description is required')

        # Validate amounts
        debit = transaction_data.get('debit_amount')
        credit = transaction_data.get('credit_amount')

        if debit is None and credit is None:
            errors.append('Either debit or credit amount is required')
        if debit is not None and credit is not None:
            errors.append('Transaction cannot have both debit and credit amounts')

        # Validate amount values
        if debit is not None and debit <= 0:
            errors.append('Debit amount must be positive')
        if credit is not None and credit <= 0:
            errors.append('Credit amount must be positive')

        return len(errors) == 0, errors
    
    @staticmethod
    def detect_duplicates(transactions: List[Dict]) -> List[int]:
        """Detect potential duplicate transactions"""
        duplicates = []
        
        for i, trans1 in enumerate(transactions):
            for j, trans2 in enumerate(transactions[i+1:], i+1):
                if DataCleaner._are_duplicates(trans1, trans2):
                    duplicates.extend([i, j])
        
        return list(set(duplicates))
    
    @staticmethod
    def _are_duplicates(trans1: Dict, trans2: Dict) -> bool:
        """Check if two transactions are duplicates"""
        # Same date and amount
        if (trans1.get('transaction_date') == trans2.get('transaction_date') and
            trans1.get('debit_amount') == trans2.get('debit_amount') and
            trans1.get('credit_amount') == trans2.get('credit_amount')):
            
            # Similar description (80% similarity)
            desc1 = trans1.get('description', '').lower()
            desc2 = trans2.get('description', '').lower()
            
            if desc1 and desc2:
                similarity = DataCleaner._calculate_similarity(desc1, desc2)
                return similarity > 0.8
        
        return False
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        # Simple Jaccard similarity
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0