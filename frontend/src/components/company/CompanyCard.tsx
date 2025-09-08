import React from 'react';
import { 
  Card, 
  CardContent, 
  CardActions, 
  Typography, 
  Button, 
  Chip,
  Box,
  LinearProgress 
} from '@mui/material';
import { 
  Business as BusinessIcon,
  Refresh as RefreshIcon,
  Assessment as AssessmentIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon 
} from '@mui/icons-material';
import { format } from 'date-fns';
import { CompanyCardProps, Company } from '../../types';

const getStatusColor = (status: Company['knowledge_base_status']) => {
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

const getStatusIcon = (status: Company['knowledge_base_status']): React.ReactElement | undefined => {
  switch (status) {
    case 'active':
      return <CheckCircleIcon fontSize="small" />;
    case 'error':
      return <ErrorIcon fontSize="small" />;
    default:
      return undefined;
  }
};

const CompanyCard: React.FC<CompanyCardProps> = ({ company, onRefresh, onViewDetails, isRefreshing }) => {
  const { ticker, company_name, knowledge_base_status, stats } = company;
  
  const handleRefresh = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    onRefresh(ticker);
  };
  
  const handleViewDetails = () => {
    onViewDetails(ticker);
  };

  return (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        cursor: 'pointer',
        '&:hover': {
          boxShadow: 6,
        }
      }}
      onClick={handleViewDetails}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" alignItems="center" mb={1}>
          <BusinessIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6" component="h2" noWrap>
            {ticker}
          </Typography>
        </Box>
        
        <Typography variant="body2" color="text.secondary" mb={2} noWrap>
          {company_name}
        </Typography>
        
        <Box mb={2}>
          <Chip
            icon={getStatusIcon(knowledge_base_status)}
            label={knowledge_base_status?.toUpperCase() || 'UNKNOWN'}
            color={getStatusColor(knowledge_base_status)}
            size="small"
          />
        </Box>
        
        {isRefreshing && (
          <Box mb={2}>
            <LinearProgress />
            <Typography variant="caption" color="text.secondary">
              Refreshing knowledge base...
            </Typography>
          </Box>
        )}
        
        <Box>
          <Typography variant="body2" color="text.secondary">
            Reports: {stats?.total_reports || 0}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Chunks: {stats?.total_chunks || 0}
          </Typography>
          {stats?.last_refresh && (
            <Typography variant="caption" color="text.secondary">
              Updated: {format(new Date(stats.last_refresh), 'MMM dd, yyyy')}
            </Typography>
          )}
        </Box>
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          Refresh KB
        </Button>
        <Button
          size="small"
          startIcon={<AssessmentIcon />}
          onClick={handleViewDetails}
        >
          Details
        </Button>
      </CardActions>
    </Card>
  );
};

export default CompanyCard;
