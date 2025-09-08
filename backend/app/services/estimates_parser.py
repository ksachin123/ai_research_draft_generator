"""
SVG Financial Data Parser Service

This service extracts financial data from SVG files containing balance sheets,
cash flow statements, and income statements with analyst estimates.
"""

import os
import re
import json
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET
import logging

logger = logging.getLogger(__name__)

class SVGFinancialParser:
    """Parser for extracting financial data from SVG files."""

    def __init__(self, config):
        self.namespace = {'svg': 'http://www.w3.org/2000/svg'}
        self.config = config

    def parse_estimates_folder(self, ticker: str) -> Dict[str, Any]:
        """
        Parse all SVG files in the estimates folder for a given ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing parsed financial data from all statements
        """
        estimates_path = os.path.join(self.config.DATA_ROOT_PATH, "research", ticker.upper(), "estimates")
        
        if not os.path.exists(estimates_path):
            logger.warning(f"Estimates folder not found for {ticker}: {estimates_path}")
            return {}
        
        estimates_data = {
            'ticker': ticker,
            'last_updated': None,
            'balance_sheet': {},
            'cash_flow': {},
            'income_statement': {}
        }
        
        # Parse each financial statement
        for filename in os.listdir(estimates_path):
            if filename.endswith('.svg'):
                file_path = os.path.join(estimates_path, filename)
                
                try:
                    if 'BalanceSheet' in filename:
                        estimates_data['balance_sheet'] = self._parse_svg_file(file_path, 'balance_sheet')
                    elif 'CashFlow' in filename:
                        estimates_data['cash_flow'] = self._parse_svg_file(file_path, 'cash_flow')
                    elif 'IncomeStatement' in filename:
                        estimates_data['income_statement'] = self._parse_svg_file(file_path, 'income_statement')
                        
                    # Update last modified time
                    file_mtime = os.path.getmtime(file_path)
                    if not estimates_data['last_updated'] or file_mtime > estimates_data['last_updated']:
                        estimates_data['last_updated'] = file_mtime
                        
                except Exception as e:
                    logger.error(f"Error parsing {filename}: {str(e)}")
                    continue
        
        return estimates_data
    
    def _parse_svg_file(self, file_path: str, statement_type: str) -> Dict[str, Any]:
        """
        Parse individual SVG file to extract financial data.
        
        Args:
            file_path: Path to the SVG file
            statement_type: Type of financial statement
            
        Returns:
            Dictionary containing extracted financial data
        """
        try:
            # Parse SVG XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract all text elements
            text_elements = self._extract_text_elements(root)
            
            # Parse based on statement type
            if statement_type == 'income_statement':
                return self._parse_income_statement(text_elements)
            elif statement_type == 'balance_sheet':
                return self._parse_balance_sheet(text_elements)
            elif statement_type == 'cash_flow':
                return self._parse_cash_flow(text_elements)
            
            return {}
            
        except Exception as e:
            logger.error(f"Error parsing SVG file {file_path}: {str(e)}")
            return {}
    
    def _extract_text_elements(self, root) -> List[Dict[str, Any]]:
        """Extract all text elements from SVG with their positions and content."""
        text_elements = []
        
        # Find all text elements
        for text_elem in root.iter('{http://www.w3.org/2000/svg}text'):
            # Get text content
            tspan = text_elem.find('{http://www.w3.org/2000/svg}tspan')
            if tspan is not None and tspan.text:
                content = tspan.text.strip()
                
                # Get position from transform attribute
                transform = text_elem.get('transform', '')
                position = self._extract_position_from_transform(transform)
                
                # Get styling information
                style = text_elem.get('style', '')
                font_weight = 'bold' if 'font-weight:bold' in style else 'normal'
                
                text_elements.append({
                    'content': content,
                    'position': position,
                    'font_weight': font_weight,
                    'is_percentage': '%' in content,
                    'is_currency': '$' in content,
                    'is_number': self._is_numeric_value(content)
                })
        
        # Sort by vertical position (y coordinate) to maintain reading order
        text_elements.sort(key=lambda x: (-x['position']['y'], x['position']['x']))
        
        return text_elements
    
    def _extract_position_from_transform(self, transform: str) -> Dict[str, float]:
        """Extract x,y coordinates from SVG transform attribute."""
        # Parse matrix transform: matrix(1,0,0,-1,x,y)
        matrix_match = re.search(r'matrix\([^,]+,[^,]+,[^,]+,[^,]+,([^,]+),([^)]+)\)', transform)
        if matrix_match:
            return {
                'x': float(matrix_match.group(1)),
                'y': float(matrix_match.group(2))
            }
        return {'x': 0, 'y': 0}
    
    def _is_numeric_value(self, text: str) -> bool:
        """Check if text represents a numeric value."""
        # Remove common formatting characters
        cleaned = re.sub(r'[,$%()B-]', '', text)
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _parse_income_statement(self, text_elements: List[Dict]) -> Dict[str, Any]:
        """Parse income statement data from text elements."""
        data = {
            'revenue': {},
            'gross_profit': {},
            'operating_income': {},
            'net_income': {},
            'margins': {},
            'segment_data': {},
            'quarterly_data': [],
            'estimates': {}
        }
        
        # Look for key financial metrics and segment data
        for i, element in enumerate(text_elements):
            content = element['content'].lower()
            
            # Identify revenue segments (iPhone, Mac, iPad, Services, etc.)
            if any(segment in content for segment in ['iphone', 'mac', 'ipad', 'services', 'wearables']):
                segment_name = element['content']
                # Look for associated percentage values in nearby elements
                segment_values = self._find_nearby_values(text_elements, i, segment_name)
                if segment_values:
                    data['segment_data'][segment_name] = segment_values
            
            # Identify margin data
            elif 'gross margin' in content:
                margin_values = self._find_nearby_values(text_elements, i, 'Gross Margin')
                if margin_values:
                    data['margins']['gross_margin'] = margin_values
            
            # Look for quarterly patterns or estimates
            elif self._is_quarterly_indicator(content):
                quarterly_info = self._extract_quarterly_data(text_elements, i)
                if quarterly_info:
                    data['quarterly_data'].append(quarterly_info)
        
        return data
    
    def _parse_balance_sheet(self, text_elements: List[Dict]) -> Dict[str, Any]:
        """Parse balance sheet data from text elements."""
        data = {
            'assets': {},
            'liabilities': {},
            'equity': {},
            'quarterly_data': [],
            'estimates': {}
        }
        
        # Implementation similar to income statement but for balance sheet metrics
        # This would identify key balance sheet items like cash, receivables, inventory, etc.
        
        return data
    
    def _parse_cash_flow(self, text_elements: List[Dict]) -> Dict[str, Any]:
        """Parse cash flow statement data from text elements."""
        data = {
            'operating_cash_flow': {},
            'investing_cash_flow': {},
            'financing_cash_flow': {},
            'free_cash_flow': {},
            'quarterly_data': [],
            'estimates': {}
        }
        
        # Implementation for cash flow specific metrics
        
        return data
    
    def _find_nearby_values(self, text_elements: List[Dict], center_index: int, label: str) -> Dict[str, Any]:
        """Find numeric values near a given label element."""
        values = {
            'actuals': [],
            'estimates': [],
            'growth_rates': []
        }
        
        # Look in elements following the label (typically on the same row)
        y_position = text_elements[center_index]['position']['y']
        tolerance = 10  # Y-position tolerance for same row
        
        for i in range(center_index + 1, min(center_index + 20, len(text_elements))):
            element = text_elements[i]
            
            # Check if element is on roughly the same row
            if abs(element['position']['y'] - y_position) <= tolerance:
                if element['is_percentage'] or element['is_number']:
                    # Determine if this is historical data or estimate based on position/context
                    if self._is_estimate_value(element, i, text_elements):
                        values['estimates'].append({
                            'value': element['content'],
                            'position': element['position']
                        })
                    else:
                        values['actuals'].append({
                            'value': element['content'],
                            'position': element['position']
                        })
            elif element['position']['y'] < y_position - tolerance:
                # Moved to next row, stop searching
                break
        
        return values if values['actuals'] or values['estimates'] else {}
    
    def _is_quarterly_indicator(self, text: str) -> bool:
        """Check if text indicates quarterly or period data."""
        quarterly_patterns = [
            r'q[1-4]', r'fy\d{2}', r'20\d{2}', r'quarter', r'fiscal'
        ]
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in quarterly_patterns)
    
    def _is_estimate_value(self, element: Dict, index: int, text_elements: List[Dict]) -> bool:
        """Determine if a value represents an estimate vs actual historical data."""
        # This could be enhanced with more sophisticated logic based on:
        # - Position patterns (estimates typically on the right side)
        # - Font styling (estimates might use different styling)
        # - Contextual clues from nearby text
        
        x_position = element['position']['x']
        # If positioned towards the right, more likely to be an estimate
        return x_position > 600  # Threshold based on SVG coordinate system
    
    def _extract_quarterly_data(self, text_elements: List[Dict], index: int) -> Dict:
        """Extract quarterly or periodic data from around a quarterly indicator."""
        # Implementation to extract quarterly financial data
        return {}
    
    def get_comparable_metrics(self, estimates_data: Dict, document_metrics: Dict) -> Dict[str, Any]:
        """
        Compare document metrics against estimates data to find relevant comparisons.
        
        Args:
            estimates_data: Parsed estimates data from SVG files
            document_metrics: Metrics extracted from uploaded document
            
        Returns:
            Dictionary containing comparison analysis
        """
        comparisons = {
            'revenue_comparisons': [],
            'margin_comparisons': [],
            'segment_comparisons': [],
            'estimate_vs_actual': [],
            'growth_implications': []
        }
        
        # Compare revenue metrics
        if 'revenue' in document_metrics:
            revenue_comparison = self._compare_revenue_metrics(
                estimates_data, document_metrics['revenue']
            )
            if revenue_comparison:
                comparisons['revenue_comparisons'].extend(revenue_comparison)
        
        # Compare margin metrics
        if 'margins' in document_metrics:
            margin_comparison = self._compare_margin_metrics(
                estimates_data, document_metrics['margins']
            )
            if margin_comparison:
                comparisons['margin_comparisons'].extend(margin_comparison)
        
        # Compare segment performance
        for statement_type in ['income_statement', 'balance_sheet', 'cash_flow']:
            if statement_type in estimates_data and 'segment_data' in estimates_data[statement_type]:
                segment_comparison = self._compare_segment_data(
                    estimates_data[statement_type]['segment_data'], 
                    document_metrics.get('segments', {})
                )
                if segment_comparison:
                    comparisons['segment_comparisons'].extend(segment_comparison)
        
        return comparisons
    
    def _compare_revenue_metrics(self, estimates_data: Dict, document_revenue: Dict) -> List[Dict]:
        """Compare revenue metrics between estimates and document."""
        comparisons = []
        
        # Implementation for revenue comparison logic
        
        return comparisons
    
    def _compare_margin_metrics(self, estimates_data: Dict, document_margins: Dict) -> List[Dict]:
        """Compare margin metrics between estimates and document."""
        comparisons = []
        
        # Implementation for margin comparison logic
        
        return comparisons
    
    def _compare_segment_data(self, estimates_segments: Dict, document_segments: Dict) -> List[Dict]:
        """Compare segment data between estimates and document."""
        comparisons = []
        
        # Implementation for segment comparison logic
        
        return comparisons

def create_estimates_parser(config) -> SVGFinancialParser:
    """Factory function to create SVG financial parser instance."""
    return SVGFinancialParser(config=config)
