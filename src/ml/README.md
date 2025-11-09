# Puda ML Module

**Modular Machine Learning for Document Processing**

## Design Philosophy

✅ **Everything Modular** - Models, data, and inference are completely separated  
✅ **Start Light** - Small transformer or CNN backbone, expand when proven necessary  
✅ **Clear Separation** - Each module has single responsibility

## Quick Start

### 1. Install Dependencies

```bash
pip install torch torchvision
```

### 2. Create a Model

```python
from src.ml.models import ModelRegistry

# Use lightweight MobileNetV3 (2.5M params)
model = ModelRegistry.create(
    "mobilenet_v3_small",
    num_classes=10,
    pretrained=True
)

print(f"Parameters: {model.num_parameters:,}")
# Output: Parameters: 2,542,634
```

### 3. Run Inference

```python
from src.ml.inference import InferenceEngine

# Create inference engine
engine = InferenceEngine(
    model=model,
    device="cpu",  # or "cuda"
    batch_size=32
)

# Single prediction
result = engine.predict_single("document.jpg")
print(f"Class: {result['class']}, Confidence: {result['confidence']:.2%}")

# Batch prediction
results = engine.predict_batch([
    "doc1.jpg",
    "doc2.jpg",
    "doc3.jpg"
])
```

### 4. Benchmark Performance

```python
# Benchmark inference speed
stats = engine.benchmark(num_iterations=100)
print(f"Average inference: {stats['mean_ms']:.2f}ms")
# Expected: ~5-10ms on CPU, ~1-2ms on GPU
```

## Module Structure

```
src/ml/
├── models/              # Model architectures
│   ├── base.py          # Base classes
│   ├── registry.py      # Model factory
│   ├── backbones/       # CNN, Transformer, Hybrid
│   │   └── cnn.py       # MobileNet, ResNet, EfficientNet
│   └── heads/           # Classification, detection
├── data/                # Data handling (coming soon)
│   ├── datasets.py
│   ├── preprocessing.py
│   └── augmentation.py
├── inference/           # Inference engine
│   └── engine.py        # Batch, streaming, optimization
└── training/            # Training pipeline (coming soon)
    ├── trainer.py
    ├── callbacks.py
    └── metrics.py
```

## Available Models

### Lightweight CNN Backbones

| Model | Parameters | Inference (CPU) | Best For |
|-------|------------|----------------|----------|
| **MobileNetV3-Small** | 2.5M | 5-10ms | **Production (Start Here)** |
| MobileNetV3-Large | 5.5M | 10-15ms | Better accuracy |
| ResNet-18 | 11M | 15-20ms | Baseline comparison |

### Usage

```python
# Default: MobileNetV3-Small (recommended)
model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)

# Larger model if needed
model = ModelRegistry.create("mobilenet_v3_large", num_classes=10)

# ResNet baseline
model = ModelRegistry.create("resnet18", num_classes=10)
```

## Modular Design Examples

### Swap Models Without Code Changes

```python
# Configuration-driven model selection
config = {
    "model_name": "mobilenet_v3_small",  # Change this to swap models
    "num_classes": 10,
    "device": "cpu"
}

model = ModelRegistry.create(config["model_name"], num_classes=config["num_classes"])
engine = InferenceEngine(model, device=config["device"])
```

### Independent Module Testing

```python
# Test model independently
model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
dummy_input = torch.randn(1, 3, 224, 224)
output = model(dummy_input)
assert output.shape == (1, 10)

# Test inference independently
engine = InferenceEngine(model)
result = engine.predict_single("test.jpg")
assert "class" in result and "confidence" in result
```

### Save and Load Models

```python
# Save model
model.save("models/classifier_v1.pt")

# Load model
loaded_model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
loaded_model = loaded_model.load("models/classifier_v1.pt")

# Or use inference engine directly
engine = InferenceEngine.from_checkpoint("models/classifier_v1.pt")
```

## Integration with Puda System

### Add to Dashboard API

```python
# In dashboard_api.py
from src.ml.inference import InferenceEngine
from src.ml.models import ModelRegistry

# Initialize at startup
try:
    classifier = ModelRegistry.load("classifier_v1")
    ml_engine = InferenceEngine(classifier, device="cpu")
    ML_AVAILABLE = True
except Exception as e:
    print(f"ML module not available: {e}")
    ML_AVAILABLE = False

@app.route('/api/ml/classify', methods=['POST'])
def classify_document():
    """Classify document and suggest routing."""
    if not ML_AVAILABLE:
        return jsonify({"error": "ML not available"}), 503
    
    image_path = request.json['image_path']
    result = ml_engine.predict_single(image_path)
    
    # Route based on confidence
    if result['confidence'] > 0.9:
        severity = 'auto'
    elif result['confidence'] > 0.7:
        severity = 'manual'
    else:
        severity = 'qc'
    
    return jsonify({
        "doc_type": result['class'],
        "confidence": result['confidence'],
        "suggested_severity": severity
    })
```

## Performance Characteristics

### MobileNetV3-Small (Default)

**Hardware: Intel i7 CPU**
- Single inference: ~5-10ms
- Batch (32): ~150-200ms
- Memory: ~10MB

**Hardware: NVIDIA GPU**
- Single inference: ~1-2ms
- Batch (32): ~15-20ms
- Memory: ~50MB (with CUDA)

### Model Size

```
mobilenet_v3_small.pt     ~10MB
mobilenet_v3_small.onnx   ~8MB (optimized)
mobilenet_v3_small.qint8  ~2.5MB (quantized)
```

## Next Steps

### Phase 1: Current (Baseline)
- ✅ CNN backbones (MobileNet, ResNet)
- ✅ Model registry
- ✅ Inference engine
- ⏳ Data module (preprocessing, augmentation)
- ⏳ Training module (trainer, callbacks)

### Phase 2: Optimization (When Needed)
- Quantization (4x size reduction)
- ONNX export (cross-platform)
- TensorRT (GPU optimization)
- Model distillation

### Phase 3: Advanced (If Required)
- Transformer backbones (ViT)
- Multi-modal models (vision + text)
- Custom hybrid architectures
- Active learning pipeline

## Development

### Add New Model

```python
from src.ml.models import ModelRegistry, BaseClassifier

@ModelRegistry.register("my_custom_model")
class MyCustomModel(BaseClassifier):
    def __init__(self, num_classes=10):
        super().__init__(num_classes)
        # Define your architecture
        self.conv1 = nn.Conv2d(3, 64, 3)
        self.fc = nn.Linear(64, num_classes)
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.fc(x)
        return x
    
    @classmethod
    def from_config(cls, config):
        return cls(num_classes=config["num_classes"])

# Use it
model = ModelRegistry.create("my_custom_model", num_classes=10)
```

### Test Model

```python
import pytest
from src.ml.models import ModelRegistry

def test_mobilenet_forward():
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
    x = torch.randn(2, 3, 224, 224)
    y = model(x)
    assert y.shape == (2, 10)

def test_inference_engine():
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
    engine = InferenceEngine(model)
    
    # Test single
    result = engine.predict_single("test_image.jpg")
    assert 0 <= result['confidence'] <= 1
    assert isinstance(result['class'], int)
```

## References

- [MobileNetV3 Paper](https://arxiv.org/abs/1905.02244)
- [PyTorch Models](https://pytorch.org/vision/stable/models.html)
- [Design Philosophy](../../../DESIGN_PHILOSOPHY.md)
