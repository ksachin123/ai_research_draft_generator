import { AxiosResponse } from 'axios';
import api from './api';

// Type definitions for batch operations
export interface BatchDocument {
  upload_id: string;
  filename: string;
  document_type: string;
  upload_date: string;
  status: string;
}

export interface BatchAnalyzedDocument {
  upload_id: string;
  document_info: {
    filename: string;
    upload_date: string;
    document_type: string;
    description?: string;
  };
  analysis: {
    executive_summary?: string;
    key_changes?: string[];
    new_insights?: string[];
    analyst_estimates_comparison?: string[];
    financial_performance?: string[];
    potential_thesis_impact?: string;
    requires_attention?: string[];
    [key: string]: any;
  };
  analysis_date: string;
  status: string;
  generation_metadata?: {
    prompt_used: string;
    model: string;
    temperature: number;
    max_tokens: number;
    analysis_type: string;
    context_documents_count: number;
    analyst_estimates_included: boolean;
    analyst_estimates_length: number;
    generation_timestamp: string;
  };
  context_sources?: Array<{
    content: string;
    metadata: any;
    distance: number;
  }>;
}

export interface Batch {
  batch_id: string;
  ticker: string;
  name: string;
  description: string;
  created_at: string;
  status: 'created' | 'analyzing' | 'analyzed' | 'report_generated';
  upload_ids: string[];
  documents: BatchDocument[];
  analysis_status: 'pending' | 'in_progress' | 'completed' | 'partial';
  report_status: 'pending' | 'generating' | 'generated';
  analyzed_documents?: number;
  failed_documents?: number;
  analysis_completed_at?: string;
  report_generated_at?: string;
  report_content?: BatchReport;
  analyzed_documents_data?: BatchAnalyzedDocument[];
}

export interface BatchReport {
  executive_summary: string;
  key_developments: string;
  financial_insights: string;
  strategic_implications: string;
  risk_assessment: string;
  investment_recommendation: string;
  next_steps: string;
  full_content: string;
  metadata?: {
    documents_analyzed: number;
    batch_info: any;
    ticker: string;
    generated_at: string;
    model_used: string;
    context_documents_count: number;
  };
}

export interface BatchAnalysisResult {
  batch_id: string;
  analyzed_documents: any[];
  failed_analyses: any[];
  successful_analyses: number;
  total_documents: number;
  batch_status: string;
}

export interface BatchCreateRequest {
  upload_ids: string[];
  name?: string;
  description?: string;
}

export interface BatchListResponse {
  batches: Batch[];
}

class BatchService {
  // Get all batches for a company
  async getBatches(ticker: string): Promise<BatchListResponse> {
    const response: AxiosResponse = await api.get(
      `/companies/${ticker}/batches`
    );
    return response.data.data;
  }

  // Get specific batch details
  async getBatch(ticker: string, batchId: string): Promise<Batch> {
    const response: AxiosResponse = await api.get(
      `/companies/${ticker}/batches/${batchId}`
    );
    return response.data.data.batch;
  }

  // Create a new batch
  async createBatch(ticker: string, request: BatchCreateRequest): Promise<Batch> {
    const response: AxiosResponse = await api.post(
      `/companies/${ticker}/batches`,
      request
    );
    return response.data.data.batch;
  }

  // Trigger batch analysis
  async analyzeBatch(ticker: string, batchId: string): Promise<BatchAnalysisResult> {
    const response: AxiosResponse = await api.post(
      `/companies/${ticker}/batches/${batchId}/analyze`,
      {},
      {
        timeout: 300000, // 5 minutes for batch analysis
      }
    );
    return response.data.data;
  }

  // Generate batch report
  async generateBatchReport(ticker: string, batchId: string): Promise<BatchReport> {
    const response: AxiosResponse = await api.post(`/companies/${ticker}/batches/${batchId}/report`);
    return response.data.data.report;
  }

  // Delete a batch
  async deleteBatch(ticker: string, batchId: string): Promise<void> {
    await api.delete(`/companies/${ticker}/batches/${batchId}`);
  }

  // Helper method to get batch status display text
  getBatchStatusDisplay(status: string): string {
    const statusMap: Record<string, string> = {
      'created': 'Ready for Analysis',
      'analyzing': 'Analysis in Progress',
      'analyzed': 'Analysis Complete',
      'report_generated': 'Report Generated',
    };
    return statusMap[status] || status;
  }

  // Helper method to get batch status color
  getBatchStatusColor(status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' {
    const colorMap: Record<string, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
      'created': 'info',
      'analyzing': 'warning', 
      'analyzed': 'primary',
      'report_generated': 'success',
    };
    return colorMap[status] || 'default';
  }

  // Helper method to format batch dates
  formatBatchDate(dateString: string): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }

  // Helper method to get progress percentage for batch
  getBatchProgress(batch: Batch): number {
    if (batch.report_status === 'generated') return 100;
    if (batch.analysis_status === 'completed') return 75;
    if (batch.analysis_status === 'in_progress') return 50;
    if (batch.analysis_status === 'partial') return 60;
    return 25; // Created state
  }
}

export const batchService = new BatchService();
export default batchService;
