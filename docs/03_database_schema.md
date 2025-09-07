# AI Research Draft Generator - Database Schema

## 1. Overview

The system uses ChromaDB as the primary vector database for storing document embeddings and metadata. The database design supports efficient similarity search, metadata filtering, and persistent storage across application restarts.

## 2. ChromaDB Configuration

### 2.1 Database Location
- **Path**: `./chroma_db/`
- **Type**: Persistent local storage
- **Client**: `chromadb.PersistentClient`

### 2.2 Connection Configuration
```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)
```

## 3. Collection Schema

### 3.1 Naming Convention
- **Pattern**: `company_{ticker}_knowledge_base`
- **Examples**: 
  - `company_aapl_knowledge_base`
  - `company_msft_knowledge_base`
  - `company_googl_knowledge_base`

### 3.2 Document Chunk Structure

Each document chunk is stored as a vector with associated metadata:

```python
{
    "id": "aapl_report_20250613_chunk_001",
    "embedding": [0.1, 0.2, -0.3, ...],  # 1536-dimensional vector
    "metadata": {
        "company_ticker": "AAPL",
        "document_type": "past_report",
        "file_name": "APPLE_20250613_0902.pdf",
        "file_path": "data/research/AAPL/past_reports/APPLE_20250613_0902.pdf",
        "chunk_index": 1,
        "total_chunks": 45,
        "processed_date": "2025-09-07T10:30:00Z",
        "content_type": "research_analysis",
        "page_number": 1,
        "word_count": 512,
        "file_hash": "sha256:abc123...",
        "processing_version": "1.0"
    },
    "document": "Apple's Q2 2025 results demonstrated strong iPhone sales..."
}
```

### 3.3 Investment Data Structure

Investment data is stored as separate documents with special metadata:

```python
{
    "id": "aapl_investment_thesis_20250907",
    "embedding": [0.4, -0.1, 0.6, ...],
    "metadata": {
        "company_ticker": "AAPL",
        "document_type": "investment_data",
        "data_type": "investment_thesis",
        "file_name": "investmentthesis.json",
        "processed_date": "2025-09-07T10:30:00Z",
        "rating": "Overweight",
        "target_price": "240.00",
        "content_type": "structured_data",
        "is_current": true,
        "processing_version": "1.0"
    },
    "document": "Investment Thesis: With the largest base of pent up iPhone demand ever..."
}
```

## 4. Metadata Fields Reference

### 4.1 Required Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `company_ticker` | string | Stock ticker symbol | "AAPL" |
| `document_type` | string | Type of document | "past_report", "investment_data", "uploaded_document" |
| `file_name` | string | Original filename | "APPLE_20250613_0902.pdf" |
| `processed_date` | string | ISO timestamp of processing | "2025-09-07T10:30:00Z" |
| `content_type` | string | Content classification | "research_analysis", "structured_data" |
| `processing_version` | string | Schema version | "1.0" |

### 4.2 Document-Specific Metadata

#### Past Reports (`document_type: "past_report"`)
| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Full file system path |
| `chunk_index` | integer | Chunk sequence number |
| `total_chunks` | integer | Total chunks in document |
| `page_number` | integer | Original page number |
| `word_count` | integer | Words in chunk |
| `file_hash` | string | SHA256 hash for duplicate detection |

#### Investment Data (`document_type: "investment_data"`)
| Field | Type | Description |
|-------|------|-------------|
| `data_type` | string | "investment_thesis", "investment_drivers", "risks" |
| `rating` | string | Current investment rating |
| `target_price` | string | Price target |
| `is_current` | boolean | Whether this is latest data |

#### Uploaded Documents (`document_type: "uploaded_document"`)
| Field | Type | Description |
|-------|------|-------------|
| `upload_id` | string | Unique upload identifier |
| `upload_date` | string | Upload timestamp |
| `analysis_type` | string | Type of analysis requested |
| `file_size` | integer | File size in bytes |
| `user_description` | string | User-provided description |

## 5. Query Patterns

### 5.1 Similarity Search
```python
# Find similar content for new document analysis
results = collection.query(
    query_embeddings=[new_document_embedding],
    n_results=10,
    where={
        "company_ticker": "AAPL",
        "document_type": {"$in": ["past_report", "investment_data"]}
    },
    include=["documents", "metadatas", "distances"]
)
```

### 5.2 Metadata Filtering
```python
# Get all past reports for a company
results = collection.get(
    where={
        "company_ticker": "AAPL",
        "document_type": "past_report"
    },
    include=["documents", "metadatas"]
)
```

### 5.3 Current Investment Data
```python
# Get latest investment thesis
results = collection.get(
    where={
        "company_ticker": "AAPL",
        "document_type": "investment_data",
        "data_type": "investment_thesis",
        "is_current": True
    },
    include=["documents", "metadatas"]
)
```

## 6. Processing State Management

### 6.1 Processed Files Tracking

A separate JSON file tracks processing state for each company:

**File**: `chroma_db/processing_state/{ticker}.json`

```json
{
  "company_ticker": "AAPL",
  "last_updated": "2025-09-07T10:30:00Z",
  "processed_files": {
    "past_reports": [
      {
        "file_name": "APPLE_20250613_0902.pdf",
        "file_path": "data/research/AAPL/past_reports/APPLE_20250613_0902.pdf",
        "file_hash": "sha256:abc123...",
        "processed_date": "2025-09-07T09:15:00Z",
        "chunk_count": 45,
        "status": "completed"
      }
    ],
    "investment_data": [
      {
        "file_name": "investmentthesis.json",
        "file_path": "data/research/AAPL/investment_data/investmentthesis.json",
        "processed_date": "2025-09-07T10:30:00Z",
        "status": "completed"
      }
    ],
    "uploaded_documents": [
      {
        "upload_id": "upload_aapl_20250907_103500",
        "file_name": "AAPL_Q3_2025_Earnings_Transcript.pdf",
        "processed_date": "2025-09-07T10:35:00Z",
        "status": "completed"
      }
    ]
  },
  "statistics": {
    "total_chunks": 156,
    "total_documents": 4,
    "last_refresh_duration": "00:03:15"
  }
}
```

## 7. Data Lifecycle Management

### 7.1 Incremental Updates

1. **Past Reports**: Skip files that already exist with same hash
2. **Investment Data**: Always update to reflect latest changes
3. **Uploaded Documents**: Process once, then archive

### 7.2 Data Cleanup

1. **Stale Investment Data**: Mark old investment data as `is_current: false`
2. **Uploaded Documents**: Remove after 30 days
3. **Collection Optimization**: Periodic reindexing for performance

### 7.3 Backup Strategy

1. **ChromaDB Backup**: Copy entire `chroma_db/` directory
2. **Processing State**: Backup processing state JSON files
3. **Recovery**: Restore from backup or rebuild from source files

## 8. Performance Considerations

### 8.1 Indexing Strategy
- **Automatic**: ChromaDB handles vector indexing automatically
- **Collection Size**: Optimal for <100K documents per collection
- **Memory Usage**: ~1GB RAM for 10K documents with embeddings

### 8.2 Query Optimization
- **Metadata Filtering**: Use before similarity search for better performance
- **Result Limits**: Limit results to 50 for UI display
- **Caching**: Cache frequent queries (investment data, company stats)

### 8.3 Storage Estimates

| Data Type | Size per Item | Items per Company | Total per Company |
|-----------|---------------|-------------------|-------------------|
| Report Chunk | 2KB | ~200 | 400KB |
| Investment Data | 1KB | ~10 | 10KB |
| Metadata | 500B | ~210 | 105KB |
| **Total** | | | **~515KB** |

**System Total (15 companies)**: ~7.7MB

## 9. Security & Access Control

### 9.1 Data Access Patterns
- **Read-Heavy**: Similarity search and metadata queries
- **Write-Light**: Periodic knowledge base updates
- **No Direct Access**: All access through API layer

### 9.2 Data Validation
- **Schema Validation**: Ensure required metadata fields
- **Content Validation**: Verify document content format
- **Duplicate Prevention**: Use file hashes to prevent duplicates

## 10. Monitoring & Maintenance

### 10.1 Health Checks
```python
# Collection health check
def check_collection_health(collection_name):
    collection = client.get_collection(collection_name)
    count = collection.count()
    
    # Verify recent updates
    recent = collection.get(
        where={"processed_date": {"$gte": "2025-09-06T00:00:00Z"}},
        limit=1
    )
    
    return {
        "collection_name": collection_name,
        "document_count": count,
        "has_recent_updates": len(recent["ids"]) > 0,
        "status": "healthy" if count > 0 else "empty"
    }
```

### 10.2 Performance Metrics
- Collection document counts
- Query response times
- Processing duration tracking
- Storage size monitoring
