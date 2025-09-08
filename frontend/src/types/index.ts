// API Types
export interface Company {
  ticker: string;
  company_name: string;
  knowledge_base_status: 'active' | 'processing' | 'error' | 'inactive';
  stats?: {
    total_reports: number;
    total_chunks: number;
    last_refresh?: string;
  };
  created_at?: string;
}

export interface Document {
  filename: string;
  file_size: number;
  upload_date: string;
  processing_status: 'processed' | 'processing' | 'error' | 'pending';
}

export interface Report {
  title?: string;
  report_type?: string;
  created_at: string;
  content?: Record<string, string>;
  metadata?: {
    sources_used?: string;
    generated_at?: string;
    model_used?: string;
  };
}

export interface UploadedFile {
  name: string;
  size: number;
  status: 'processed' | 'processing' | 'error' | 'pending';
  uploaded_at?: string;
}

export interface ReportSection {
  value: string;
  label: string;
}

export interface ReportType {
  value: string;
  label: string;
}

export interface GenerateReportRequest {
  report_type: string;
  focus_areas: string[];
  additional_context: string;
  sections: string[];
}

// Component Props
export interface CompanyCardProps {
  company: Company;
  onRefresh: (ticker: string) => void;
  onViewDetails: (ticker: string) => void;
  isRefreshing: boolean;
}

export interface DocumentUploadProps {
  companyTicker: string;
  onUploadSuccess?: (result: any) => void;
}

export interface ReportGenerationProps {
  companyTicker: string;
  companyName: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status?: string;
}

export interface CompaniesResponse {
  companies: Company[];
}

export interface DocumentsResponse {
  documents: Document[];
}

export interface ReportsResponse {
  reports: Report[];
}
