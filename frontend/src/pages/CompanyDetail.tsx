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
  Assessment as ReportsIcon,
  CloudUpload as UploadIcon,
  AutoAwesome as GenerateIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import DocumentUpload from '../components/document/DocumentUpload';
import ReportGeneration from '../components/report/ReportGeneration';
import { companyService } from '../services/companyService';
import { Document as UploadedDocument } from '../services/documentService';

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
      console.log('Company data refreshed successfully');
    } catch (err: any) {
      console.error('Failed to refresh data after upload:', err);
      // Don't set error state to avoid disrupting the upload success display
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number): void => {
    setActiveTab(newValue);
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
                label="Upload Documents" 
                iconPosition="start"
              />
              <Tab 
                icon={<GenerateIcon />} 
                label="Generate Report" 
                iconPosition="start"
              />
              <Tab 
                icon={<ReportsIcon />} 
                label="View Reports" 
                iconPosition="start"
              />
            </Tabs>
          </Box>

          <CardContent>
            {activeTab === 0 && (
              <DocumentUpload 
                ticker={ticker!}
                onUploadComplete={handleUploadSuccess}
              />
            )}

            {activeTab === 1 && (
              <ReportGeneration 
                companyTicker={ticker!}
                companyName={company.company_name}
              />
            )}

            {activeTab === 2 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Document Library
                </Typography>
                {documents.length === 0 ? (
                  <Box textAlign="center" py={4}>
                    <ReportsIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      No documents uploaded
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mb={3}>
                      Upload PDF documents to build the knowledge base for this company.
                    </Typography>
                    <Button
                      variant="contained"
                      startIcon={<UploadIcon />}
                      onClick={() => setActiveTab(0)}
                    >
                      Upload Documents
                    </Button>
                  </Box>
                ) : (
                  <Box display="flex" flexDirection="column" gap={2}>
                    {documents.map((doc, index) => (
                      <Box key={index}>
                        <Card variant="outlined">
                          <CardContent>
                            <Box display="flex" justifyContent="space-between" alignItems="start">
                              <Box flexGrow={1}>
                                <Typography variant="subtitle1" gutterBottom>
                                  {doc.filename}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Size: {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Uploaded: {format(new Date(doc.upload_date), 'PPP p')}
                                </Typography>
                              </Box>
                              <Chip
                                label={doc.processing_status?.toUpperCase() || 'UNKNOWN'}
                                color={getStatusColor(doc.processing_status)}
                                size="small"
                              />
                            </Box>
                          </CardContent>
                        </Card>
                      </Box>
                    ))}
                  </Box>
                )}

                {reports.length > 0 && (
                  <>
                    <Divider sx={{ my: 3 }} />
                    <Typography variant="h6" gutterBottom>
                      Generated Reports
                    </Typography>
                    <Box display="flex" flexDirection="column" gap={2}>
                      {reports.map((report, index) => (
                        <Box key={index}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="subtitle1" gutterBottom>
                                {report.title || `Report ${index + 1}`}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Type: {report.report_type?.toUpperCase() || 'UNKNOWN'}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Generated: {format(new Date(report.created_at), 'PPP p')}
                              </Typography>
                            </CardContent>
                          </Card>
                        </Box>
                      ))}
                    </Box>
                  </>
                )}
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default CompanyDetail;
