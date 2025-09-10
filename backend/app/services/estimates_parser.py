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
            logger.warning(f"[SVG_PARSER][{ticker}] Estimates folder not found: {estimates_path}")
            return {}
        
        logger.info(f"[SVG_PARSER][{ticker}] Starting parse of estimates folder: {estimates_path}")
        estimates_data = {
            'ticker': ticker,
            'last_updated': None,
            'balance_sheet': {},
            'cash_flow': {},
            'income_statement': {}
        }
        
        # Parse each financial statement
        svg_files = [f for f in os.listdir(estimates_path) if f.endswith('.svg')]
        logger.info(f"[SVG_PARSER][{ticker}] Found {len(svg_files)} SVG files: {svg_files}")
        
        for filename in svg_files:
            file_path = os.path.join(estimates_path, filename)
            
            try:
                logger.debug(f"[SVG_PARSER][{ticker}] Processing file: {filename}")
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
                    
                logger.debug(f"[SVG_PARSER][{ticker}] Successfully parsed {filename} (mtime: {file_mtime})")
                    
            except Exception as e:
                logger.error(f"[SVG_PARSER][{ticker}] Error parsing {filename}: {str(e)}")
                continue
        
        # Log summary of parsed data
        for statement_type in ['income_statement', 'balance_sheet', 'cash_flow']:
            statement_data = estimates_data.get(statement_type, {})
            if isinstance(statement_data, dict):
                segments = len(statement_data.get('segment_data', {}))
                margins = len(statement_data.get('margins', {}))
                quarterly = len(statement_data.get('quarterly_data', []))
                logger.info(f"[SVG_PARSER][{ticker}] {statement_type}: {segments} segments, {margins} margins, {quarterly} quarterly entries")
        
        logger.info(f"[SVG_PARSER][{ticker}] Completed parsing. Last updated: {estimates_data.get('last_updated')}")
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
            logger.debug(f"[SVG_PARSER] Parsing SVG file: {os.path.basename(file_path)} ({statement_type})")
            # Parse SVG XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract all text elements
            text_elements = self._extract_text_elements(root)
            logger.debug(f"[SVG_PARSER] Extracted {len(text_elements)} text elements from {os.path.basename(file_path)}")
            
            # Parse based on statement type
            if statement_type == 'income_statement':
                result = self._parse_income_statement(text_elements)
            elif statement_type == 'balance_sheet':
                result = self._parse_balance_sheet(text_elements)
            elif statement_type == 'cash_flow':
                result = self._parse_cash_flow(text_elements)
            else:
                logger.warning(f"[SVG_PARSER] Unknown statement type: {statement_type}")
                return {}
            
            logger.debug(f"[SVG_PARSER] Completed parsing {os.path.basename(file_path)} ({statement_type})")
            return result
            
        except Exception as e:
            logger.error(f"[SVG_PARSER] Error parsing SVG file {file_path}: {str(e)}")
            return {}
    
    def _extract_text_elements(self, root) -> List[Dict[str, Any]]:
        """Extract all text elements from SVG with their positions and content."""
        text_elements = []
        element_count = 0
        
        logger.debug("[SVG_PARSER] Starting text element extraction")
        
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
                element_count += 1
        
        logger.debug(f"[SVG_PARSER] Extracted {element_count} text elements")
        
        # Sort by vertical position (y coordinate) to maintain reading order
        text_elements.sort(key=lambda x: (-x['position']['y'], x['position']['x']))
        
        # Log sample of extracted elements
        if text_elements:
            sample_size = min(5, len(text_elements))
            sample_contents = [elem['content'][:20] for elem in text_elements[:sample_size]]
            logger.debug(f"[SVG_PARSER] Sample elements: {sample_contents}")
        
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
        logger.debug(f"[SVG_PARSER] Parsing income statement from {len(text_elements)} text elements")
        
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
        
        segments_found = 0
        margins_found = 0
        quarterly_found = 0
        
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
                    segments_found += 1
                    logger.debug(f"[SVG_PARSER] Found segment: {segment_name}")
            
            # Identify margin data
            elif 'gross margin' in content:
                margin_values = self._find_nearby_values(text_elements, i, 'Gross Margin')
                if margin_values:
                    data['margins']['gross_margin'] = margin_values
                    margins_found += 1
                    logger.debug(f"[SVG_PARSER] Found gross margin data")
            
            # Look for quarterly patterns or estimates
            elif self._is_quarterly_indicator(content):
                quarterly_info = self._extract_quarterly_data(text_elements, i)
                if quarterly_info:
                    data['quarterly_data'].append(quarterly_info)
                    quarterly_found += 1
                    logger.debug(f"[SVG_PARSER] Found quarterly data: {content}")
        
        logger.info(f"[SVG_PARSER] Income statement parsed: {segments_found} segments, {margins_found} margins, {quarterly_found} quarterly entries")
        return data
    
    def _parse_balance_sheet(self, text_elements: List[Dict]) -> Dict[str, Any]:
        """Parse balance sheet data from text elements."""
        logger.debug(f"[SVG_PARSER] Parsing balance sheet from {len(text_elements)} text elements")
        
        data = {
            'assets': {},
            'liabilities': {},
            'equity': {},
            'quarterly_data': [],
            'estimates': {}
        }
        
        # Implementation similar to income statement but for balance sheet metrics
        # This would identify key balance sheet items like cash, receivables, inventory, etc.
        
        logger.debug("[SVG_PARSER] Balance sheet parsing completed (placeholder implementation)")
        return data
    
    def _parse_cash_flow(self, text_elements: List[Dict]) -> Dict[str, Any]:
        """Parse cash flow statement data from text elements."""
        logger.debug(f"[SVG_PARSER] Parsing cash flow from {len(text_elements)} text elements")
        
        data = {
            'operating_cash_flow': {},
            'investing_cash_flow': {},
            'financing_cash_flow': {},
            'free_cash_flow': {},
            'quarterly_data': [],
            'estimates': {}
        }
        
        # Implementation for cash flow specific metrics
        
        logger.debug("[SVG_PARSER] Cash flow parsing completed (placeholder implementation)")
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
        
        values_found = 0
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
                    values_found += 1
            elif element['position']['y'] < y_position - tolerance:
                # Moved to next row, stop searching
                break
        
        if values_found > 0:
            logger.debug(f"[SVG_PARSER] Found {values_found} values for label '{label}': {len(values['actuals'])} actuals, {len(values['estimates'])} estimates")
        
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
