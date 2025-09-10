import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Paper,
  List,
  ListItem,
  ListItemText,
  Button,
  Collapse,
  IconButton
} from '@mui/material';
import {
  CheckCircle,
  TrendingUp,
  Insights,
  Description,
  Timeline,
  ExpandMore,
  ExpandLess,
  Code,
  Settings,
  Warning
} from '@mui/icons-material';
import { DocumentAnalysis } from '../../services/documentService';

interface DocumentAnalysisDisplayProps {
  analysis: DocumentAnalysis;
  onClose?: () => void;
  onApprove?: (uploadId: string) => void;
  ticker: string;
}

const DocumentAnalysisDisplay: React.FC<DocumentAnalysisDisplayProps> = ({ 
  analysis, 
  onClose,
  onApprove,
  ticker 
}) => {
  const [showPrompt, setShowPrompt] = useState(false);
  const [approving, setApproving] = useState(false);

  // Helper function to check if comparative analysis data is available
  const hasComparativeAnalysis = () => {
    const comp = analysis.analysis.comparative_analysis;
    return comp && (
      comp.estimates_vs_actuals ||
      comp.segment_comparison ||
      comp.margin_analysis ||
      comp.investment_thesis_impact ||
      comp.risk_assessment_update ||
      (comp.actionable_insights && comp.actionable_insights.length > 0) ||
      (comp.variance_highlights && comp.variance_highlights.length > 0) ||
      (comp.key_findings && comp.key_findings.length > 0)
    );
  };

  const handleApprove = async () => {
    if (onApprove && analysis.upload_id) {
      setApproving(true);
      try {
        await onApprove(analysis.upload_id);
      } catch (error) {
        console.error('Failed to approve analysis:', error);
      } finally {
        setApproving(false);
      }
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'analysis_ready':
        return 'success';
      case 'analysis_approved':
        return 'primary';
      case 'analysis_error':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Helper function to detect and parse markdown tables
  const parseMarkdownTables = (content: string) => {
    // Primary regex for well-formed tables with separator row
    const tableRegex = /\|(.+)\|\s*\n\|[-\s|:]+\|\s*\n((?:\|.+\|\s*\n?)*)/g;
    
    // Fallback regex for tables without proper separator (just consecutive pipe rows)
    const simpleTableRegex = /(\|.+\|\s*\n){2,}/g;
    
    const parts: Array<{
      type: 'text' | 'table';
      content?: string;
      headers?: string[];
      rows?: string[][];
    }> = [];
    let lastIndex = 0;
    let match;

    // First try the standard table format
    while ((match = tableRegex.exec(content)) !== null) {
      // Add content before the table
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex, match.index)
        });
      }

      // Parse the table
      const headerRow = match[1];
      const dataRows = match[2];
      
      const headers = headerRow.split('|').map(h => h.trim()).filter(h => h);
      const rows = dataRows.trim().split('\n').map(row => 
        row.split('|').map(cell => cell.trim()).filter(cell => cell)
      );

      parts.push({
        type: 'table',
        headers,
        rows
      });

      lastIndex = match.index + match[0].length;
    }

    // If no standard tables found, try simple table format
    if (parts.filter(p => p.type === 'table').length === 0) {
      lastIndex = 0;
      const simpleMatches = Array.from(content.matchAll(simpleTableRegex));
      
      for (const match of simpleMatches) {
        // Add content before the table
        if (match.index !== undefined && match.index > lastIndex) {
          parts.push({
            type: 'text',
            content: content.slice(lastIndex, match.index)
          });
        }

        // Parse simple table (first row as headers, rest as data)
        const tableLines = match[0].trim().split('\n');
        if (tableLines.length >= 2) {
          const headers = tableLines[0].split('|').map(h => h.trim()).filter(h => h);
          const rows = tableLines.slice(1).map(row => 
            row.split('|').map(cell => cell.trim()).filter(cell => cell)
          );

          parts.push({
            type: 'table',
            headers,
            rows
          });
        }

        lastIndex = (match.index || 0) + match[0].length;
      }
    }

    // Add remaining content
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex)
      });
    }

    return parts;
  };

  // Component to render markdown content with proper styling
  const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
    // Parse content for tables
    const parsedContent = parseMarkdownTables(content);
    
    return (
      <Box>
        {parsedContent.map((part, index) => {
          if (part.type === 'table' && part.headers && part.rows) {
            return (
              <Box key={index} sx={{ overflowX: 'auto', mb: 2 }}>
                <table style={{ 
                  width: '100%', 
                  borderCollapse: 'collapse',
                  border: '1px solid #e0e0e0'
                }}>
                  <thead style={{ backgroundColor: '#f5f5f5' }}>
                    <tr style={{ borderBottom: '1px solid #e0e0e0' }}>
                      {part.headers.map((header, headerIndex) => (
                        <th key={headerIndex} style={{ 
                          padding: '8px 12px', 
                          textAlign: 'left', 
                          fontWeight: 'bold',
                          borderRight: '1px solid #e0e0e0'
                        }}>
                          <Typography variant="body2" fontWeight="bold">
                            {header}
                          </Typography>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {part.rows.map((row, rowIndex) => (
                      <tr key={rowIndex} style={{ borderBottom: '1px solid #e0e0e0' }}>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} style={{ 
                            padding: '8px 12px', 
                            borderRight: '1px solid #e0e0e0',
                            verticalAlign: 'top'
                          }}>
                            <Typography variant="body2">
                              {cell}
                            </Typography>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Box>
            );
          } else if (part.content) {
            // Render regular markdown for non-table content
            return (
              <ReactMarkdown
                key={index}
                components={{
                  p: ({ children }) => <Typography variant="body1" paragraph>{children}</Typography>,
                  h1: ({ children }) => <Typography variant="h4" gutterBottom>{children}</Typography>,
                  h2: ({ children }) => <Typography variant="h5" gutterBottom>{children}</Typography>,
                  h3: ({ children }) => <Typography variant="h6" gutterBottom>{children}</Typography>,
                  ul: ({ children }) => <List dense>{children}</List>,
                  ol: ({ children }) => <List dense>{children}</List>,
                  li: ({ children }) => (
                    <ListItem disablePadding>
                      <ListItemText primary={children} sx={{ ml: 1 }} />
                    </ListItem>
                  ),
                  strong: ({ children }) => <Typography component="span" fontWeight="bold">{children}</Typography>,
                  em: ({ children }) => <Typography component="span" fontStyle="italic">{children}</Typography>,
                  code: ({ children }) => (
                    <Typography 
                      component="code" 
                      sx={{ 
                        bgcolor: 'grey.100', 
                        px: 0.5, 
                        py: 0.25, 
                        borderRadius: 0.5, 
                        fontFamily: 'monospace',
                        fontSize: '0.9em'
                      }}
                    >
                      {children}
                    </Typography>
                  ),
                }}
              >
                {part.content}
              </ReactMarkdown>
            );
          }
          return null;
        })}
      </Box>
    );
  };

  // Enhanced component to render markdown arrays with table detection
  const MarkdownArrayRenderer: React.FC<{ items: string[] }> = ({ items }) => {
    // Check if the array contains table data
    const hasTableData = items.some(item => item.trim().startsWith('|') && item.includes('|'));
    
    if (hasTableData) {
      // Reconstruct table from array elements
      const tableRows: string[] = [];
      const nonTableItems: string[] = [];
      let currentTableBlock: string[] = [];
      
      for (const item of items) {
        if (item.trim().startsWith('|') && item.includes('|')) {
          currentTableBlock.push(item);
        } else {
          // If we have accumulated table rows, join them and add to tableRows
          if (currentTableBlock.length > 0) {
            tableRows.push(currentTableBlock.join('\n'));
            currentTableBlock = [];
          }
          nonTableItems.push(item);
        }
      }
      
      // Add any remaining table block
      if (currentTableBlock.length > 0) {
        tableRows.push(currentTableBlock.join('\n'));
      }
      
      return (
        <Box>
          {/* Render reconstructed tables */}
          {tableRows.map((tableContent, tableIndex) => (
            <Box key={`table-${tableIndex}`} sx={{ mb: 2 }}>
              <MarkdownRenderer content={tableContent} />
            </Box>
          ))}
          
          {/* Render non-table items as list */}
          {nonTableItems.length > 0 && (
            <List dense>
              {nonTableItems.map((item, index) => (
                <ListItem key={`text-${index}`} disablePadding>
                  <Box sx={{ ml: 1, width: '100%' }}>
                    <MarkdownRenderer content={item} />
                  </Box>
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      );
    }
    
    // Fallback to original list rendering for non-table arrays
    return (
      <List dense>
        {items.map((item, index) => (
          <ListItem key={index} disablePadding>
            <Box sx={{ ml: 1, width: '100%' }}>
              <MarkdownRenderer content={item} />
            </Box>
          </ListItem>
        ))}
      </List>
    );
  };

  return (
    <Card elevation={3} sx={{ maxWidth: '100%', mb: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircle color="success" />
            <Typography variant="h5" component="h2">
              Document Analysis Results
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {analysis.status === 'analysis_ready' && onApprove && (
              <Button 
                onClick={handleApprove} 
                variant="contained" 
                size="small"
                disabled={approving}
                color="primary"
              >
                {approving ? 'Approving...' : 'Approve Analysis'}
              </Button>
            )}
            {onClose && (
              <Button onClick={onClose} variant="outlined" size="small">
                Close
              </Button>
            )}
          </Box>
        </Box>

        {/* Document Info */}
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
          <Typography variant="h6" gutterBottom>
            <Description sx={{ verticalAlign: 'middle', mr: 1 }} />
            Document Information
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            <Typography variant="body2">
              <strong>Filename:</strong> {analysis.document_info.filename}
            </Typography>
            <Typography variant="body2">
              <strong>Type:</strong> {analysis.document_info.document_type}
            </Typography>
            <Typography variant="body2">
              <strong>Uploaded:</strong> {formatDate(analysis.document_info.upload_date)}
            </Typography>
            {analysis.analysis_date && (
              <Typography variant="body2">
                <strong>Analyzed:</strong> {formatDate(analysis.analysis_date)}
              </Typography>
            )}
          </Box>
          <Box sx={{ mt: 1 }}>
            <Chip 
              label={analysis.status.replace('_', ' ').toUpperCase()} 
              color={getStatusColor(analysis.status)}
              size="small"
            />
          </Box>
        </Paper>

        {/* Analysis Results */}
        {analysis.analysis && (
          <Box>
            {/* Executive Summary */}
            {analysis.analysis.executive_summary && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Insights sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Executive Summary
                </Typography>
                <MarkdownRenderer content={analysis.analysis.executive_summary} />
              </Paper>
            )}

            {/* Key Changes */}
            {analysis.analysis.key_changes && analysis.analysis.key_changes.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Timeline sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Key Changes
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.key_changes} />
              </Paper>
            )}

            {/* New Insights */}
            {analysis.analysis.new_insights && analysis.analysis.new_insights.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <TrendingUp sx={{ verticalAlign: 'middle', mr: 1 }} />
                  New Insights
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.new_insights} />
              </Paper>
            )}

            {/* Investment Thesis Impact */}
            {analysis.analysis.potential_thesis_impact && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Investment Thesis Impact
                </Typography>
                <MarkdownRenderer content={analysis.analysis.potential_thesis_impact} />
              </Paper>
            )}

            {/* Business Segments */}
            {analysis.analysis.business_segments && analysis.analysis.business_segments.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <TrendingUp sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Business Segments
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.business_segments} />
              </Paper>
            )}

            {/* Actionable Insights */}
            {analysis.analysis.actionable_insights && analysis.analysis.actionable_insights.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Insights sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Actionable Insights
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.actionable_insights} />
              </Paper>
            )}

            {/* Investment Implications */}
            {analysis.analysis.investment_implications && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <TrendingUp sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Investment Implications
                </Typography>
                <MarkdownRenderer content={analysis.analysis.investment_implications} />
              </Paper>
            )}

            {/* Margin Comparison */}
            {analysis.analysis.margin_comparison && analysis.analysis.margin_comparison.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Timeline sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Margin Comparison
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.margin_comparison} />
              </Paper>
            )}

            {/* Financial Performance */}
            {analysis.analysis.financial_performance && analysis.analysis.financial_performance.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Timeline sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Financial Performance
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.financial_performance} />
              </Paper>
            )}

            {/* Forward Looking Insights */}
            {analysis.analysis.forward_looking_insights && analysis.analysis.forward_looking_insights.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <TrendingUp sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Forward Looking Insights
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.forward_looking_insights} />
              </Paper>
            )}

            {/* Requires Attention */}
            {analysis.analysis.requires_attention && analysis.analysis.requires_attention.length > 0 && (
              <Paper sx={{ p: 2, mb: 2, bgcolor: 'warning.light' }}>
                <Typography variant="h6" gutterBottom>
                  <Warning sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Requires Attention
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.requires_attention} />
              </Paper>
            )}

            {/* Strategic Development */}
            {analysis.analysis.strategic_developments && analysis.analysis.strategic_developments.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Description sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Strategic Development
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.strategic_developments} />
              </Paper>
            )}

            {/* Analyst Estimates Comparison - New Section */}
            {analysis.analysis.analyst_estimates_comparison && analysis.analysis.analyst_estimates_comparison.length > 0 && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <Timeline sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Analyst Estimates vs Actuals Comparison
                </Typography>
                <MarkdownArrayRenderer items={analysis.analysis.analyst_estimates_comparison} />
                <Paper sx={{ p: 1, mt: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
                  <Typography variant="body2">
                    <strong>Beat/Miss Analysis:</strong> This section provides detailed comparison of actual reported numbers against analyst estimates with quantified variances and investment implications.
                  </Typography>
                </Paper>
              </Paper>
            )}

            {/* Comparative Analysis Section */}
            {hasComparativeAnalysis() && (
              <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.paper' }}>
                <Typography variant="h6" gutterBottom>
                  <Insights sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Estimates Comparison Analysis
                </Typography>
                
                {/* Comparative Executive Summary */}
                {analysis.analysis?.comparative_analysis?.executive_summary && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Executive Summary
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.executive_summary} />
                  </Box>
                )}

                {/* Estimates vs Actuals */}
                {analysis.analysis?.comparative_analysis?.estimates_vs_actuals && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Estimates vs Actuals
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.estimates_vs_actuals} />
                  </Box>
                )}

                {/* Always show this section if comparative_analysis exists */}
                {!analysis.analysis?.comparative_analysis?.estimates_vs_actuals && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                      Estimates vs Actuals: No data available
                    </Typography>
                  </Box>
                )}

                {/* Segment Comparison */}
                {analysis.analysis?.comparative_analysis?.segment_comparison && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Segment Comparison
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.segment_comparison} />
                  </Box>
                )}

                {/* Margin Analysis */}
                {analysis.analysis?.comparative_analysis?.margin_analysis && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Margin Analysis
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.margin_analysis} />
                  </Box>
                )}

                {/* Investment Thesis Impact */}
                {analysis.analysis?.comparative_analysis?.investment_thesis_impact && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Investment Thesis Impact
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.investment_thesis_impact} />
                  </Box>
                )}

                {/* Risk Assessment Update */}
                {analysis.analysis?.comparative_analysis?.risk_assessment_update && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Risk Assessment Update
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.risk_assessment_update} />
                  </Box>
                )}

                {/* Actionable Insights */}
                {analysis.analysis?.comparative_analysis?.actionable_insights && analysis.analysis.comparative_analysis.actionable_insights.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Actionable Insights
                    </Typography>
                    <MarkdownArrayRenderer items={analysis.analysis.comparative_analysis.actionable_insights} />
                  </Box>
                )}

                {/* Variance Highlights */}
                {analysis.analysis?.comparative_analysis?.variance_highlights && analysis.analysis.comparative_analysis.variance_highlights.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Variance Highlights
                    </Typography>
                    <MarkdownArrayRenderer items={analysis.analysis.comparative_analysis.variance_highlights} />
                  </Box>
                )}

                {/* Legacy support for old structure */}
                {/* Key Findings */}
                {analysis.analysis?.comparative_analysis?.key_findings && analysis.analysis.comparative_analysis.key_findings.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Key Findings
                    </Typography>
                    <MarkdownArrayRenderer items={analysis.analysis.comparative_analysis.key_findings} />
                  </Box>
                )}

                {/* Legacy Estimates Analysis */}
                {analysis.analysis?.comparative_analysis?.estimates_analysis && !analysis.analysis.comparative_analysis.estimates_vs_actuals && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Estimates Analysis
                    </Typography>
                    <MarkdownRenderer content={analysis.analysis.comparative_analysis.estimates_analysis} />
                  </Box>
                )}

                {/* Legacy Metric Comparisons */}
                {analysis.analysis?.comparative_analysis?.metric_comparisons && analysis.analysis.comparative_analysis.metric_comparisons.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Metric Comparisons
                    </Typography>
                    <List dense>
                      {analysis.analysis.comparative_analysis.metric_comparisons.map((comparison, index) => (
                        <ListItem key={index} disablePadding>
                          <Box sx={{ ml: 1, width: '100%' }}>
                            <Typography variant="body2" fontWeight="bold">
                              {comparison.metric || comparison}
                            </Typography>
                            {comparison.analysis && (
                              <MarkdownRenderer content={comparison.analysis} />
                            )}
                          </Box>
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {/* Legacy Recommendations */}
                {analysis.analysis?.comparative_analysis?.recommendations && analysis.analysis.comparative_analysis.recommendations.length > 0 && !analysis.analysis.comparative_analysis.actionable_insights && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Recommendations
                    </Typography>
                    <MarkdownArrayRenderer items={analysis.analysis.comparative_analysis.recommendations} />
                  </Box>
                )}
              </Paper>
            )}

            {/* Estimates Comparison Indicator */}
            {hasComparativeAnalysis() && (
              <Paper sx={{ p: 1, mb: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
                <Typography variant="body2">
                  ✓ This analysis includes comparison with estimates data from the knowledge base
                </Typography>
              </Paper>
            )}

            {/* Enhanced Analyst Estimates Indicator */}
            {analysis.generation_metadata?.analyst_estimates_included && (
              <Paper sx={{ p: 1, mb: 2, bgcolor: 'info.light', color: 'info.contrastText', display: 'flex', alignItems: 'center' }}>
                <Timeline sx={{ mr: 1 }} />
                <div>
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                    ✨ Enhanced Analysis with Current Quarter Analyst Estimates
                  </div>
                  <div style={{ fontSize: '0.875rem', opacity: 0.9 }}>
                    This analysis includes comprehensive comparison against {' '}
                    {analysis.generation_metadata.analyst_estimates_length ? 
                      `${Math.round(analysis.generation_metadata.analyst_estimates_length / 100)} analyst metrics` : 
                      'current analyst estimates'} for beat/miss analysis and investment implications.
                  </div>
                </div>
              </Paper>
            )}
          </Box>
        )}

        {/* Generation Metadata */}
        {analysis.generation_metadata && (
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="h6">
                <Settings sx={{ verticalAlign: 'middle', mr: 1 }} />
                Analysis Generation Details
              </Typography>
              <IconButton 
                onClick={() => setShowPrompt(!showPrompt)}
                size="small"
                sx={{ ml: 1 }}
              >
                {showPrompt ? <ExpandLess /> : <ExpandMore />}
                <Typography variant="body2" sx={{ ml: 0.5 }}>
                  {showPrompt ? 'Hide' : 'Show'} Prompt
                </Typography>
              </IconButton>
            </Box>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
              <Box sx={{ minWidth: 150 }}>
                <Typography variant="body2" color="textSecondary">Model</Typography>
                <Typography variant="body1">{analysis.generation_metadata.model}</Typography>
              </Box>
              <Box sx={{ minWidth: 150 }}>
                <Typography variant="body2" color="textSecondary">Analysis Type</Typography>
                <Typography variant="body1">{analysis.generation_metadata.analysis_type}</Typography>
              </Box>
              <Box sx={{ minWidth: 150 }}>
                <Typography variant="body2" color="textSecondary">Context Documents</Typography>
                <Typography variant="body1">{analysis.generation_metadata.context_documents_count}</Typography>
              </Box>
              <Box sx={{ minWidth: 150 }}>
                <Typography variant="body2" color="textSecondary">Temperature</Typography>
                <Typography variant="body1">{analysis.generation_metadata.temperature}</Typography>
              </Box>
              <Box sx={{ minWidth: 150 }}>
                <Typography variant="body2" color="textSecondary">Max Tokens</Typography>
                <Typography variant="body1">{analysis.generation_metadata.max_tokens}</Typography>
              </Box>
              <Box sx={{ minWidth: 150 }}>
                <Typography variant="body2" color="textSecondary">Generated</Typography>
                <Typography variant="body1">
                  {formatDate(analysis.generation_metadata.generation_timestamp)}
                </Typography>
              </Box>
              {analysis.generation_metadata.analyst_estimates_included !== undefined && (
                <Box sx={{ minWidth: 150 }}>
                  <Typography variant="body2" color="textSecondary">Analyst Estimates</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body1">
                      {analysis.generation_metadata.analyst_estimates_included ? 'Included' : 'Not Available'}
                    </Typography>
                    {analysis.generation_metadata.analyst_estimates_included && (
                      <Chip 
                        label="Enhanced" 
                        size="small" 
                        color="primary" 
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>
              )}
              {analysis.generation_metadata.analyst_estimates_length && analysis.generation_metadata.analyst_estimates_length > 0 && (
                <Box sx={{ minWidth: 150 }}>
                  <Typography variant="body2" color="textSecondary">Estimates Data Size</Typography>
                  <Typography variant="body1">
                    {analysis.generation_metadata.analyst_estimates_length.toLocaleString()} chars
                  </Typography>
                </Box>
              )}
            </Box>

            {/* Analysis Generation Details Text */}
            {analysis.analysis.analysis_generation_details && (
              <Box sx={{ mb: 2, p: 2, bgcolor: 'primary.light', borderRadius: 1 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ color: 'primary.contrastText' }}>
                  <Insights sx={{ verticalAlign: 'middle', mr: 1 }} />
                  How This Analysis Was Generated
                </Typography>
                <Box sx={{ color: 'primary.contrastText' }}>
                  <MarkdownRenderer content={analysis.analysis.analysis_generation_details} />
                </Box>
              </Box>
            )}

            <Collapse in={showPrompt}>
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  <Code sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Prompt Used for Analysis Generation
                </Typography>
                <Paper 
                  sx={{ 
                    p: 2, 
                    bgcolor: 'grey.100', 
                    maxHeight: 400, 
                    overflow: 'auto',
                    border: '1px solid',
                    borderColor: 'grey.300'
                  }}
                >
                  <Typography 
                    variant="body2" 
                    component="pre" 
                    sx={{ 
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                      margin: 0
                    }}
                  >
                    {analysis.generation_metadata.prompt_used}
                  </Typography>
                </Paper>
              </Box>
            </Collapse>
          </Paper>
        )}

        {/* Context Sources */}
        {analysis.context_sources && analysis.context_sources.length > 0 && (
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
            <Typography variant="h6" gutterBottom>
              Analysis Context Sources
            </Typography>
            <Typography variant="body2" paragraph>
              This analysis was generated using context from the following sources:
            </Typography>
            <List dense>
              {analysis.context_sources.map((source, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemText 
                    primary={source.document}
                    secondary={`Relevance: ${(source.relevance_score * 100).toFixed(1)}%`}
                    sx={{ ml: 1 }}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        )}

        {analysis.status === 'analysis_ready' && (
          <Paper sx={{ p: 1, mt: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
            <Typography variant="body2">
              Analysis is complete and ready for review. This analysis will be used for report generation.
            </Typography>
          </Paper>
        )}
        
        {analysis.status === 'analysis_approved' && (
          <Paper sx={{ p: 1, mt: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
            <Typography variant="body2">
              Analysis has been approved and is ready for report generation.
            </Typography>
          </Paper>
        )}
      </CardContent>
    </Card>
  );
};

export default DocumentAnalysisDisplay;
