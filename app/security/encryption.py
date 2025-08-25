"""
Encryption Service for LocalAgent
CVE-2024-LOCALAGENT-002 Mitigation: Advanced AES-256-GCM encryption with secure key derivation
"""

import os
import base64
import secrets
import logging
from typing import Optional, Dict, Any, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import json

from .audit import AuditLogger


class EncryptionService:
    """
    Advanced encryption service using AES-256-GCM and Fernet
    
    Features:
    - AES-256-GCM for authenticated encryption
    - PBKDF2 key derivation with configurable iterations
    - Key rotation capabilities
    - Secure random nonce generation
    - Comprehensive audit logging
    - Memory protection for keys
    """
    
    def __init__(self, master_password: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger()
        
        # Use environment variable or generate secure password
        self.master_password = (
            master_password or 
            os.getenv('LOCALAGENT_MASTER_KEY') or 
            self._generate_master_password()
        ).encode()
        
        # Key derivation parameters
        self.kdf_iterations = 100000  # NIST recommended minimum
        self.salt_size = 32
        self.nonce_size = 12  # For AES-GCM
        
        # Key rotation tracking
        self.key_version = 1
        self.last_rotation = datetime.utcnow()
        
        self.audit_logger.log_key_operation("encryption_service_initialized", {
            "kdf_iterations": self.kdf_iterations,
            "key_version": self.key_version
        })
    
    def _generate_master_password(self) -> str:
        """Generate a secure master password if none provided"""
        password = base64.b64encode(secrets.token_bytes(32)).decode()
        self.logger.warning("Generated temporary master password - consider setting LOCALAGENT_MASTER_KEY")
        return password
    
    def _derive_key(self, salt: bytes, purpose: str = "default") -> bytes:
        """
        Derive encryption key using PBKDF2
        
        Args:
            salt: Salt for key derivation
            purpose: Purpose identifier for key derivation
        
        Returns:
            32-byte derived key
        """
        try:
            # Add purpose to password for key separation
            password_with_purpose = self.master_password + purpose.encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.kdf_iterations,
            )
            
            return kdf.derive(password_with_purpose)
            
        except Exception as e:
            self.logger.error(f"Key derivation failed: {e}")
            self.audit_logger.log_key_operation("key_derivation_error", {
                "purpose": purpose,
                "error": str(e)
            })
            raise
    
    def encrypt_aes_gcm(self, data: Union[str, bytes], purpose: str = "default") -> Dict[str, str]:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Data to encrypt (string or bytes)
            purpose: Purpose identifier for key derivation
        
        Returns:
            Dictionary with encrypted data, salt, nonce, and metadata
        """
        try:
            # Convert to bytes if string
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Generate random salt and nonce
            salt = secrets.token_bytes(self.salt_size)
            nonce = secrets.token_bytes(self.nonce_size)
            
            # Derive key
            key = self._derive_key(salt, purpose)
            
            # Encrypt with AES-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            
            # Prepare result
            result = {
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "salt": base64.b64encode(salt).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "algorithm": "AES-256-GCM",
                "kdf": "PBKDF2",
                "iterations": self.kdf_iterations,
                "key_version": self.key_version,
                "encrypted_at": datetime.utcnow().isoformat(),
                "purpose": purpose
            }
            
            # Audit log (without sensitive data)
            self.audit_logger.log_key_operation("data_encrypted_aes_gcm", {
                "purpose": purpose,
                "data_length": len(data),
                "algorithm": "AES-256-GCM",
                "key_version": self.key_version
            })
            
            # Clear sensitive data from memory
            key = b"0" * len(key)
            data = b"0" * len(data)
            del key, data
            
            return result
            
        except Exception as e:
            self.logger.error(f"AES-GCM encryption failed: {e}")
            self.audit_logger.log_key_operation("encryption_error_aes_gcm", {
                "purpose": purpose,
                "error": str(e)
            })
            raise
    
    def decrypt_aes_gcm(self, encrypted_data: Dict[str, str]) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Dictionary with encrypted data and metadata
        
        Returns:
            Decrypted bytes
        """
        try:
            # Validate required fields
            required_fields = ["ciphertext", "salt", "nonce", "purpose"]
            for field in required_fields:
                if field not in encrypted_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Decode components
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            salt = base64.b64decode(encrypted_data["salt"])
            nonce = base64.b64decode(encrypted_data["nonce"])
            purpose = encrypted_data["purpose"]
            
            # Check key version compatibility
            key_version = encrypted_data.get("key_version", 1)
            if key_version > self.key_version:
                raise ValueError(f"Data encrypted with newer key version: {key_version}")
            
            # Derive key
            key = self._derive_key(salt, purpose)
            
            # Decrypt
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Audit log
            self.audit_logger.log_key_operation("data_decrypted_aes_gcm", {
                "purpose": purpose,
                "data_length": len(plaintext),
                "key_version": key_version
            })
            
            # Clear key from memory
            key = b"0" * len(key)
            del key
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"AES-GCM decryption failed: {e}")
            self.audit_logger.log_key_operation("decryption_error_aes_gcm", {
                "purpose": encrypted_data.get("purpose", "unknown"),
                "error": str(e)
            })
            raise
    
    def encrypt_fernet(self, data: Union[str, bytes], purpose: str = "default") -> Dict[str, str]:
        """
        Encrypt data using Fernet (AES-128 in CBC mode with HMAC)
        
        Args:
            data: Data to encrypt
            purpose: Purpose identifier for key derivation
        
        Returns:
            Dictionary with encrypted data and metadata
        """
        try:
            # Convert to bytes if string
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Generate salt
            salt = secrets.token_bytes(self.salt_size)
            
            # Derive key and create Fernet instance
            derived_key = self._derive_key(salt, purpose)
            fernet_key = base64.urlsafe_b64encode(derived_key)
            fernet = Fernet(fernet_key)
            
            # Encrypt
            ciphertext = fernet.encrypt(data)
            
            result = {
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "salt": base64.b64encode(salt).decode(),
                "algorithm": "Fernet",
                "kdf": "PBKDF2",
                "iterations": self.kdf_iterations,
                "key_version": self.key_version,
                "encrypted_at": datetime.utcnow().isoformat(),
                "purpose": purpose
            }
            
            self.audit_logger.log_key_operation("data_encrypted_fernet", {
                "purpose": purpose,
                "data_length": len(data),
                "key_version": self.key_version
            })
            
            # Clear sensitive data
            derived_key = b"0" * len(derived_key)
            fernet_key = b"0" * len(fernet_key)
            data = b"0" * len(data)
            del derived_key, fernet_key, data
            
            return result
            
        except Exception as e:
            self.logger.error(f"Fernet encryption failed: {e}")
            self.audit_logger.log_key_operation("encryption_error_fernet", {
                "purpose": purpose,
                "error": str(e)
            })
            raise
    
    def decrypt_fernet(self, encrypted_data: Dict[str, str]) -> bytes:
        """
        Decrypt Fernet-encrypted data
        
        Args:
            encrypted_data: Dictionary with encrypted data and metadata
        
        Returns:
            Decrypted bytes
        """
        try:
            # Validate required fields
            required_fields = ["ciphertext", "salt", "purpose"]
            for field in required_fields:
                if field not in encrypted_data:
                    raise ValueError(f"Missing required field: {field}")
            
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            salt = base64.b64decode(encrypted_data["salt"])
            purpose = encrypted_data["purpose"]
            
            # Derive key and create Fernet instance
            derived_key = self._derive_key(salt, purpose)
            fernet_key = base64.urlsafe_b64encode(derived_key)
            fernet = Fernet(fernet_key)
            
            # Decrypt
            plaintext = fernet.decrypt(ciphertext)
            
            self.audit_logger.log_key_operation("data_decrypted_fernet", {
                "purpose": purpose,
                "data_length": len(plaintext)
            })
            
            # Clear sensitive data
            derived_key = b"0" * len(derived_key)
            fernet_key = b"0" * len(fernet_key)
            del derived_key, fernet_key
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"Fernet decryption failed: {e}")
            self.audit_logger.log_key_operation("decryption_error_fernet", {
                "purpose": encrypted_data.get("purpose", "unknown"),
                "error": str(e)
            })
            raise
    
    def rotate_key(self) -> bool:
        """
        Rotate the master key version
        
        Returns:
            True if successful
        """
        try:
            old_version = self.key_version
            self.key_version += 1
            self.last_rotation = datetime.utcnow()
            
            self.audit_logger.log_key_operation("key_rotated", {
                "old_version": old_version,
                "new_version": self.key_version,
                "rotation_time": self.last_rotation.isoformat()
            })
            
            self.logger.info(f"Key rotated from version {old_version} to {self.key_version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Key rotation failed: {e}")
            self.audit_logger.log_key_operation("key_rotation_error", {"error": str(e)})
            return False
    
    def should_rotate_key(self, max_age_days: int = 90) -> bool:
        """
        Check if key should be rotated based on age
        
        Args:
            max_age_days: Maximum key age in days
        
        Returns:
            True if key should be rotated
        """
        age = datetime.utcnow() - self.last_rotation
        return age.days >= max_age_days
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """
        Get information about the encryption service
        
        Returns:
            Dictionary with encryption service information
        """
        return {
            "key_version": self.key_version,
            "last_rotation": self.last_rotation.isoformat(),
            "kdf_iterations": self.kdf_iterations,
            "supported_algorithms": ["AES-256-GCM", "Fernet"],
            "key_age_days": (datetime.utcnow() - self.last_rotation).days,
            "should_rotate": self.should_rotate_key()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check encryption service health
        
        Returns:
            Health status dictionary
        """
        try:
            health = {
                "healthy": True,
                "aes_gcm_functional": False,
                "fernet_functional": False,
                "key_version": self.key_version,
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Test AES-GCM
            try:
                test_data = "health_check_aes_gcm"
                encrypted = self.encrypt_aes_gcm(test_data, "health_check")
                decrypted = self.decrypt_aes_gcm(encrypted).decode()
                health["aes_gcm_functional"] = (decrypted == test_data)
            except Exception as e:
                health["aes_gcm_error"] = str(e)
                health["healthy"] = False
            
            # Test Fernet
            try:
                test_data = "health_check_fernet"
                encrypted = self.encrypt_fernet(test_data, "health_check")
                decrypted = self.decrypt_fernet(encrypted).decode()
                health["fernet_functional"] = (decrypted == test_data)
            except Exception as e:
                health["fernet_error"] = str(e)
                health["healthy"] = False
            
            return health
            
        except Exception as e:
            self.logger.error(f"Encryption health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    def __del__(self):
        """Destructor to clear sensitive data"""
        try:
            if hasattr(self, 'master_password'):
                self.master_password = b"0" * len(self.master_password)
        except:
            pass