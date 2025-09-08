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
  Divider,
  Alert,
  Button,
  Collapse,
  IconButton,
  Grid,
  CircularProgress
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

  // Component to render markdown content with proper styling
  const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => (
    <ReactMarkdown
      components={{
        // Override default components for better styling
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
      {content}
    </ReactMarkdown>
  );

  // Component to render markdown arrays (like key_changes, new_insights)
  const MarkdownArrayRenderer: React.FC<{ items: string[] }> = ({ items }) => (
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

            {/* Comparative Analysis Section */}
            {analysis.has_estimates_comparison && analysis.comparative_analysis && (
              <Paper sx={{ p: 2, mb: 2, bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                <Typography variant="h6" gutterBottom>
                  <Insights sx={{ verticalAlign: 'middle', mr: 1 }} />
                  Estimates Comparison Analysis
                </Typography>
                
                {/* Comparative Executive Summary */}
                {analysis.comparative_analysis.executive_summary && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Summary
                    </Typography>
                    <MarkdownRenderer content={analysis.comparative_analysis.executive_summary} />
                  </Box>
                )}

                {/* Key Findings */}
                {analysis.comparative_analysis.key_findings && analysis.comparative_analysis.key_findings.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Key Findings
                    </Typography>
                    <MarkdownArrayRenderer items={analysis.comparative_analysis.key_findings} />
                  </Box>
                )}

                {/* Estimates Analysis */}
                {analysis.comparative_analysis.estimates_analysis && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Estimates Analysis
                    </Typography>
                    <MarkdownRenderer content={analysis.comparative_analysis.estimates_analysis} />
                  </Box>
                )}

                {/* Metric Comparisons */}
                {analysis.comparative_analysis.metric_comparisons && analysis.comparative_analysis.metric_comparisons.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Metric Comparisons
                    </Typography>
                    <List dense>
                      {analysis.comparative_analysis.metric_comparisons.map((comparison, index) => (
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

                {/* Recommendations */}
                {analysis.comparative_analysis.recommendations && analysis.comparative_analysis.recommendations.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Recommendations
                    </Typography>
                    <MarkdownArrayRenderer items={analysis.comparative_analysis.recommendations} />
                  </Box>
                )}
              </Paper>
            )}

            {/* Estimates Comparison Indicator */}
            {analysis.has_estimates_comparison && (
              <Alert severity="success" sx={{ mb: 2 }}>
                <Typography>
                  ✓ This analysis includes comparison with estimates data from the knowledge base
                </Typography>
              </Alert>
            )}
          </Box>
        )}

        {/* Generation Metadata */}
        {analysis.generation_metadata && (
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
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
            
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6} sm={4}>
                <Typography variant="body2" color="textSecondary">Model</Typography>
                <Typography variant="body1">{analysis.generation_metadata.model}</Typography>
              </Grid>
              <Grid item xs={6} sm={4}>
                <Typography variant="body2" color="textSecondary">Analysis Type</Typography>
                <Typography variant="body1">{analysis.generation_metadata.analysis_type}</Typography>
              </Grid>
              <Grid item xs={6} sm={4}>
                <Typography variant="body2" color="textSecondary">Context Documents</Typography>
                <Typography variant="body1">{analysis.generation_metadata.context_documents_count}</Typography>
              </Grid>
              <Grid item xs={6} sm={4}>
                <Typography variant="body2" color="textSecondary">Temperature</Typography>
                <Typography variant="body1">{analysis.generation_metadata.temperature}</Typography>
              </Grid>
              <Grid item xs={6} sm={4}>
                <Typography variant="body2" color="textSecondary">Max Tokens</Typography>
                <Typography variant="body1">{analysis.generation_metadata.max_tokens}</Typography>
              </Grid>
              <Grid item xs={6} sm={4}>
                <Typography variant="body2" color="textSecondary">Generated</Typography>
                <Typography variant="body1">
                  {formatDate(analysis.generation_metadata.generation_timestamp)}
                </Typography>
              </Grid>
            </Grid>

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
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography>Analysis is complete and ready for review. This analysis will be used for report generation.</Typography>
          </Alert>
        )}
        
        {analysis.status === 'analysis_approved' && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <Typography>Analysis has been approved and is ready for report generation.</Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default DocumentAnalysisDisplay;
