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
  ListItemSecondaryAction,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Description as DescriptionIcon,
  Visibility as VisibilityIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Assessment as AssessmentIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { documentService, Document } from '../../services/documentService';
import AnalysisReview from './AnalysisReview';

interface DocumentListProps {
  ticker: string;
  onRefresh?: () => void;
}

const DocumentList: React.FC<DocumentListProps> = ({ ticker, onRefresh }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [showAnalysisReview, setShowAnalysisReview] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, [ticker]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await documentService.getDocuments(ticker);
      setDocuments(docs);
    } catch (err: any) {
      console.error('Failed to load documents:', err);
      setError(err.response?.data?.error?.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleViewAnalysis = (uploadId: string) => {
    setSelectedDocument(uploadId);
    setShowAnalysisReview(true);
  };

  const handleAnalysisApproved = () => {
    setShowAnalysisReview(false);
    setSelectedDocument(null);
    loadDocuments(); // Refresh the list
    if (onRefresh) onRefresh();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'analysis_ready':
        return <ScheduleIcon color="warning" />;
      case 'analysis_approved':
        return <CheckCircleIcon color="success" />;
      case 'report_generated':
        return <AssessmentIcon color="success" />;
      case 'analysis_error':
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <CircularProgress size={24} />;
    }
  };

  const getActionButton = (document: Document) => {
    if (document.status === 'analysis_ready') {
      return (
        <Button
          size="small"
          variant="contained"
          color="warning"
          startIcon={<VisibilityIcon />}
          onClick={() => handleViewAnalysis(document.upload_id)}
        >
          Review Analysis
        </Button>
      );
    }

    if (document.status === 'analysis_approved') {
      return (
        <Button
          size="small"
          variant="contained"
          color="success"
          startIcon={<AssessmentIcon />}
          onClick={() => {/* Navigate to report generation */}}
        >
          Generate Report
        </Button>
      );
    }

    if (document.status === 'report_generated') {
      return (
        <Button
          size="small"
          variant="outlined"
          color="primary"
          startIcon={<VisibilityIcon />}
          onClick={() => {/* View generated report */}}
        >
          View Report
        </Button>
      );
    }

    return null;
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
            <CircularProgress />
            <Typography variant="body1" sx={{ ml: 2 }}>
              Loading documents...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
            <Button onClick={loadDocuments} sx={{ ml: 2 }}>
              Retry
            </Button>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Uploaded Documents ({documents.length})
          </Typography>
          <IconButton onClick={loadDocuments} size="small">
            <RefreshIcon />
          </IconButton>
        </Box>

        {documents.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <DescriptionIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
            <Typography variant="body1" color="textSecondary">
              No documents uploaded yet
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Upload a document to start the two-stage analysis workflow
            </Typography>
          </Box>
        ) : (
          <List>
            {documents.map((document, index) => (
              <React.Fragment key={document.upload_id}>
                <ListItem alignItems="flex-start">
                  <ListItemIcon>
                    {getStatusIcon(document.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle1">
                          {document.filename}
                        </Typography>
                        <Chip
                          label={document.document_type?.replace('_', ' ') || 'Unknown'}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="textSecondary">
                          Uploaded: {new Date(document.upload_date).toLocaleDateString()}
                        </Typography>
                        {document.analysis_date && (
                          <Typography variant="body2" color="textSecondary">
                            Analysis: {new Date(document.analysis_date).toLocaleDateString()}
                          </Typography>
                        )}
                        {document.approval_date && (
                          <Typography variant="body2" color="textSecondary">
                            Approved: {new Date(document.approval_date).toLocaleDateString()}
                          </Typography>
                        )}
                        <Box sx={{ mt: 1 }}>
                          <Chip
                            label={documentService.getStatusDisplay(document.status)}
                            color={documentService.getStatusColor(document.status)}
                            size="small"
                          />
                        </Box>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    {getActionButton(document)}
                  </ListItemSecondaryAction>
                </ListItem>
                {index < documents.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </CardContent>

      {/* Analysis Review Dialog */}
      <Dialog
        open={showAnalysisReview}
        onClose={() => setShowAnalysisReview(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Document Analysis Review
        </DialogTitle>
        <DialogContent>
          {selectedDocument && (
            <AnalysisReview
              ticker={ticker}
              uploadId={selectedDocument}
              onAnalysisApproved={handleAnalysisApproved}
              onClose={() => setShowAnalysisReview(false)}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAnalysisReview(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default DocumentList;
