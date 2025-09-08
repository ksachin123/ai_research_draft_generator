import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
  Paper,
  Divider
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Assignment as ReportIcon
} from '@mui/icons-material';
import { companyService } from '../../services/companyService';

// Type definitions
interface ReportSection {
  value: string;
  label: string;
}

interface ReportType {
  value: string;
  label: string;
}

interface FormData {
  reportType: string;
  focusAreas: string[];
  additionalContext: string;
  sections: string[];
}

interface GeneratedReport {
  content?: Record<string, string>;
  metadata?: {
    sources_used?: string;
    generated_at?: string;
    model_used?: string;
  };
}

interface ReportGenerationProps {
  companyTicker: string;
  companyName: string;
}

const REPORT_SECTIONS: ReportSection[] = [
  { value: 'executive_summary', label: 'Executive Summary' },
  { value: 'investment_thesis', label: 'Investment Thesis' },
  { value: 'key_developments', label: 'Key Developments' },
  { value: 'financial_analysis', label: 'Financial Analysis' },
  { value: 'risk_assessment', label: 'Risk Assessment' },
  { value: 'recommendation', label: 'Recommendation' },
  { value: 'price_target', label: 'Price Target' }
];

const REPORT_TYPES: ReportType[] = [
  { value: 'initiation', label: 'Initiation Report' },
  { value: 'update', label: 'Update Report' },
  { value: 'earnings', label: 'Earnings Report' },
  { value: 'event_driven', label: 'Event-Driven Report' }
];

const ReportGeneration: React.FC<ReportGenerationProps> = ({ companyTicker, companyName }) => {
  const [generating, setGenerating] = useState<boolean>(false);
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    reportType: 'update',
    focusAreas: [],
    additionalContext: '',
    sections: ['executive_summary', 'key_developments', 'recommendation']
  });

  const handleInputChange = (field: keyof FormData, value: any): void => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSectionToggle = (section: string): void => {
    setFormData(prev => ({
      ...prev,
      sections: prev.sections.includes(section)
        ? prev.sections.filter(s => s !== section)
        : [...prev.sections, section]
    }));
  };

  const handleGenerateReport = async (): Promise<void> => {
    if (formData.sections.length === 0) {
      setError('Please select at least one report section.');
      return;
    }

    setGenerating(true);
    setError(null);
    setGeneratedReport(null);

    try {
      const result = await companyService.generateReport(companyTicker, {
        report_type: formData.reportType,
        focus_areas: formData.focusAreas,
        additional_context: formData.additionalContext,
        sections: formData.sections
      });

      setGeneratedReport(result);

    } catch (err: any) {
      console.error('Report generation error:', err);
      setError(err.message || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadReport = (): void => {
    if (!generatedReport) return;

    const content = formatReportForDownload(generatedReport);
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${companyTicker}_research_report_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatReportForDownload = (report: GeneratedReport): string => {
    let content = `Investment Research Report: ${companyTicker}\n`;
    content += `Generated: ${new Date().toLocaleString()}\n`;
    content += `Report Type: ${formData.reportType.toUpperCase()}\n`;
    content += '='.repeat(50) + '\n\n';

    if (report.content) {
      Object.entries(report.content).forEach(([section, text]) => {
        const sectionLabel = REPORT_SECTIONS.find(s => s.value === section)?.label || section;
        content += `${sectionLabel.toUpperCase()}\n`;
        content += '-'.repeat(sectionLabel.length) + '\n';
        content += `${text}\n\n`;
      });
    }

    if (report.metadata) {
      content += 'METADATA\n';
      content += '--------\n';
      content += `Sources: ${report.metadata.sources_used || 'N/A'}\n`;
      content += `Generated At: ${report.metadata.generated_at || 'N/A'}\n`;
      content += `Model: ${report.metadata.model_used || 'N/A'}\n`;
    }

    return content;
  };

  return (
    <Box>
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" mb={2}>
            <ReportIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">
              Generate Research Report
            </Typography>
          </Box>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Generate an AI-powered investment research report for {companyName} ({companyTicker})
          </Typography>

          {error && (
            <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" noValidate>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Report Type</InputLabel>
              <Select
                value={formData.reportType}
                onChange={(e) => handleInputChange('reportType', e.target.value)}
                label="Report Type"
              >
                {REPORT_TYPES.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Typography variant="subtitle2" gutterBottom>
              Report Sections
            </Typography>
            <Box sx={{ mb: 3 }}>
              {REPORT_SECTIONS.map((section) => (
                <Chip
                  key={section.value}
                  label={section.label}
                  onClick={() => handleSectionToggle(section.value)}
                  color={formData.sections.includes(section.value) ? 'primary' : 'default'}
                  variant={formData.sections.includes(section.value) ? 'filled' : 'outlined'}
                  sx={{ m: 0.5, cursor: 'pointer' }}
                />
              ))}
            </Box>

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Additional Context (Optional)"
              placeholder="Provide any specific focus areas, recent events, or context you want the AI to consider..."
              value={formData.additionalContext}
              onChange={(e) => handleInputChange('additionalContext', e.target.value)}
              sx={{ mb: 3 }}
            />

            <Button
              variant="contained"
              size="large"
              startIcon={generating ? <CircularProgress size={20} /> : <AIIcon />}
              onClick={handleGenerateReport}
              disabled={generating || formData.sections.length === 0}
              fullWidth
            >
              {generating ? 'Generating Report...' : 'Generate Report'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {generatedReport && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                Generated Report
              </Typography>
              <Box>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<RefreshIcon />}
                  onClick={handleGenerateReport}
                  disabled={generating}
                  sx={{ mr: 1 }}
                >
                  Regenerate
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownloadReport}
                >
                  Download
                </Button>
              </Box>
            </Box>

            <Paper variant="outlined" sx={{ p: 2, maxHeight: 600, overflow: 'auto' }}>
              {generatedReport.content && Object.entries(generatedReport.content).map(([section, content]) => {
                const sectionLabel = REPORT_SECTIONS.find(s => s.value === section)?.label || section;
                return (
                  <Box key={section} sx={{ mb: 3 }}>
                    <Typography variant="h6" gutterBottom color="primary">
                      {sectionLabel}
                    </Typography>
                    <Typography 
                      variant="body1" 
                      component="div"
                      sx={{ 
                        whiteSpace: 'pre-wrap',
                        lineHeight: 1.6
                      }}
                    >
                      {content}
                    </Typography>
                    <Divider sx={{ mt: 2 }} />
                  </Box>
                );
              })}

              {generatedReport.metadata && (
                <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    <strong>Sources:</strong> {generatedReport.metadata.sources_used || 'Knowledge base'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    <strong>Generated:</strong> {generatedReport.metadata.generated_at ? 
                      new Date(generatedReport.metadata.generated_at).toLocaleString() : 
                      new Date().toLocaleString()
                    }
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    <strong>Model:</strong> {generatedReport.metadata.model_used || 'GPT-4o-mini'}
                  </Typography>
                </Box>
              )}
            </Paper>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default ReportGeneration;
