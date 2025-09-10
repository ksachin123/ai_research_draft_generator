# SVG Financial Data Parser - Usage Guide

## Overview

I've created a comprehensive parser for Apple's Income Statement SVG file that converts the complex SVG format into structured JSON data. The parser successfully extracts:

- **17 time periods**: Including quarterly data (Dec-23, Mar-24, etc.) and annual data (2023A, 2024A, 2025E, etc.)
- **30 financial metrics**: Including Revenues, iPhone, iPad, Services, Operating Income, EPS, etc.

## Key Features

### 1. Data Extraction
- Parses SVG text elements and their positions
- Identifies period headers (quarters and fiscal years)
- Extracts financial metrics and their corresponding values
- Handles various number formats ($, commas, percentages)

### 2. Structured Output
The parser creates a JSON structure with:
```json
{
  "company": "AAPL",
  "statement_type": "Income Statement",
  "parse_timestamp": "2025-09-10T15:20:13.499683",
  "periods": ["Dec-23", "Mar-24", ..., "2027E"],
  "metrics": {
    "Revenues": {
      "Dec-23": 119575,
      "2024A": 391035,
      "2025E": 406838
    }
  }
}
```

### 3. Analysis Capabilities
- **Period Comparison**: Compare any metric between two periods
- **Growth Rate Calculation**: Automatic percentage change calculation
- **Data Querying**: Get specific metric values for any period
- **Trend Analysis**: Track metrics across multiple periods

## Usage Examples

### Basic Usage
```python
from svg_financial_parser import IncomeStatementSVGParser

# Initialize parser
parser = IncomeStatementSVGParser("path/to/IncomeStatement.svg")

# Parse the SVG file
data = parser.parse_svg_to_json()

# Get specific metric value
revenue_2024 = parser.get_metric_value("Revenues", "2024A")
print(f"2024 Revenue: ${revenue_2024:,}")  # Output: 2024 Revenue: $391,035
```

### Comparative Analysis
```python
# Compare revenue between two years
comparison = parser.compare_periods("Revenues", "2024A", "2025E")
print(f"Growth: {comparison['percentage_change']:.1f}%")  # Output: Growth: 4.0%
```

### Quarterly Trend Analysis
```python
# Track iPhone revenue across quarters
quarters = ["Dec-23", "Mar-24", "Jun-24", "Sep-24", "Dec-24"]
for quarter in quarters:
    value = parser.get_metric_value("iPhone", quarter)
    print(f"{quarter}: ${value:,}")
```

## Sample Results from Apple's Data

### Annual Revenue Growth
- 2023A → 2024A: +2.0%
- 2024A → 2025E: +4.0%
- 2025E → 2026E: +6.7%
- 2026E → 2027E: +6.8%

### iPhone Revenue Seasonality
- Dec-23: $69,702M (Holiday quarter)
- Mar-24: $45,963M (Post-holiday dip)
- Jun-24: $39,296M (Lowest quarter)
- Sep-24: $46,222M (New iPhone launch)
- Dec-24: $69,138M (Holiday quarter)

### EPS Growth Trajectory
- 2023A: $6.13
- 2024A: $6.75 (+10.1%)
- 2025E: $7.12 (+5.5%)
- 2026E: $7.69 (+8.0%)
- 2027E: $8.67 (+12.7%)

## Files Created

1. **`svg_financial_parser.py`** - Main parser class with full functionality
2. **`IncomeStatement_parsed.json`** - Complete parsed data in JSON format
3. **`standalone_parser_test.py`** - Test script demonstrating all features

## Key Benefits for Financial Analysis

1. **Easy Data Access**: Query any metric for any period with simple method calls
2. **Automated Calculations**: Built-in growth rate and comparison calculations
3. **Structured Format**: Clean JSON output suitable for databases, APIs, or further processing
4. **Flexible Querying**: Get data for specific periods, compare periods, or analyze trends
5. **Error Handling**: Robust parsing with proper error handling for missing data

## Use Cases

- **Quarterly Earnings Analysis**: Compare current quarter vs. previous quarter/year
- **Forecast Tracking**: Compare estimates vs. actuals
- **Trend Analysis**: Track metrics over multiple periods
- **Performance Metrics**: Calculate growth rates, margins, and other KPIs
- **Data Visualization**: Export data for charts and dashboards
- **Financial Modeling**: Use structured data for financial models and projections

The parser successfully converts the complex SVG financial data into an easily queryable format, making it simple to perform comparative analysis and track Apple's financial performance across quarters and years.
