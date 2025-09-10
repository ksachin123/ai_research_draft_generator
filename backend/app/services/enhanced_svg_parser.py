"""
Enhanced SVG Financial Parser Service - App Integration

This service integrates with the standalone enhanced parser to provide
financial data for the knowledge base.
"""

import os
import sys
from datetime import datetime
from typing import Optional

# Add the backend directory to access standalone parser
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_dir)

from standalone_enhanced_parser import create_standalone_parser

class EnhancedSVGFinancialParser:
    """App-level wrapper for the enhanced financial parser."""

    def __init__(self, config):
        self.config = config
        self.parser = create_standalone_parser(config.DATA_ROOT_PATH)
        
    def parse_financial_statements(self, ticker: str):
        """Parse financial statements using the standalone parser."""
        return self.parser.parse_financial_statements(ticker)
    
    def get_current_quarter_estimates(self, ticker: str, target_date: Optional[datetime] = None):
        """Get current quarter estimates for a ticker."""
        return self.parser.extract_current_quarter_estimates(
            self.parser.parse_financial_statements(ticker), target_date
        )
    
    def get_current_quarter_estimates_for_ai(self, ticker: str, target_date: Optional[datetime] = None):
        """Get current quarter estimates formatted for AI prompts."""
        return self.parser.get_current_quarter_estimates_for_ai(ticker, target_date)

def create_enhanced_financial_parser(config):
    """Factory function to create the enhanced financial parser."""
    return EnhancedSVGFinancialParser(config)
