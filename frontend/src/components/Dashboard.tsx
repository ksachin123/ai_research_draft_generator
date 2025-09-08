import React, { useState, useEffect } from 'react';
import { 
  Container,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Button,
  TextField,
  InputAdornment,
  Card,
  CardContent,
  LinearProgress,
  Chip
} from '@mui/material';
import { 
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Business as BusinessIcon 
} from '@mui/icons-material';
import CompanyCard from './company/CompanyCard';
import { companyService } from '../services/companyService';
import { Company } from '../types';

const Dashboard: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<Record<string, boolean>>({});
  const [refreshingAll, setRefreshingAll] = useState<boolean>(false);
  const [refreshProgress, setRefreshProgress] = useState<{
    current: number;
    total: number;
    currentCompany?: string;
    jobId?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  
  useEffect(() => {
    loadCompanies();
  }, []);
  
  const loadCompanies = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await companyService.getAllCompanies();
      // Handle the response data structure flexibly
      const companies = (response.data as any)?.companies || (response.data as any)?.data?.companies || [];
      setCompanies(companies);
    } catch (err) {
      console.error('Failed to load companies:', err);
      setError('Failed to load companies. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleRefreshKnowledgeBase = async (ticker: string) => {
    try {
      setRefreshing(prev => ({ ...prev, [ticker]: true }));
      await companyService.refreshKnowledgeBase(ticker);
      
      // Reload companies to get updated status
      await loadCompanies();
    } catch (err) {
      console.error(`Failed to refresh knowledge base for ${ticker}:`, err);
      setError(`Failed to refresh knowledge base for ${ticker}.`);
    } finally {
      setRefreshing(prev => ({ ...prev, [ticker]: false }));
    }
  };

  const handleRefreshAllKnowledgeBases = async () => {
    try {
      setRefreshingAll(true);
      setError(null);
      setRefreshProgress(null);
      
      // Start the background job
      const startResponse = await companyService.refreshAllKnowledgeBases();
      const jobId = startResponse.job_id;
      
      setRefreshProgress({
        current: 0,
        total: startResponse.total_companies,
        jobId: jobId
      });
      
      // Poll for job status
      const pollJobStatus = async () => {
        try {
          const jobStatus = await companyService.getRefreshJobStatus(jobId);
          
          setRefreshProgress({
            current: jobStatus.progress.current,
            total: jobStatus.progress.total,
            currentCompany: jobStatus.progress.current_company,
            jobId: jobId
          });
          
          if (jobStatus.status === 'completed') {
            // Job completed successfully
            setRefreshingAll(false);
            setRefreshProgress(null);
            await loadCompanies(); // Reload companies to get updated status
            return;
          } else if (jobStatus.status === 'failed') {
            // Job failed
            setRefreshingAll(false);
            setRefreshProgress(null);
            setError(`Refresh job failed: ${jobStatus.error || 'Unknown error'}`);
            return;
          }
          
          // Continue polling if job is still running
          setTimeout(pollJobStatus, 2000); // Poll every 2 seconds
        } catch (pollErr) {
          console.error('Failed to poll job status:', pollErr);
          setError('Failed to get refresh progress status.');
          setRefreshingAll(false);
          setRefreshProgress(null);
        }
      };
      
      // Start polling
      setTimeout(pollJobStatus, 1000); // Start polling after 1 second
      
    } catch (err) {
      console.error('Failed to start knowledge base refresh:', err);
      setError('Failed to start knowledge base refresh.');
      setRefreshingAll(false);
      setRefreshProgress(null);
    }
  };
  
  const handleViewDetails = (ticker: string) => {
    // Navigate to company details page
    window.location.href = `/company/${ticker}`;
  };
  
  const filteredCompanies = companies.filter(company => 
    company.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
    company.company_name.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  if (loading) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minHeight="60vh"
      >
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Container maxWidth="xl">
      <Box py={3}>
        <Box display="flex" alignItems="center" mb={3}>
          <BusinessIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4" component="h1" gutterBottom>
            Investment Research Dashboard
          </Typography>
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

        {refreshProgress && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Typography variant="h6">
                  Refreshing Knowledge Base
                </Typography>
                <Chip 
                  label={`${refreshProgress.current}/${refreshProgress.total}`}
                  color="primary"
                  size="small"
                />
              </Box>
              
              <LinearProgress 
                variant="determinate" 
                value={(refreshProgress.current / refreshProgress.total) * 100}
                sx={{ mb: 2 }}
              />
              
              {refreshProgress.currentCompany && (
                <Typography variant="body2" color="textSecondary">
                  Currently processing: {refreshProgress.currentCompany}
                </Typography>
              )}
              
              <Typography variant="body2" color="textSecondary">
                Job ID: {refreshProgress.jobId}
              </Typography>
            </CardContent>
          </Card>
        )}
        
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <TextField
            placeholder="Search companies..."
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ minWidth: 300 }}
          />
          
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={handleRefreshAllKnowledgeBases}
            disabled={refreshingAll}
          >
            {refreshingAll ? 'Refreshing...' : 'Refresh KB'}
          </Button>
        </Box>
        
        {filteredCompanies.length === 0 ? (
          <Card>
            <CardContent>
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <BusinessIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  {companies.length === 0 ? 'No companies found' : 'No matching companies'}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  {companies.length === 0 
                    ? 'Companies will be loaded from the data folder. Click "Refresh KB" to scan for companies.'
                    : 'Try adjusting your search terms.'
                  }
                </Typography>
                {companies.length === 0 && (
                  <Button
                    variant="contained"
                    startIcon={<RefreshIcon />}
                    onClick={handleRefreshAllKnowledgeBases}
                    disabled={refreshingAll}
                  >
                    {refreshingAll ? 'Scanning...' : 'Refresh KB'}
                  </Button>
                )}
              </Box>
            </CardContent>
          </Card>
        ) : (
          <Box 
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)',
                lg: 'repeat(4, 1fr)'
              },
              gap: 3
            }}
          >
            {filteredCompanies.map((company) => (
              <CompanyCard
                key={company.ticker}
                company={company}
                onRefresh={handleRefreshKnowledgeBase}
                onViewDetails={handleViewDetails}
                isRefreshing={refreshing[company.ticker] || false}
              />
            ))}
          </Box>
        )}
        
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Showing {filteredCompanies.length} of {companies.length} companies
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default Dashboard;
