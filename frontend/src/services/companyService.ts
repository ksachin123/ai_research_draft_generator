import { AxiosResponse } from 'axios';
import api from './api';

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
  content?: Record<string, string>;
  metadata?: {
    sources_used?: string;
    generated_at?: string;
    model_used?: string;
  };
}

interface KnowledgeBaseStatus {
  status: string;
  last_refresh?: string;
  document_count: number;
}

interface InvestmentData {
  investment_thesis?: any;
  investment_drivers?: any;
  risks?: any;
}

interface KnowledgeBaseDocument {
  id: string;
  content: string;
  content_preview: string;
  metadata: {
    document_type: string;
    source_file: string;
    processed_date?: string;
    report_date?: string;
    page_number?: number;
    chunk_index?: number;
    contains_analyst_estimates: boolean;
    historical_financial_data: boolean;
    content_priority: number;
  };
}

interface KnowledgeBaseContentResponse {
  success: boolean;
  data: {
    ticker: string;
    documents: KnowledgeBaseDocument[];
    pagination: {
      page: number;
      page_size: number;
      total_items: number;
      total_pages: number;
      has_next: boolean;
      has_prev: boolean;
    };
    filters: {
      document_type?: string;
      search_query?: string;
    };
  };
}

interface KnowledgeBaseDocumentTypesResponse {
  success: boolean;
  data: {
    ticker: string;
    document_types: string[];
  };
}

interface UploadResult {
  uploaded_files: Document[];
  success: boolean;
}

interface RefreshJobProgress {
  current: number;
  total: number;
  current_company?: string;
}

interface RefreshJobResult {
  ticker: string;
  status: 'success' | 'error';
  reports_processed?: number;
  investment_data_processed?: boolean;
  total_documents?: number;
  processing_time_seconds?: number;
  error?: string;
}

interface RefreshJob {
  job_id: string;
  status: 'pending' | 'starting' | 'running' | 'completed' | 'failed';
  progress: RefreshJobProgress;
  results: RefreshJobResult[];
  error?: string;
  created_at: string;
  updated_at: string;
}

interface RefreshStartResponse {
  job_id: string;
  total_companies: number;
  companies_found: string[];
}

interface ReportGenerationData {
  report_type: string;
  focus_areas: string[];
  additional_context: string;
  sections: string[];
}

export const companyService = {
  // Get all companies
  getAllCompanies: (): Promise<AxiosResponse<Company[]>> => api.get('/companies/'),

  // Get company details
  getCompanyDetails: async (ticker: string): Promise<Company> => {
    const response = await api.get<Company>(`/companies/${ticker}`);
    return response.data;
  },

  // Get company (alias for compatibility)
  getCompany: async (ticker: string): Promise<AxiosResponse<Company>> => {
    return api.get<Company>(`/companies/${ticker}`);
  },

  // Get documents for a company
  getDocuments: async (ticker: string): Promise<AxiosResponse<{ documents: Document[] }>> => {
    return api.get<{ documents: Document[] }>(`/companies/${ticker}/documents`);
  },

  // Get reports for a company
  getReports: async (ticker: string): Promise<AxiosResponse<{ reports: Report[] }>> => {
    return api.get<{ reports: Report[] }>(`/companies/${ticker}/reports`);
  },

  // Refresh knowledge base
  refreshKnowledgeBase: async (ticker: string, options: Record<string, any> = {}): Promise<any> => {
    const response = await api.post(`/companies/${ticker}/knowledge-base/refresh`, options);
    return response.data;
  },

  // Get knowledge base status
  getKnowledgeBaseStatus: async (ticker: string): Promise<KnowledgeBaseStatus> => {
    const response = await api.get<KnowledgeBaseStatus>(`/companies/${ticker}/knowledge-base/status`);
    return response.data;
  },

  // Get knowledge base content with pagination and filtering
  getKnowledgeBaseContent: async (
    ticker: string, 
    page: number = 1, 
    pageSize: number = 20,
    documentType?: string,
    searchQuery?: string
  ): Promise<KnowledgeBaseContentResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    
    if (documentType) {
      params.append('document_type', documentType);
    }
    
    if (searchQuery) {
      params.append('search', searchQuery);
    }
    
    const response = await api.get<KnowledgeBaseContentResponse>(
      `/companies/${ticker}/knowledge-base/content?${params}`
    );
    return response.data;
  },

  // Get knowledge base document types
  getKnowledgeBaseDocumentTypes: async (ticker: string): Promise<KnowledgeBaseDocumentTypesResponse> => {
    const response = await api.get<KnowledgeBaseDocumentTypesResponse>(
      `/companies/${ticker}/knowledge-base/document-types`
    );
    return response.data;
  },

  // Get investment data
  getInvestmentData: async (ticker: string): Promise<InvestmentData> => {
    const response = await api.get<InvestmentData>(`/companies/${ticker}/investment-data`);
    return response.data;
  },

  // Upload document
  uploadDocument: async (ticker: string, formData: FormData): Promise<UploadResult> => {
    const response = await api.post<UploadResult>(`/companies/${ticker}/documents/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Generate report
  generateReport: async (ticker: string, reportData: ReportGenerationData): Promise<Report> => {
    const response = await api.post<Report>(`/companies/${ticker}/reports/generate`, reportData);
    return response.data;
  },

  // Refresh knowledge base for all companies
  refreshAllKnowledgeBases: async (): Promise<RefreshStartResponse> => {
    const response = await api.post<RefreshStartResponse>('/companies/refresh-all');
    return response.data;
  },

  // Get refresh job status
  getRefreshJobStatus: async (jobId: string): Promise<RefreshJob> => {
    const response = await api.get<RefreshJob>(`/companies/refresh-status/${jobId}`);
    return response.data;
  },
};

export default companyService;
