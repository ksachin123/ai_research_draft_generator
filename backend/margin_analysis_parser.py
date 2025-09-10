#!/usr/bin/env python3
"""
MarginAnalysis.svg Parser

This module provides functionality to parse Apple's Margin Analysis SVG files
and extract financial margin data into structured JSON format.
"""

import xml.etree.ElementTree as ET
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


class MarginAnalysisSVGParser:
    """Parser for Apple Margin Analysis SVG files."""
    
    def __init__(self):
        self.periods = []
        self.metrics = {}
        self.parsed_data = {}
    
    def parse_svg_to_json(self, svg_file_path: str) -> Dict[str, Any]:
        """
        Parse MarginAnalysis SVG file and return structured JSON data.
        
        Args:
            svg_file_path (str): Path to the MarginAnalysis SVG file
            
        Returns:
            Dict[str, Any]: Structured financial data with periods, metrics, and analysis
        """
        try:
            # Parse the SVG file
            tree = ET.parse(svg_file_path)
            root = tree.getroot()
            
            # Extract text elements
            text_elements = self._extract_text_elements(root)
            
            # Parse periods and metrics
            self._parse_periods(text_elements)
            self._parse_metrics(text_elements)
            
            # Build structured data
            self.parsed_data = {
                "document_type": "margin_analysis",
                "company": "AAPL",
                "parsed_date": datetime.now().isoformat(),
                "periods": self.periods,
                "metrics": self.metrics,
                "analysis": self._generate_analysis()
            }
            
            return self.parsed_data
            
        except Exception as e:
            print(f"Error parsing MarginAnalysis SVG: {str(e)}")
            return {}
    
    def _extract_text_elements(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract all text elements with their positions and content."""
        text_elements = []
        
        # Define namespace
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Find all text elements
        for text_elem in root.findall('.//svg:text', ns):
            transform = text_elem.get('transform', '')
            
            # Extract position from transform matrix
            x_pos, y_pos = self._extract_position(transform)
            
            # Get text content
            tspan = text_elem.find('.//svg:tspan', ns)
            if tspan is not None and tspan.text:
                text_content = tspan.text.strip()
                
                if text_content:  # Only add non-empty text
                    text_elements.append({
                        'text': text_content,
                        'x': x_pos,
                        'y': y_pos,
                        'transform': transform
                    })
        
        # Sort by y-position (top to bottom), then x-position (left to right)
        text_elements.sort(key=lambda x: (-x['y'], x['x']))
        
        return text_elements
    
    def _extract_position(self, transform: str) -> tuple:
        """Extract x, y position from SVG transform matrix."""
        # Look for matrix(1,0,0,-1,x,y) pattern
        matrix_match = re.search(r'matrix\(1,0,0,-1,([0-9.]+),([0-9.]+)\)', transform)
        if matrix_match:
            x = float(matrix_match.group(1))
            y = float(matrix_match.group(2))
            return x, y
        return 0, 0
    
    def _parse_periods(self, text_elements: List[Dict[str, Any]]) -> None:
        """Parse time periods from text elements."""
        period_patterns = [
            r'^(Dec|Mar|Jun|Sep)-\d{2}$',  # Quarterly: Dec-24, Mar-25, etc.
            r'^\d{4}[AE]$'  # Annual: 2023A, 2024A, 2025E, etc.
        ]
        
        periods = []
        
        for elem in text_elements:
            text = elem['text']
            for pattern in period_patterns:
                if re.match(pattern, text):
                    periods.append({
                        'period': text,
                        'x': elem['x'],
                        'y': elem['y']
                    })
        
        # Sort periods by x-position to get chronological order
        periods.sort(key=lambda x: x['x'])
        
        self.periods = [p['period'] for p in periods]
    
    def _parse_metrics(self, text_elements: List[Dict[str, Any]]) -> None:
        """Parse margin metrics and their values."""
        
        # Define key margin metrics to look for
        margin_metrics = [
            'Revenue',
            'iPhone', 
            'iPad',
            'Mac',
            'Wearables, Home and Accessories',
            'Services',
            'Gross Margin',
            'ModelWare EPS',
            'Sequential Growth (%)'
        ]
        
        # Group text elements by approximate y-position (rows)
        rows = self._group_by_rows(text_elements)
        
        for row in rows:
            # Check if this row contains a metric label
            metric_name = None
            for elem in row:
                text = elem['text']
                if any(metric in text for metric in margin_metrics):
                    metric_name = text
                    break
            
            if metric_name:
                # Extract values for this metric across periods
                values = self._extract_row_values(row, metric_name)
                if values:
                    self.metrics[metric_name] = values
    
    def _group_by_rows(self, text_elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group text elements by approximate y-position (rows)."""
        if not text_elements:
            return []
        
        # Sort by y-position
        sorted_elements = sorted(text_elements, key=lambda x: -x['y'])  # Top to bottom
        
        rows = []
        current_row = [sorted_elements[0]]
        current_y = sorted_elements[0]['y']
        
        for elem in sorted_elements[1:]:
            # If y-position is close to current row, add to current row
            if abs(elem['y'] - current_y) < 5:  # Tolerance for same row
                current_row.append(elem)
            else:
                # Start new row
                if current_row:
                    # Sort current row by x-position (left to right)
                    current_row.sort(key=lambda x: x['x'])
                    rows.append(current_row)
                current_row = [elem]
                current_y = elem['y']
        
        # Add last row
        if current_row:
            current_row.sort(key=lambda x: x['x'])
            rows.append(current_row)
        
        return rows
    
    def _extract_row_values(self, row: List[Dict[str, Any]], metric_name: str) -> Dict[str, Any]:
        """Extract values for a metric across all periods in a row."""
        values = {}
        
        # Skip the first element (metric name)
        value_elements = row[1:]  
        
        # Use only as many periods as we have values to avoid index issues
        available_periods = self.periods[:len(value_elements)]
        
        # Match values to periods
        for i, period in enumerate(available_periods):
            if i < len(value_elements):
                raw_value = value_elements[i]['text']
                parsed_value = self._parse_numeric_value(raw_value)
                values[period] = {
                    'raw': raw_value,
                    'value': parsed_value
                }
        
        return values
    
    def _parse_numeric_value(self, text: str) -> Optional[float]:
        """Parse numeric values from text, handling percentages and negatives."""
        if not text or text == '-':
            return None
        
        # Remove common non-numeric characters but keep decimal points, commas, negative signs, percentages
        cleaned = re.sub(r'[^\d.,\-+%]', '', text)
        
        if not cleaned:
            return None
        
        try:
            # Handle percentage values
            if '%' in text:
                numeric_part = cleaned.replace('%', '')
                return float(numeric_part)
            
            # Handle regular numbers (remove commas)
            numeric_part = cleaned.replace(',', '')
            return float(numeric_part)
            
        except ValueError:
            return None
    
    def _generate_analysis(self) -> Dict[str, Any]:
        """Generate analysis insights from the parsed data."""
        analysis = {
            "summary": {
                "total_periods": len(self.periods),
                "total_metrics": len(self.metrics),
                "data_types": ["margins", "growth_rates", "sequential_changes"]
            },
            "insights": []
        }
        
        # Add period-specific insights
        if self.periods:
            analysis["period_range"] = {
                "start": self.periods[0] if self.periods else None,
                "end": self.periods[-1] if self.periods else None
            }
        
        # Add margin-specific insights
        if "Gross Margin" in self.metrics:
            gross_margin_data = self.metrics["Gross Margin"]
            latest_values = []
            for period in self.periods[-3:]:  # Last 3 periods
                if period in gross_margin_data and gross_margin_data[period]['value'] is not None:
                    latest_values.append(gross_margin_data[period]['value'])
            
            if len(latest_values) >= 2:
                trend = "improving" if latest_values[-1] > latest_values[0] else "declining"
                analysis["insights"].append(f"Gross margin is {trend} in recent periods")
        
        return analysis
    
    def get_metric_value(self, metric_name: str, period: str) -> Optional[float]:
        """Get a specific metric value for a specific period."""
        if metric_name in self.metrics and period in self.metrics[metric_name]:
            return self.metrics[metric_name][period]['value']
        return None
    
    def compare_periods(self, metric_name: str, period1: str, period2: str) -> Optional[Dict[str, Any]]:
        """Compare a metric between two periods."""
        val1 = self.get_metric_value(metric_name, period1)
        val2 = self.get_metric_value(metric_name, period2)
        
        if val1 is not None and val2 is not None:
            change = val2 - val1
            pct_change = (change / val1) * 100 if val1 != 0 else None
            
            return {
                "metric": metric_name,
                "period1": period1,
                "period2": period2,
                "value1": val1,
                "value2": val2,
                "absolute_change": change,
                "percent_change": pct_change
            }
        return None
    
    def save_to_json(self, output_file: str) -> bool:
        """Save parsed data to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.parsed_data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving to JSON: {str(e)}")
            return False


def main():
    """Test the MarginAnalysis parser with sample file."""
    parser = MarginAnalysisSVGParser()
    
    # Test with Apple's MarginAnalysis SVG
    svg_file = "/Users/sachin/code/github/ai_research_draft_generator/data/research/AAPL/estimates/MarginAnalysis.svg"
    
    print("Parsing MarginAnalysis SVG...")
    parsed_data = parser.parse_svg_to_json(svg_file)
    
    if parsed_data:
        print(f"\n✅ Successfully parsed MarginAnalysis data!")
        print(f"📊 Found {len(parsed_data.get('periods', []))} periods")
        print(f"📈 Found {len(parsed_data.get('metrics', {}))} metrics")
        
        # Show sample data
        if parsed_data.get('periods'):
            print(f"\n📅 Periods: {', '.join(parsed_data['periods'][:5])}{'...' if len(parsed_data['periods']) > 5 else ''}")
        
        if parsed_data.get('metrics'):
            print(f"\n📊 Metrics:")
            for metric_name in list(parsed_data['metrics'].keys())[:5]:
                print(f"   • {metric_name}")
            if len(parsed_data['metrics']) > 5:
                print(f"   • ... and {len(parsed_data['metrics']) - 5} more")
        
        # Save to JSON
        output_file = "MarginAnalysis_parsed.json"
        if parser.save_to_json(output_file):
            print(f"\n💾 Data saved to {output_file}")
        
        # Show some sample analysis
        print("\n🔍 Sample Analysis:")
        if "Gross Margin" in parsed_data.get('metrics', {}):
            gross_margin = parsed_data['metrics']['Gross Margin']
            if gross_margin and parsed_data.get('periods'):
                latest_period = parsed_data['periods'][-1]
                if latest_period in gross_margin:
                    latest_value = gross_margin[latest_period]['value']
                    print(f"   • Latest Gross Margin ({latest_period}): {latest_value}%")
        
        # Compare periods if we have enough data
        if len(parsed_data.get('periods', [])) >= 2 and "Revenue" in parsed_data.get('metrics', {}):
            period1 = parsed_data['periods'][0]
            period2 = parsed_data['periods'][-1]
            comparison = parser.compare_periods("Revenue", period1, period2)
            if comparison and comparison['percent_change']:
                print(f"   • Revenue change {period1}→{period2}: {comparison['percent_change']:.1f}%")
    
    else:
        print("❌ Failed to parse MarginAnalysis data")


if __name__ == "__main__":
    main()
