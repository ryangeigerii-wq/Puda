# AI Paper Reader Project - Copilot Instructions

## Project Overview
This is a Python-based AI system that reads physical papers using OCR, classifies/sorts documents, and provides authorization controls.

## Core Features
- **Document Scanning**: OCR integration using Tesseract for reading physical papers
- **Classification & Sorting**: ML-based document categorization system
- **Authorization**: User authentication and document access control
- **Output Generation**: Processed document output with metadata

## Technology Stack
- Python 3.9+
- Tesseract OCR for text extraction
- OpenCV for image preprocessing
- scikit-learn for ML classification
- Flask/FastAPI for REST API
- SQLite/PostgreSQL for data storage

## Project Structure
- `src/scanner/`: OCR and image processing modules
- `src/classifier/`: ML-based document classification
- `src/auth/`: Authorization and user management
- `src/api/`: REST API endpoints
- `src/physical/`: Physical paper handling and zone management
  - `zones.py`: Zone classes (Intake, Prep, Scanning)
  - `control.py`: Central paper control system
- `config/`: Configuration files
- `tests/`: Unit and integration tests
- CLI interfaces: `intake_cli.py`, `prep_cli.py`, `scan_cli.py`

## Development Guidelines
- Use type hints for all Python functions
- Follow PEP 8 style guidelines
- Write docstrings for all public functions
- Implement error handling and logging
- Create unit tests for core functionality
