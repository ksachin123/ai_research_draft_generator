"""
Income Statement SVG Parser for Financial Reports

This module provides functionality to parse Apple's Income Statement SVG files
containing quarterly and annual financial data.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime


class IncomeStatementSVGParser:
    """
    Parser for Apple's Income Statement SVG files containing quarterly financial data.
    Extracts revenue, expenses, profit metrics, and EPS data.
    """
    
    def __init__(self):
        self.parsed_data = {}
        
    def parse_svg_to_json(self, svg_file_path: str) -> Dict[str, Any]:
        """
        Parse the SVG file and convert to structured JSON format.
        
        Args:
            svg_file_path: Path to the Income Statement SVG file
        
        Returns:
            Dict containing parsed financial data with periods, metrics, and analysis
        """
        try:
            tree = ET.parse(svg_file_path)
            root = tree.getroot()
            text_elements = self._extract_text_elements(root)
            periods, metrics_data = self._parse_text_elements(text_elements)
            structured_data = self._create_structured_json(periods, metrics_data)
            self.parsed_data = structured_data
            return structured_data
        except Exception as e:
            raise Exception(f"Error parsing Income Statement SVG file: {str(e)}")
    
    def _extract_text_elements(self, root: ET.Element) -> List[Tuple[str, float, float]]:
        """Extract all text elements with their positions from the SVG."""
        text_elements = []
        for text_elem in root.findall('.//{http://www.w3.org/2000/svg}text'):
            text_content = ""
            tspan_elements = text_elem.findall('.//{http://www.w3.org/2000/svg}tspan')
            if tspan_elements:
                for tspan in tspan_elements:
                    if tspan.text:
                        text_content += tspan.text.strip()
            else:
                if text_elem.text:
                    text_content = text_elem.text.strip()
            
            if text_content:
                x_pos, y_pos = self._extract_position(text_elem)
                text_elements.append((text_content, x_pos, y_pos))
        
        # Sort by y-position (descending) then x-position
        text_elements.sort(key=lambda x: (-x[2], x[1]))
        return text_elements
    
    def _extract_position(self, text_elem: ET.Element) -> Tuple[float, float]:
        """Extract x,y position from SVG transform attributes."""
        transform = text_elem.get('transform', '')
        
        # Check for matrix transform
        matrix_match = re.search(r'matrix\([^,]+,[^,]+,[^,]+,[^,]+,([^,]+),([^)]+)\)', transform)
        if matrix_match:
            x_pos = float(matrix_match.group(1))
            y_pos = float(matrix_match.group(2))
            return x_pos, y_pos
        
        # Check for translate transform
        translate_match = re.search(r'translate\(([^,]+),([^)]+)\)', transform)
        if translate_match:
            x_pos = float(translate_match.group(1))
            y_pos = float(translate_match.group(2))
            return x_pos, y_pos
        
        return 0.0, 0.0
    
    def _parse_text_elements(self, text_elements: List[Tuple[str, float, float]]) -> Tuple[List[str], Dict[str, List[Any]]]:
        """Parse text elements to identify periods and extract metric data."""
        periods = []
        metrics_data = {}
        current_metric = None
        
        # Group elements by y-position (rows)
        y_groups = self._group_by_y_position(text_elements)
        
        for y_pos in sorted(y_groups.keys(), reverse=True):
            row_elements = sorted(y_groups[y_pos], key=lambda x: x[1])
            
            # Check if this row contains period headers
            if self._is_period_header_row(row_elements):
                periods = self._extract_periods(row_elements)
                continue
            
            # Extract metric name and values
            metric_name = self._extract_metric_name(row_elements)
            if metric_name:
                current_metric = metric_name
                values = self._extract_metric_values(row_elements)
                if values:
                    metrics_data[current_metric] = values
        
        return periods, metrics_data
    
    def _group_by_y_position(self, text_elements: List[Tuple[str, float, float]], tolerance: float = 5.0) -> Dict[float, List[Tuple[str, float, float]]]:
        """Group text elements by similar y-position to identify rows."""
        groups = {}
        for text, x_pos, y_pos in text_elements:
            found_group = False
            for existing_y in groups.keys():
                if abs(y_pos - existing_y) <= tolerance:
                    groups[existing_y].append((text, x_pos, y_pos))
                    found_group = True
                    break
            
            if not found_group:
                groups[y_pos] = [(text, x_pos, y_pos)]
        
        return groups
    
    def _is_period_header_row(self, row_elements: List[Tuple[str, float, float]]) -> bool:
        """Check if a row contains period headers (quarters/years)."""
        period_patterns = [
            r'(Dec|Mar|Jun|Sep)-\d{2}',  # Dec-23, Mar-24, etc.
            r'FY\d{4}[AE]?',             # FY2024A, FY2025E
            r'20\d{2}[AE]',              # 2024A, 2025E
            r'Calendar',
            r'Fiscal'
        ]
        
        for text, _, _ in row_elements:
            for pattern in period_patterns:
                if re.search(pattern, text):
                    return True
        return False
    
    def _extract_periods(self, row_elements: List[Tuple[str, float, float]]) -> List[str]:
        """Extract period identifiers from header row."""
        periods = []
        period_patterns = [
            r'(Dec|Mar|Jun|Sep)-\d{2}',
            r'FY\d{4}[AE]?',
            r'20\d{2}[AE]',
        ]
        
        for text, _, _ in row_elements:
            # Try specific patterns first
            for pattern in period_patterns:
                match = re.search(pattern, text)
                if match:
                    periods.append(match.group(0))
                    break
            else:
                # Check for other period indicators
                if any(keyword in text.lower() for keyword in ['calendar', 'fiscal', 'quarter', 'q1', 'q2', 'q3', 'q4']):
                    periods.append(text)
        
        return periods
    
    def _extract_metric_name(self, row_elements: List[Tuple[str, float, float]]) -> Optional[str]:
        """Extract metric name from the leftmost element of a row."""
        if not row_elements:
            return None
        
        leftmost_element = min(row_elements, key=lambda x: x[1])
        text = leftmost_element[0]
        
        # Income Statement specific indicators
        metric_indicators = [
            'revenue', 'income', 'expense', 'profit', 'loss', 'margin',
            'iphone', 'ipad', 'mac', 'services', 'wearables',
            'eps', 'shares', 'dividend', 'gross', 'operating', 'net',
            'cost', 'research', 'development', 'sales', 'marketing',
            'fully-diluted', 'payment', 'outstanding', 'basic',
            'other products', 'tax', 'provision', 'ebitda'
        ]
        
        text_lower = text.lower()
        if any(indicator in text_lower for indicator in metric_indicators):
            return text
        
        # Skip if it looks like a value (has $ or % or numbers)
        if re.search(r'[\$%]|\d+[,.]?\d*|\([^)]*\)', text):
            return None
        
        # Accept if it's a reasonable length and doesn't contain numbers
        if len(text) > 5 and not re.search(r'\d', text):
            return text
        
        return None
    
    def _extract_metric_values(self, row_elements: List[Tuple[str, float, float]]) -> List[Any]:
        """Extract numeric values from a metric row."""
        values = []
        if len(row_elements) <= 1:
            return values
        
        # Skip the first element (metric name) and process the rest
        sorted_elements = sorted(row_elements, key=lambda x: x[1])[1:]
        
        for text, _, _ in sorted_elements:
            cleaned_value = self._clean_financial_value(text)
            if cleaned_value is not None:
                values.append(cleaned_value)
        
        return values
    
    def _clean_financial_value(self, text: str) -> Any:
        """Clean and convert financial text to appropriate numeric type."""
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Handle N/A values
        if text.lower() in ['n/a', 'na', '-', '--']:
            return None
        
        # Handle percentages
        if '%' in text:
            try:
                number = re.search(r'[-+]?\d*\.?\d+', text)
                if number:
                    return float(number.group(0))
            except:
                pass
        
        # Handle dollar amounts
        if '$' in text:
            try:
                cleaned = re.sub(r'[$,]', '', text)
                if '(' in cleaned and ')' in cleaned:
                    # Negative values in parentheses
                    number = re.search(r'\d*\.?\d+', cleaned)
                    if number:
                        return -float(number.group(0))
                else:
                    number = re.search(r'[-+]?\d*\.?\d+', cleaned)
                    if number:
                        return float(number.group(0))
            except:
                pass
        
        # Handle plain numbers (with potential parentheses for negatives)
        try:
            cleaned = text.replace(',', '')
            if '(' in cleaned and ')' in cleaned:
                number = re.search(r'\d*\.?\d+', cleaned)
                if number:
                    return -float(number.group(0))
            else:
                number = re.search(r'[-+]?\d*\.?\d+', cleaned)
                if number:
                    value = float(number.group(0))
                    return int(value) if value.is_integer() else value
        except:
            pass
        
        # Return as string if can't parse as number
        return text
    
    def _create_structured_json(self, periods: List[str], metrics_data: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Create the final structured JSON output with analysis."""
        structured_data = {
            "company": "AAPL",
            "statement_type": "Income Statement",
            "parse_timestamp": datetime.now().isoformat(),
            "periods": periods,
            "metrics": {},
            "analysis": {
                "revenue_metrics": [],
                "profitability_metrics": [],
                "per_share_metrics": [],
                "segment_analysis": {}
            }
        }
        
        # Map metrics to periods
        for metric_name, values in metrics_data.items():
            structured_data["metrics"][metric_name] = {}
            for i, value in enumerate(values):
                if i < len(periods):
                    structured_data["metrics"][metric_name][periods[i]] = value
        
        # Generate analysis insights
        self._generate_analysis_insights(structured_data)
        
        return structured_data
    
    def _generate_analysis_insights(self, data: Dict[str, Any]) -> None:
        """Generate analysis insights for Income Statement data."""
        metrics = data["metrics"]
        analysis = data["analysis"]
        
        # Identify revenue metrics
        for metric_name in metrics.keys():
            metric_lower = metric_name.lower()
            if any(term in metric_lower for term in ['revenue', 'iphone', 'ipad', 'mac', 'services', 'wearables']):
                analysis["revenue_metrics"].append(metric_name)
            elif any(term in metric_lower for term in ['income', 'profit', 'margin', 'ebitda']):
                analysis["profitability_metrics"].append(metric_name)
            elif any(term in metric_lower for term in ['eps', 'shares', 'dividend']):
                analysis["per_share_metrics"].append(metric_name)
        
        # Segment analysis for Apple's main product categories
        segments = ['iPhone', 'iPad', 'Mac', 'Services', 'Wearables']
        for segment in segments:
            for metric_name in metrics.keys():
                if segment.lower() in metric_name.lower():
                    if segment not in analysis["segment_analysis"]:
                        analysis["segment_analysis"][segment] = []
                    analysis["segment_analysis"][segment].append(metric_name)
    
    def get_metric_value(self, metric_name: str, period: str) -> Any:
        """Get a specific metric value for a given period."""
        if not self.parsed_data:
            raise Exception("Data not parsed yet. Call parse_svg_to_json() first.")
        
        metrics = self.parsed_data.get("metrics", {})
        if metric_name in metrics and period in metrics[metric_name]:
            return metrics[metric_name][period]
        
        return None
    
    def compare_periods(self, metric_name: str, period1: str, period2: str) -> Dict[str, Any]:
        """Compare a metric between two periods."""
        value1 = self.get_metric_value(metric_name, period1)
        value2 = self.get_metric_value(metric_name, period2)
        
        if value1 is None or value2 is None:
            return {
                "metric": metric_name,
                "period1": period1,
                "period2": period2,
                "value1": value1,
                "value2": value2,
                "difference": None,
                "percentage_change": None,
                "error": "One or both values are missing"
            }
        
        try:
            val1 = float(value1)
            val2 = float(value2)
            
            difference = val2 - val1
            percentage_change = (difference / val1 * 100) if val1 != 0 else None
            
            return {
                "metric": metric_name,
                "period1": period1,
                "period2": period2,
                "value1": value1,
                "value2": value2,
                "difference": difference,
                "percentage_change": percentage_change
            }
        except (ValueError, TypeError):
            return {
                "metric": metric_name,
                "period1": period1,
                "period2": period2,
                "value1": value1,
                "value2": value2,
                "difference": None,
                "percentage_change": None,
                "error": "Values are not numeric"
            }
    
    def get_revenue_breakdown(self) -> Dict[str, Any]:
        """Get revenue breakdown by product segments."""
        if not self.parsed_data:
            return {}
        
        revenue_segments = {}
        metrics = self.parsed_data.get("metrics", {})
        
        for metric_name, periods_data in metrics.items():
            metric_lower = metric_name.lower()
            if any(segment in metric_lower for segment in ['iphone', 'ipad', 'mac', 'services', 'wearables']):
                revenue_segments[metric_name] = periods_data
        
        return revenue_segments
    
    def get_profitability_metrics(self) -> Dict[str, Any]:
        """Get key profitability metrics."""
        if not self.parsed_data:
            return {}
        
        profitability = {}
        metrics = self.parsed_data.get("metrics", {})
        
        for metric_name, periods_data in metrics.items():
            metric_lower = metric_name.lower()
            if any(term in metric_lower for term in ['income', 'profit', 'margin', 'eps']):
                profitability[metric_name] = periods_data
        
        return profitability


def main():
    """Test function for the Income Statement parser."""
    print("=== Income Statement SVG Parser Test ===")
    
    # Test the parser
    svg_file_path = "/Users/sachin/code/github/ai_research_draft_generator/data/research/AAPL/estimates/IncomeStatement.svg"
    parser = IncomeStatementSVGParser()
    
    try:
        # Parse data
        data = parser.parse_svg_to_json(svg_file_path)
        
        print(f"Company: {data['company']}")
        print(f"Statement Type: {data['statement_type']}")
        print(f"Periods: {len(data['periods'])} available")
        print(f"Metrics: {len(data['metrics'])} available")
        
        print(f"\nPeriods: {data['periods']}")
        
        print("\n=== Sample Metrics ===")
        metrics = list(data['metrics'].keys())
        for i, metric in enumerate(metrics[:10]):  # Show first 10 metrics
            print(f"{i+1:2d}. {metric}")
        
        print("\n=== Analysis Insights ===")
        analysis = data.get('analysis', {})
        print(f"Revenue Metrics: {len(analysis.get('revenue_metrics', []))}")
        print(f"Profitability Metrics: {len(analysis.get('profitability_metrics', []))}")
        print(f"Per-Share Metrics: {len(analysis.get('per_share_metrics', []))}")
        
        print("\n=== Parser Test Completed Successfully! ===")
        
    except Exception as e:
        print(f"Error during parsing: {e}")


if __name__ == "__main__":
    main()
