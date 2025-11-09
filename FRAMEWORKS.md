# 🎯 Puda AI - Key Frameworks

**Core frameworks for Puda's ML body to work properly.**

---

## Framework Stack

### 🔥 PyTorch — Training Backbone
**Purpose:** Deep learning framework for model training and inference

```python
import torch
import torch.nn as nn
import torch.optim as optim

# Example: Train a model
model = MobileNetV3Small(num_classes=10)
optimizer = optim.Adam(model.parameters(), lr=1e-4)
criterion = nn.CrossEntropyLoss()

# Training loop
for images, labels in dataloader:
    optimizer.zero_grad()
    outputs = model(images)
    loss = criterion(outputs, labels)
    loss.backward()
    optimizer.step()
```

**Why PyTorch?**
- Industry standard for research and production
- Dynamic computation graphs (easier debugging)
- Excellent ecosystem (torchvision, torchaudio, etc.)
- Native ONNX export support

**Version:** `torch>=2.0.0`

---

### 🤗 Transformers (Hugging Face) — Pretrained Models and Tokenizers
**Purpose:** Access to thousands of pretrained models and tokenizers

```python
from transformers import AutoTokenizer, AutoModel

# Load pretrained BERT for text understanding
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
model = AutoModel.from_pretrained("distilbert-base-uncased")

# Tokenize OCR text
text = "Invoice for $1,500.00 dated 2025-11-08"
inputs = tokenizer(text, return_tensors="pt")
outputs = model(**inputs)

# Use for document classification, entity extraction, etc.
```

**Why Transformers?**
- Pretrained models save weeks of training time
- State-of-the-art NLP and vision models
- Unified API across all model architectures
- Easy fine-tuning on custom data

**Models We'll Use:**
- **DistilBERT**: Text understanding from OCR output (~66M params)
- **LayoutLM**: Document understanding with layout (~125M params)
- **Vision Transformers (ViT)**: Image classification (~86M params)

**Version:** `transformers>=4.35.0`

---

### 🚀 FastAPI — Simple REST Interface for Inference
**Purpose:** Modern, fast API framework for ML model serving

```python
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Puda ML API")

class ClassificationRequest(BaseModel):
    image_path: str
    confidence_threshold: float = 0.7

class ClassificationResponse(BaseModel):
    doc_type: str
    confidence: float
    severity: str  # auto, manual, qc

@app.post("/classify", response_model=ClassificationResponse)
async def classify_document(request: ClassificationRequest):
    # Use inference engine
    result = ml_engine.predict_single(request.image_path)
    
    # Route based on confidence
    if result['confidence'] > 0.9:
        severity = 'auto'
    elif result['confidence'] > 0.7:
        severity = 'manual'
    else:
        severity = 'qc'
    
    return ClassificationResponse(
        doc_type=result['class'],
        confidence=result['confidence'],
        severity=severity
    )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Handle file upload
    contents = await file.read()
    # Process image...
    return {"filename": file.filename}

# Run: uvicorn ml_api:app --host 0.0.0.0 --port 8081
```

**Why FastAPI?**
- Automatic API documentation (Swagger UI)
- Type validation with Pydantic
- Async support for concurrent requests
- 3x faster than Flask for ML workloads
- Native Python 3.6+ type hints

**Integration:**
- Dashboard API (Flask): User interface, routing, QC
- ML API (FastAPI): Model inference, classification
- Both run on different ports (8080, 8081)

**Version:** `fastapi>=0.104.0`, `uvicorn>=0.24.0`

---

### ⚡ ONNX Runtime — Portable Inference Backend
**Purpose:** Cross-platform, optimized model inference

```python
import onnxruntime as ort
import numpy as np

# Load ONNX model
session = ort.InferenceSession("classifier.onnx")

# Get input/output names
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

# Run inference
image = np.random.randn(1, 3, 224, 224).astype(np.float32)
result = session.run([output_name], {input_name: image})

# Result is 3-5x faster than PyTorch on CPU
```

**Why ONNX Runtime?**
- **Fast**: 2-5x faster than PyTorch on CPU
- **Portable**: Works on Windows, Linux, macOS, mobile
- **Language agnostic**: Python, C++, C#, Java, JavaScript
- **Production ready**: Used by Microsoft, Meta, AWS

**Performance Benefits:**
```
PyTorch:       10ms per image
ONNX Runtime:   3ms per image (3.3x speedup)
TensorRT:       1ms per image (10x speedup on GPU)
```

**Version:** `onnxruntime>=1.16.0`

---

### 📊 Pandas / NumPy — Data Manipulation
**Purpose:** Data loading, preprocessing, and analysis

```python
import pandas as pd
import numpy as np

# Load training data
df = pd.read_csv("training_data.csv")

# Statistics
print(f"Total documents: {len(df)}")
print(f"Document types:\n{df['doc_type'].value_counts()}")

# Filter and process
invoices = df[df['doc_type'] == 'invoice']
amounts = invoices['amount'].apply(lambda x: float(x.replace('$', '')))
print(f"Average invoice: ${amounts.mean():.2f}")

# Create training batches
def create_batches(images, labels, batch_size=32):
    indices = np.arange(len(images))
    np.random.shuffle(indices)
    
    for start in range(0, len(images), batch_size):
        batch_idx = indices[start:start + batch_size]
        yield images[batch_idx], labels[batch_idx]
```

**Why Pandas/NumPy?**
- **NumPy**: Fast array operations, tensor manipulation
- **Pandas**: Easy data loading, filtering, grouping
- **Integration**: Works seamlessly with PyTorch tensors

**Use Cases:**
- Load training data from CSV/JSON
- Analyze model performance metrics
- Generate training/validation splits
- Process OCR output data

**Version:** `numpy>=1.24.0`, `pandas>=2.0.0`

---

### 🔬 Optuna — Hyperparameter Tuning (Optional)
**Purpose:** Automated hyperparameter optimization

```python
import optuna

def objective(trial):
    # Suggest hyperparameters
    lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
    dropout = trial.suggest_float("dropout", 0.1, 0.5)
    
    # Train model with these hyperparameters
    model = create_model(dropout=dropout)
    accuracy = train_and_evaluate(model, lr=lr, batch_size=batch_size)
    
    return accuracy

# Run optimization
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=50)

print(f"Best params: {study.best_params}")
print(f"Best accuracy: {study.best_value:.2%}")
```

**Why Optuna?**
- **Smart search**: Bayesian optimization, not random
- **Parallel**: Run multiple trials concurrently
- **Pruning**: Stop bad trials early
- **Visualization**: Built-in plotting

**When to Use:**
- After baseline model is working
- When accuracy needs improvement
- Before production deployment
- Optional: Add when needed (`pip install optuna`)

**Version:** `optuna>=3.4.0` (commented out by default)

---

## Framework Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Puda AI System                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Training Pipeline (PyTorch)              │  │
│  │  • Load data with Pandas                              │  │
│  │  • Train with PyTorch + Transformers                  │  │
│  │  • Optimize with Optuna (optional)                    │  │
│  │  • Export to ONNX                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Production Inference (ONNX Runtime)          │  │
│  │  • Load ONNX model                                    │  │
│  │  • Serve via FastAPI                                  │  │
│  │  • 3-5x faster than PyTorch                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Dashboard API (Flask)                      │  │
│  │  • Call FastAPI ML endpoints                          │  │
│  │  • Route documents (auto/manual/qc)                   │  │
│  │  • User interface                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Full Installation (All Frameworks)
```bash
pip install -r requirements.txt
```

### Minimal Installation (Inference Only)
```bash
# Core ML
pip install torch torchvision transformers

# Inference
pip install onnx onnxruntime

# API
pip install fastapi uvicorn pydantic

# Data
pip install numpy pandas
```

### Development Installation (Training + Optimization)
```bash
# Everything above plus:
pip install optuna tensorboard scikit-learn
```

---

## Framework Versions

| Framework | Version | Purpose |
|-----------|---------|---------|
| PyTorch | >=2.0.0 | Training backbone |
| Transformers | >=4.35.0 | Pretrained models |
| FastAPI | >=0.104.0 | ML inference API |
| Uvicorn | >=0.24.0 | ASGI server |
| ONNX | >=1.14.0 | Model export |
| ONNX Runtime | >=1.16.0 | Fast inference |
| NumPy | >=1.24.0 | Array operations |
| Pandas | >=2.0.0 | Data manipulation |
| Optuna | >=3.4.0 | Hyperparameter tuning (optional) |

---

## Quick Start Examples

### 1. Train with PyTorch + Transformers
```python
from transformers import AutoModel
import torch.nn as nn

# Load pretrained backbone
backbone = AutoModel.from_pretrained("google/vit-base-patch16-224")

# Add classification head
class DocumentClassifier(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.backbone = backbone
        self.classifier = nn.Linear(768, num_classes)
    
    def forward(self, x):
        features = self.backbone(x).last_hidden_state[:, 0]
        return self.classifier(features)

model = DocumentClassifier()
# Train...
```

### 2. Export to ONNX
```python
from src.ml.models import export_model

# Export trained model
export_model(model, "classifier.onnx", format="onnx")
```

### 3. Serve with FastAPI
```python
from fastapi import FastAPI
import onnxruntime as ort

app = FastAPI()
session = ort.InferenceSession("classifier.onnx")

@app.post("/classify")
async def classify(image: UploadFile):
    # Preprocess image
    tensor = preprocess(image)
    
    # Run ONNX inference (fast!)
    result = session.run(None, {"input": tensor})
    
    return {"class": result[0], "confidence": result[1]}
```

### 4. Analyze with Pandas
```python
import pandas as pd

# Load results
df = pd.read_csv("classification_results.csv")

# Analysis
print(df.groupby('doc_type')['confidence'].mean())
print(df[df['confidence'] < 0.7].shape[0], "docs sent to QC")
```

---

## Production Deployment Stack

**Development:**
- PyTorch: Model development and training
- Transformers: Pretrained model access
- Pandas/NumPy: Data analysis
- Optuna: Hyperparameter optimization

**Production:**
- ONNX Runtime: Fast inference (no PyTorch)
- FastAPI: ML API endpoints
- Flask: Dashboard and user interface
- Docker: Containerized deployment

**Deployment:**
```bash
# Training server (GPU)
python train_model.py
python export_model.py

# Production server (CPU)
uvicorn ml_api:app --host 0.0.0.0 --port 8081  # FastAPI ML API
python dashboard_api.py --port 8080            # Flask Dashboard
```

---

## Framework File Structure

```
Puda/
├── requirements.txt         # All framework dependencies
├── src/
│   ├── ml/
│   │   ├── models/         # PyTorch models
│   │   ├── data/           # Pandas/NumPy data loading
│   │   ├── inference/      # ONNX Runtime inference
│   │   └── training/       # PyTorch training + Optuna
│   └── api/
│       ├── ml_api.py       # FastAPI ML endpoints
│       └── dashboard_api.py # Flask dashboard (existing)
├── models/
│   ├── classifier.pt       # PyTorch checkpoint
│   └── classifier.onnx     # ONNX production model
└── data/
    └── training/           # Pandas-friendly CSVs
```

---

## Next Steps

1. **Install frameworks**: `pip install -r requirements.txt`
2. **Train baseline model**: Use PyTorch + Transformers
3. **Export to ONNX**: `export_model(model, "model.onnx")`
4. **Create FastAPI endpoint**: Serve ONNX model
5. **Integrate with Dashboard**: Call FastAPI from Flask
6. **Optimize (optional)**: Use Optuna for hyperparameter tuning

---

**All frameworks are now configured for Puda's body to work properly!** 🚀
