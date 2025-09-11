import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Alert,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Assignment as ReportIcon,
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  Settings as SettingsIcon
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
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
              <Chip 
                label={`Model: ${report.metadata.model_used}`} 
                size="small" 
                variant="outlined" 
              />
              <Chip 
                label={`Documents: ${report.metadata.documents_analyzed}`} 
                size="small" 
                variant="outlined" 
              />
              <Chip 
                label={`Report Type: ${report.metadata.report_type || 'Standard'}`} 
                size="small" 
                variant="outlined" 
              />
              {report.metadata.generation_method && (
                <Chip 
                  label={`Method: ${report.metadata.generation_method}`} 
                  size="small" 
                  variant="outlined" 
                  color="primary"
                />
              )}
              {report.metadata.sections_generated && (
                <Chip 
                  label={`Sections: ${report.metadata.sections_generated.length}`} 
                  size="small" 
                  variant="outlined" 
                  color="secondary"
                />
              )}
            </Box>

            {/* Generation Details Accordion */}
            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="generation-details-content"
                id="generation-details-header"
              >
                <Box display="flex" alignItems="center">
                  <SettingsIcon sx={{ mr: 1, fontSize: '1rem' }} />
                  <Typography variant="subtitle2">
                    Generation Details & Prompts Used
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box>
                  {/* Basic Generation Info */}
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    <strong>Generation Method:</strong> {report.metadata.generation_method || 'Legacy single prompt'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    <strong>Context Length:</strong> {report.metadata.context_length ? 
                      `${report.metadata.context_length.toLocaleString()} characters` : 'Not specified'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    <strong>Analyst Estimates:</strong> {report.metadata.analyst_estimates_length ? 
                      `${report.metadata.analyst_estimates_length} characters` : 'Not provided'}
                  </Typography>
                  
                  <Divider sx={{ my: 2 }} />

                  {/* Section-Specific Prompts */}
                  {report.metadata.prompts_used && Object.keys(report.metadata.prompts_used).length > 0 ? (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                        <CodeIcon sx={{ mr: 1, fontSize: '1rem' }} />
                        Section-Specific Prompts Used
                      </Typography>
                      <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                        This report was generated using specialized prompts for each section to maximize content quality and relevance.
                      </Typography>
                      
                      {Object.entries(report.metadata.prompts_used).map(([section, prompt]) => (
                        <Accordion key={section} sx={{ mb: 1 }}>
                          <AccordionSummary
                            expandIcon={<ExpandMoreIcon />}
                            sx={{ 
                              backgroundColor: 'primary.50',
                              '&:hover': { backgroundColor: 'primary.100' }
                            }}
                          >
                            <Box display="flex" alignItems="center" width="100%">
                              <Chip 
                                label={section.replace('_', ' ').toUpperCase()} 
                                size="small" 
                                color="primary" 
                                variant="filled"
                                sx={{ mr: 2 }}
                              />
                              <Typography variant="body2" color="text.secondary">
                                Click to view section-specific prompt ({prompt.length.toLocaleString()} characters)
                              </Typography>
                            </Box>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Box>
                              <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                                This prompt was specifically crafted for generating the {section.replace('_', ' ')} section:
                              </Typography>
                              <Box 
                                sx={{ 
                                  fontFamily: 'monospace',
                                  backgroundColor: 'grey.50',
                                  border: '1px solid',
                                  borderColor: 'grey.300',
                                  borderRadius: 1,
                                  p: 2,
                                  fontSize: '0.75rem',
                                  lineHeight: 1.4,
                                  maxHeight: '400px',
                                  overflowY: 'auto',
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word'
                                }}
                              >
                                {prompt}
                              </Box>
                              <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                                <Button
                                  size="small"
                                  startIcon={<CopyIcon />}
                                  onClick={async () => {
                                    try {
                                      await navigator.clipboard.writeText(prompt);
                                      setCopySuccess(true);
                                      setTimeout(() => setCopySuccess(false), 2000);
                                    } catch (err) {
                                      console.error('Failed to copy prompt:', err);
                                    }
                                  }}
                                >
                                  Copy Prompt
                                </Button>
                              </Box>
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      ))}
                    </Box>
                  ) : (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        <CodeIcon sx={{ mr: 1, fontSize: '1rem' }} />
                        Single Prompt Generation
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        This report was generated using a single comprehensive prompt. 
                        Section-specific prompts are used in newer generation methods for better quality.
                      </Typography>
                    </Box>
                  )}

                  {/* Sections Generated */}
                  {report.metadata.sections_generated && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Sections Generated:
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {report.metadata.sections_generated.map((section) => (
                          <Chip 
                            key={section}
                            label={section.replace('_', ' ')}
                            size="small"
                            variant="filled"
                            color="success"
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Box>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default BatchReportDisplay;
