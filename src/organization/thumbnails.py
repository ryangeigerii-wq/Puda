"""
Thumbnail Generator - Create preview images and cache

Automatically generates thumbnails in multiple sizes for fast preview loading.
Supports batch processing and automation for archived documents.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

try:
    from PIL import Image
except ImportError:
    Image = None


class ThumbnailSizes:
    """Standard thumbnail sizes."""
    SMALL = (150, 200)      # Small thumbnail for lists
    MEDIUM = (300, 400)     # Medium thumbnail for cards
    LARGE = (600, 800)      # Large thumbnail for preview
    ICON = (64, 64)         # Icon size for quick view


class ThumbnailGenerator:
    """
    Generate thumbnails and preview cache for documents.
    
    Features:
    - Multiple thumbnail sizes (icon, small, medium, large)
    - Batch processing
    - Preview cache management
    - Auto-generation on archive
    - Maintains aspect ratio
    """
    
    def __init__(
        self,
        archive_base_dir: str = "data/archive",
        cache_dir: Optional[str] = None
    ):
        """
        Initialize thumbnail generator.
        
        Args:
            archive_base_dir: Base directory of archived documents
            cache_dir: Cache directory (defaults to archive/.thumbnails)
        """
        self.archive_base_dir = Path(archive_base_dir)
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self.archive_base_dir / ".thumbnails"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Check dependencies
        if not Image:
            raise ImportError("PIL required: pip install Pillow")
    
    def generate_thumbnail(
        self,
        image_path: Path,
        size: Tuple[int, int],
        output_path: Path,
        quality: int = 85
    ) -> bool:
        """
        Generate a single thumbnail.
        
        Args:
            image_path: Source image path
            size: Target size (width, height)
            output_path: Output thumbnail path
            quality: JPEG quality (1-100)
            
        Returns:
            True if successful
        """
        try:
            # Open and convert image
            img = Image.open(image_path)
            
            # Convert to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Calculate dimensions maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save thumbnail
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            return True
        
        except Exception as e:
            print(f"Error generating thumbnail for {image_path}: {e}")
            return False
    
    def generate_all_sizes(
        self,
        image_path: Path,
        page_id: str,
        sizes: Optional[Dict[str, Tuple[int, int]]] = None
    ) -> Dict[str, Path]:
        """
        Generate thumbnails in all standard sizes.
        
        Args:
            image_path: Source image path
            page_id: Page identifier
            sizes: Custom sizes dict (name -> (width, height))
            
        Returns:
            Dict mapping size names to generated thumbnail paths
        """
        if sizes is None:
            sizes = {
                'icon': ThumbnailSizes.ICON,
                'small': ThumbnailSizes.SMALL,
                'medium': ThumbnailSizes.MEDIUM,
                'large': ThumbnailSizes.LARGE
            }
        
        thumbnails = {}
        
        for size_name, dimensions in sizes.items():
            output_path = self.cache_dir / f"{page_id}_{size_name}.jpg"
            
            if self.generate_thumbnail(image_path, dimensions, output_path):
                thumbnails[size_name] = output_path
        
        return thumbnails
    
    def generate_batch_thumbnails(
        self,
        owner: str,
        year: str,
        doc_type: str,
        batch_id: str,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate thumbnails for all pages in a batch.
        
        Args:
            owner: Document owner
            year: Year
            doc_type: Document type
            batch_id: Batch ID
            force_regenerate: Regenerate existing thumbnails
            
        Returns:
            Dictionary with generation statistics
        """
        batch_folder = self.archive_base_dir / owner / year / doc_type / batch_id
        
        if not batch_folder.exists():
            raise ValueError(f"Batch folder not found: {batch_folder}")
        
        # Find all images
        image_files = list(batch_folder.glob("*.png")) + list(batch_folder.glob("*.jpg"))
        
        stats = {
            'total_images': len(image_files),
            'generated': 0,
            'skipped': 0,
            'failed': 0,
            'thumbnails': {}
        }
        
        for image_file in image_files:
            page_id = image_file.stem
            
            # Skip if thumbnails exist and not force regenerating
            if not force_regenerate:
                existing = self.cache_dir / f"{page_id}_small.jpg"
                if existing.exists():
                    stats['skipped'] += 1
                    continue
            
            # Generate all sizes
            try:
                thumbnails = self.generate_all_sizes(image_file, page_id)
                
                if thumbnails:
                    stats['generated'] += 1
                    stats['thumbnails'][page_id] = {
                        size: str(path) for size, path in thumbnails.items()
                    }
                else:
                    stats['failed'] += 1
            
            except Exception as e:
                print(f"Error processing {page_id}: {e}")
                stats['failed'] += 1
        
        # Write thumbnail manifest
        self._write_thumbnail_manifest(owner, year, doc_type, batch_id, stats['thumbnails'])
        
        return stats
    
    def _write_thumbnail_manifest(
        self,
        owner: str,
        year: str,
        doc_type: str,
        batch_id: str,
        thumbnails: Dict[str, Dict[str, str]]
    ):
        """Write thumbnail manifest for batch."""
        manifest = {
            'batch': {
                'owner': owner,
                'year': year,
                'doc_type': doc_type,
                'batch_id': batch_id
            },
            'thumbnails': thumbnails,
            'sizes': {
                'icon': list(ThumbnailSizes.ICON),
                'small': list(ThumbnailSizes.SMALL),
                'medium': list(ThumbnailSizes.MEDIUM),
                'large': list(ThumbnailSizes.LARGE)
            }
        }
        
        manifest_path = self.cache_dir / f"{owner}_{year}_{doc_type}_{batch_id}_manifest.json"
        
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write thumbnail manifest: {e}")
    
    def get_thumbnail(
        self,
        page_id: str,
        size: str = 'medium'
    ) -> Optional[Path]:
        """
        Get thumbnail path for a page.
        
        Args:
            page_id: Page identifier
            size: Thumbnail size (icon/small/medium/large)
            
        Returns:
            Path to thumbnail or None if not found
        """
        thumbnail_path = self.cache_dir / f"{page_id}_{size}.jpg"
        
        if thumbnail_path.exists():
            return thumbnail_path
        
        return None
    
    def clear_cache(
        self,
        owner: Optional[str] = None,
        year: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> int:
        """
        Clear thumbnail cache.
        
        Args:
            owner: Filter by owner (None = all)
            year: Filter by year (None = all)
            doc_type: Filter by doc type (None = all)
            
        Returns:
            Number of thumbnails deleted
        """
        if not owner and not year and not doc_type:
            # Clear entire cache
            count = 0
            for file in self.cache_dir.glob("*.jpg"):
                file.unlink()
                count += 1
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
                count += 1
            return count
        
        # Clear specific batches
        pattern = f"{owner or '*'}_{year or '*'}_{doc_type or '*'}_*"
        count = 0
        
        for manifest in self.cache_dir.glob(f"{pattern}_manifest.json"):
            # Load manifest to find thumbnails
            try:
                with open(manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Delete thumbnails
                for page_thumbnails in data['thumbnails'].values():
                    for thumbnail_path in page_thumbnails.values():
                        path = Path(thumbnail_path)
                        if path.exists():
                            path.unlink()
                            count += 1
                
                # Delete manifest
                manifest.unlink()
                count += 1
            
            except Exception as e:
                print(f"Error clearing cache: {e}")
        
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        thumbnails = list(self.cache_dir.glob("*.jpg"))
        manifests = list(self.cache_dir.glob("*.json"))
        
        total_size = sum(f.stat().st_size for f in thumbnails)
        
        return {
            'thumbnail_count': len(thumbnails),
            'manifest_count': len(manifests),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }


class ThumbnailAutomation:
    """
    Automated thumbnail generation for archived batches.
    
    Monitors archive directory and generates thumbnails automatically.
    """
    
    def __init__(
        self,
        generator: Optional[ThumbnailGenerator] = None,
        auto_generate: bool = True
    ):
        """
        Initialize thumbnail automation.
        
        Args:
            generator: ThumbnailGenerator instance
            auto_generate: Automatically generate thumbnails
        """
        self.generator = generator or ThumbnailGenerator()
        self.auto_generate = auto_generate
        
        # Track processed batches
        self.processed_batches: set = set()
        self._load_processed_batches()
    
    def _load_processed_batches(self):
        """Load list of already-processed batches."""
        state_file = Path("data/organization/.thumbnail_batches.json")
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    self.processed_batches = set(json.load(f))
            except:
                pass
    
    def _save_processed_batches(self):
        """Save list of processed batches."""
        state_file = Path("data/organization/.thumbnail_batches.json")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_batches), f)
        except Exception as e:
            print(f"Warning: Failed to save processed batches: {e}")
    
    def process_batch(
        self,
        owner: str,
        year: str,
        doc_type: str,
        batch_id: str,
        force: bool = False
    ) -> bool:
        """
        Process a single batch for thumbnail generation.
        
        Returns:
            True if thumbnails generated
        """
        batch_key = f"{owner}/{year}/{doc_type}/{batch_id}"
        
        # Skip if already processed
        if batch_key in self.processed_batches and not force:
            return False
        
        try:
            # Generate thumbnails
            stats = self.generator.generate_batch_thumbnails(
                owner, year, doc_type, batch_id,
                force_regenerate=force
            )
            
            if stats['generated'] > 0 or stats['skipped'] > 0:
                # Mark as processed
                self.processed_batches.add(batch_key)
                self._save_processed_batches()
                
                print(f"✓ Thumbnails: {batch_key}")
                print(f"  Generated: {stats['generated']}, Skipped: {stats['skipped']}, Failed: {stats['failed']}")
                return True
        
        except Exception as e:
            print(f"Error processing batch {batch_key}: {e}")
            return False
        
        return False
    
    def scan_and_generate(self) -> int:
        """
        Scan archive and generate thumbnails for all batches.
        
        Returns:
            Number of batches processed
        """
        if not self.auto_generate:
            return 0
        
        # Find all batch folders
        processed_count = 0
        
        for owner_dir in self.generator.archive_base_dir.glob("*"):
            if not owner_dir.is_dir() or owner_dir.name.startswith("."):
                continue
            
            for year_dir in owner_dir.glob("*"):
                if not year_dir.is_dir():
                    continue
                
                for doc_type_dir in year_dir.glob("*"):
                    if not doc_type_dir.is_dir():
                        continue
                    
                    for batch_dir in doc_type_dir.glob("*"):
                        if not batch_dir.is_dir():
                            continue
                        
                        # Extract components
                        owner = owner_dir.name
                        year = year_dir.name
                        doc_type = doc_type_dir.name
                        batch_id = batch_dir.name
                        
                        if self.process_batch(owner, year, doc_type, batch_id):
                            processed_count += 1
        
        return processed_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get automation statistics."""
        cache_stats = self.generator.get_cache_stats()
        
        return {
            'total_processed': len(self.processed_batches),
            'auto_generate_enabled': self.auto_generate,
            'cache_stats': cache_stats
        }
