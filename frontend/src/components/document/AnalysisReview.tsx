import React, { useState, useEffect } from 'react';
import SimpleMarkdown from '../common/SimpleMarkdown';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Button,
  Grid,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
  IconButton,
  Collapse
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Source as SourceIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { documentService, DocumentAnalysis } from '../../services/documentService';

interface AnalysisReviewProps {
  ticker: string;
  uploadId: string;
  onClose?: () => void;
}

const AnalysisReview: React.FC<AnalysisReviewProps> = ({
  ticker,
  uploadId,
  onClose
}) => {
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    summary: true,
    changes: true,
    insights: true,
    impact: true,
    financial: false,
    segments: false,
    strategic: false,
    forward: false,
    attention: false
  });

  useEffect(() => {
    loadAnalysis();
  }, [ticker, uploadId]);

  const loadAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const analysisData = await documentService.getAnalysis(ticker, uploadId);
      setAnalysis(analysisData);
    } catch (err: any) {
      console.error('Failed to load analysis:', err);
      setError(err.response?.data?.error?.message || 'Failed to load analysis results');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getConfidenceColor = (confidence: string) => {
    if (confidence.toLowerCase().includes('high')) return 'success';
    if (confidence.toLowerCase().includes('medium')) return 'warning';
    if (confidence.toLowerCase().includes('low')) return 'error';
    return 'default';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Loading analysis results...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
        <Button onClick={loadAnalysis} sx={{ ml: 2 }}>
          Retry
        </Button>
      </Alert>
    );
  }

  if (!analysis) {
    return (
      <Alert severity="info">
        Analysis results not available. Please check the document status.
      </Alert>
    );
  }

  return (
    <Box sx={{ maxWidth: '100%', margin: '0 auto' }}>
      {/* Document Info Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ flex: 1, minWidth: '300px' }}>
              <Typography variant="h6" gutterBottom>
                Initial Analysis: {analysis.document_info.filename}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip 
                  icon={<AssessmentIcon />}
                  label={analysis.document_info.document_type.replace('_', ' ')}
                  variant="outlined"
                  size="small"
                />
                <Chip 
                  label={analysis.status}
                  color="warning"
                  size="small"
                />
                <Chip 
                  label={`Analyzed: ${new Date(analysis.analysis_date).toLocaleDateString()}`}
                  variant="outlined"
                  size="small"
                />
              </Box>
            </Box>
            <Box sx={{ textAlign: 'right' }}>
              {onClose && (
                <Button
                  variant="outlined"
                  onClick={onClose}
                >
                  Close
                </Button>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Executive Summary */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Executive Summary</Typography>
            <IconButton onClick={() => toggleSection('summary')}>
              {expandedSections.summary ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={expandedSections.summary}>
            <Box sx={{ mt: 2 }}>
              <SimpleMarkdown>
                {analysis.analysis.executive_summary || 'No executive summary available'}
              </SimpleMarkdown>
            </Box>
          </Collapse>
        </CardContent>
      </Card>

      {/* Key Changes */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Key Changes Identified</Typography>
            <IconButton onClick={() => toggleSection('changes')}>
              {expandedSections.changes ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={expandedSections.changes}>
            {analysis.analysis.key_changes && analysis.analysis.key_changes.length > 0 ? (
              <List>
                {analysis.analysis.key_changes.map((change, index) => (
                  <ListItem key={index} divider>
                    <ListItemText 
                      primary={
                        <SimpleMarkdown variant="body2">
                          {change}
                        </SimpleMarkdown>
                      } 
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                No key changes identified
              </Typography>
            )}
          </Collapse>
        </CardContent>
      </Card>

      {/* New Insights */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">New Insights Discovered</Typography>
            <IconButton onClick={() => toggleSection('insights')}>
              {expandedSections.insights ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={expandedSections.insights}>
            {analysis.analysis.new_insights && analysis.analysis.new_insights.length > 0 ? (
              <List>
                {analysis.analysis.new_insights.map((insight, index) => (
                  <ListItem key={index} divider>
                    <ListItemText 
                      primary={
                        <SimpleMarkdown variant="body2">
                          {insight}
                        </SimpleMarkdown>
                      } 
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                No new insights identified
              </Typography>
            )}
          </Collapse>
        </CardContent>
      </Card>

      {/* Investment Thesis Impact */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Investment Thesis Impact</Typography>
            <IconButton onClick={() => toggleSection('impact')}>
              {expandedSections.impact ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={expandedSections.impact}>
            <Box sx={{ mt: 2 }}>
              <SimpleMarkdown>
                {analysis.analysis.potential_thesis_impact || 'No thesis impact assessment available'}
              </SimpleMarkdown>
            </Box>
          </Collapse>
        </CardContent>
      </Card>

      {/* Financial Performance Details */}
      {analysis.analysis.financial_performance && analysis.analysis.financial_performance.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Financial Performance Analysis</Typography>
              <IconButton onClick={() => toggleSection('financial')}>
                {expandedSections.financial ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Collapse in={expandedSections.financial}>
              <List>
                {analysis.analysis.financial_performance.map((item, index) => (
                  <ListItem key={index} divider>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Business Segments */}
      {analysis.analysis.business_segments && analysis.analysis.business_segments.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Business Segments Analysis</Typography>
              <IconButton onClick={() => toggleSection('segments')}>
                {expandedSections.segments ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Collapse in={expandedSections.segments}>
              <List>
                {analysis.analysis.business_segments.map((item, index) => (
                  <ListItem key={index} divider>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Strategic Developments */}
      {analysis.analysis.strategic_developments && analysis.analysis.strategic_developments.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Strategic Developments</Typography>
              <IconButton onClick={() => toggleSection('strategic')}>
                {expandedSections.strategic ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Collapse in={expandedSections.strategic}>
              <List>
                {analysis.analysis.strategic_developments.map((item, index) => (
                  <ListItem key={index} divider>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Forward-Looking Analysis */}
      {analysis.analysis.forward_looking_insights && analysis.analysis.forward_looking_insights.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Forward-Looking Analysis</Typography>
              <IconButton onClick={() => toggleSection('forward')}>
                {expandedSections.forward ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Collapse in={expandedSections.forward}>
              <List>
                {analysis.analysis.forward_looking_insights.map((item, index) => (
                  <ListItem key={index} divider>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Items Requiring Attention */}
      {analysis.analysis.requires_attention && analysis.analysis.requires_attention.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" sx={{ color: 'warning.main' }}>
                Items Requiring Attention
              </Typography>
              <IconButton onClick={() => toggleSection('attention')}>
                {expandedSections.attention ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Collapse in={expandedSections.attention}>
              <List>
                {analysis.analysis.requires_attention.map((item, index) => (
                  <ListItem key={index} divider>
                    <ListItemText 
                      primary={item}
                      sx={{ '& .MuiListItemText-primary': { color: 'warning.main' } }}
                    />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Confidence Assessment */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Confidence Assessment</Typography>
          <Chip 
            label={analysis.analysis.confidence_assessment || 'Not specified'}
            color={getConfidenceColor(analysis.analysis.confidence_assessment || '')}
            variant="outlined"
          />
        </CardContent>
      </Card>

      {/* Context Sources */}
      {analysis.context_sources && analysis.context_sources.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <SourceIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Context Sources
            </Typography>
            <List>
              {analysis.context_sources.map((source, index) => (
                <ListItem key={index}>
                  <ListItemText 
                    primary={source.document}
                    secondary={`Relevance: ${Math.round(source.relevance_score * 100)}% (${source.type})`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default AnalysisReview;
