import React, { useState, useRef } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  LinearProgress,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  IconButton
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  AttachFile as AttachFileIcon,
  Analytics as AnalyticsIcon
} from '@mui/icons-material';
import { documentService, Document, DocumentAnalysis, UploadResponse } from '../../services/documentService';
import { batchService, Batch } from '../../services/batchService';
import DocumentAnalysisDisplay from './DocumentAnalysisDisplay';

interface DocumentUploadProps {
  ticker: string;
  onUploadComplete?: (documents: Document[]) => void;
  onBatchCreated?: (batch: Batch) => void;
}

interface UploadingFile {
  file: File;
  progress: number;
  status: 'uploading' | 'success' | 'error';
  document?: Document;
  error?: string;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ ticker, onUploadComplete, onBatchCreated }) => {
  const [selectedDocumentType, setSelectedDocumentType] = useState<string>('10-Q');
  const [description, setDescription] = useState<string>('');
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<DocumentAnalysis[]>([]);
  const [showAnalysis, setShowAnalysis] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const documentTypes = [
    { value: '10-Q', label: '10-Q Quarterly Report' },
    { value: '10-K', label: '10-K Annual Report' },
    { value: '8-K', label: '8-K Current Report' },
    { value: 'earnings_call', label: 'Earnings Call Transcript' },
    { value: 'investor_presentation', label: 'Investor Presentation' },
    { value: 'press_release', label: 'Press Release' },
    { value: 'other', label: 'Other Document' }
  ];

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      uploadFiles(Array.from(files));
    }
  };

  const uploadFiles = async (files: File[]) => {
    setGlobalError(null);
    
    // Initialize uploading files state
    const initialUploadingFiles: UploadingFile[] = files.map(file => ({
      file,
      progress: 0,
      status: 'uploading'
    }));
    
    setUploadingFiles(prev => [...prev, ...initialUploadingFiles]);

    // Upload files sequentially to avoid overwhelming the server
    const results: Document[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      try {
        // Update progress to show upload started
        setUploadingFiles(prev => prev.map(f => 
          f.file === file ? { ...f, progress: 25 } : f
        ));

        const uploadResponse: UploadResponse = await documentService.uploadDocument(
          ticker,
          file,
          selectedDocumentType,
          description || undefined
        );

        // Update progress to show upload completed
        setUploadingFiles(prev => prev.map(f => 
          f.file === file ? { 
            ...f, 
            progress: 100, 
            status: 'success', 
            document: uploadResponse.document 
          } : f
        ));

        results.push(uploadResponse.document);

      } catch (error: any) {
        console.error(`Failed to upload ${file.name}:`, error);
        
        setUploadingFiles(prev => prev.map(f => 
          f.file === file ? { 
            ...f, 
            progress: 0, 
            status: 'error',
            error: error.response?.data?.error?.message || 'Upload failed'
          } : f
        ));
      }
    }

    // Notify parent component of successful uploads
    if (results.length > 0 && onUploadComplete) {
      onUploadComplete(results);
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const triggerBatchAnalysis = async () => {
    const successfulUploads = uploadingFiles.filter(f => f.status === 'success' && f.document);
    
    if (successfulUploads.length === 0) {
      setGlobalError('No successfully uploaded documents to analyze');
      return;
    }

    try {
      setGlobalError(null);
      
      // Update status to show analysis in progress
      setUploadingFiles(prev => prev.map(f => 
        f.status === 'success' ? { ...f, progress: 50 } : f
      ));

      const uploadIds = successfulUploads.map(f => f.document!.upload_id);
      console.log('Creating batch for upload IDs:', uploadIds);

      // Step 1: Create a batch
      const batchName = `Analysis Batch - ${new Date().toLocaleDateString()}`;
      const batchDescription = `Batch analysis of ${uploadIds.length} documents (${successfulUploads.map(f => f.document!.filename).join(', ')})`;
      
      const batch = await batchService.createBatch(ticker, {
        upload_ids: uploadIds,
        name: batchName,
        description: batchDescription
      });
      
      console.log('Batch created:', batch);

      // Step 2: Trigger batch analysis
      const batchResult = await batchService.analyzeBatch(ticker, batch.batch_id);
      
      console.log('Batch analysis completed:', batchResult);
      
      // Show successful analyses
      if (batchResult.analyzed_documents && batchResult.analyzed_documents.length > 0) {
        setAnalysisResults(batchResult.analyzed_documents);
        setShowAnalysis(true);
        
        // Clear successfully analyzed uploads
        setUploadingFiles(prev => prev.filter(f => f.status !== 'success'));
        
        // Scroll to top to show analysis results
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Notify parent about batch creation
        if (onBatchCreated) {
          onBatchCreated(batch);
        }
      }
      
      // Show errors for failed analyses
      if (batchResult.failed_analyses && batchResult.failed_analyses.length > 0) {
        const errorMessages = batchResult.failed_analyses
          .map(fail => `${fail.upload_id}: ${fail.error}`)
          .join('; ');
        setGlobalError(`Some analyses failed: ${errorMessages}`);
      }
      
      if (batchResult.successful_analyses === 0) {
        setGlobalError('All document analyses failed. Please check the documents and try again.');
      }
      
    } catch (error: any) {
      console.error('Batch analysis failed:', error);
      setGlobalError(`Failed to analyze documents: ${error.message}`);
      
      // Reset upload progress on error
      setUploadingFiles(prev => prev.map(f => 
        f.status === 'success' ? { ...f, progress: 100 } : f
      ));
    }
  };

  const handleCloseAnalysis = () => {
    setShowAnalysis(false);
    setAnalysisResults([]);
    // Clear successful uploads when analysis is closed
    setUploadingFiles(prev => prev.filter(f => f.status !== 'success'));
  };

  const removeUploadingFile = (index: number) => {
    setUploadingFiles(prev => prev.filter((_, idx) => idx !== index));
  };

  const retryUpload = (index: number) => {
    const fileToRetry = uploadingFiles[index];
    if (fileToRetry && fileToRetry.status === 'error') {
      uploadFiles([fileToRetry.file]);
      // Remove the failed one from the list
      removeUploadingFile(index);
    }
  };

  return (
    <Box>
      {/* Analysis Results - displayed prominently at the top when available */}
      {showAnalysis && analysisResults.length > 0 && (
        <Card sx={{ mb: 3, border: '2px solid', borderColor: 'primary.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5" sx={{ color: 'primary.main', display: 'flex', alignItems: 'center' }}>
                <AnalyticsIcon sx={{ mr: 1 }} />
                Analysis Results ({analysisResults.length} document{analysisResults.length > 1 ? 's' : ''})
              </Typography>
              <Button 
                onClick={handleCloseAnalysis} 
                variant="outlined"
                size="small"
                startIcon={<RefreshIcon />}
              >
                Continue Uploading
              </Button>
            </Box>
            {analysisResults.map((analysis) => (
              <DocumentAnalysisDisplay
                key={analysis.upload_id}
                analysis={analysis}
                ticker={ticker}
                onClose={analysisResults.length === 1 ? handleCloseAnalysis : undefined}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Upload Section */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Upload Documents for {ticker}
          </Typography>
          
          <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
            Upload multiple documents first, then trigger batch analysis. 
            This allows you to upload different document types and analyze them together.
          </Typography>

        {globalError && (
          <Paper sx={{ mb: 2, p: 2, bgcolor: 'error.light' }}>
            <Typography color="error">
              {globalError}
            </Typography>
          </Paper>
        )}

        {/* Document Type Selection */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Document Type</InputLabel>
            <Select
              value={selectedDocumentType}
              label="Document Type"
              onChange={(e) => setSelectedDocumentType(e.target.value)}
            >
              {documentTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <TextField
            label="Description (Optional)"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDescription(e.target.value)}
            sx={{ flex: 1 }}
            placeholder="Brief description of the document..."
          />
        </Box>

        {/* File Upload Area */}
        <Box
          sx={{
            border: '2px dashed',
            borderColor: 'grey.300',
            borderRadius: 1,
            p: 4,
            textAlign: 'center',
            mb: 3
          }}
        >
          <CloudUploadIcon sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Select Files to Upload
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Supported formats: PDF, DOC, DOCX, TXT (max 50MB each)
          </Typography>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.txt"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          <Button
            variant="contained"
            startIcon={<AttachFileIcon />}
            onClick={() => fileInputRef.current?.click()}
            size="large"
          >
            Select Files
          </Button>
        </Box>

        {/* Uploading Files Progress */}
        {uploadingFiles.length > 0 && (
          <Box>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle1" gutterBottom>
              Upload Progress
            </Typography>
            
            <List>
              {uploadingFiles.map((uploadingFile, index) => (
                <ListItem
                  key={index}
                  secondaryAction={
                    uploadingFile.status === 'error' ? (
                      <Box>
                        <IconButton 
                          edge="end" 
                          onClick={() => retryUpload(index)}
                          color="primary"
                          sx={{ mr: 1 }}
                        >
                          <RefreshIcon />
                        </IconButton>
                        <IconButton 
                          edge="end" 
                          onClick={() => removeUploadingFile(index)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    ) : (
                      uploadingFile.status === 'success' && (
                        <Chip
                          icon={<CheckCircleIcon />}
                          label="Upload Complete"
                          color="success"
                          size="small"
                        />
                      )
                    )
                  }
                >
                  <ListItemIcon>
                    {uploadingFile.status === 'success' ? (
                      <CheckCircleIcon color="success" />
                    ) : uploadingFile.status === 'error' ? (
                      <ErrorIcon color="error" />
                    ) : (
                      <DescriptionIcon color="primary" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={uploadingFile.file.name}
                    secondary={
                      <Box>
                        <Typography variant="body2" color="textSecondary">
                          {(uploadingFile.file.size / 1024 / 1024).toFixed(2)} MB
                        </Typography>
                        {uploadingFile.status === 'uploading' && (
                          <Box sx={{ mt: 1 }}>
                            <LinearProgress 
                              variant="determinate" 
                              value={uploadingFile.progress} 
                            />
                          </Box>
                        )}
                        {uploadingFile.status === 'error' && uploadingFile.error && (
                          <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                            {uploadingFile.error}
                          </Typography>
                        )}
                        {uploadingFile.status === 'success' && uploadingFile.document && (
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" color="success.main">
                              Upload successful - Ready for analysis
                            </Typography>
                            {uploadingFile.progress === 50 && (
                              <Box sx={{ mt: 1 }}>
                                <LinearProgress variant="indeterminate" />
                                <Typography variant="body2" color="primary">
                                  Analysis in progress...
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
            
            {/* Batch Analysis Button */}
            {uploadingFiles.some(f => f.status === 'success') && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={triggerBatchAnalysis}
                  disabled={uploadingFiles.some(f => f.progress === 50)} // Disable if analysis in progress
                  size="large"
                  startIcon={<AnalyticsIcon />}
                >
                  Analyze Uploaded Documents ({uploadingFiles.filter(f => f.status === 'success').length})
                </Button>
              </Box>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
    </Box>
  );
};

export default DocumentUpload;
