"""
Encryption Manager - AES-256 Encryption for Documents

Provides encryption/decryption for documents at rest with key management.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from base64 import b64encode, b64decode

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not installed. Encryption disabled.")
    print("Install via: pip install cryptography")


class EncryptionManager:
    """
    AES-256 encryption manager for document encryption at rest.
    
    Features:
    - AES-256-CBC encryption
    - Key derivation from master key
    - IV generation per file
    - Encrypted metadata storage
    """
    
    def __init__(
        self,
        key_file: str = "data/.encryption_key",
        auto_generate: bool = True
    ):
        """
        Initialize encryption manager.
        
        Args:
            key_file: Path to master key file
            auto_generate: Auto-generate key if not found
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography library required for encryption")
        
        self.key_file = Path(key_file)
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or generate master key
        if self.key_file.exists():
            self.master_key = self._load_key()
        elif auto_generate:
            self.master_key = self._generate_key()
        else:
            raise FileNotFoundError(f"Encryption key not found: {key_file}")
    
    def _generate_key(self) -> bytes:
        """
        Generate new master encryption key (256-bit).
        
        Returns:
            Master key bytes
        """
        key = os.urandom(32)  # 256 bits
        
        # Save key with restrictive permissions
        self.key_file.write_bytes(key)
        
        # Try to set restrictive permissions (Unix-like systems)
        try:
            os.chmod(self.key_file, 0o600)
        except Exception:
            pass  # Windows doesn't support Unix permissions
        
        print(f"Generated new encryption key: {self.key_file}")
        return key
    
    def _load_key(self) -> bytes:
        """
        Load master encryption key from file.
        
        Returns:
            Master key bytes
        """
        return self.key_file.read_bytes()
    
    def _derive_key(self, context: str) -> bytes:
        """
        Derive encryption key from master key with context.
        
        Args:
            context: Context string (e.g., document ID)
            
        Returns:
            Derived key bytes
        """
        # Use HKDF-like derivation (simplified)
        combined = self.master_key + context.encode()
        return hashlib.sha256(combined).digest()
    
    def encrypt_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Encrypt file with AES-256-CBC.
        
        Args:
            input_path: Path to file to encrypt
            output_path: Path for encrypted file (default: input_path.encrypted)
            document_id: Document ID for key derivation
            
        Returns:
            Dictionary with encryption metadata
        """
        if output_path is None:
            output_path = Path(str(input_path) + '.encrypted')
        
        # Use document ID or filename for key derivation
        context = document_id or input_path.name
        derived_key = self._derive_key(context)
        
        # Generate random IV (16 bytes for AES)
        iv = os.urandom(16)
        
        # Read input file
        plaintext = input_path.read_bytes()
        
        # Pad plaintext to block size (128 bits = 16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_plaintext = padder.update(plaintext) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        
        # Write encrypted file (IV + ciphertext)
        output_path.write_bytes(iv + ciphertext)
        
        # Return metadata
        return {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'document_id': context,
            'algorithm': 'AES-256-CBC',
            'iv': b64encode(iv).decode(),
            'encrypted_size': len(iv + ciphertext),
            'original_size': len(plaintext)
        }
    
    def decrypt_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        document_id: Optional[str] = None
    ) -> Path:
        """
        Decrypt file encrypted with AES-256-CBC.
        
        Args:
            input_path: Path to encrypted file
            output_path: Path for decrypted file
            document_id: Document ID for key derivation
            
        Returns:
            Path to decrypted file
        """
        if output_path is None:
            # Remove .encrypted extension or add .decrypted
            if str(input_path).endswith('.encrypted'):
                output_path = Path(str(input_path)[:-10])
            else:
                output_path = Path(str(input_path) + '.decrypted')
        
        # Use document ID or filename for key derivation
        context = document_id or input_path.name.replace('.encrypted', '')
        derived_key = self._derive_key(context)
        
        # Read encrypted file
        encrypted_data = input_path.read_bytes()
        
        # Extract IV (first 16 bytes)
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        # Write decrypted file
        output_path.write_bytes(plaintext)
        
        return output_path
    
    def encrypt_data(self, data: bytes, context: str = "default") -> bytes:
        """
        Encrypt raw data.
        
        Args:
            data: Data to encrypt
            context: Context for key derivation
            
        Returns:
            Encrypted data (IV + ciphertext)
        """
        derived_key = self._derive_key(context)
        iv = os.urandom(16)
        
        # Pad data
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return iv + ciphertext
    
    def decrypt_data(self, encrypted_data: bytes, context: str = "default") -> bytes:
        """
        Decrypt raw data.
        
        Args:
            encrypted_data: Encrypted data (IV + ciphertext)
            context: Context for key derivation
            
        Returns:
            Decrypted data
        """
        derived_key = self._derive_key(context)
        
        # Extract IV and ciphertext
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(derived_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    def encrypt_text(self, text: str, context: str = "default") -> str:
        """
        Encrypt text string (returns base64).
        
        Args:
            text: Text to encrypt
            context: Context for key derivation
            
        Returns:
            Base64-encoded encrypted text
        """
        encrypted = self.encrypt_data(text.encode(), context)
        return b64encode(encrypted).decode()
    
    def decrypt_text(self, encrypted_text: str, context: str = "default") -> str:
        """
        Decrypt base64-encoded text.
        
        Args:
            encrypted_text: Base64-encoded encrypted text
            context: Context for key derivation
            
        Returns:
            Decrypted text
        """
        encrypted = b64decode(encrypted_text.encode())
        decrypted = self.decrypt_data(encrypted, context)
        return decrypted.decode()
    
    def rotate_key(self, new_key_file: Optional[str] = None):
        """
        Rotate encryption key.
        
        WARNING: This will invalidate all existing encrypted data
        unless you re-encrypt it with the new key.
        
        Args:
            new_key_file: Path for new key file
        """
        if new_key_file:
            old_key_file = self.key_file
            self.key_file = Path(new_key_file)
        
        # Generate new key
        self.master_key = self._generate_key()
        
        print(f"Key rotated. Old encrypted data will need re-encryption.")
    
    @staticmethod
    def is_encrypted(file_path: Path) -> bool:
        """
        Check if file appears to be encrypted.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file likely encrypted
        """
        # Simple heuristic: encrypted files have high entropy
        # and no recognizable file headers
        if not file_path.exists():
            return False
        
        # Check extension
        if str(file_path).endswith('.encrypted'):
            return True
        
        # Check entropy (simplified check)
        try:
            data = file_path.read_bytes()[:1024]  # First 1KB
            if len(data) == 0:
                return False
            
            # Calculate byte frequency
            freq = [data.count(i) for i in range(256)]
            total = sum(freq)
            entropy = -sum((f/total) * (f/total).bit_length() for f in freq if f > 0)
            
            # High entropy suggests encryption (>7.5 bits per byte)
            return entropy > 7.5
        except Exception:
            return False
