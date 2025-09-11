import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Business as BusinessIcon,
  CloudUpload as UploadIcon,
  Refresh as RefreshIcon,
  Storage as KnowledgeBaseIcon,
  BatchPrediction as BatchIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import DocumentUpload from '../components/document/DocumentUpload';
import KnowledgeBaseContent from '../components/KnowledgeBaseContent';
import BatchManager from '../components/batch/BatchManager';
import { companyService } from '../services/companyService';
import { Document as UploadedDocument } from '../services/documentService';
import { Batch } from '../services/batchService';

// Type definitions
interface Company {
  ticker: string;
  company_name: string;
  knowledge_base_status: string;
  stats?: {
    last_refresh?: string;
    total_reports?: number;
    total_chunks?: number;
  };
  created_at?: string;
}

interface Document {
  filename: string;
  file_size: number;
  upload_date: string;
  processing_status: string;
  analysis_date?: string;
}

interface Report {
  title: string;
  report_type: string;
  created_at: string;
}

const CompanyDetail: React.FC = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<number>(0);
  const [company, setCompany] = useState<Company | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [hasNewAnalysis, setHasNewAnalysis] = useState<boolean>(false);
  const [currentBatch, setCurrentBatch] = useState<Batch | null>(null);

  const loadCompanyDetails = useCallback(async (): Promise<void> => {
    if (!ticker) return;
    
    try {
      setLoading(true);
      setError(null);

      const [companyResponse, documentsResponse, reportsResponse] = await Promise.all([
        companyService.getCompany(ticker),
        companyService.getDocuments(ticker),
        companyService.getReports(ticker)
      ]);

      setCompany(companyResponse.data);
      setDocuments(documentsResponse.data.documents || []);
      setReports(reportsResponse.data.reports || []);
      
      // Check for recent analysis (within last hour)
      const hasRecentAnalysis = documentsResponse.data.documents?.some((doc: Document) => {
        if (doc.analysis_date) {
          const analysisTime = new Date(doc.analysis_date).getTime();
          const oneHourAgo = Date.now() - (60 * 60 * 1000);
          return analysisTime > oneHourAgo;
        }
        return false;
      });
      setHasNewAnalysis(hasRecentAnalysis || false);
    } catch (err: any) {
      console.error('Failed to load company details:', err);
      setError('Failed to load company details. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    loadCompanyDetails();
  }, [loadCompanyDetails]);

  const handleRefreshKnowledgeBase = async (): Promise<void> => {
    if (!ticker) return;
    
    try {
      setRefreshing(true);
      await companyService.refreshKnowledgeBase(ticker);
      await loadCompanyDetails();
    } catch (err: any) {
      console.error('Failed to refresh knowledge base:', err);
      setError('Failed to refresh knowledge base.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleUploadSuccess = async (documents?: UploadedDocument[]): Promise<void> => {
    // Refresh data without triggering loading state to preserve upload success UI
    if (!ticker) return;
    
    try {
      console.log('Refreshing company data after successful upload...');
      const [companyResponse, documentsResponse, reportsResponse] = await Promise.all([
        companyService.getCompany(ticker),
        companyService.getDocuments(ticker),
        companyService.getReports(ticker)
      ]);

      setCompany(companyResponse.data);
      setDocuments(documentsResponse.data.documents || []);
      setReports(reportsResponse.data.reports || []);
      
      // Check for recent analysis and potentially switch to upload tab to see results
      const hasRecentAnalysis = documentsResponse.data.documents?.some((doc: Document) => {
        if (doc.analysis_date) {
          const analysisTime = new Date(doc.analysis_date).getTime();
          const oneHourAgo = Date.now() - (60 * 60 * 1000);
          return analysisTime > oneHourAgo;
        }
        return false;
      });
      
      if (hasRecentAnalysis && !hasNewAnalysis) {
        setHasNewAnalysis(true);
        // Optional: Auto-switch to upload tab to show analysis results
        // setActiveTab(0);
      }
      
      console.log('Company data refreshed successfully');
    } catch (err: any) {
      console.error('Failed to refresh data after upload:', err);
      // Don't set error state to avoid disrupting the upload success display
    }
  };

  const handleBatchCreated = (batch: Batch) => {
    setCurrentBatch(batch);
    // Optionally auto-switch to analysis tab
    // setActiveTab(1);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number): void => {
    setActiveTab(newValue);
    // Clear new analysis indicator when user visits upload tab
    if (newValue === 0 && hasNewAnalysis) {
      setHasNewAnalysis(false);
    }
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!company || !ticker) {
    return (
      <Container maxWidth="lg">
        <Box py={3}>
          <Alert severity="error">
            Company not found.
            <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
          </Alert>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box py={3}>
        {/* Header */}
        <Box display="flex" alignItems="center" mb={3}>
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/')}
            sx={{ mr: 2 }}
          >
            Back to Dashboard
          </Button>
          <BusinessIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
          <Box flexGrow={1}>
            <Typography variant="h4" component="h1">
              {company.ticker}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {company.company_name}
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={refreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={handleRefreshKnowledgeBase}
            disabled={refreshing}
          >
            {refreshing ? 'Refreshing...' : 'Refresh KB'}
          </Button>
        </Box>

        {error && (
          <Alert 
            severity="error" 
            onClose={() => setError(null)} 
            sx={{ mb: 3 }}
          >
            {error}
          </Alert>
        )}

        {/* Company Info Card */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" flexDirection={{ xs: 'column', md: 'row' }} gap={3}>
              <Box flex="1">
                <Typography variant="h6" gutterBottom>
                  Knowledge Base Status
                </Typography>
                <Box display="flex" alignItems="center" mb={2}>
                  <Chip
                    label={company.knowledge_base_status?.toUpperCase() || 'UNKNOWN'}
                    color={getStatusColor(company.knowledge_base_status)}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Last Updated: {company.stats?.last_refresh ? 
                    format(new Date(company.stats.last_refresh), 'PPP p') : 
                    'Never'
                  }
                </Typography>
              </Box>
              <Box flex="1">
                <Typography variant="h6" gutterBottom>
                  Statistics
                </Typography>
                <Box>
                  <Typography variant="body2">
                    Total Documents: {company.stats?.total_reports || 0}
                  </Typography>
                  <Typography variant="body2">
                    Processed Chunks: {company.stats?.total_chunks || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Created: {company.created_at ? 
                      format(new Date(company.created_at), 'PPP') : 
                      'Unknown'
                    }
                  </Typography>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Card>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={activeTab} 
              onChange={handleTabChange}
              aria-label="company detail tabs"
            >
              <Tab 
                icon={<UploadIcon />} 
                label={
                  <Box sx={{ position: 'relative' }}>
                    Upload Documents
                    {hasNewAnalysis && (
                      <Chip 
                        label="New Analysis!" 
                        color="primary" 
                        size="small" 
                        sx={{ ml: 1, fontSize: '0.7rem', height: '20px' }} 
                      />
                    )}
                  </Box>
                }
                iconPosition="start"
              />
              <Tab 
                icon={<BatchIcon />} 
                label="Analysis" 
                iconPosition="start"
              />
              <Tab 
                icon={<KnowledgeBaseIcon />} 
                label="Knowledge Base" 
                iconPosition="start"
              />
            </Tabs>
          </Box>

          <CardContent>
            {activeTab === 0 && (
              <DocumentUpload 
                ticker={ticker!}
                onUploadComplete={handleUploadSuccess}
                onBatchCreated={handleBatchCreated}
              />
            )}

            {activeTab === 1 && (
              <BatchManager 
                ticker={ticker!}
              />
            )}

            {activeTab === 2 && (
              <KnowledgeBaseContent ticker={ticker!} />
            )}
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default CompanyDetail;
