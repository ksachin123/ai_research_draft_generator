"""
Current Quarter Estimates Extractor

This service extracts only the first estimated values for the current quarter
from parsed financial statement data to be used in AI prompts for comparative analysis.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class CurrentQuarterEstimatesExtractor:
    """
    Extracts current quarter estimates from parsed financial data for AI prompt inclusion.
    """
    
    def __init__(self):
        self.current_quarter_estimates = {}
        
    def extract_current_quarter_estimates(self, financial_data: Dict[str, Any], target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Extract only the first estimated values for the current quarter from all financial statements.
        
        Args:
            financial_data: Parsed financial data from standalone enhanced parser
            target_date: Optional date to determine the quarter for (defaults to current date)
            
        Returns:
            Dict containing current quarter estimates formatted for AI prompts
        """
        try:
            current_quarter = self._determine_current_quarter(target_date)
            
            estimates = {
                'ticker': financial_data.get('ticker', 'Unknown'),
                'current_quarter': current_quarter,
                'target_date': (target_date or datetime.now()).strftime('%Y-%m-%d'),
                'estimate_date': datetime.now().strftime('%Y-%m-%d'),
                'income_statement_estimates': {},
                'balance_sheet_estimates': {},
                'cash_flow_estimates': {},
                'margin_analysis_estimates': {},
                'formatted_for_ai': ''
            }
            
            # Extract estimates from each statement type
            estimates['income_statement_estimates'] = self._extract_statement_estimates(
                financial_data.get('income_statement', {}), current_quarter, target_date
            )
            
            estimates['balance_sheet_estimates'] = self._extract_statement_estimates(
                financial_data.get('balance_sheet', {}), current_quarter, target_date
            )
            
            estimates['cash_flow_estimates'] = self._extract_statement_estimates(
                financial_data.get('cash_flow', {}), current_quarter, target_date
            )
            
            estimates['margin_analysis_estimates'] = self._extract_statement_estimates(
                financial_data.get('margin_analysis', {}), current_quarter, target_date
            )
            
            # Create formatted text for AI prompts
            estimates['formatted_for_ai'] = self._format_estimates_for_ai_prompt(estimates)
            
            return estimates
            
        except Exception as e:
            logger.error(f"Error extracting current quarter estimates: {str(e)}")
            return {}
    
    def _determine_current_quarter(self, target_date: Optional[datetime] = None) -> str:
        """
        Determine the current quarter based on the provided date or today's date.
        
        Args:
            target_date: Optional date to determine quarter for (defaults to current date)
        
        Returns:
            String representation of current quarter (e.g., 'Dec-25', 'Mar-26')
        """
        date_to_use = target_date or datetime.now()
        year = date_to_use.year
        month = date_to_use.month
        
        # Determine quarter based on Apple's fiscal year (ends in September)
        # Q1 (Oct-Dec), Q2 (Jan-Mar), Q3 (Apr-Jun), Q4 (Jul-Sep)
        if month in [10, 11, 12]:  # Q1
            quarter_end_month = "Dec"
            fiscal_year = year
        elif month in [1, 2, 3]:    # Q2  
            quarter_end_month = "Mar"
            fiscal_year = year
        elif month in [4, 5, 6]:    # Q3
            quarter_end_month = "Jun" 
            fiscal_year = year
        else:                       # Q4 (Jul, Aug, Sep)
            quarter_end_month = "Sep"
            fiscal_year = year
        
        # Format as shown in the data (e.g., "Dec-25")
        quarter = f"{quarter_end_month}-{str(fiscal_year)[-2:]}"
        logger.info(f"Determined current quarter as {quarter} for date {date_to_use.strftime('%Y-%m-%d')}") 
        return quarter
    
    def _extract_statement_estimates(self, statement_data: Dict[str, Any], 
                                   current_quarter: str, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Extract estimates for the current quarter from a specific financial statement.
        
        Args:
            statement_data: Parsed data from a financial statement
            current_quarter: Target quarter string (e.g., 'Dec-25')
            target_date: Optional date to determine if period is estimate (defaults to current date)
            
        Returns:
            Dict containing current quarter estimates for this statement
        """
        estimates = {}
        
        if not statement_data or 'metrics' not in statement_data:
            return estimates
        
        metrics = statement_data['metrics']
        
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, dict) and current_quarter in metric_data:
                quarter_data = metric_data[current_quarter]
                
                # Extract the estimated value
                if isinstance(quarter_data, dict):
                    estimates[metric_name] = {
                        'value': quarter_data.get('value'),
                        'raw': quarter_data.get('raw'),
                        'period': current_quarter,
                        'is_estimate': self._is_estimate_period(current_quarter, target_date)
                    }
                else:
                    estimates[metric_name] = {
                        'value': quarter_data,
                        'raw': str(quarter_data),
                        'period': current_quarter,
                        'is_estimate': self._is_estimate_period(current_quarter, target_date)
                    }
        
        return estimates
    
    def _is_estimate_period(self, period: str, target_date: Optional[datetime] = None) -> bool:
        """
        Determine if a period represents an estimate vs actual data.
        
        Args:
            period: Period string (e.g., 'Dec-25', '2025E')
            target_date: Optional date for comparison (defaults to current date)
            
        Returns:
            True if period represents an estimate
        """
        # Use provided date or current date for comparison
        comparison_date = target_date or datetime.now()
        current_year = comparison_date.year
        current_month = comparison_date.month
        
        # Check if period has 'E' for estimate
        if period.endswith('E'):
            return True
        
        # Parse quarterly periods (e.g., 'Dec-25')
        quarter_match = re.match(r'([A-Za-z]{3})-(\d{2})', period)
        if quarter_match:
            month_abbr = quarter_match.group(1)
            year_suffix = quarter_match.group(2)
            full_year = 2000 + int(year_suffix)
            
            # Convert month abbreviation to number
            month_map = {
                'Dec': 12, 'Mar': 3, 'Jun': 6, 'Sep': 9
            }
            period_month = month_map.get(month_abbr)
            
            if period_month:
                # If the period is in the future, it's an estimate
                period_date = datetime(full_year, period_month, 1)
                return period_date > comparison_date
        
        return False
    
    def _format_estimates_for_ai_prompt(self, estimates: Dict[str, Any]) -> str:
        """
        Format the extracted estimates into a clear text format for AI prompts.
        
        Args:
            estimates: Extracted estimates data
            
        Returns:
            Formatted string for inclusion in AI prompts
        """
        ticker = estimates.get('ticker', 'Unknown')
        current_quarter = estimates.get('current_quarter', 'Unknown')
        
        prompt_text = f"""
CURRENT QUARTER ANALYST ESTIMATES FOR {ticker}
Quarter: {current_quarter}
Target Date: {estimates.get('target_date', 'Unknown')}
Generated on: {estimates.get('estimate_date', 'Unknown')}

Please use these current analyst estimates to compare against the actual numbers reported in the uploaded document:

"""
        
        # Format Income Statement estimates
        if estimates.get('income_statement_estimates'):
            prompt_text += "\n--- INCOME STATEMENT ESTIMATES ---\n"
            for metric, data in estimates['income_statement_estimates'].items():
                value = data.get('raw', data.get('value', 'N/A'))
                prompt_text += f"• {metric}: {value}\n"
        
        # Format Balance Sheet estimates
        if estimates.get('balance_sheet_estimates'):
            prompt_text += "\n--- BALANCE SHEET ESTIMATES ---\n"
            for metric, data in estimates['balance_sheet_estimates'].items():
                value = data.get('raw', data.get('value', 'N/A'))
                prompt_text += f"• {metric}: {value}\n"
        
        # Format Cash Flow estimates
        if estimates.get('cash_flow_estimates'):
            prompt_text += "\n--- CASH FLOW ESTIMATES ---\n"
            for metric, data in estimates['cash_flow_estimates'].items():
                value = data.get('raw', data.get('value', 'N/A'))
                prompt_text += f"• {metric}: {value}\n"
        
        # Format Margin Analysis estimates
        if estimates.get('margin_analysis_estimates'):
            prompt_text += "\n--- MARGIN ANALYSIS ESTIMATES ---\n"
            for metric, data in estimates['margin_analysis_estimates'].items():
                value = data.get('raw', data.get('value', 'N/A'))
                prompt_text += f"• {metric}: {value}\n"
        
        prompt_text += """
ANALYSIS INSTRUCTIONS:
1. Compare the actual numbers from the uploaded document against these estimates
2. Calculate the variance (actual vs estimate) for each metric
3. Identify significant beats or misses (>5% variance)
4. Provide insights on what the variances might indicate about company performance
5. Consider the impact on future quarters and overall financial health
"""
        
        return prompt_text.strip()

    def get_estimates_summary(self, estimates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of the extracted estimates for quick reference.
        
        Args:
            estimates: Extracted estimates data
            
        Returns:
            Summary dict with key metrics and counts
        """
        summary = {
            'ticker': estimates.get('ticker'),
            'current_quarter': estimates.get('current_quarter'),
            'total_estimates': 0,
            'statements_with_estimates': [],
            'key_revenue_estimates': {},
            'key_profit_estimates': {},
            'key_margin_estimates': {}
        }
        
        # Count estimates by statement type
        for statement_type in ['income_statement', 'balance_sheet', 'cash_flow', 'margin_analysis']:
            statement_estimates = estimates.get(f'{statement_type}_estimates', {})
            if statement_estimates:
                summary['statements_with_estimates'].append(statement_type)
                summary['total_estimates'] += len(statement_estimates)
        
        # Extract key metrics for summary
        income_estimates = estimates.get('income_statement_estimates', {})
        margin_estimates = estimates.get('margin_analysis_estimates', {})
        
        # Key revenue metrics
        revenue_keys = ['Revenues', 'iPhone', 'iPad', 'Mac', 'Services', 'Wearables, Home and Accessories']
        for key in revenue_keys:
            if key in income_estimates:
                summary['key_revenue_estimates'][key] = income_estimates[key].get('raw')
        
        # Key profit metrics  
        profit_keys = ['Gross Profit', 'Operating Income', 'Net Income']
        for key in profit_keys:
            if key in income_estimates:
                summary['key_profit_estimates'][key] = income_estimates[key].get('raw')
        
        # Key margin metrics
        margin_keys = ['Gross Margin', 'iPhone', 'Services']
        for key in margin_keys:
            if key in margin_estimates:
                summary['key_margin_estimates'][key] = margin_estimates[key].get('raw')
        
        return summary


def create_estimates_extractor():
    """Factory function to create the estimates extractor."""
    return CurrentQuarterEstimatesExtractor()
