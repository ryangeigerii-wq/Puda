# Processing Layer (HomeBrew AI Core)

Purpose: Transform raw scans into structured data.

## Overview
The processing layer operates on page-level artifacts, enriching metadata and eventually converting them into structured representations suitable for downstream ML, indexing, and export.

### Current Components
- `RawArtifact`: Input container referencing file storage and metadata.
- `MetadataEnrichmentProcessor`: Adds processing timestamps and batch association.
- `DummyClassifier`: Placeholder structuring processor producing minimal `StructuredArtifact` objects.
- `ProcessingPipeline`: Orchestrates sequential processors then structurer.

### Roadmap (Future Layers)
1. OCR Text Normalization
2. Document Type Classification (real model)
3. Field Extraction / Entity Tagging (NER, regex, ML hybrids)
4. Sensitive Data Redaction (PII/PHI masking)
5. Quality Metrics & Confidence Scoring (model quality telemetry)
6. Aggregation / Cross-Doc Linking (thread related documents)
7. Export Formatting (JSON, XML, relational DB, search index)
8. Feedback Loop / Active Learning Hooks (human review integration)

### Example Usage
```python
from src.processing.processing import RawArtifact, ProcessingContext, build_default_pipeline, structured_to_json

pipeline = build_default_pipeline()
artifacts = [RawArtifact(page_id="PAPER-1:1", storage_ref="path/to/file1"), RawArtifact(page_id="PAPER-1:2", storage_ref="path/to/file2")]
ctx = ProcessingContext(batch_id="BATCH-ABC", operator_id="OP-42")
structured = pipeline.run(artifacts, ctx)
print(structured_to_json(structured))
```

### Extending
Implement a new processor:
```python
class MyProcessor:
    name = "my_processor"
    def process(self, artifact, ctx):
        artifact.metadata.setdefault("custom", {})["flag"] = True
        return artifact
```
Add to pipeline:
```python
pipeline = ProcessingPipeline(processors=[MetadataEnrichmentProcessor(), MyProcessor()], structurer=DummyClassifier())
```

### Testing
See `test_processing.py` for current sanity checks. Add more tests as new processors and structurers are introduced.

### Future Considerations
- Parallelism (process pages concurrently)
- Memory management / streaming (avoid full in-memory loads)
- Error handling strategy (retry, quarantine, metrics)
- Observability (metrics hooks, tracing IDs)
- Configuration-driven pipeline assembly

"""