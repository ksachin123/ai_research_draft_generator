import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ExtractedTable:
    """Structured representation of an extracted table"""
    title: str
    headers: List[str]
    data: List[List[str]]
    page_number: int
    table_type: str  # 'financial', 'segment', 'other'
    confidence_score: float

class EnhancedPDFProcessor:
    """Enhanced PDF processor with advanced table extraction capabilities"""
    
    def __init__(self):
        self.financial_keywords = [
            'revenue', 'sales', 'income', 'profit', 'loss', 'margin', 'ebitda',
            'cash flow', 'assets', 'liabilities', 'equity', 'shares', 'eps',
            'operating', 'net income', 'gross margin', 'cost of sales'
        ]
        
        self.table_patterns = {
            'income_statement': ['net sales', 'cost of sales', 'gross margin', 'operating income'],
            'balance_sheet': ['assets', 'liabilities', 'equity', 'cash'],
            'cash_flow': ['operating activities', 'investing activities', 'financing activities'],
            'segment': ['americas', 'europe', 'china', 'japan', 'asia pacific'],
            'product_revenue': ['iphone', 'mac', 'ipad', 'services', 'wearables']
        }
    
    def extract_pdf_with_tables(self, file_path: str) -> Tuple[str, List[ExtractedTable], Dict]:
        """Extract both text and structured tables from PDF"""
        try:
            extracted_text = ""
            extracted_tables = []
            total_pages = 0
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text() or ""
                    extracted_text += f"\n--- Page {page_num} ---\n{page_text}"
                    
                    # Extract tables
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if self._is_meaningful_table(table):
                            processed_table = self._process_table(
                                table, page_num, table_idx, page_text
                            )
                            if processed_table:
                                extracted_tables.append(processed_table)
            
            metadata = {
                "total_pages": total_pages,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()),
                "tables_extracted": len(extracted_tables),
                "financial_tables": len([t for t in extracted_tables if t.table_type == 'financial'])
            }
            
            logger.info(f"Enhanced extraction: {total_pages} pages, {len(extracted_tables)} tables")
            return extracted_text, extracted_tables, metadata
            
        except Exception as e:
            logger.error(f"Enhanced PDF extraction failed for {file_path}: {str(e)}")
            raise
    
    def _is_meaningful_table(self, table: List[List]) -> bool:
        """Determine if a table contains meaningful financial data"""
        if not table or len(table) < 2:
            return False
        
        # Check for minimum dimensions
        if len(table[0]) < 2:
            return False
        
        # Count non-empty cells
        non_empty_cells = sum(1 for row in table for cell in row if cell and str(cell).strip())
        total_cells = len(table) * len(table[0])
        
        # Require at least 30% filled cells
        if non_empty_cells / total_cells < 0.3:
            return False
        
        # Check for financial indicators
        table_text = ' '.join(str(cell).lower() for row in table for cell in row if cell)
        financial_matches = sum(1 for keyword in self.financial_keywords if keyword in table_text)
        
        return financial_matches >= 2
    
    def _process_table(self, table: List[List], page_num: int, table_idx: int, page_context: str) -> Optional[ExtractedTable]:
        """Process and classify a raw table"""
        try:
            # Clean table data
            cleaned_table = []
            for row in table:
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                cleaned_table.append(cleaned_row)
            
            if not cleaned_table:
                return None
            
            # Extract headers (usually first row)
            headers = cleaned_table[0] if cleaned_table else []
            data_rows = cleaned_table[1:] if len(cleaned_table) > 1 else []
            
            # Determine table type and title
            table_type, title = self._classify_table(cleaned_table, page_context)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(cleaned_table, table_type)
            
            return ExtractedTable(
                title=title,
                headers=headers,
                data=data_rows,
                page_number=page_num,
                table_type=table_type,
                confidence_score=confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to process table on page {page_num}: {str(e)}")
            return None
    
    def _classify_table(self, table: List[List], page_context: str) -> Tuple[str, str]:
        """Classify table type and extract title"""
        table_text = ' '.join(str(cell).lower() for row in table for cell in row if cell)
        context_text = page_context.lower()
        
        # Check for specific financial statement types
        for pattern_name, keywords in self.table_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in table_text)
            if matches >= 2:
                title = self._extract_title_from_context(context_text, pattern_name)
                return 'financial', title
        
        # Default classification
        title = self._extract_generic_title(table, context_text)
        return 'other', title
    
    def _extract_title_from_context(self, context: str, pattern_name: str) -> str:
        """Extract table title from surrounding page context"""
        title_patterns = {
            'income_statement': r'(condensed consolidated statements of operations|income statement)',
            'balance_sheet': r'(condensed consolidated balance sheets|balance sheet)',
            'cash_flow': r'(condensed consolidated statements of cash flows|cash flow)',
            'segment': r'(segment information|geographic data)',
            'product_revenue': r'(net sales by category|products and services performance)'
        }
        
        pattern = title_patterns.get(pattern_name, pattern_name)
        match = re.search(pattern, context, re.IGNORECASE)
        
        if match:
            return match.group(1).title()
        return pattern_name.replace('_', ' ').title()
    
    def _extract_generic_title(self, table: List[List], context: str) -> str:
        """Extract generic title from table or context"""
        # Look for table title in first few rows
        for row in table[:3]:
            for cell in row:
                if cell and len(str(cell)) > 10 and ':' not in str(cell):
                    return str(cell).strip()
        
        return "Financial Table"
    
    def _calculate_confidence(self, table: List[List], table_type: str) -> float:
        """Calculate confidence score for table extraction"""
        base_score = 0.5
        
        # Bonus for financial table type
        if table_type == 'financial':
            base_score += 0.2
        
        # Bonus for numeric content
        numeric_cells = 0
        total_cells = 0
        
        for row in table:
            for cell in row:
                if cell:
                    total_cells += 1
                    if self._is_numeric(str(cell)):
                        numeric_cells += 1
        
        if total_cells > 0:
            numeric_ratio = numeric_cells / total_cells
            base_score += numeric_ratio * 0.3
        
        return min(base_score, 1.0)
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text represents a numeric value"""
        # Remove common formatting
        cleaned = re.sub(r'[,$%()—\s]', '', text)
        cleaned = cleaned.replace('—', '-')  # En dash to minus
        
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def convert_tables_to_structured_text(self, tables: List[ExtractedTable]) -> str:
        """Convert extracted tables back to structured text format"""
        structured_text = ""
        
        for table in tables:
            structured_text += f"\n\n=== {table.title} (Page {table.page_number}) ===\n"
            structured_text += f"Table Type: {table.table_type} (Confidence: {table.confidence_score:.2f})\n\n"
            
            # Format headers
            if table.headers:
                structured_text += "| " + " | ".join(table.headers) + " |\n"
                structured_text += "|" + "|".join(["-" * (len(h) + 2) for h in table.headers]) + "|\n"
            
            # Format data rows
            for row in table.data:
                if any(cell.strip() for cell in row):  # Skip empty rows
                    structured_text += "| " + " | ".join(row) + " |\n"
        
        return structured_text
    
    def extract_key_financial_metrics(self, tables: List[ExtractedTable]) -> Dict:
        """Extract specific financial metrics from tables"""
        metrics = {
            "revenue": {},
            "income": {},
            "margins": {},
            "shares": {},
            "segments": {}
        }
        
        for table in tables:
            if table.table_type != 'financial':
                continue
            
            # Convert table to DataFrame for easier analysis
            try:
                df = pd.DataFrame(table.data, columns=table.headers)
                
                # Extract revenue metrics
                revenue_rows = df[df.iloc[:, 0].str.contains('revenue|sales', case=False, na=False)]
                for _, row in revenue_rows.iterrows():
                    metrics["revenue"][row.iloc[0]] = list(row.iloc[1:])
                
                # Extract income metrics
                income_rows = df[df.iloc[:, 0].str.contains('income|profit', case=False, na=False)]
                for _, row in income_rows.iterrows():
                    metrics["income"][row.iloc[0]] = list(row.iloc[1:])
                
                # Extract margin metrics
                margin_rows = df[df.iloc[:, 0].str.contains('margin', case=False, na=False)]
                for _, row in margin_rows.iterrows():
                    metrics["margins"][row.iloc[0]] = list(row.iloc[1:])
                    
            except Exception as e:
                logger.warning(f"Failed to extract metrics from table {table.title}: {str(e)}")
        
        return metrics
