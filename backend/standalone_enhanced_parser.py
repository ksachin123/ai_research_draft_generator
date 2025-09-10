"""
Standalone Enhanced SVG Financial Parser Service

This service integrates all the new SVG parsers (Balance Sheet, Cash Flow, 
Margin Analysis, Income Statement) to create comprehensive financial data
for knowledge base integration and comparative analysis.

Now includes current quarter estimates extraction for AI prompt integration.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import the new parsers directly from the backend directory
import sys
backend_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)

from balance_sheet_parser import BalanceSheetSVGParser
from cash_flow_parser import CashFlowSVGParser  
from margin_analysis_parser import MarginAnalysisSVGParser
from income_statement_parser import IncomeStatementSVGParser

# Import the estimates extractor from the backend directory
from current_quarter_estimates_extractor import CurrentQuarterEstimatesExtractor

logger = logging.getLogger(__name__)

class StandaloneEnhancedSVGParser:
    """Standalone enhanced parser that integrates all financial statement parsers."""

    def __init__(self, data_root_path: str):
        self.data_root_path = data_root_path
        self.balance_sheet_parser = BalanceSheetSVGParser()
        self.cash_flow_parser = CashFlowSVGParser()
        self.margin_analysis_parser = MarginAnalysisSVGParser()
        self.income_statement_parser = IncomeStatementSVGParser()
        self.estimates_extractor = CurrentQuarterEstimatesExtractor()
        
    def parse_financial_statements(self, ticker: str) -> Dict[str, Any]:
        """
        Parse all financial statement SVG files for comprehensive analysis.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing parsed data from all financial statements
        """
        
        estimates_path = os.path.join(self.data_root_path, "research", ticker.upper(), "estimates")
                
        if not estimates_path:
            logger.warning(f"[ENHANCED_SVG_PARSER][{ticker}] No estimates folder found in potential paths")
            return {}

        logger.info(f"[ENHANCED_SVG_PARSER][{ticker}] Parsing financial statements from: {estimates_path}")
        
        # Initialize comprehensive financial data structure
        financial_data = {
            'ticker': ticker.upper(),
            'last_updated': datetime.utcnow().timestamp(),
            'parsing_summary': {
                'statements_found': [],
                'statements_parsed': [],
                'total_periods': 0,
                'total_metrics': 0
            },
            'balance_sheet': {},
            'cash_flow': {},
            'margin_analysis': {},
            'income_statement': {},
            'comparative_analysis': {}
        }
        
        # Define SVG file mappings
        svg_mappings = {
            'balance_sheet': {
                'files': ['BalanceSheet.svg', 'balance_sheet.svg', 'Balance_Sheet.svg'],
                'parser': self.balance_sheet_parser,
                'statement_type': 'Balance Sheet'
            },
            'income_statement': {
                'files': ['IncomeStatement.svg', 'income_statement.svg', 'Income_Statement.svg'],
                'parser': self.income_statement_parser,
                'statement_type': 'Income Statement'
            },
            'cash_flow': {
                'files': ['CashFlow.svg', 'cash_flow.svg', 'Cash_Flow.svg', 'CashFlowStatement.svg'],
                'parser': self.cash_flow_parser,
                'statement_type': 'Cash Flow Statement'
            },
            'margin_analysis': {
                'files': ['MarginAnalysis.svg', 'margin_analysis.svg', 'Margin_Analysis.svg'],
                'parser': self.margin_analysis_parser,
                'statement_type': 'Margin Analysis'
            }
        }
        
        # Process each statement type
        for statement_key, mapping in svg_mappings.items():
            try:
                svg_file_path = self._find_svg_file(estimates_path, mapping['files'])
                if svg_file_path:
                    financial_data['parsing_summary']['statements_found'].append(mapping['statement_type'])
                    
                    # All parsers now use the same pattern: parse_svg_to_json(file_path)
                    parsed_data = mapping['parser'].parse_svg_to_json(svg_file_path)
                    
                    if parsed_data and parsed_data.get('metrics'):
                        financial_data[statement_key] = parsed_data
                        financial_data['parsing_summary']['statements_parsed'].append(mapping['statement_type'])
                        financial_data['parsing_summary']['total_periods'] = max(
                            financial_data['parsing_summary']['total_periods'],
                            len(parsed_data.get('periods', []))
                        )
                        financial_data['parsing_summary']['total_metrics'] += len(parsed_data.get('metrics', {}))
                        
                        logger.info(f"[ENHANCED_SVG_PARSER][{ticker}] Successfully parsed {mapping['statement_type']}: "
                                   f"{len(parsed_data.get('periods', []))} periods, "
                                   f"{len(parsed_data.get('metrics', {}))} metrics")
                    else:
                        logger.warning(f"[ENHANCED_SVG_PARSER][{ticker}] Failed to parse {mapping['statement_type']}")
                else:
                    logger.info(f"[ENHANCED_SVG_PARSER][{ticker}] {mapping['statement_type']} SVG not found")
                    
            except Exception as e:
                logger.error(f"[ENHANCED_SVG_PARSER][{ticker}] Error parsing {mapping['statement_type']}: {str(e)}")
        
        # Generate comparative analysis
        if financial_data['parsing_summary']['statements_parsed']:
            financial_data['comparative_analysis'] = self._generate_comparative_analysis(financial_data)
        
        # Extract current quarter estimates for AI prompts
        financial_data['current_quarter_estimates'] = self.extract_current_quarter_estimates(financial_data)
        
        return financial_data
    
    def extract_current_quarter_estimates(self, financial_data: Dict[str, Any], target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Extract current quarter estimates for AI prompt inclusion.
        
        Args:
            financial_data: Full parsed financial data
            target_date: Optional date to determine the quarter for (defaults to current date)
            
        Returns:
            Dict containing current quarter estimates formatted for AI prompts
        """
        try:
            return self.estimates_extractor.extract_current_quarter_estimates(financial_data, target_date)
        except Exception as e:
            logger.error(f"Error extracting current quarter estimates: {str(e)}")
            return {}
    
    def get_current_quarter_estimates_for_ai(self, ticker: str, target_date: Optional[datetime] = None) -> str:
        """
        Get current quarter estimates formatted specifically for AI prompts.
        
        Args:
            ticker: Stock ticker symbol
            target_date: Optional date to determine the quarter for (defaults to current date)
            
        Returns:
            Formatted string ready for inclusion in AI prompts
        """
        try:
            # Parse the financial statements
            financial_data = self.parse_financial_statements(ticker)
            
            # Extract estimates with the specified target date
            estimates = self.extract_current_quarter_estimates(financial_data, target_date)
            return estimates.get('formatted_for_ai', '')
            
        except Exception as e:
            logger.error(f"Error getting current quarter estimates for AI: {str(e)}")
            return f"Error retrieving current quarter estimates for {ticker}: {str(e)}"
    
    def _find_svg_file(self, estimates_path: str, file_candidates: List[str]) -> Optional[str]:
        """Find the first existing SVG file from a list of candidates."""
        for filename in file_candidates:
            file_path = os.path.join(estimates_path, filename)
            if os.path.exists(file_path):
                return file_path
        return None
    
    def _generate_comparative_analysis(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparative analysis data for easy querying."""
        analysis = {
            'periods_overview': self._extract_periods_overview(financial_data),
            'key_metrics_summary': self._extract_key_metrics(financial_data),
            'growth_trends': self._analyze_growth_trends(financial_data),
            'segment_analysis': self._analyze_segments(financial_data)
        }
        return analysis
    
    def _extract_periods_overview(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract overview of all time periods across statements."""
        all_periods = set()
        
        for statement in ['balance_sheet', 'income_statement', 'cash_flow', 'margin_analysis']:
            if financial_data[statement].get('periods'):
                all_periods.update(financial_data[statement]['periods'])
        
        # Categorize periods
        quarterly_periods = [p for p in all_periods if any(q in p for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Mar', 'Jun', 'Sep', 'Dec'])]
        annual_periods = [p for p in all_periods if any(y in p for y in ['2023', '2024', '2025', '2026', '2027'])]
        
        return {
            'all_periods': sorted(list(all_periods)),
            'quarterly_periods': sorted(quarterly_periods),
            'annual_periods': sorted(annual_periods),
            'latest_quarter': max(quarterly_periods) if quarterly_periods else None,
            'latest_annual': max(annual_periods) if annual_periods else None
        }
    
    def _extract_key_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics for comparative analysis."""
        key_metrics = {
            'revenue_metrics': {},
            'profitability_metrics': {},
            'liquidity_metrics': {},
            'efficiency_metrics': {}
        }
        
        # Extract revenue metrics from Income Statement (primary source)
        if financial_data['income_statement'].get('metrics'):
            is_metrics = financial_data['income_statement']['metrics']
            
            # Total revenues and segment revenues
            if 'Revenues' in is_metrics:
                key_metrics['revenue_metrics']['total_revenue'] = is_metrics['Revenues']
            
            # Product segment revenues from Income Statement
            for product in ['iPhone', 'iPad', 'Mac', 'Services', 'Wearables, Home and Accessories']:
                if product in is_metrics:
                    key_metrics['revenue_metrics'][f'{product.lower().replace(" ", "_").replace(",", "")}_revenue'] = is_metrics[product]
            
            # Profitability metrics from Income Statement
            if 'Gross Profit' in is_metrics:
                key_metrics['profitability_metrics']['gross_profit'] = is_metrics['Gross Profit']
            if 'Gross Margin' in is_metrics:
                key_metrics['profitability_metrics']['gross_margin_pct'] = is_metrics['Gross Margin']
            if 'Net Income' in is_metrics:
                key_metrics['profitability_metrics']['net_income'] = is_metrics['Net Income']
            if 'Operating Income' in is_metrics:
                key_metrics['profitability_metrics']['operating_income'] = is_metrics['Operating Income']
        
        # Supplement with revenue metrics from margin analysis
        if financial_data['margin_analysis'].get('metrics'):
            ma_metrics = financial_data['margin_analysis']['metrics']
            if 'Revenue' in ma_metrics and 'total_revenue' not in key_metrics['revenue_metrics']:
                key_metrics['revenue_metrics']['revenue_growth'] = ma_metrics['Revenue']
            
            # Product segment performance (margins)
            for product in ['iPhone', 'iPad', 'Mac', 'Services']:
                if product in ma_metrics:
                    key_metrics['profitability_metrics'][f'{product.lower()}_margin'] = ma_metrics[product]
        
        # Extract liquidity from balance sheet
        if financial_data['balance_sheet'].get('metrics'):
            bs_metrics = financial_data['balance_sheet']['metrics']
            if 'Cash and cash equivalents' in bs_metrics:
                key_metrics['liquidity_metrics']['cash_position'] = bs_metrics['Cash and cash equivalents']
        
        # Extract cash flow metrics
        if financial_data['cash_flow'].get('metrics'):
            cf_metrics = financial_data['cash_flow']['metrics']
            if 'Operating Cash Flow' in cf_metrics:
                key_metrics['efficiency_metrics']['operating_cash_flow'] = cf_metrics['Operating Cash Flow']
            if 'Net Income / (Loss)' in cf_metrics:
                key_metrics['efficiency_metrics']['net_income_cf'] = cf_metrics['Net Income / (Loss)']
        
        return key_metrics
    
    def _analyze_growth_trends(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze growth trends across time periods."""
        growth_analysis = {
            'revenue_growth_trend': {},
            'profitability_trends': {},
            'margin_trends': {},
            'cash_flow_trends': {}
        }
        
        # Analyze revenue growth from Income Statement (primary source)
        if financial_data['income_statement'].get('metrics', {}).get('Revenues'):
            revenue_data = financial_data['income_statement']['metrics']['Revenues']
            growth_analysis['revenue_growth_trend']['total_revenue'] = self._calculate_trend_analysis(revenue_data)
        
        # Analyze segment revenue trends from Income Statement
        if financial_data['income_statement'].get('metrics'):
            is_metrics = financial_data['income_statement']['metrics']
            for segment in ['iPhone', 'iPad', 'Mac', 'Services', 'Wearables, Home and Accessories']:
                if segment in is_metrics:
                    segment_key = segment.lower().replace(" ", "_").replace(",", "")
                    growth_analysis['revenue_growth_trend'][f'{segment_key}_trend'] = self._calculate_trend_analysis(is_metrics[segment])
        
        # Analyze profitability trends from Income Statement
        if financial_data['income_statement'].get('metrics'):
            is_metrics = financial_data['income_statement']['metrics']
            if 'Gross Profit' in is_metrics:
                growth_analysis['profitability_trends']['gross_profit'] = self._calculate_trend_analysis(is_metrics['Gross Profit'])
            if 'Net Income' in is_metrics:
                growth_analysis['profitability_trends']['net_income'] = self._calculate_trend_analysis(is_metrics['Net Income'])
            if 'Operating Income' in is_metrics:
                growth_analysis['profitability_trends']['operating_income'] = self._calculate_trend_analysis(is_metrics['Operating Income'])
        
        # Supplement with margin trends from margin analysis
        if financial_data['margin_analysis'].get('metrics', {}).get('Gross Margin'):
            margin_data = financial_data['margin_analysis']['metrics']['Gross Margin']
            growth_analysis['margin_trends']['gross_margin'] = self._calculate_trend_analysis(margin_data)
        
        # Analyze cash flow trends
        if financial_data['cash_flow'].get('metrics'):
            cf_metrics = financial_data['cash_flow']['metrics']
            if 'Operating Cash Flow' in cf_metrics:
                growth_analysis['cash_flow_trends']['operating_cash_flow'] = self._calculate_trend_analysis(cf_metrics['Operating Cash Flow'])
            if 'Net Income / (Loss)' in cf_metrics:
                growth_analysis['cash_flow_trends']['net_income_cf'] = self._calculate_trend_analysis(cf_metrics['Net Income / (Loss)'])
        
        return growth_analysis
    
    def _calculate_trend_analysis(self, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trend analysis for a specific metric."""
        if not metric_data:
            return {}
        
        periods = sorted(metric_data.keys())
        values = []
        
        for period in periods:
            if isinstance(metric_data[period], dict) and 'value' in metric_data[period]:
                values.append(metric_data[period]['value'])
        
        if len(values) < 2:
            return {'trend': 'insufficient_data'}
        
        # Simple trend analysis
        recent_avg = sum(values[-3:]) / len(values[-3:]) if len(values) >= 3 else values[-1]
        earlier_avg = sum(values[:3]) / len(values[:3]) if len(values) >= 3 else values[0]
        
        trend_direction = 'improving' if recent_avg > earlier_avg else 'declining'
        trend_magnitude = abs(recent_avg - earlier_avg)
        
        return {
            'trend': trend_direction,
            'magnitude': trend_magnitude,
            'recent_average': recent_avg,
            'earlier_average': earlier_avg,
            'latest_value': values[-1],
            'data_points': len(values)
        }
    
    def _analyze_segments(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business segments (particularly for Apple)."""
        segment_analysis = {}
        
        # Analyze Apple's key product segments
        segments = ['iPhone', 'iPad', 'Mac', 'Wearables, Home and Accessories', 'Services']
        
        for segment in segments:
            segment_key = segment.lower().replace(' ', '_').replace(',', '')
            segment_info = {
                'name': segment,
                'revenue_data': {},
                'margin_data': {},
                'trends': {}
            }
            
            # Get revenue data from Income Statement (primary source)
            if financial_data['income_statement'].get('metrics', {}).get(segment):
                is_segment_data = financial_data['income_statement']['metrics'][segment]
                segment_info['revenue_data'] = is_segment_data
                segment_info['trends']['revenue_trend'] = self._calculate_trend_analysis(is_segment_data)
            
            # Get margin data from margin analysis
            if financial_data['margin_analysis'].get('metrics', {}).get(segment):
                ma_segment_data = financial_data['margin_analysis']['metrics'][segment]
                segment_info['margin_data'] = ma_segment_data
                segment_info['trends']['margin_trend'] = self._calculate_trend_analysis(ma_segment_data)
            
            # Only add to analysis if we have data for this segment
            if segment_info['revenue_data'] or segment_info['margin_data']:
                segment_analysis[segment_key] = segment_info
        
        return segment_analysis

def create_standalone_parser(data_root_path: str):
    """Factory function to create the standalone enhanced financial parser."""
    return StandaloneEnhancedSVGParser(data_root_path)
