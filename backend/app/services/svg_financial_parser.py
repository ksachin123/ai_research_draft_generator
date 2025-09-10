"""
SVG Financial Data Parser for Income Statement

This module parses Apple's Income Statement data from SVG format and converts it to structured JSON.
The SVG contains financial metrics organized by quarters with actual and estimated values.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime


class IncomeStatementSVGParser:
    """
    Parser for Apple's Income Statement SVG files containing quarterly financial data.
    
    Extracts period headers (quarters/years), financial metrics, and their corresponding values
    to create a structured JSON representation suitable for financial analysis.
    """
    
    def __init__(self, svg_file_path: str):
        """
        Initialize the parser with SVG file path.
        
        Args:
            svg_file_path (str): Path to the SVG file containing income statement data
        """
        self.svg_file_path = svg_file_path
        self.parsed_data = {}
        
    def parse_svg_to_json(self) -> Dict[str, Any]:
        """
        Parse the SVG file and extract financial data into structured JSON format.
        
        Returns:
            Dict[str, Any]: Structured financial data with periods and metrics
        """
        try:
            # Parse the SVG file
            tree = ET.parse(self.svg_file_path)
            root = tree.getroot()
            
            # Extract all text elements
            text_elements = self._extract_text_elements(root)
            
            # Parse the text elements to identify structure
            periods, metrics_data = self._parse_text_elements(text_elements)
            
            # Create structured JSON
            structured_data = self._create_structured_json(periods, metrics_data)
            
            self.parsed_data = structured_data
            return structured_data
            
        except Exception as e:
            raise Exception(f"Error parsing SVG file: {str(e)}")
    
    def _extract_text_elements(self, root: ET.Element) -> List[Tuple[str, float, float]]:
        """
        Extract all text elements with their content and positions.
        
        Args:
            root: SVG root element
            
        Returns:
            List of tuples containing (text_content, x_position, y_position)
        """
        text_elements = []
        
        # Find all text elements in the SVG
        for text_elem in root.findall('.//{http://www.w3.org/2000/svg}text'):
            text_content = ""
            
            # Get text content from tspan elements
            tspan_elements = text_elem.findall('.//{http://www.w3.org/2000/svg}tspan')
            if tspan_elements:
                for tspan in tspan_elements:
                    if tspan.text:
                        text_content += tspan.text.strip()
            else:
                # Direct text content
                if text_elem.text:
                    text_content = text_elem.text.strip()
            
            if text_content:
                # Extract position from transform attribute
                x_pos, y_pos = self._extract_position(text_elem)
                text_elements.append((text_content, x_pos, y_pos))
        
        # Sort by Y position (top to bottom), then by X position (left to right)
        text_elements.sort(key=lambda x: (-x[2], x[1]))
        
        return text_elements
    
    def _extract_position(self, text_elem: ET.Element) -> Tuple[float, float]:
        """
        Extract X and Y position from text element's transform attribute.
        
        Args:
            text_elem: SVG text element
            
        Returns:
            Tuple of (x_position, y_position)
        """
        transform = text_elem.get('transform', '')
        
        # Parse matrix transform: matrix(1,0,0,-1,x_pos,y_pos)
        matrix_match = re.search(r'matrix\([^,]+,[^,]+,[^,]+,[^,]+,([^,]+),([^)]+)\)', transform)
        if matrix_match:
            x_pos = float(matrix_match.group(1))
            y_pos = float(matrix_match.group(2))
            return x_pos, y_pos
        
        # Parse translate transform: translate(x_pos,y_pos)
        translate_match = re.search(r'translate\(([^,]+),([^)]+)\)', transform)
        if translate_match:
            x_pos = float(translate_match.group(1))
            y_pos = float(translate_match.group(2))
            return x_pos, y_pos
        
        # Default position
        return 0.0, 0.0
    
    def _parse_text_elements(self, text_elements: List[Tuple[str, float, float]]) -> Tuple[List[str], Dict[str, List[Any]]]:
        """
        Parse text elements to identify periods and financial metrics.
        
        Args:
            text_elements: List of (text, x_pos, y_pos) tuples
            
        Returns:
            Tuple of (periods_list, metrics_data_dict)
        """
        periods = []
        metrics_data = {}
        current_metric = None
        
        # Group elements by Y position (rows)
        y_groups = self._group_by_y_position(text_elements)
        
        for y_pos in sorted(y_groups.keys(), reverse=True):  # Top to bottom
            row_elements = sorted(y_groups[y_pos], key=lambda x: x[1])  # Left to right
            
            # Check if this row contains period headers
            if self._is_period_header_row(row_elements):
                periods = self._extract_periods(row_elements)
                continue
            
            # Check if this row contains a financial metric
            metric_name = self._extract_metric_name(row_elements)
            if metric_name:
                current_metric = metric_name
                # Extract values for this metric
                values = self._extract_metric_values(row_elements)
                if values:
                    metrics_data[current_metric] = values
        
        return periods, metrics_data
    
    def _group_by_y_position(self, text_elements: List[Tuple[str, float, float]], tolerance: float = 5.0) -> Dict[float, List[Tuple[str, float, float]]]:
        """
        Group text elements by Y position with tolerance for alignment.
        
        Args:
            text_elements: List of text elements
            tolerance: Y position tolerance for grouping
            
        Returns:
            Dictionary mapping Y positions to lists of elements
        """
        groups = {}
        
        for text, x_pos, y_pos in text_elements:
            # Find existing group within tolerance
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
        """
        Determine if a row contains period headers (quarters/years).
        
        Args:
            row_elements: List of elements in the row
            
        Returns:
            bool: True if row contains period headers
        """
        period_patterns = [
            r'(Dec|Mar|Jun|Sep)-\d{2}',  # Quarter patterns like Dec-23, Mar-24
            r'FY\d{4}[AE]?',             # Fiscal year patterns like FY2024A, FY2025E
            r'20\d{2}[AE]',              # Year patterns like 2024A, 2025E
            r'Calendar',                 # Calendar year indicators
            r'Fiscal'                    # Fiscal year indicators
        ]
        
        for text, _, _ in row_elements:
            for pattern in period_patterns:
                if re.search(pattern, text):
                    return True
        return False
    
    def _extract_periods(self, row_elements: List[Tuple[str, float, float]]) -> List[str]:
        """
        Extract period headers from a row.
        
        Args:
            row_elements: List of elements in the row
            
        Returns:
            List of period strings
        """
        periods = []
        period_patterns = [
            r'(Dec|Mar|Jun|Sep)-\d{2}',
            r'FY\d{4}[AE]?',
            r'20\d{2}[AE]',
        ]
        
        for text, _, _ in row_elements:
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
        """
        Extract financial metric name from the leftmost element in a row.
        
        Args:
            row_elements: List of elements in the row
            
        Returns:
            Metric name if found, None otherwise
        """
        if not row_elements:
            return None
        
        # Get leftmost element (metric name should be on the left)
        leftmost_element = min(row_elements, key=lambda x: x[1])
        text = leftmost_element[0]
        
        # Check if this looks like a financial metric name
        metric_indicators = [
            'revenue', 'income', 'expense', 'profit', 'loss', 'margin',
            'iphone', 'ipad', 'mac', 'services', 'wearables',
            'eps', 'shares', 'dividend', 'gross', 'operating', 'net',
            'cost', 'research', 'development', 'sales', 'marketing',
            'fully-diluted', 'payment', 'outstanding', 'basic'
        ]
        
        text_lower = text.lower()
        if any(indicator in text_lower for indicator in metric_indicators):
            return text
        
        # Check for patterns that indicate financial metrics
        if re.search(r'[\$%]|\d+[,.]?\d*|\([^)]*\)', text):
            # This looks like it contains financial data, not a metric name
            return None
        
        # If text is long enough and doesn't contain numbers, might be a metric name
        if len(text) > 5 and not re.search(r'\d', text):
            return text
        
        return None
    
    def _extract_metric_values(self, row_elements: List[Tuple[str, float, float]]) -> List[Any]:
        """
        Extract financial values from a row, excluding the metric name.
        
        Args:
            row_elements: List of elements in the row
            
        Returns:
            List of financial values
        """
        values = []
        
        # Skip the leftmost element (metric name)
        if len(row_elements) <= 1:
            return values
        
        # Sort by X position and skip the first (leftmost) element
        sorted_elements = sorted(row_elements, key=lambda x: x[1])[1:]
        
        for text, _, _ in sorted_elements:
            # Clean and parse the value
            cleaned_value = self._clean_financial_value(text)
            if cleaned_value is not None:
                values.append(cleaned_value)
        
        return values
    
    def _clean_financial_value(self, text: str) -> Any:
        """
        Clean and convert financial text to appropriate data type.
        
        Args:
            text: Raw text value
            
        Returns:
            Cleaned value (float, int, or string)
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Handle special cases
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
        
        # Handle currency values
        if '$' in text:
            try:
                # Remove $ and commas, handle negatives
                cleaned = re.sub(r'[$,]', '', text)
                if '(' in cleaned and ')' in cleaned:
                    # Negative value in parentheses
                    number = re.search(r'\d*\.?\d+', cleaned)
                    if number:
                        return -float(number.group(0))
                else:
                    number = re.search(r'[-+]?\d*\.?\d+', cleaned)
                    if number:
                        return float(number.group(0))
            except:
                pass
        
        # Handle regular numbers (with commas)
        try:
            cleaned = text.replace(',', '')
            if '(' in cleaned and ')' in cleaned:
                # Negative value in parentheses
                number = re.search(r'\d*\.?\d+', cleaned)
                if number:
                    return -float(number.group(0))
            else:
                number = re.search(r'[-+]?\d*\.?\d+', cleaned)
                if number:
                    value = float(number.group(0))
                    # Return as int if it's a whole number
                    return int(value) if value.is_integer() else value
        except:
            pass
        
        # Return as string if can't parse as number
        return text
    
    def _create_structured_json(self, periods: List[str], metrics_data: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Create structured JSON from parsed periods and metrics data.
        
        Args:
            periods: List of period headers
            metrics_data: Dictionary of metric names to values
            
        Returns:
            Structured financial data dictionary
        """
        structured_data = {
            "company": "AAPL",
            "statement_type": "Income Statement",
            "parse_timestamp": datetime.now().isoformat(),
            "periods": periods,
            "metrics": {}
        }
        
        # Organize metrics by period
        for metric_name, values in metrics_data.items():
            structured_data["metrics"][metric_name] = {}
            
            # Map values to periods
            for i, value in enumerate(values):
                if i < len(periods):
                    structured_data["metrics"][metric_name][periods[i]] = value
        
        return structured_data
    
    def get_metric_value(self, metric_name: str, period: str) -> Any:
        """
        Get a specific metric value for a given period.
        
        Args:
            metric_name: Name of the financial metric
            period: Period identifier (e.g., "Dec-23", "2024A")
            
        Returns:
            Value for the metric in the specified period, None if not found
        """
        if not self.parsed_data:
            raise Exception("Data not parsed yet. Call parse_svg_to_json() first.")
        
        metrics = self.parsed_data.get("metrics", {})
        if metric_name in metrics and period in metrics[metric_name]:
            return metrics[metric_name][period]
        
        return None
    
    def get_all_periods(self) -> List[str]:
        """
        Get all available periods in the data.
        
        Returns:
            List of period identifiers
        """
        if not self.parsed_data:
            raise Exception("Data not parsed yet. Call parse_svg_to_json() first.")
        
        return self.parsed_data.get("periods", [])
    
    def get_all_metrics(self) -> List[str]:
        """
        Get all available metric names.
        
        Returns:
            List of metric names
        """
        if not self.parsed_data:
            raise Exception("Data not parsed yet. Call parse_svg_to_json() first.")
        
        return list(self.parsed_data.get("metrics", {}).keys())
    
    def save_to_json(self, output_path: str) -> None:
        """
        Save parsed data to JSON file.
        
        Args:
            output_path: Path where to save the JSON file
        """
        if not self.parsed_data:
            raise Exception("Data not parsed yet. Call parse_svg_to_json() first.")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.parsed_data, f, indent=2, ensure_ascii=False)
    
    def compare_periods(self, metric_name: str, period1: str, period2: str) -> Dict[str, Any]:
        """
        Compare a metric between two periods.
        
        Args:
            metric_name: Name of the financial metric
            period1: First period to compare
            period2: Second period to compare
            
        Returns:
            Dictionary containing comparison data
        """
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
            # Convert to float for calculation
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


def main():
    """
    Example usage of the IncomeStatementSVGParser.
    """
    # Initialize parser
    svg_file_path = "/Users/sachin/code/github/ai_research_draft_generator/data/research/AAPL/estimates/IncomeStatement.svg"
    parser = IncomeStatementSVGParser(svg_file_path)
    
    try:
        # Parse the SVG file
        print("Parsing SVG file...")
        structured_data = parser.parse_svg_to_json()
        
        # Print basic information
        print(f"\nParsed data for {structured_data['company']} - {structured_data['statement_type']}")
        print(f"Number of periods: {len(structured_data['periods'])}")
        print(f"Number of metrics: {len(structured_data['metrics'])}")
        
        print(f"\nPeriods: {structured_data['periods']}")
        print(f"\nMetrics: {list(structured_data['metrics'].keys())}")
        
        # Example: Get a specific metric value
        periods = parser.get_all_periods()
        if len(periods) >= 2:
            latest_period = periods[-1]
            previous_period = periods[-2]
            
            # Example comparison
            metrics = parser.get_all_metrics()
            if metrics:
                first_metric = metrics[0]
                comparison = parser.compare_periods(first_metric, previous_period, latest_period)
                print(f"\nExample comparison - {first_metric}:")
                print(f"{previous_period}: {comparison['value1']}")
                print(f"{latest_period}: {comparison['value2']}")
                if comparison.get('percentage_change'):
                    print(f"Change: {comparison['percentage_change']:.2f}%")
        
        # Save to JSON file
        output_file = "/Users/sachin/code/github/ai_research_draft_generator/data/research/AAPL/estimates/IncomeStatement_parsed.json"
        parser.save_to_json(output_file)
        print(f"\nParsed data saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
