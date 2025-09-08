import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Tabs,
  Tab,
  Paper
} from '@mui/material';
import { useParams } from 'react-router-dom';
import DocumentUpload from '../components/document/DocumentUpload';
import DocumentList from '../components/document/DocumentList';
import { Document } from '../services/documentService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`document-tabpanel-${index}`}
      aria-labelledby={`document-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `document-tab-${index}`,
    'aria-controls': `document-tabpanel-${index}`,
  };
}

const DocumentManagementPage: React.FC = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const [currentTab, setCurrentTab] = useState(0);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  if (!ticker) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Paper sx={{ p: 3, bgcolor: 'error.light' }}>
          <Typography color="error">
            Ticker symbol is required to access document management.
          </Typography>
        </Paper>
      </Container>
    );
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleUploadComplete = (documents: Document[]) => {
    // Switch to document list to see the uploaded documents
    setCurrentTab(1);
    
    // Trigger refresh of document list
    setRefreshTrigger(prev => prev + 1);
  };

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Document Management - {ticker}
      </Typography>

      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        Manage documents for {ticker} using the two-stage analysis workflow
      </Typography>

      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={currentTab} onChange={handleTabChange} aria-label="document management tabs">
            <Tab label="Upload Documents" {...a11yProps(0)} />
            <Tab label="Document List & Analysis" {...a11yProps(1)} />
          </Tabs>
        </Box>

        <TabPanel value={currentTab} index={0}>
          <DocumentUpload
            ticker={ticker}
            onUploadComplete={handleUploadComplete}
          />
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <DocumentList
            ticker={ticker}
            onRefresh={handleRefresh}
            key={refreshTrigger} // Force re-render when refreshTrigger changes
          />
        </TabPanel>
      </Paper>

      {/* Two-Stage Workflow Explanation */}
      <Paper sx={{ mt: 4, p: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom>
          Two-Stage Analysis Workflow
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Stage 1: Initial Analysis
            </Typography>
            <Typography variant="body2">
              • Documents are automatically analyzed after upload
              <br />
              • Key changes and insights are extracted
              <br />
              • Analysis readiness is flagged for review
              <br />
              • Context from knowledge base is incorporated
            </Typography>
          </Box>
          
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Stage 2: Detailed Report Generation
            </Typography>
            <Typography variant="body2">
              • Review and approve the initial analysis
              <br />
              • Generate comprehensive investment reports
              <br />
              • Include detailed thesis impact analysis
              <br />
              • Export final reports for distribution
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default DocumentManagementPage;
