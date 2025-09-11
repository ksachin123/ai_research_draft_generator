import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Alert,
  Chip
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Assignment as ReportIcon
} from '@mui/icons-material';
import { BatchReport } from '../../services/batchService';
import SimpleMarkdown from '../common/SimpleMarkdown';

interface BatchReportDisplayProps {
  report: BatchReport;
  batchName: string;
  ticker: string;
  onCopy?: () => void;
}

const BatchReportDisplay: React.FC<BatchReportDisplayProps> = ({
  report,
  batchName,
  ticker,
  onCopy
}) => {
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(report.full_content);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 3000);
      if (onCopy) onCopy();
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      alert('Failed to copy to clipboard. Please copy manually.');
    }
  };

  const handleDownload = () => {
    const content = report.full_content;
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${ticker}_batch_report_${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Card sx={{ mt: 3, border: '2px solid', borderColor: 'success.main' }}>
      <CardContent>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box>
            <Typography variant="h5" sx={{ color: 'success.main', display: 'flex', alignItems: 'center' }}>
              <ReportIcon sx={{ mr: 1 }} />
              Draft Report Generated
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {batchName} • {ticker}
            </Typography>
            {report.metadata && (
              <Typography variant="body2" color="text.secondary">
                Generated: {new Date(report.metadata.generated_at || '').toLocaleString()} • 
                Documents analyzed: {report.metadata.documents_analyzed}
              </Typography>
            )}
          </Box>
          <Box display="flex" gap={1}>
            <Button
              variant="outlined"
              startIcon={<CopyIcon />}
              onClick={handleCopyToClipboard}
              size="small"
            >
              Copy Report
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
              size="small"
            >
              Download
            </Button>
          </Box>
        </Box>

        {copySuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Report copied to clipboard! You can now paste it into your authoring tool.
          </Alert>
        )}

        {/* Report Content */}
        <Box sx={{ mt: 2 }}>
          <SimpleMarkdown>{report.full_content}</SimpleMarkdown>
        </Box>

        {/* Metadata */}
        {report.metadata && (
          <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip 
              label={`Model: ${report.metadata.model_used}`} 
              size="small" 
              variant="outlined" 
            />
            <Chip 
              label={`Context Sources: ${report.metadata.context_documents_count}`} 
              size="small" 
              variant="outlined" 
            />
            <Chip 
              label={`Documents: ${report.metadata.documents_analyzed}`} 
              size="small" 
              variant="outlined" 
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default BatchReportDisplay;
