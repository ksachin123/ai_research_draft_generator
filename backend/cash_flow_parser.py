#!/usr/bin/env python3
"""
Cash Flow SVG Parser for Apple Financial Data

This module provides functionality to parse Apple's Cash Flow Statement data from SVG files
and convert it into structured JSON format for analysis and reporting.

Based on the successful Income Statement parser pattern.
"""

import xml.etree.ElementTree as ET
import re
from datetime import datetime
import json


class CashFlowSVGParser:
    """Parser for Cash Flow Statement SVG files to extract financial data."""
    
    def __init__(self):
        self.debug = False
    
    def set_debug(self, debug=True):
        """Enable or disable debug output."""
        self.debug = debug
    
    def parse_svg_to_json(self, svg_file_path):
        """
        Parse Cash Flow SVG file and extract financial data.
        
        Args:
            svg_file_path (str): Path to the Cash Flow SVG file
            
        Returns:
            dict: Structured financial data with periods, metrics, and analysis
        """
        try:
            tree = ET.parse(svg_file_path)
            root = tree.getroot()
            
            # Extract text elements
            text_elements = []
            for text in root.findall('.//{http://www.w3.org/2000/svg}text'):
                tspan = text.find('.//{http://www.w3.org/2000/svg}tspan')
                if tspan is not None and tspan.text:
                    # Extract position from transform matrix
                    transform = text.get('transform', '')
                    x, y = self._extract_position(transform)
                    text_elements.append({
                        'text': tspan.text.strip(),
                        'x': x,
                        'y': y
                    })
            
            if self.debug:
                print(f"Found {len(text_elements)} text elements")
                for elem in text_elements[:20]:  # Show first 20 for debugging
                    print(f"  {elem}")
            
            # Group elements by vertical position (y-coordinate) for rows
            rows = self._group_by_rows(text_elements)
            
            # Extract periods (dates) and metrics
            periods = self._extract_periods(rows)
            metrics = self._extract_metrics(rows, periods)
            
            # Build structured data
            result = {
                'statement_type': 'Cash Flow Statement',
                'company': 'Apple Inc. (AAPL)',
                'periods': periods,
                'total_periods': len(periods),
                'metrics': metrics,
                'total_metrics': len(metrics),
                'parsed_at': datetime.now().isoformat(),
                'source_file': svg_file_path
            }
            
            # Add comparative analysis
            result['analysis'] = self._generate_analysis(metrics, periods)
            
            return result
            
        except Exception as e:
            return {
                'error': f"Failed to parse SVG file: {str(e)}",
                'statement_type': 'Cash Flow Statement',
                'parsed_at': datetime.now().isoformat()
            }
    
    def _extract_position(self, transform_str):
        """Extract x, y coordinates from SVG transform matrix."""
        match = re.search(r'matrix\([^,]+,[^,]+,[^,]+,[^,]+,([^,]+),([^)]+)\)', transform_str)
        if match:
            try:
                x = float(match.group(1))
                y = float(match.group(2))
                return x, y
            except ValueError:
                pass
        return 0, 0
    
    def _group_by_rows(self, text_elements, tolerance=5):
        """Group text elements by row based on y-coordinate."""
        rows = {}
        for elem in text_elements:
            y = elem['y']
            # Find existing row within tolerance
            row_key = None
            for existing_y in rows.keys():
                if abs(y - existing_y) <= tolerance:
                    row_key = existing_y
                    break
            
            if row_key is None:
                row_key = y
                rows[row_key] = []
            
            rows[row_key].append(elem)
        
        # Sort elements within each row by x-coordinate
        for row in rows.values():
            row.sort(key=lambda x: x['x'])
        
        return dict(sorted(rows.items(), key=lambda x: -x[0]))  # Sort by y descending (top to bottom)
    
    def _extract_periods(self, rows):
        """Extract time periods from the data."""
        periods = []
        period_patterns = [
            r'Dec-\d{2}', r'Mar-\d{2}', r'Jun-\d{2}', r'Sep-\d{2}',  # Quarters
            r'\d{4}[AE]'  # Annual (A=Actual, E=Estimate)
        ]
        
        for y, row_elements in rows.items():
            for elem in row_elements:
                text = elem['text']
                for pattern in period_patterns:
                    if re.match(pattern, text):
                        if text not in periods:
                            periods.append(text)
        
        return periods
    
    def _extract_metrics(self, rows, periods):
        """Extract cash flow statement metrics and their values."""
        metrics = {}
        
        # Cash flow statement metric patterns
        operating_patterns = [
            'Net income', 'Adjustments to reconcile net income',
            'Depreciation & Amortization', 'Depreciation and amortization',
            'Stock based compensation expense', 'Stock-based compensation',
            'Deferred income tax expense', 'Changes in operating assets and liabilities',
            'Accounts receivable', 'Inventories', 'Accounts payable',
            'Other current assets', 'Other current liabilities',
            'Cash generated by operating activities', 'Net cash from operating activities'
        ]
        
        investing_patterns = [
            'Purchases of marketable securities', 'Proceeds from maturities of marketable securities',
            'Proceeds from sales of marketable securities', 'Payments for acquisition of property',
            'Payments made in connection with business acquisitions',
            'Purchase of non-marketable securities', 'Proceeds from non-marketable securities',
            'Cash used for investing activities', 'Net cash used in investing activities'
        ]
        
        financing_patterns = [
            'Proceeds from issuance of common stock', 'Payments for taxes related to net share settlement',
            'Payments for dividends and dividend equivalents', 'Repurchases of common stock',
            'Proceeds from issuance of term debt', 'Repayments of term debt',
            'Proceeds from/(Repayments of) commercial paper', 'Other financing activities',
            'Cash used for financing activities', 'Net cash used in financing activities'
        ]
        
        other_patterns = [
            'Net increase/(decrease) in cash', 'Cash and cash equivalents, beginning of period',
            'Cash and cash equivalents, end of period'
        ]
        
        all_patterns = operating_patterns + investing_patterns + financing_patterns + other_patterns
        
        for y, row_elements in rows.items():
            if len(row_elements) < 2:  # Need at least metric name and one value
                continue
            
            # First element is typically the metric name
            metric_name = row_elements[0]['text']
            
            # Check if this looks like a cash flow metric
            if (any(pattern.lower() in metric_name.lower() for pattern in all_patterns) or
                len(metric_name.split()) > 2):  # Multi-word descriptions are likely metrics
                
                values = {}
                
                # Extract numeric values from remaining elements
                for i, elem in enumerate(row_elements[1:], 1):
                    value_text = elem['text']
                    numeric_value = self._parse_numeric_value(value_text)
                    
                    if numeric_value is not None:
                        # Try to match with periods by position
                        if i <= len(periods):
                            period = periods[i-1] if i-1 < len(periods) else f"Col_{i}"
                            values[period] = numeric_value
                
                if values:  # Only add if we found numeric values
                    metrics[metric_name] = values
        
        return metrics
    
    def _parse_numeric_value(self, text):
        """Parse numeric value from text, handling commas, negatives, and different formats."""
        if not text or text in ['-', '—', 'n/a', 'N/A']:
            return None
        
        # Remove currency symbols, commas, and whitespace
        clean_text = re.sub(r'[\$,\s]', '', text)
        
        # Handle negative values in parentheses
        if clean_text.startswith('(') and clean_text.endswith(')'):
            clean_text = '-' + clean_text[1:-1]
        
        # Extract numeric value
        match = re.search(r'-?\d+\.?\d*', clean_text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        
        return None
    
    def _generate_analysis(self, metrics, periods):
        """Generate comparative analysis of cash flow data."""
        analysis = {
            'operating_activities': {},
            'investing_activities': {},
            'financing_activities': {},
            'cash_changes': {},
            'period_comparison': {}
        }
        
        # Categorize metrics
        for metric_name, values in metrics.items():
            metric_lower = metric_name.lower()
            
            if any(term in metric_lower for term in ['operating', 'net income', 'depreciation', 'stock based']):
                analysis['operating_activities'][metric_name] = values
            elif any(term in metric_lower for term in ['investing', 'marketable securities', 'acquisition', 'property']):
                analysis['investing_activities'][metric_name] = values
            elif any(term in metric_lower for term in ['financing', 'dividends', 'stock', 'debt', 'commercial paper']):
                analysis['financing_activities'][metric_name] = values
            elif any(term in metric_lower for term in ['cash and cash equivalents', 'net increase', 'net decrease']):
                analysis['cash_changes'][metric_name] = values
        
        # Calculate period comparisons if we have at least 2 periods
        if len(periods) >= 2:
            latest_period = periods[0] if periods else None
            previous_period = periods[1] if len(periods) > 1 else None
            
            if latest_period and previous_period:
                analysis['period_comparison'] = self._compare_periods(
                    metrics, latest_period, previous_period
                )
        
        # Add growth calculations
        for metric_name, values in metrics.items():
            if len(values) >= 2:
                periods_list = list(values.keys())
                if len(periods_list) >= 2:
                    latest_val = values[periods_list[0]]
                    previous_val = values[periods_list[1]]
                    
                    if previous_val and previous_val != 0:
                        growth_rate = ((latest_val - previous_val) / abs(previous_val)) * 100
                        
                        # Add to appropriate category
                        if metric_name in analysis['operating_activities']:
                            if 'growth_rates' not in analysis['operating_activities']:
                                analysis['operating_activities']['growth_rates'] = {}
                            analysis['operating_activities']['growth_rates'][f"{metric_name}_growth"] = round(growth_rate, 2)
        
        return analysis
    
    def _compare_periods(self, metrics, period1, period2):
        """Compare two periods for key metrics."""
        comparison = {}
        
        for metric_name, values in metrics.items():
            if period1 in values and period2 in values:
                val1 = values[period1]
                val2 = values[period2]
                
                if val2 != 0:
                    change = val1 - val2
                    pct_change = (change / abs(val2)) * 100
                    
                    comparison[metric_name] = {
                        f'{period1}_value': val1,
                        f'{period2}_value': val2,
                        'absolute_change': round(change, 2),
                        'percentage_change': round(pct_change, 2)
                    }
        
        return comparison
    
    def get_metric_value(self, data, metric_name, period):
        """Get specific metric value for a given period."""
        if 'metrics' not in data:
            return None
        
        # Try exact match first
        if metric_name in data['metrics']:
            return data['metrics'][metric_name].get(period)
        
        # Try partial match
        for key in data['metrics']:
            if metric_name.lower() in key.lower():
                return data['metrics'][key].get(period)
        
        return None
    
    def save_to_json(self, data, output_path):
        """Save parsed data to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Cash flow data saved to: {output_path}")


def main():
    """Example usage of the CashFlowSVGParser."""
    parser = CashFlowSVGParser()
    parser.set_debug(True)  # Enable debug output
    
    # Path to the Cash Flow SVG file
    svg_file = "/Users/sachin/code/github/ai_research_draft_generator/data/uploads/estimates_old/CashFlow.svg"
    
    # Parse the SVG file
    print("Parsing Cash Flow SVG file...")
    result = parser.parse_svg_to_json(svg_file)
    
    # Display results
    if 'error' in result:
        print(f"Error: {result['error']}")
        return
    
    print(f"\nSuccessfully parsed {result['statement_type']}")
    print(f"Company: {result['company']}")
    print(f"Periods found: {result['total_periods']}")
    print(f"Metrics extracted: {result['total_metrics']}")
    
    # Show some sample data
    print(f"\nPeriods: {result['periods'][:5]}...")  # First 5 periods
    
    print(f"\nSample metrics:")
    if isinstance(result.get('metrics'), dict):
        for i, (metric, values) in enumerate(result['metrics'].items()):
            if i >= 5:  # Show first 5 metrics
                break
            if isinstance(values, dict):
                print(f"  {metric}: {dict(list(values.items())[:3])}")  # First 3 values
    
    # Save to JSON file
    output_file = "/Users/sachin/code/github/ai_research_draft_generator/backend/CashFlow_parsed.json"
    parser.save_to_json(result, output_file)
    
    # Show some analysis
    if 'analysis' in result and isinstance(result.get('analysis'), dict):
        analysis = result['analysis']
        print(f"\nAnalysis Summary:")
        if isinstance(analysis, dict):
            print(f"  Operating activities: {len(analysis.get('operating_activities', {}))}")
            print(f"  Investing activities: {len(analysis.get('investing_activities', {}))}")
            print(f"  Financing activities: {len(analysis.get('financing_activities', {}))}")
            print(f"  Cash changes: {len(analysis.get('cash_changes', {}))}")
            
            period_comp = analysis.get('period_comparison', {})
            if period_comp and isinstance(period_comp, dict):
                print(f"  Period comparisons: {len(period_comp)}")
                for metric_name, comparison in list(period_comp.items())[:3]:
                    if isinstance(comparison, dict):
                        pct_change = comparison.get('percentage_change', 0)
                        print(f"    {metric_name}: {pct_change}% change")


if __name__ == "__main__":
    main()
