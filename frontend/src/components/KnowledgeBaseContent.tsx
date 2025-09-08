import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  MenuItem,
  Pagination,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  Grid,
  InputAdornment,
  Skeleton
} from '@mui/material';
import {
  Search as SearchIcon,
  Visibility as ViewIcon,
  Close as CloseIcon,
  FilterList as FilterIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import companyService from '../services/companyService';

interface KnowledgeBaseDocument {
  id: string;
  content: string;
  content_preview: string;
  metadata: {
    document_type: string;
    source_file: string;
    processed_date?: string;
    report_date?: string;
    page_number?: number;
    chunk_index?: number;
    contains_analyst_estimates: boolean;
    historical_financial_data: boolean;
    content_priority: number;
  };
}

interface KnowledgeBaseContentProps {
  ticker: string;
}

const KnowledgeBaseContent: React.FC<KnowledgeBaseContentProps> = ({ ticker }) => {
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [documentType, setDocumentType] = useState<string>('');
  const [documentTypes, setDocumentTypes] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeBaseDocument | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const pageSize = 20;

  const fetchDocumentTypes = async () => {
    try {
      const response = await companyService.getKnowledgeBaseDocumentTypes(ticker);
      if (response.success) {
        setDocumentTypes(response.data.document_types);
      }
    } catch (err) {
      console.error('Failed to fetch document types:', err);
    }
  };

  const fetchDocuments = async (currentPage: number = 1, search: string = '', type: string = '') => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await companyService.getKnowledgeBaseContent(
        ticker,
        currentPage,
        pageSize,
        type || undefined,
        search || undefined
      );
      
      if (response.success) {
        setDocuments(response.data.documents);
        setTotalPages(response.data.pagination.total_pages);
        setTotalItems(response.data.pagination.total_items);
      } else {
        setError('Failed to load knowledge base content');
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
      setError('Failed to load knowledge base content');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocumentTypes();
    fetchDocuments();
  }, [ticker]);

  const handleSearch = () => {
    setPage(1);
    fetchDocuments(1, searchQuery, documentType);
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    fetchDocuments(value, searchQuery, documentType);
  };

  const handleDocumentTypeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newType = event.target.value;
    setDocumentType(newType);
    setPage(1);
    fetchDocuments(1, searchQuery, newType);
  };

  const handleViewDocument = (document: KnowledgeBaseDocument) => {
    setSelectedDocument(document);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedDocument(null);
  };

  const getDocumentTypeColor = (type: string): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
    switch (type) {
      case 'past_report': return 'primary';
      case 'investment_data': return 'secondary';
      case 'uploaded_document': return 'info';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: number): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
    if (priority >= 0.7) return 'error';
    if (priority >= 0.4) return 'warning';
    return 'success';
  };

  return (
    <Box>
      {/* Header */}
      <Typography variant="h6" gutterBottom>
        Knowledge Base Content
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Browse and search through the processed documents in the knowledge base for {ticker}.
      </Typography>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                placeholder="Search content..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                select
                label="Document Type"
                value={documentType}
                onChange={handleDocumentTypeChange}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <FilterIcon />
                    </InputAdornment>
                  ),
                }}
              >
                <MenuItem value="">All Types</MenuItem>
                {documentTypes.map((type) => (
                  <MenuItem key={type} value={type}>
                    {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="contained"
                onClick={handleSearch}
              >
                Search
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Results Summary */}
      {!loading && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Showing {documents.length} of {totalItems} documents
          {searchQuery && ` for "${searchQuery}"`}
          {documentType && ` in ${documentType.replace('_', ' ')}`}
        </Typography>
      )}

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Box>
          {[...Array(5)].map((_, index) => (
            <Card key={index} sx={{ mb: 2 }}>
              <CardContent>
                <Skeleton variant="text" width="60%" height={24} />
                <Skeleton variant="text" width="40%" height={20} sx={{ mb: 2 }} />
                <Skeleton variant="text" width="100%" height={16} />
                <Skeleton variant="text" width="100%" height={16} />
                <Skeleton variant="text" width="80%" height={16} />
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Documents List */}
      {!loading && documents.length === 0 && (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No documents found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {searchQuery || documentType 
                ? 'Try adjusting your search or filter criteria.'
                : 'The knowledge base appears to be empty.'}
            </Typography>
          </CardContent>
        </Card>
      )}

      {!loading && documents.map((document) => (
        <Card key={document.id} sx={{ mb: 2 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
              <Box flexGrow={1}>
                <Typography variant="subtitle1" gutterBottom>
                  {document.metadata.source_file}
                </Typography>
                
                {/* Chips */}
                <Box display="flex" gap={1} mb={2} flexWrap="wrap">
                  <Chip
                    label={document.metadata.document_type.replace('_', ' ').toUpperCase()}
                    color={getDocumentTypeColor(document.metadata.document_type)}
                    size="small"
                  />
                  
                  <Chip
                    label={`Priority: ${document.metadata.content_priority.toFixed(1)}`}
                    color={getPriorityColor(document.metadata.content_priority)}
                    size="small"
                  />
                  
                  {document.metadata.contains_analyst_estimates && (
                    <Chip
                      label="Analyst Estimates"
                      color="warning"
                      size="small"
                    />
                  )}
                  
                  {document.metadata.historical_financial_data && (
                    <Chip
                      label="Financial Data"
                      color="info"
                      size="small"
                    />
                  )}
                  
                  {document.metadata.page_number && (
                    <Chip
                      label={`Page ${document.metadata.page_number}`}
                      variant="outlined"
                      size="small"
                    />
                  )}
                </Box>
                
                {/* Content Preview */}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {document.content_preview}
                </Typography>
                
                {/* Metadata */}
                <Typography variant="caption" color="text.secondary">
                  {document.metadata.processed_date && (
                    <>Processed: {format(new Date(document.metadata.processed_date), 'MMM d, yyyy HH:mm')}</>
                  )}
                  {document.metadata.report_date && (
                    <> • Report Date: {format(new Date(document.metadata.report_date), 'MMM d, yyyy')}</>
                  )}
                  {document.metadata.chunk_index !== undefined && (
                    <> • Chunk #{document.metadata.chunk_index}</>
                  )}
                </Typography>
              </Box>
              
              <IconButton
                onClick={() => handleViewDocument(document)}
                color="primary"
                size="small"
              >
                <ViewIcon />
              </IconButton>
            </Box>
          </CardContent>
        </Card>
      ))}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <Box display="flex" justifyContent="center" mt={3}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            size="large"
          />
        </Box>
      )}

      {/* Document View Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {selectedDocument?.metadata.source_file}
            </Typography>
            <IconButton onClick={handleCloseDialog} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedDocument && (
            <Box>
              {/* Document metadata */}
              <Box mb={3}>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Document Type: {selectedDocument.metadata.document_type.replace('_', ' ')}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Priority: {selectedDocument.metadata.content_priority.toFixed(2)}
                    </Typography>
                  </Grid>
                  {selectedDocument.metadata.processed_date && (
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Processed: {format(new Date(selectedDocument.metadata.processed_date), 'PPP p')}
                      </Typography>
                    </Grid>
                  )}
                  {selectedDocument.metadata.report_date && (
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Report Date: {format(new Date(selectedDocument.metadata.report_date), 'PPP')}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </Box>
              
              {/* Full content */}
              <Box 
                sx={{ 
                  maxHeight: '400px', 
                  overflowY: 'auto',
                  backgroundColor: 'grey.50',
                  p: 2,
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap'
                }}
              >
                {selectedDocument.content}
              </Box>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialog}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default KnowledgeBaseContent;
