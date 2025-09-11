import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Chip,
  IconButton,
  Collapse,
  Modal,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Visibility as ViewIcon,
  Code as CodeIcon,
  Close as CloseIcon,
  Description as DocumentIcon,
  CheckCircle as CheckCircleIcon,
  TrendingUp as TrendingUpIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';
import SimpleMarkdown from '../common/SimpleMarkdown';

interface BatchAnalyzedDocument {
  upload_id: string;
  document_info: {
    filename: string;
    upload_date: string;
    document_type: string;
    description?: string;
  };
  analysis: {
    executive_summary?: string;
    key_changes?: string[];
    new_insights?: string[];
    analyst_estimates_comparison?: string[];
    financial_performance?: string[];
    potential_thesis_impact?: string;
    requires_attention?: string[];
    [key: string]: any;
  };
  analysis_date: string;
  status: string;
  generation_metadata?: {
    prompt_used: string;
    model: string;
    temperature: number;
    max_tokens: number;
    analysis_type: string;
    context_documents_count: number;
    analyst_estimates_included: boolean;
    analyst_estimates_length: number;
    generation_timestamp: string;
  };
  context_sources?: Array<{
    content: string;
    metadata: any;
    distance: number;
  }>;
}

interface BatchDocumentAnalysisDisplayProps {
  documents: BatchAnalyzedDocument[];
  batchName: string;
  ticker: string;
}

const BatchDocumentAnalysisDisplay: React.FC<BatchDocumentAnalysisDisplayProps> = ({
  documents,
  batchName,
  ticker
}) => {
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [selectedDoc, setSelectedDoc] = useState<BatchAnalyzedDocument | null>(null);
  const [showPrompt, setShowPrompt] = useState<boolean>(false);

  const toggleDocExpansion = (uploadId: string) => {
    setExpandedDoc(expandedDoc === uploadId ? null : uploadId);
  };

  const openDocumentModal = (doc: BatchAnalyzedDocument) => {
    setSelectedDoc(doc);
    setModalOpen(true);
    setShowPrompt(false);
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedDoc(null);
    setShowPrompt(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'analysis_ready':
        return 'success';
      case 'analysis_error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Individual Document Analysis ({documents.length})
      </Typography>

      <List>
        {documents.map((doc) => (
          <Card key={doc.upload_id} sx={{ mb: 2 }}>
            <ListItem>
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <DocumentIcon color="primary" />
                    <Typography variant="subtitle1">
                      {doc.document_info.filename}
                    </Typography>
                    <Chip 
                      label={doc.status.replace('_', ' ').toUpperCase()}
                      color={getStatusColor(doc.status)}
                      size="small"
                    />
                    {doc.generation_metadata?.analyst_estimates_included && (
                      <Chip 
                        label="Enhanced with Estimates"
                        color="primary"
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Type: {doc.document_info.document_type} • 
                      Uploaded: {formatDate(doc.document_info.upload_date)} • 
                      Analyzed: {formatDate(doc.analysis_date)}
                    </Typography>
                    {doc.generation_metadata && (
                      <Typography variant="body2" color="text.secondary">
                        Model: {doc.generation_metadata.model} • 
                        Context Sources: {doc.generation_metadata.context_documents_count}
                        {doc.generation_metadata.analyst_estimates_included && (
                          <> • Analyst Estimates: {doc.generation_metadata.analyst_estimates_length} chars</>
                        )}
                      </Typography>
                    )}
                  </Box>
                }
              />
              <Box display="flex" alignItems="center" gap={1}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<ViewIcon />}
                  onClick={() => openDocumentModal(doc)}
                >
                  View Analysis
                </Button>
                <IconButton 
                  onClick={() => toggleDocExpansion(doc.upload_id)}
                  size="small"
                >
                  {expandedDoc === doc.upload_id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>
            </ListItem>

            <Collapse in={expandedDoc === doc.upload_id} timeout="auto" unmountOnExit>
              <CardContent sx={{ pt: 0 }}>
                {/* Executive Summary Preview */}
                {doc.analysis.executive_summary && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      <CheckCircleIcon sx={{ verticalAlign: 'middle', mr: 1, fontSize: 16 }} />
                      Executive Summary
                    </Typography>
                    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
                      <SimpleMarkdown>{doc.analysis.executive_summary}</SimpleMarkdown>
                    </Paper>
                  </Box>
                )}

                {/* Key Changes Preview */}
                {doc.analysis.key_changes && doc.analysis.key_changes.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      <TrendingUpIcon sx={{ verticalAlign: 'middle', mr: 1, fontSize: 16 }} />
                      Key Changes ({doc.analysis.key_changes.length})
                    </Typography>
                    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
                      <SimpleMarkdown>{doc.analysis.key_changes.slice(0, 3).join('\n\n')}</SimpleMarkdown>
                      {doc.analysis.key_changes.length > 3 && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                          ...and {doc.analysis.key_changes.length - 3} more items
                        </Typography>
                      )}
                    </Paper>
                  </Box>
                )}

                {/* Analyst Estimates Preview */}
                {doc.analysis.analyst_estimates_comparison && doc.analysis.analyst_estimates_comparison.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      <TimelineIcon sx={{ verticalAlign: 'middle', mr: 1, fontSize: 16 }} />
                      Analyst Estimates vs Actuals
                    </Typography>
                    <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                      <SimpleMarkdown>{doc.analysis.analyst_estimates_comparison.slice(0, 2).join('\n\n')}</SimpleMarkdown>
                      {doc.analysis.analyst_estimates_comparison.length > 2 && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                          ...view full analysis for complete comparison
                        </Typography>
                      )}
                    </Paper>
                  </Box>
                )}

                <Box display="flex" justifyContent="flex-end">
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<ViewIcon />}
                    onClick={() => openDocumentModal(doc)}
                  >
                    View Complete Analysis
                  </Button>
                </Box>
              </CardContent>
            </Collapse>
          </Card>
        ))}
      </List>

      {/* Modal for Full Document Analysis */}
      <Modal
        open={modalOpen}
        onClose={closeModal}
        aria-labelledby="document-analysis-modal"
      >
        <Box
          sx={{
            position: 'absolute',
            top: '5%',
            left: '5%',
            width: '90%',
            height: '90%',
            bgcolor: 'background.paper',
            borderRadius: 2,
            boxShadow: 24,
            overflow: 'auto',
            p: 3
          }}
        >
          {selectedDoc && (
            <Box>
              {/* Modal Header */}
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Box>
                  <Typography variant="h5" gutterBottom>
                    Document Analysis: {selectedDoc.document_info.filename}
                  </Typography>
                  <Typography variant="subtitle1" color="text.secondary">
                    Batch: {batchName} • Company: {ticker}
                  </Typography>
                </Box>
                <IconButton onClick={closeModal} size="large">
                  <CloseIcon />
                </IconButton>
              </Box>

              {/* Document Info */}
              <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                <Typography variant="body2">
                  <strong>Type:</strong> {selectedDoc.document_info.document_type} • 
                  <strong> Uploaded:</strong> {formatDate(selectedDoc.document_info.upload_date)} • 
                  <strong> Analyzed:</strong> {formatDate(selectedDoc.analysis_date)}
                </Typography>
                <Chip 
                  label={selectedDoc.status.replace('_', ' ').toUpperCase()}
                  color={getStatusColor(selectedDoc.status)}
                  size="small"
                  sx={{ mt: 1 }}
                />
              </Paper>

              {/* Analysis Content */}
              <Box sx={{ mb: 3 }}>
                {/* Executive Summary */}
                {selectedDoc.analysis.executive_summary && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      <CheckCircleIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Executive Summary
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.executive_summary}</SimpleMarkdown>
                  </Paper>
                )}

                {/* Key Changes */}
                {selectedDoc.analysis.key_changes && selectedDoc.analysis.key_changes.length > 0 && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      <TrendingUpIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Key Changes
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.key_changes.join('\n\n')}</SimpleMarkdown>
                  </Paper>
                )}

                {/* Analyst Estimates Comparison */}
                {selectedDoc.analysis.analyst_estimates_comparison && selectedDoc.analysis.analyst_estimates_comparison.length > 0 && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      <TimelineIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Analyst Estimates vs Actuals Comparison
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.analyst_estimates_comparison.join('\n\n')}</SimpleMarkdown>
                  </Paper>
                )}

                {/* Financial Performance */}
                {selectedDoc.analysis.financial_performance && selectedDoc.analysis.financial_performance.length > 0 && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Financial Performance
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.financial_performance.join('\n\n')}</SimpleMarkdown>
                  </Paper>
                )}

                {/* New Insights */}
                {selectedDoc.analysis.new_insights && selectedDoc.analysis.new_insights.length > 0 && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      New Insights
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.new_insights.join('\n\n')}</SimpleMarkdown>
                  </Paper>
                )}

                {/* Potential Thesis Impact */}
                {selectedDoc.analysis.potential_thesis_impact && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Potential Thesis Impact
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.potential_thesis_impact}</SimpleMarkdown>
                  </Paper>
                )}

                {/* Requires Attention */}
                {selectedDoc.analysis.requires_attention && selectedDoc.analysis.requires_attention.length > 0 && (
                  <Paper sx={{ p: 2, mb: 2, bgcolor: 'warning.light' }}>
                    <Typography variant="h6" gutterBottom>
                      Requires Attention
                    </Typography>
                    <SimpleMarkdown>{selectedDoc.analysis.requires_attention.join('\n\n')}</SimpleMarkdown>
                  </Paper>
                )}
              </Box>

              {/* Generation Metadata */}
              {selectedDoc.generation_metadata && (
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">
                      Analysis Generation Details
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<CodeIcon />}
                      onClick={() => setShowPrompt(!showPrompt)}
                    >
                      {showPrompt ? 'Hide' : 'View'} Prompt
                    </Button>
                  </Box>

                  <Box display="flex" flexWrap="wrap" gap={2} mb={2}>
                    <Box>
                      <Typography variant="body2" color="textSecondary">Model</Typography>
                      <Typography variant="body1">{selectedDoc.generation_metadata.model}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="textSecondary">Analysis Type</Typography>
                      <Typography variant="body1">{selectedDoc.generation_metadata.analysis_type}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="textSecondary">Context Sources</Typography>
                      <Typography variant="body1">{selectedDoc.generation_metadata.context_documents_count}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="textSecondary">Generated</Typography>
                      <Typography variant="body1">{formatDate(selectedDoc.generation_metadata.generation_timestamp)}</Typography>
                    </Box>
                    {selectedDoc.generation_metadata.analyst_estimates_included && (
                      <Box>
                        <Typography variant="body2" color="textSecondary">Analyst Estimates</Typography>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1">Included</Typography>
                          <Chip label="Enhanced" size="small" color="primary" variant="outlined" />
                        </Box>
                      </Box>
                    )}
                  </Box>

                  <Collapse in={showPrompt}>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Prompt Used for Analysis:
                      </Typography>
                      <Paper sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 300, overflow: 'auto' }}>
                        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                          {selectedDoc.generation_metadata.prompt_used}
                        </Typography>
                      </Paper>
                    </Box>
                  </Collapse>
                </Paper>
              )}

              {/* Context Sources */}
              {selectedDoc.context_sources && selectedDoc.context_sources.length > 0 && (
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Analysis Context Sources
                  </Typography>
                  <Typography variant="body2" paragraph>
                    This analysis was generated using context from the following sources:
                  </Typography>
                  <List dense>
                    {selectedDoc.context_sources.map((source, index) => (
                      <ListItem key={index} disablePadding>
                        <ListItemText 
                          primary={source.content.substring(0, 100) + '...'}
                          secondary={`Relevance: ${(1 - source.distance).toFixed(3)} • Type: ${source.metadata?.content_type || 'Unknown'}`}
                          sx={{ ml: 1 }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              )}
            </Box>
          )}
        </Box>
      </Modal>
    </Box>
  );
};

export default BatchDocumentAnalysisDisplay;
