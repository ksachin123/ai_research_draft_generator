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
  AttachFile as AttachFileIcon
} from '@mui/icons-material';
import { documentService, Document, DocumentAnalysis, UploadResponse } from '../../services/documentService';
import DocumentAnalysisDisplay from './DocumentAnalysisDisplay';

interface DocumentUploadProps {
  ticker: string;
  onUploadComplete?: (documents: Document[]) => void;
}

interface UploadingFile {
  file: File;
  progress: number;
  status: 'uploading' | 'success' | 'error';
  document?: Document;
  error?: string;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ ticker, onUploadComplete }) => {
  const [selectedDocumentType, setSelectedDocumentType] = useState<string>('10-K');
  const [description, setDescription] = useState<string>('');
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<DocumentAnalysis[]>([]);
  const [showAnalysis, setShowAnalysis] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const documentTypes = [
    { value: '10-K', label: '10-K Annual Report' },
    { value: '10-Q', label: '10-Q Quarterly Report' },
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
    const analyses: DocumentAnalysis[] = [];
    
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

        // If analysis is included in upload response, add it to analyses
        if (uploadResponse.analysis) {
          console.log('Analysis included in upload response for:', file.name);
          analyses.push(uploadResponse.analysis);
        }

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

    // Show analysis results if available
    if (analyses.length > 0) {
      console.log('Displaying analysis results from upload response:', analyses);
      setAnalysisResults(analyses);
      setShowAnalysis(true);
    } else if (results.length > 0) {
      // Fallback: Fetch analysis results for successful uploads if not included in response
      try {
        console.log('Fetching analysis results for uploaded documents...');
        const analysisPromises = results.map(doc => 
          documentService.getAnalysis(ticker, doc.upload_id)
        );
        const fetchedAnalyses = await Promise.all(analysisPromises);
        
        console.log('Analysis results fetched successfully:', fetchedAnalyses);
        setAnalysisResults(fetchedAnalyses);
        setShowAnalysis(true);
        
      } catch (error: any) {
        console.error('Failed to fetch analysis results:', error);
        // Still clear uploads after delay even if analysis fetch fails
        setTimeout(() => {
          setUploadingFiles(prev => prev.filter(f => f.status !== 'success'));
        }, 3000);
      }
    } else {
      // Clear completed uploads after a delay if no successful results
      setTimeout(() => {
        setUploadingFiles(prev => prev.filter(f => f.status !== 'success'));
      }, 3000);
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleCloseAnalysis = () => {
    setShowAnalysis(false);
    setAnalysisResults([]);
    // Clear successful uploads when analysis is closed
    setUploadingFiles(prev => prev.filter(f => f.status !== 'success'));
  };

  const handleApproveAnalysis = async (uploadId: string) => {
    try {
      const approvalData = {
        modifications: {},
        notes: 'Analysis approved via UI'
      };

      await documentService.approveAnalysis(ticker, uploadId, approvalData);
      
      // Refresh the analysis to show updated status
      const updatedAnalysis = await documentService.getAnalysis(ticker, uploadId);
      setAnalysisResults(prev => 
        prev.map(analysis => 
          analysis.upload_id === uploadId ? updatedAnalysis : analysis
        )
      );
    } catch (error: any) {
      console.error('Failed to approve analysis:', error);
      setGlobalError(`Failed to approve analysis: ${error.message}`);
    }
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
    <>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Upload Documents for {ticker}
          </Typography>
          
          <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
            Upload financial documents to begin the two-stage analysis workflow. 
            Documents will be automatically analyzed after upload.
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
                          label="Analysis Started"
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
                          <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>
                            Upload successful - Initial analysis in progress
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </CardContent>
    </Card>
    
    {/* Analysis Results Display */}
    {showAnalysis && analysisResults.length > 0 && (
      <Box sx={{ mt: 3 }}>
        {analysisResults.map((analysis, index) => (
          <DocumentAnalysisDisplay
            key={analysis.upload_id}
            analysis={analysis}
            ticker={ticker}
            onClose={analysisResults.length === 1 ? handleCloseAnalysis : undefined}
            onApprove={handleApproveAnalysis}
          />
        ))}
        {analysisResults.length > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Button onClick={handleCloseAnalysis} variant="outlined">
              Close All Analysis Results
            </Button>
          </Box>
        )}
      </Box>
    )}
    </>
  );
};

export default DocumentUpload;
