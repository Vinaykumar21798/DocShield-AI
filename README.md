# PII-PHI Document Intelligence PoC
## Week 1 Progress Report – Architecture & Foundation

---

## Project Overview

The goal of this project is to build a Document Intelligence pipeline capable of processing uploaded documents through multiple stages, including document ingestion, OCR, entity extraction, and further AI-based document analysis.

Week 1 focused on establishing the core backend infrastructure, database design, upload pipeline, and asynchronous processing framework that will support the upcoming OCR and document intelligence modules.

---

# Week 1 Objectives

The following objectives were planned for Week 1:

- Finalize Dev 1 architecture
- Setup FastAPI project structure
- Configure PostgreSQL
- Configure Redis
- Design database schema
- Design Upload API
- Design Document Processing workflow
- Build upload pipeline
- Prepare asynchronous processing infrastructure

---

# Week 1 Deliverables Status

| Deliverable | Status |
|------------|--------|
| Dev 1 Architecture Finalized | ✅ Completed |
| FastAPI Project Setup | ✅ Completed |
| PostgreSQL Configuration | ✅ Completed |
| Redis Configuration | ✅ Completed |
| Database Schema Design | ✅ Completed |
| Upload API Design | ✅ Completed |
| Upload Module Implementation | ✅ Completed |
| Document Processing Job Creation | ✅ Completed |
| Redis Queue Integration | ✅ Completed |
| Background Worker Setup | ✅ Completed |
| Document Processing Workflow Design | ✅ Completed |

---

# Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Queue System | Redis |
| Data Validation | Pydantic |
| File Storage | Local Storage |
| API Documentation | Swagger / OpenAPI |

---

# Current Project Structure

```text
PII-PHI-Document-Intelligence-PoC/
│
├── api/
│   ├── dependencies.py
│   └── routes/
│       └── upload.py
│
├── core/
│   ├── config.py
│   └── database.py
│
├── database/
│   ├── models/
│   │   ├── document.py
│   │   ├── processing_job.py
│   │   └── ocr_result.py
│   │
│   └── repositories/
│       ├── base_repository.py
│       ├── document_repository.py
│       ├── processing_job_repository.py
│       └── ocr_result_repository.py
│
├── modules/
│   └── upload/
│       ├── validator.py
│       ├── storage.py
│       └── service.py
│
├── redis_queue/
│   ├── redis_client.py
│   ├── job_schema.py
│   ├── producer.py
│   ├── consumer.py
│   └── worker.py
│
├── storage/
│   └── uploads/
│
├── main.py
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# Database Schema

## Documents

Stores metadata for every uploaded document.

| Field |
|------|
| id |
| filename |
| stored_filename |
| file_type |
| file_size |
| storage_path |
| status |
| created_at |
| updated_at |

---

## Processing Jobs

Tracks the processing status of each uploaded document.

| Field |
|------|
| id |
| document_id |
| job_status |
| workflow_stage |
| queue_name |
| worker_id |
| retry_count |
| error_message |
| started_at |
| completed_at |
| created_at |
| updated_at |

---

## OCR Results

Stores OCR extraction details for each processed document.

| Field |
|------|
| id |
| document_id |
| extraction_method |
| extracted_text |
| extracted_text_path |
| confidence_score |
| page_count |
| processing_time |
| is_searchable |
| created_at |
| updated_at |

---

# Upload API

## Endpoint

```
POST /upload
```

## Features

- Supports single document upload
- Supports multiple document upload
- File validation
- Local file storage
- Document metadata storage
- Processing Job creation
- Automatic Redis Queue publishing

---

# Current Processing Workflow

```text
Client
   │
   ▼
POST /upload
   │
   ▼
Validate Files
   │
   ▼
Store Files
   │
   ▼
Create Document Record
   │
   ▼
Create Processing Job
   │
   ▼
Store in PostgreSQL
   │
   ▼
Publish Job to Redis Queue
```

---

# Redis Processing Flow

```text
Upload API
      │
      ▼
Upload Service
      │
      ▼
Redis Producer
      │
      ▼
Redis Queue
      │
      ▼
Redis Consumer
      │
      ▼
Background Worker
```

The background worker infrastructure has been implemented and is ready for integrating OCR processing in the next development phase.

---

# Module Responsibilities

## API Layer

Responsible for receiving HTTP requests and exposing REST endpoints.

- Upload API
- Dependency Injection

---

## Upload Module

Responsible for handling document uploads.

Functions include:

- File validation
- File storage
- Document creation
- Processing Job creation
- Redis Queue publishing

---

## Database Layer

Responsible for persistent storage.

Includes:

- Documents
- Processing Jobs
- OCR Results

---

## Redis Queue

Responsible for asynchronous document processing.

Components:

- Producer
- Queue
- Consumer
- Worker

---

# Completed Features

- FastAPI backend setup
- PostgreSQL integration
- Redis integration
- SQLAlchemy models
- Repository layer
- Upload API
- Single file upload
- Multiple file upload
- File validation
- Local file storage
- Document metadata storage
- Processing Job creation
- Redis Producer
- Redis Consumer
- Background Worker infrastructure
- OCR database schema
- API documentation using Swagger

---

# Week 2 Planned Work

The following modules are planned for implementation in Week 2:

- OCR integration
- OCR processing within background workers
- OCR result storage
- Document text extraction
- Processing Job status updates during execution

---

# Week 1 Outcome

The foundational backend infrastructure for the Document Intelligence PoC has been successfully completed.

The system is capable of:

- Accepting one or multiple document uploads through a single API.
- Validating and storing uploaded documents.
- Recording document metadata in PostgreSQL.
- Creating processing jobs for each uploaded document.
- Publishing processing jobs to Redis for asynchronous execution.
- Running background workers prepared for OCR integration in the next development phase.

The project is now ready to proceed with OCR implementation and document intelligence processing in Week 2.