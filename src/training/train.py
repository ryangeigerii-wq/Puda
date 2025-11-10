"""
Training Script for PudaModel

Multi-task training for document intelligence:
- Classification: Document type (invoice, receipt, contract, etc.)
- Extraction: Named entity recognition (dates, amounts, names, etc.)
- Multi-task learning with weighted loss

Usage:
    # Classification only
    python -m src.training.train --data data/train.json --epochs 3 --task classify
    
    # Extraction only
    python -m src.training.train --data data/train.json --epochs 3 --task extract
    
    # Multi-task (both)
    python -m src.training.train --data data/train.json --epochs 5 --task both
    
    # With validation
    python -m src.training.train --data data/train.json --val-data data/val.json --epochs 10

Data format:
    [
        {
            "text": "Invoice from ACME Corp dated 2025-11-10 for $1,500.00",
            "doc_type": "invoice",  // for classification
            "entities": [  // for extraction
                {"text": "ACME Corp", "label": "ORG", "start": 13, "end": 22},
                {"text": "2025-11-10", "label": "DATE", "start": 29, "end": 39},
                {"text": "$1,500.00", "label": "AMOUNT", "start": 44, "end": 53}
            ]
        },
        ...
    ]
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import sys

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from tqdm import tqdm

from src.ml.models.puda_model import PudaModel, load_tokenizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentDataset(Dataset):
    """Dataset for document training."""
    
    def __init__(
        self,
        data: List[Dict[str, Any]],
        tokenizer,
        max_length: int = 512,
        task: str = "both"
    ):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.task = task
        
        # NER tag mapping (BIO format)
        self.ner_tag_map = {tag: idx for idx, tag in enumerate(PudaModel.NER_TAGS)}
        self.doc_type_map = {dtype: idx for idx, dtype in enumerate(PudaModel.DOC_TYPES)}
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item["text"]
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
            return_offsets_mapping=True
        )
        
        input_ids = encoding["input_ids"].squeeze(0)
        attention_mask = encoding["attention_mask"].squeeze(0)
        offset_mapping = encoding["offset_mapping"].squeeze(0)
        
        # Classification label
        doc_type = item.get("doc_type", "other")
        class_label = self.doc_type_map.get(doc_type, self.doc_type_map["other"])
        
        # NER labels (BIO tagging)
        ner_labels = self._create_ner_labels(
            item.get("entities", []),
            offset_mapping,
            len(input_ids)
        )
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "class_label": torch.tensor(class_label, dtype=torch.long),
            "ner_labels": torch.tensor(ner_labels, dtype=torch.long)
        }
    
    def _create_ner_labels(
        self,
        entities: List[Dict],
        offset_mapping: torch.Tensor,
        seq_length: int
    ) -> List[int]:
        """Create BIO tags for tokens."""
        labels = [self.ner_tag_map["O"]] * seq_length
        
        for entity in entities:
            start_char = entity["start"]
            end_char = entity["end"]
            label = entity["label"]
            
            # Find tokens that overlap with entity
            entity_tokens = []
            for token_idx, (token_start, token_end) in enumerate(offset_mapping):
                if token_start == token_end == 0:  # Special token
                    continue
                
                # Check overlap
                if token_start < end_char and token_end > start_char:
                    entity_tokens.append(token_idx)
            
            # Apply BIO tags
            for i, token_idx in enumerate(entity_tokens):
                prefix = "B" if i == 0 else "I"
                tag = f"{prefix}-{label}"
                if tag in self.ner_tag_map:
                    labels[token_idx] = self.ner_tag_map[tag]
        
        return labels


def load_data(data_path: str) -> List[Dict[str, Any]]:
    """Load training data from JSON file."""
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data)} examples from {data_path}")
    return data


def train_epoch(
    model: PudaModel,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    device: torch.device,
    task: str = "both",
    class_weight: float = 1.0,
    ner_weight: float = 1.0
) -> Dict[str, float]:
    """Train for one epoch."""
    model.train()
    
    total_loss = 0
    class_loss_total = 0
    ner_loss_total = 0
    
    class_criterion = nn.CrossEntropyLoss()
    ner_criterion = nn.CrossEntropyLoss(ignore_index=-100)
    
    progress = tqdm(dataloader, desc="Training")
    
    for batch in progress:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        class_labels = batch["class_label"].to(device)
        ner_labels = batch["ner_labels"].to(device)
        
        # Forward pass
        outputs = model(input_ids, attention_mask)
        
        # Compute losses
        loss = 0
        
        if task in ["classify", "both"]:
            class_logits = outputs["classification_logits"]
            class_loss = class_criterion(class_logits, class_labels)
            loss += class_weight * class_loss
            class_loss_total += class_loss.item()
        
        if task in ["extract", "both"]:
            ner_logits = outputs["extraction_logits"]
            ner_logits_flat = ner_logits.view(-1, ner_logits.size(-1))
            ner_labels_flat = ner_labels.view(-1)
            ner_loss = ner_criterion(ner_logits_flat, ner_labels_flat)
            loss += ner_weight * ner_loss
            ner_loss_total += ner_loss.item()
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        
        total_loss += loss.item()
        
        # Update progress bar
        progress.set_postfix({
            "loss": f"{loss.item():.4f}",
            "lr": f"{scheduler.get_last_lr()[0]:.2e}"
        })
    
    num_batches = len(dataloader)
    return {
        "total_loss": total_loss / num_batches,
        "class_loss": class_loss_total / num_batches if task in ["classify", "both"] else 0,
        "ner_loss": ner_loss_total / num_batches if task in ["extract", "both"] else 0
    }


def evaluate(
    model: PudaModel,
    dataloader: DataLoader,
    device: torch.device,
    task: str = "both"
) -> Dict[str, float]:
    """Evaluate model."""
    model.eval()
    
    class_correct = 0
    class_total = 0
    ner_correct = 0
    ner_total = 0
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Evaluating"):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            class_labels = batch["class_label"].to(device)
            ner_labels = batch["ner_labels"].to(device)
            
            outputs = model(input_ids, attention_mask)
            
            # Classification accuracy
            if task in ["classify", "both"]:
                class_preds = outputs["classification_logits"].argmax(dim=-1)
                class_correct += (class_preds == class_labels).sum().item()
                class_total += class_labels.size(0)
            
            # NER accuracy (token-level)
            if task in ["extract", "both"]:
                ner_preds = outputs["extraction_logits"].argmax(dim=-1)
                mask = (ner_labels != -100) & (attention_mask == 1)
                ner_correct += ((ner_preds == ner_labels) & mask).sum().item()
                ner_total += mask.sum().item()
    
    results = {}
    if task in ["classify", "both"]:
        results["class_accuracy"] = class_correct / class_total if class_total > 0 else 0
    if task in ["extract", "both"]:
        results["ner_accuracy"] = ner_correct / ner_total if ner_total > 0 else 0
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Train PudaModel")
    parser.add_argument("--data", type=str, required=True, help="Training data JSON file")
    parser.add_argument("--val-data", type=str, help="Validation data JSON file")
    parser.add_argument("--output", type=str, default="models/puda_trained.pt", help="Output model path")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--task", type=str, default="both", choices=["classify", "extract", "both"], help="Training task")
    parser.add_argument("--class-weight", type=float, default=1.0, help="Classification loss weight")
    parser.add_argument("--ner-weight", type=float, default=1.0, help="NER loss weight")
    parser.add_argument("--max-length", type=int, default=512, help="Max sequence length")
    parser.add_argument("--warmup-steps", type=int, default=100, help="Warmup steps")
    parser.add_argument("--use-bilstm", action="store_true", help="Use BiLSTM layer")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda)")
    
    args = parser.parse_args()
    
    # Setup
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    # Load data
    train_data = load_data(args.data)
    
    # Load tokenizer and model
    logger.info("Loading model and tokenizer...")
    tokenizer = load_tokenizer()
    model = PudaModel(
        model_name="distilbert-base-multilingual-cased",
        use_bilstm=args.use_bilstm,
        dropout=0.1,
        freeze_backbone=False
    )
    model = model.to(device)
    logger.info(f"Model parameters: {model.count_parameters():,}")
    
    # Create datasets
    train_dataset = DocumentDataset(train_data, tokenizer, args.max_length, args.task)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    
    val_loader = None
    if args.val_data:
        val_data = load_data(args.val_data)
        val_dataset = DocumentDataset(val_data, tokenizer, args.max_length, args.task)
        val_loader = DataLoader(val_dataset, batch_size=args.batch_size)
    
    # Setup optimizer and scheduler
    optimizer = AdamW(model.parameters(), lr=args.lr)
    total_steps = len(train_loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=args.warmup_steps,
        num_training_steps=total_steps
    )
    
    # Training loop
    logger.info(f"Training for {args.epochs} epochs...")
    best_val_metric = 0
    
    for epoch in range(args.epochs):
        logger.info(f"\nEpoch {epoch + 1}/{args.epochs}")
        
        # Train
        train_metrics = train_epoch(
            model, train_loader, optimizer, scheduler, device,
            args.task, args.class_weight, args.ner_weight
        )
        
        logger.info(f"Train loss: {train_metrics['total_loss']:.4f}")
        if args.task in ["classify", "both"]:
            logger.info(f"  Class loss: {train_metrics['class_loss']:.4f}")
        if args.task in ["extract", "both"]:
            logger.info(f"  NER loss: {train_metrics['ner_loss']:.4f}")
        
        # Evaluate
        if val_loader:
            val_metrics = evaluate(model, val_loader, device, args.task)
            logger.info("Validation metrics:")
            for metric, value in val_metrics.items():
                logger.info(f"  {metric}: {value:.4f}")
            
            # Save best model
            val_metric = val_metrics.get("class_accuracy", 0) + val_metrics.get("ner_accuracy", 0)
            if val_metric > best_val_metric:
                best_val_metric = val_metric
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save({
                    "model_state_dict": model.state_dict(),
                    "config": model.get_config(),
                    "epoch": epoch,
                    "metrics": val_metrics
                }, output_path)
                logger.info(f"✓ Saved best model to {output_path}")
    
    # Save final model
    if not val_loader:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": model.state_dict(),
            "config": model.get_config(),
            "epoch": args.epochs
        }, output_path)
        logger.info(f"✓ Saved final model to {output_path}")
    
    logger.info("\n✅ Training complete!")


if __name__ == "__main__":
    main()
