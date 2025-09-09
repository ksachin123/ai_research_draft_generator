import { AxiosResponse } from 'axios';
import api from './api';

// Type definitions for the two-stage workflow
export interface DocumentAnalysis {
  upload_id: string;
  document_info: {
    filename: string;
    upload_date: string;
    document_type: string;
    description: string;
  };
  analysis: {
    executive_summary: string;
    key_changes: string[];
    new_insights: string[];
    potential_thesis_impact: string;
    confidence_assessment: string;
    requires_attention: string[];
    // Additional detailed sections
    financial_performance: string[];
    business_segments: string[];
    strategic_developments: string[];
    forward_looking_insights: string[];
    // New fields from API
    actionable_insights: string[];
    investment_implications: string;
    margin_comparison: string[];
    // Enhanced analysis fields for estimates comparison
    comparative_analysis?: {
      executive_summary?: string;
      key_findings?: string[];
      metric_comparisons?: any[];
      estimates_analysis?: string;
      recommendations?: string[];
      // New actual API response structure
      estimates_vs_actuals?: string;
      segment_comparison?: string;
      margin_analysis?: string;
      investment_thesis_impact?: string;
      risk_assessment_update?: string;
      actionable_insights?: string[];
      variance_highlights?: string[];
    };
  };
  has_estimates_comparison?: boolean;
  analysis_date: string;
  status: 'analysis_ready' | 'analysis_approved' | 'analysis_error';
  context_sources: ContextSource[];
  generation_metadata?: {
    prompt_used: string;
    model: string;
    temperature: number;
    max_tokens: number;
    analysis_type: string;
    context_documents_count: number;
    generation_timestamp: string;
  };
  comparative_data?: {
    document_metrics: any;
    estimates_data: any;
    comparisons: any[];
  };
  document_metrics?: any;
}

export interface ContextSource {
  type: 'knowledge_base' | 'uploaded_document';
  document: string;
  relevance_score: number;
}

export interface Document {
  upload_id: string;
  filename: string;
  upload_date: string;
  document_type: string;
  status: 'uploaded' | 'processing' | 'analysis_ready' | 'analysis_approved' | 'report_generated' | 'error';
  analysis_ready: boolean;
  analysis_approved: boolean;
  report_generated: boolean;
  content_length: number;
  analysis_date?: string;
  approval_date?: string;
  metadata: Record<string, any>;
}

export interface UploadResponse {
  document: Document;
  analysis?: DocumentAnalysis;
}

export interface ReportGenerationRequest {
  upload_id: string;
  analysis_type?: string;
  focus_areas?: string[];
  include_context?: boolean;
}

export interface GeneratedReport {
  report_id: string;
  status: string;
  analysis_type: string;
  generated_at: string;
  content: {
    executive_summary: string;
    key_changes: string[];
    new_insights: string[];
    investment_thesis_impact: string;
  };
  sources: ContextSource[];
}

export interface AnalysisApprovalRequest {
  modifications?: Record<string, any>;
  notes?: string;
}

export interface AnalysisModificationRequest {
  analysis_type?: string;
  focus_areas?: string[];
  regenerate?: boolean;
}

class DocumentService {
  
  // Upload document and trigger initial analysis
  async uploadDocument(
    ticker: string,
    file: File,
    documentType: string,
    description?: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (description) {
      formData.append('description', description);
    }

    try {
      const response: AxiosResponse = await api.post(
        `/companies/${ticker}/documents/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 120000, // 2 minutes for upload and initial analysis
        }
      );

      console.log('Upload response:', response.data);

      // Check if the response has the expected structure
      if (!response.data || !response.data.success) {
        console.error('Upload failed or unexpected response structure:', response.data);
        throw new Error(response.data?.message || 'Upload failed');
      }

      const uploadedFiles = response.data.data?.uploaded_files;
      if (!uploadedFiles || !Array.isArray(uploadedFiles)) {
        console.error('No uploaded_files in response data:', response.data);
        throw new Error('Invalid response structure from server');
      }

      if (uploadedFiles.length === 0) {
        console.error('No uploaded files in response:', response.data);
        throw new Error('No files were uploaded successfully');
      }

      const uploadResponse: UploadResponse = {
        document: uploadedFiles[0]
      };

      // Check if analysis results are included in the response
      const analysisResults = response.data.data?.analysis_results;
      if (analysisResults && analysisResults.analysis) {
        console.log('Analysis results included in upload response:', analysisResults);
        uploadResponse.analysis = {
          upload_id: analysisResults.document_info.upload_id,
          document_info: analysisResults.document_info,
          analysis: analysisResults.analysis,
          analysis_date: analysisResults.analysis_date,
          status: analysisResults.document_info.processing_status === 'analysis_ready' ? 'analysis_ready' : 'analysis_error',
          context_sources: analysisResults.context_sources || [],
          generation_metadata: analysisResults.generation_metadata
        };
        console.log('Formatted analysis data for frontend:', uploadResponse.analysis);
      }

      return uploadResponse;
      
    } catch (error: any) {
      console.error('Upload error details:', error);
      
      if (error.response) {
        console.error('Server responded with error:', error.response.status, error.response.data);
        throw new Error(error.response.data?.error?.message || `Server error: ${error.response.status}`);
      } else if (error.request) {
        console.error('No response from server:', error.request);
        throw new Error('No response from server. Please check if the backend is running.');
      } else {
        console.error('Request setup error:', error.message);
        throw new Error(error.message || 'Upload failed');
      }
    }
  }

  // Get list of uploaded documents
  async getDocuments(ticker: string): Promise<Document[]> {
    const response: AxiosResponse = await api.get(`/companies/${ticker}/documents`);
    return response.data.data.documents;
  }

  // Get initial analysis results
  async getAnalysis(ticker: string, uploadId: string): Promise<DocumentAnalysis> {
    const response: AxiosResponse = await api.get(
      `/companies/${ticker}/documents/${uploadId}/analysis`
    );
    return response.data.data;
  }

  // Trigger batch analysis for multiple uploaded documents
  async triggerBatchAnalysis(
    ticker: string, 
    uploadIds: string[], 
    options?: {
      force_reanalysis?: boolean;
    }
  ): Promise<{
    analyzed_documents: DocumentAnalysis[];
    failed_analyses: Array<{ upload_id: string; error: string }>;
    total_requested: number;
    successful_analyses: number;
    failed_analyses_count: number;
  }> {
    const response: AxiosResponse = await api.post(
      `/companies/${ticker}/documents/analyze`,
      {
        upload_ids: uploadIds,
        analysis_options: options || {}
      },
      {
        timeout: 300000, // 5 minutes for batch analysis
      }
    );
    return response.data.data;
  }

  // Approve analysis for report generation
  async approveAnalysis(
    ticker: string,
    uploadId: string,
    approvalData: AnalysisApprovalRequest
  ): Promise<{ status: string; approval_date: string }> {
    const response: AxiosResponse = await api.post(
      `/companies/${ticker}/documents/${uploadId}/analysis/approve`,
      approvalData
    );
    return response.data.data;
  }

  // Modify analysis parameters and optionally regenerate
  async modifyAnalysis(
    ticker: string,
    uploadId: string,
    modificationData: AnalysisModificationRequest
  ): Promise<DocumentAnalysis> {
    const response: AxiosResponse = await api.put(
      `/companies/${ticker}/documents/${uploadId}/analysis`,
      modificationData
    );
    return response.data.data;
  }

  // Generate detailed report (requires approved analysis)
  async generateReport(
    ticker: string,
    reportData: ReportGenerationRequest
  ): Promise<GeneratedReport> {
    const response: AxiosResponse = await api.post(
      `/companies/${ticker}/reports/generate`,
      reportData,
      {
        timeout: 180000, // 3 minutes for detailed report generation
      }
    );
    return response.data.data;
  }

  // Get generated reports list
  async getReports(ticker: string): Promise<any[]> {
    const response: AxiosResponse = await api.get(`/companies/${ticker}/reports`);
    return response.data.data.reports;
  }

  // Helper method to check if document is ready for analysis review
  isAnalysisReady(document: Document): boolean {
    return document.status === 'analysis_ready';
  }

  // Helper method to check if analysis is approved and ready for report generation
  isReadyForReport(document: Document): boolean {
    return document.status === 'analysis_approved';
  }

  // Helper method to get status display text
  getStatusDisplay(status: string): string {
    const statusMap: Record<string, string> = {
      'uploaded': 'Processing...',
      'processing': 'Processing...',
      'analysis_ready': 'Analysis Ready for Review',
      'analysis_approved': 'Ready for Report Generation',
      'report_generated': 'Report Generated',
      'analysis_error': 'Analysis Error',
      'error': 'Processing Error'
    };
    return statusMap[status] || status;
  }

  // Helper method to get status color for UI
  getStatusColor(status: string): 'primary' | 'secondary' | 'success' | 'warning' | 'error' {
    const colorMap: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'error'> = {
      'uploaded': 'primary',
      'processing': 'primary', 
      'analysis_ready': 'warning',
      'analysis_approved': 'success',
      'report_generated': 'success',
      'analysis_error': 'error',
      'error': 'error'
    };
    return colorMap[status] || 'secondary';
  }
}

export const documentService = new DocumentService();
export default documentService;
