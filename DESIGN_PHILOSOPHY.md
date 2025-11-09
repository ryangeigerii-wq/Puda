# 🎨 Puda AI - Design Philosophy

**"Start Light, Scale Smart"**

---

## Core Principles

### 1. **Everything Modular**
> Models, data, and inference are completely separated.

**Why?**
- Swap models without touching data pipelines
- Test new architectures without system rewrites
- Deploy different models for different document types
- Independent scaling of components

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                    Puda AI System                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │   Models    │   │    Data     │   │  Inference  │  │
│  │   Module    │   │   Module    │   │   Module    │  │
│  │             │   │             │   │             │  │
│  │  • CNN      │   │  • Loader   │   │  • Engine   │  │
│  │  • Trans.   │   │  • Preproc  │   │  • Batch    │  │
│  │  • Hybrid   │   │  • Augment  │   │  • Stream   │  │
│  └─────────────┘   └─────────────┘   └─────────────┘  │
│         ↓                 ↓                 ↓           │
│         └─────────────────┴─────────────────┘           │
│                    Unified Interface                    │
└─────────────────────────────────────────────────────────┘
```

### 2. **Start Light**
> Small transformer or CNN backbone. Expand only when proven necessary.

**Why?**
- Fast iteration cycles
- Lower compute requirements
- Easier debugging and understanding
- Production-ready from day one
- Cost-effective training and inference

**Model Evolution Path:**
```
Phase 1: Lightweight Baseline (NOW)
├── CNN Backbone (ResNet-18 / MobileNet)
├── Small Transformer (DistilBERT / TinyBERT)
└── ~10-50M parameters

Phase 2: Optimized Production (WHEN NEEDED)
├── Fine-tuned CNN + Attention
├── Task-specific transformer heads
└── ~50-200M parameters

Phase 3: Advanced System (IF NEEDED)
├── Multi-modal ensemble
├── Custom architecture
└── ~200M-1B parameters
```

### 3. **Exportable**
> Every model must be exportable to ONNX for production deployment.

**Why?**
- Cross-platform deployment (Windows, Linux, macOS, mobile)
- No PyTorch dependency in production
- Faster inference with optimized runtimes (TensorRT, ONNX Runtime)
- Integration with any language (Python, C++, JavaScript, Java)
- Smaller model size with optimization passes

**Export Formats:**
```python
from src.ml.models import export_model

# ONNX: Cross-platform standard
export_model(model, "model.onnx", format="onnx")

# TorchScript: PyTorch optimized
export_model(model, "model.pt", format="torchscript")

# Quantized: Mobile/edge (4x smaller)
export_model(model, "model_q.pt", format="quantized")

# All formats at once
export_model(model, "exports/model", format="all")
```

### 4. **Separation of Concerns**
Each module has a single, well-defined responsibility.

**Module Boundaries:**
```python
# ✅ GOOD: Clear separation
from src.ml.models import DocumentClassifier
from src.ml.data import DocumentDataset
from src.ml.inference import InferenceEngine

classifier = DocumentClassifier.load("models/classifier_v1.pt")
dataset = DocumentDataset("data/training")
engine = InferenceEngine(classifier)

# ❌ BAD: Mixed responsibilities
from src.ml import DoEverything
result = DoEverything.process("data/doc.jpg")  # What does this do?
```

---

## Module Design Patterns

### Models Module (`src/ml/models/`)

**Responsibility:** Define model architectures only.

**Structure:**
```
src/ml/models/
├── __init__.py
├── base.py              # Abstract base classes
├── backbones/
│   ├── cnn.py           # ResNet, MobileNet, EfficientNet
│   ├── transformer.py   # DistilBERT, TinyBERT
│   └── hybrid.py        # Vision Transformer (ViT) variants
├── heads/
│   ├── classification.py
│   ├── detection.py
│   └── segmentation.py
└── registry.py          # Model factory/registry
```

**Example:**
```python
from src.ml.models import ModelRegistry

# Register models
@ModelRegistry.register("mobilenet_v3")
class MobileNetV3Classifier(BaseModel):
    def __init__(self, num_classes=10):
        super().__init__()
        self.backbone = mobilenet_v3_small(pretrained=True)
        self.classifier = nn.Linear(1024, num_classes)
    
    def forward(self, x):
        features = self.backbone(x)
        return self.classifier(features)

# Use registry
model = ModelRegistry.create("mobilenet_v3", num_classes=5)
```

### Data Module (`src/ml/data/`)

**Responsibility:** Data loading, preprocessing, augmentation.

**Structure:**
```
src/ml/data/
├── __init__.py
├── datasets.py          # PyTorch Dataset classes
├── preprocessing.py     # Image preprocessing pipelines
├── augmentation.py      # Data augmentation strategies
├── loaders.py           # DataLoader configurations
└── transforms.py        # Custom transforms
```

**Example:**
```python
from src.ml.data import DocumentDataset, get_preprocessing_pipeline

# Preprocessing is separate from model
preprocess = get_preprocessing_pipeline(
    resize=(224, 224),
    normalize=True,
    augment=True
)

dataset = DocumentDataset(
    data_dir="data/documents",
    transform=preprocess
)

# Easy to swap preprocessing without touching model
preprocess_v2 = get_preprocessing_pipeline(
    resize=(384, 384),  # Higher resolution
    normalize=True,
    augment=False       # No augmentation for inference
)
```

### Inference Module (`src/ml/inference/`)

**Responsibility:** Run models on data, handle batching, optimization.

**Structure:**
```
src/ml/inference/
├── __init__.py
├── engine.py            # Core inference engine
├── batch.py             # Batch processing
├── streaming.py         # Real-time inference
├── optimization.py      # TensorRT, ONNX, quantization
└── ensemble.py          # Multi-model ensembles
```

**Example:**
```python
from src.ml.inference import InferenceEngine

# Inference is separate from model definition
engine = InferenceEngine(
    model=classifier,
    device="cuda",
    batch_size=32,
    optimize=True  # Enable TensorRT/ONNX
)

# Batch inference
results = engine.predict_batch(image_paths)

# Streaming inference
for image_path in image_stream:
    result = engine.predict_single(image_path)
```

---

## Lightweight Model Strategy

### Phase 1: Baseline Models (Current Focus)

#### Document Classification
**Model:** MobileNetV3-Small  
**Parameters:** ~2.5M  
**Input:** 224×224 RGB  
**Output:** Document type (invoice, receipt, contract, etc.)

```python
class LightweightClassifier(nn.Module):
    """Minimal viable classifier for document types."""
    def __init__(self, num_classes=10):
        super().__init__()
        # Start with proven, efficient architecture
        self.backbone = mobilenet_v3_small(pretrained=True)
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(1024, num_classes)
        )
    
    def forward(self, x):
        features = self.backbone(x)
        return self.classifier(features)
```

**Why MobileNetV3?**
- Optimized for mobile/edge devices
- Fast inference (~5-10ms per image)
- Pre-trained on ImageNet (transfer learning)
- Proven architecture from Google

#### Text Recognition (OCR Alternative)
**Model:** DistilBERT  
**Parameters:** ~66M (distilled from BERT's 110M)  
**Input:** Tokenized text  
**Output:** Document entities, key information

```python
class LightweightTextExtractor(nn.Module):
    """Minimal text understanding for parsed OCR."""
    def __init__(self):
        super().__init__()
        # Start with efficient transformer
        self.encoder = DistilBertModel.from_pretrained('distilbert-base-uncased')
        self.entity_classifier = nn.Linear(768, num_entity_types)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids, attention_mask)
        return self.entity_classifier(outputs.last_hidden_state)
```

**Why DistilBERT?**
- 40% smaller than BERT
- 60% faster inference
- Retains 97% of BERT's performance
- Works with existing Tesseract OCR output

### Phase 2: Optimization (When Needed)

**Triggers for Phase 2:**
- Accuracy < 90% on validation set
- Specific document types consistently fail
- User feedback indicates poor quality

**Optimizations:**
```python
# Quantization: Reduce model size by 4x
quantized_model = torch.quantization.quantize_dynamic(
    model, {nn.Linear}, dtype=torch.qint8
)

# ONNX: Cross-platform optimization
torch.onnx.export(model, dummy_input, "model.onnx")

# TensorRT: GPU optimization
trt_model = torch2trt(model, [dummy_input])
```

### Phase 3: Scaling (Only If Required)

**Triggers for Phase 3:**
- Business case proven (>10K docs/day)
- Complex documents require advanced understanding
- Multi-modal processing needed (text + layout + images)

**Advanced Options:**
- Vision Transformer (ViT) for layout understanding
- Custom hybrid architecture (CNN + Transformer)
- Multi-task learning (classification + extraction + QC)

---

## Modular Training Pipeline

### Training Module (`src/ml/training/`)

**Structure:**
```
src/ml/training/
├── __init__.py
├── trainer.py           # Training loop
├── callbacks.py         # Hooks for logging, checkpoints
├── metrics.py           # Evaluation metrics
└── config.py            # Training configurations
```

**Example:**
```python
from src.ml.training import Trainer
from src.ml.models import ModelRegistry
from src.ml.data import DocumentDataset

# Everything is configurable and swappable
config = TrainingConfig(
    model_name="mobilenet_v3",
    epochs=10,
    batch_size=32,
    learning_rate=1e-4,
    optimizer="adam"
)

trainer = Trainer(
    model=ModelRegistry.create(config.model_name),
    train_dataset=DocumentDataset("data/train"),
    val_dataset=DocumentDataset("data/val"),
    config=config
)

# Train with callbacks
trainer.train(
    callbacks=[
        CheckpointCallback(save_dir="checkpoints"),
        TensorBoardCallback(log_dir="runs"),
        EarlyStoppingCallback(patience=3)
    ]
)
```

---

## Integration with Puda System

### Document Processing Flow with ML

```
┌─────────────────────────────────────────────────────────┐
│                Physical Document Flow                    │
│  Intake → Prep → Scan → QC → Output                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓ OCR Output (Tesseract)
┌─────────────────────────────────────────────────────────┐
│                  ML Pipeline (Modular)                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐  │
│  │  1. Data Module: Load & Preprocess               │  │
│  │     • Normalize image                             │  │
│  │     • Resize to model input size                  │  │
│  │     • Tokenize OCR text                           │  │
│  └──────────────────────────────────────────────────┘  │
│                     ↓                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  2. Model Module: Inference                       │  │
│  │     • CNN: Document type classification           │  │
│  │     • Transformer: Entity extraction              │  │
│  │     • Output: Predictions + confidence            │  │
│  └──────────────────────────────────────────────────┘  │
│                     ↓                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  3. Inference Module: Route Decision              │  │
│  │     • High confidence (>0.9) → Auto               │  │
│  │     • Medium confidence (0.7-0.9) → Manual        │  │
│  │     • Low confidence (<0.7) → QC Review           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Routing Decision (dashboard_api.py)         │
│  • Store predictions in routing audit log               │
│  • Assign to appropriate queue (auto/manual/qc)         │
│  • Trigger downstream processing                        │
└─────────────────────────────────────────────────────────┘
```

### API Integration

```python
# In dashboard_api.py
from src.ml.inference import InferenceEngine
from src.ml.models import ModelRegistry

# Initialize at startup (modular!)
classifier = ModelRegistry.load("models/classifier_v1.pt")
inference_engine = InferenceEngine(classifier, device="cpu")

@app.route('/api/ml/classify', methods=['POST'])
def classify_document():
    """Classify document and route appropriately."""
    image_path = request.json['image_path']
    ocr_text = request.json.get('ocr_text', '')
    
    # Inference module handles prediction
    result = inference_engine.predict_single(image_path)
    
    # Route based on confidence
    if result['confidence'] > 0.9:
        severity = 'auto'
    elif result['confidence'] > 0.7:
        severity = 'manual'
    else:
        severity = 'qc'
    
    # Log to routing system
    log_routing_decision(
        doc_id=request.json['doc_id'],
        doc_type=result['class'],
        severity=severity,
        confidence=result['confidence'],
        model_version=classifier.version
    )
    
    return jsonify(result)
```

---

## Development Workflow

### 1. Model Development (Isolated)

```bash
# Work in ml module independently
cd src/ml/models
python experiments/train_mobilenet.py --config configs/baseline.yaml

# Test model without touching main system
python experiments/evaluate.py --model checkpoints/best.pt
```

### 2. Data Preparation (Isolated)

```bash
# Prepare data separately
cd src/ml/data
python prepare_dataset.py --input data/raw --output data/processed

# Test preprocessing pipeline
python test_preprocessing.py
```

### 3. Integration (Modular)

```bash
# Register new model
python -c "
from src.ml.models import ModelRegistry
ModelRegistry.register_checkpoint('mobilenet_v1', 'checkpoints/best.pt')
"

# Update inference config (no code changes!)
echo "model: mobilenet_v1" > config/inference.yaml

# Restart API server
.\restart-server.ps1
```

---

## File Structure

```
Puda/
├── src/
│   ├── ml/                          # ML module (new)
│   │   ├── __init__.py
│   │   ├── models/                  # Model architectures
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── backbones/
│   │   │   │   ├── cnn.py
│   │   │   │   └── transformer.py
│   │   │   ├── heads/
│   │   │   │   └── classification.py
│   │   │   └── registry.py
│   │   ├── data/                    # Data handling
│   │   │   ├── __init__.py
│   │   │   ├── datasets.py
│   │   │   ├── preprocessing.py
│   │   │   └── augmentation.py
│   │   ├── inference/               # Inference engine
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── batch.py
│   │   │   └── optimization.py
│   │   └── training/                # Training pipeline
│   │       ├── __init__.py
│   │       ├── trainer.py
│   │       ├── callbacks.py
│   │       └── metrics.py
│   ├── physical/                    # Existing modules
│   ├── authorization/
│   ├── storage/
│   └── ...
├── models/                          # Model checkpoints
│   ├── classifier_v1.pt
│   ├── classifier_v1.onnx
│   └── metadata/
│       └── classifier_v1.json
├── data/
│   ├── raw/                         # Raw scanned images
│   ├── processed/                   # Preprocessed data
│   └── training/                    # Training datasets
│       ├── train/
│       ├── val/
│       └── test/
└── configs/
    ├── models/
    │   ├── mobilenet_v3.yaml
    │   └── distilbert.yaml
    └── inference/
        └── production.yaml
```

---

## Key Benefits

### ✅ Modularity
- Swap models: `ModelRegistry.load("new_model.pt")`
- Change preprocessing: Update `data/preprocessing.py`
- Optimize inference: Switch `engine.device = "cuda"`

### ✅ Lightweight Start
- MobileNetV3: ~2.5M params, 5-10ms inference
- DistilBERT: ~66M params (vs BERT's 110M)
- Total model size: <300MB
- CPU inference capable

### ✅ Clear Separation
- Models don't know about data loading
- Data doesn't know about inference optimization
- Inference doesn't know about model internals
- Each module testable independently

### ✅ Scalability Path
- Phase 1: Baseline (now)
- Phase 2: Optimization (when proven)
- Phase 3: Advanced (if required)
- No rewrites needed, just swap modules

---

## Getting Started

### 1. Install ML Dependencies

```bash
pip install torch torchvision transformers
pip install onnx onnxruntime  # For optimization
pip install tensorboard  # For training visualization
```

### 2. Create Baseline Models

```bash
# Create model architecture
python src/ml/models/create_baseline.py

# Train on sample data
python src/ml/training/train_baseline.py --config configs/baseline.yaml

# Export for production
python src/ml/models/export.py --checkpoint models/best.pt --format onnx
```

### 3. Integrate with API

```python
# In dashboard_api.py
from src.ml.inference import InferenceEngine

# Initialize at startup
ml_engine = InferenceEngine.from_config("configs/inference/production.yaml")

# Use in endpoints
@app.route('/api/ml/classify', methods=['POST'])
def classify():
    return jsonify(ml_engine.predict(request.json['image_path']))
```

---

## Philosophy in Action

**Traditional Monolithic Approach:**
```python
# ❌ Everything coupled
class AIDocumentProcessor:
    def __init__(self):
        self.model = SomeHugeModel()
        self.preprocessor = HardcodedPreprocessing()
        
    def process(self, doc):
        # Model, data, inference all mixed
        preprocessed = self.preprocessor.preprocess(doc)
        result = self.model.predict(preprocessed)
        return self.postprocess(result)
```

**Puda Modular Approach:**
```python
# ✅ Clean separation
from src.ml.models import ModelRegistry
from src.ml.data import get_preprocessing_pipeline
from src.ml.inference import InferenceEngine

# Each component is independent
model = ModelRegistry.load("mobilenet_v3")
preprocess = get_preprocessing_pipeline("standard")
engine = InferenceEngine(model)

# Easy to swap any component
model = ModelRegistry.load("efficientnet_b0")  # Swap model
preprocess = get_preprocessing_pipeline("high_res")  # Swap preprocessing
engine = InferenceEngine(model, optimize=True)  # Add optimization
```

---

**Remember:** Start light, prove value, scale smart. Every component should be swappable without system rewrites.

---

**Version**: 1.0.0  
**Last Updated**: November 8, 2025  
**Philosophy Owner**: Puda AI Team
