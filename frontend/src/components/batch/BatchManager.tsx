import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  LinearProgress,
  Paper,
  IconButton,
  Collapse,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Folder as FolderIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Analytics as AnalyticsIcon,
  Description as DocumentIcon,
  Assignment as ReportIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { batchService, Batch, BatchReport } from '../../services/batchService';
import BatchReportDisplay from './BatchReportDisplay';
import BatchDocumentAnalysisDisplay from './BatchDocumentAnalysisDisplay';

interface BatchManagerProps {
  ticker: string;
}

const BatchManager: React.FC<BatchManagerProps> = ({ ticker }) => {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedBatch, setExpandedBatch] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState<string | null>(null);
  const [reportContent, setReportContent] = useState<{[batchId: string]: BatchReport}>({});
  const [deletingBatch, setDeletingBatch] = useState<string | null>(null);

  useEffect(() => {
    loadBatches();
  }, [ticker]);

  const loadBatches = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await batchService.getBatches(ticker);
      setBatches(response.batches);
    } catch (err: any) {
      console.error('Failed to load batches:', err);
      setError('Failed to load batches. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const generateBatchReport = async (batchId: string) => {
    try {
      setGeneratingReport(batchId);
      setError(null);
      
      const report = await batchService.generateBatchReport(ticker, batchId);
      
      setReportContent(prev => ({
        ...prev,
        [batchId]: report
      }));
      
      // Update batch status in local state
      setBatches(prev => prev.map(batch => 
        batch.batch_id === batchId 
          ? { ...batch, report_status: 'generated', report_content: report }
          : batch
      ));
      
    } catch (err: any) {
      console.error('Failed to generate batch report:', err);
      setError(`Failed to generate report: ${err.message}`);
    } finally {
      setGeneratingReport(null);
    }
  };

  const copyReportToClipboard = async (report: BatchReport) => {
    try {
      await navigator.clipboard.writeText(report.full_content);
      alert('Report content copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      alert('Failed to copy to clipboard. Please copy manually.');
    }
  };

  const deleteBatch = async (batchId: string) => {
    if (!window.confirm('Are you sure you want to delete this batch? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingBatch(batchId);
      setError(null);
      
      await batchService.deleteBatch(ticker, batchId);
      
      // Remove batch from local state
      setBatches(prev => prev.filter(batch => batch.batch_id !== batchId));
      
      // Clean up any stored report content
      setReportContent(prev => {
        const updated = { ...prev };
        delete updated[batchId];
        return updated;
      });
      
      // Close expansion if this batch was expanded
      if (expandedBatch === batchId) {
        setExpandedBatch(null);
      }
      
    } catch (err: any) {
      console.error('Failed to delete batch:', err);
      setError(`Failed to delete batch: ${err.message}`);
    } finally {
      setDeletingBatch(null);
    }
  };

  const getStatusColor = (status: string) => {
    return batchService.getBatchStatusColor(status);
  };

  const toggleBatchExpansion = (batchId: string) => {
    setExpandedBatch(expandedBatch === batchId ? null : batchId);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">
          Document Batches ({batches.length})
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadBatches}
          size="small"
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {batches.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <FolderIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Document Batches Found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Upload and analyze documents to create your first batch.
          </Typography>
        </Paper>
      ) : (
        <List>
          {batches.map((batch) => (
            <Card key={batch.batch_id} sx={{ mb: 2 }}>
              <ListItem>
                <ListItemIcon>
                  <FolderIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle1">
                        {batch.name}
                      </Typography>
                      <Chip 
                        label={batchService.getBatchStatusDisplay(batch.status)}
                        color={getStatusColor(batch.status)}
                        size="small"
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        {batch.description}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Created: {batchService.formatBatchDate(batch.created_at)} • 
                        Documents: {batch.documents.length}
                        {batch.analysis_status === 'completed' && (
                          <> • Analyzed: {batch.analyzed_documents}</>
                        )}
                      </Typography>
                    </Box>
                  }
                />
                <Box display="flex" alignItems="center" gap={1}>
                  <LinearProgress
                    variant="determinate"
                    value={batchService.getBatchProgress(batch)}
                    sx={{ width: 100, mr: 1 }}
                  />
                  <IconButton 
                    onClick={() => deleteBatch(batch.batch_id)}
                    size="small"
                    color="error"
                    disabled={deletingBatch === batch.batch_id}
                    title="Delete batch"
                  >
                    {deletingBatch === batch.batch_id ? <CircularProgress size={20} /> : <DeleteIcon />}
                  </IconButton>
                  <IconButton 
                    onClick={() => toggleBatchExpansion(batch.batch_id)}
                    size="small"
                  >
                    {expandedBatch === batch.batch_id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </IconButton>
                </Box>
              </ListItem>

              <Collapse in={expandedBatch === batch.batch_id} timeout="auto" unmountOnExit>
                <CardContent sx={{ pt: 0 }}>
                  {/* Documents in batch */}
                  <Typography variant="subtitle2" gutterBottom>
                    Documents ({batch.documents.length}):
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    {batch.documents.map((doc, index) => (
                      <Chip
                        key={doc.upload_id}
                        icon={<DocumentIcon />}
                        label={`${doc.filename} (${doc.document_type})`}
                        size="small"
                        variant="outlined"
                        sx={{ m: 0.5 }}
                      />
                    ))}
                  </Box>

                  {/* Analysis Status */}
                  {batch.analysis_status === 'completed' && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Analysis Complete:
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Completed: {batchService.formatBatchDate(batch.analysis_completed_at || '')}
                      </Typography>
                    </Box>
                  )}

                  {/* Individual Document Analysis Display */}
                  {batch.analysis_status === 'completed' && batch.analyzed_documents_data && batch.analyzed_documents_data.length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <BatchDocumentAnalysisDisplay
                        documents={batch.analyzed_documents_data}
                        batchName={batch.name}
                        ticker={ticker}
                      />
                    </Box>
                  )}

                  {/* Report Generation */}
                  <Box display="flex" alignItems="center" gap={2}>
                    {batch.analysis_status === 'completed' && batch.report_status !== 'generated' && (
                      <Button
                        variant="contained"
                        startIcon={generatingReport === batch.batch_id ? 
                          <CircularProgress size={20} /> : <ReportIcon />}
                        onClick={() => generateBatchReport(batch.batch_id)}
                        disabled={generatingReport === batch.batch_id}
                      >
                        {generatingReport === batch.batch_id ? 'Generating...' : 'Generate Draft Report'}
                      </Button>
                    )}
                  </Box>

                  {/* Report Content Display */}
                  {(reportContent[batch.batch_id] || batch.report_content) && (
                    <BatchReportDisplay
                      report={reportContent[batch.batch_id] || batch.report_content!}
                      batchName={batch.name}
                      ticker={ticker}
                      onCopy={() => {
                        // Optional: Add success feedback
                      }}
                    />
                  )}
                </CardContent>
              </Collapse>
            </Card>
          ))}
        </List>
      )}
    </Box>
  );
};

export default BatchManager;
