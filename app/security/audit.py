"""
Audit Logging System for LocalAgent Security Operations
CVE-2024-LOCALAGENT-003 Mitigation: Comprehensive audit logging for all key operations
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import threading
from queue import Queue, Empty
import time
import hashlib
import hmac


class AuditLogger:
    """
    Comprehensive audit logging system for security operations
    
    Features:
    - Structured logging in JSON format
    - Tamper detection with HMAC signatures
    - Async logging to prevent performance impact
    - Log rotation and retention policies
    - Configurable log levels and destinations
    - Thread-safe operations
    """
    
    def __init__(self, 
                 log_dir: str = None, 
                 log_level: str = "INFO",
                 enable_signing: bool = True,
                 max_log_size: int = 10 * 1024 * 1024,  # 10MB
                 max_backup_count: int = 5):
        
        self.log_dir = Path(log_dir or os.getenv('LOCALAGENT_AUDIT_LOG_DIR', '/tmp/localagent-audit'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.enable_signing = enable_signing
        self.max_log_size = max_log_size
        self.max_backup_count = max_backup_count
        
        # Signing key for tamper detection
        self.signing_key = os.getenv('LOCALAGENT_AUDIT_KEY', 'default_audit_key').encode()
        
        # Setup logger
        self.logger = self._setup_logger()
        
        # Async logging setup
        self.log_queue = Queue()
        self.logging_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.logging_thread.start()
        
        # Track session
        self.session_id = self._generate_session_id()
        self.start_time = datetime.utcnow()
        
        self._log_session_start()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = str(int(time.time() * 1000000))  # microseconds
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def _setup_logger(self) -> logging.Logger:
        """Setup the audit logger with proper handlers"""
        logger = logging.getLogger(f"localagent_audit_{id(self)}")
        logger.setLevel(self.log_level)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler with rotation
        log_file = self.log_dir / "audit.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_log_size,
            backupCount=self.max_backup_count
        )
        
        # JSON formatter
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _sign_entry(self, entry: Dict[str, Any]) -> str:
        """Generate HMAC signature for log entry"""
        if not self.enable_signing:
            return ""
        
        # Create canonical representation
        canonical = json.dumps(entry, sort_keys=True, separators=(',', ':'))
        
        # Generate HMAC
        signature = hmac.new(
            self.signing_key,
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _log_worker(self):
        """Background worker for async logging"""
        while True:
            try:
                entry = self.log_queue.get(timeout=1.0)
                if entry is None:  # Shutdown signal
                    break
                
                # Add signature
                signature = self._sign_entry(entry)
                if signature:
                    entry["_signature"] = signature
                
                # Log the entry
                log_message = json.dumps(entry, ensure_ascii=False)
                self.logger.info(log_message)
                
                self.log_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                # Fallback logging to prevent audit loss
                try:
                    error_entry = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "event_type": "audit_error",
                        "session_id": self.session_id,
                        "error": str(e),
                        "severity": "ERROR"
                    }
                    self.logger.error(json.dumps(error_entry))
                except:
                    pass  # Last resort - don't let audit errors crash the system
    
    def _log_session_start(self):
        """Log audit session start"""
        self.log_key_operation("audit_session_start", {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "log_dir": str(self.log_dir),
            "signing_enabled": self.enable_signing,
            "log_level": logging.getLevelName(self.log_level)
        }, severity="INFO")
    
    def log_key_operation(self, 
                         operation: str, 
                         details: Dict[str, Any],
                         severity: str = "INFO",
                         user_id: str = None,
                         source_ip: str = None):
        """
        Log a key operation with comprehensive context
        
        Args:
            operation: Type of operation (e.g., 'api_key_stored', 'key_retrieved')
            details: Operation-specific details
            severity: Log severity level
            user_id: User identifier (if available)
            source_ip: Source IP address (if available)
        """
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "key_operation",
                "operation": operation,
                "session_id": self.session_id,
                "severity": severity,
                "details": details
            }
            
            # Add optional context
            if user_id:
                entry["user_id"] = user_id
            if source_ip:
                entry["source_ip"] = source_ip
            
            # Add process context
            entry["process_info"] = {
                "pid": os.getpid(),
                "ppid": os.getppid() if hasattr(os, 'getppid') else None
            }
            
            # Queue for async logging
            self.log_queue.put(entry)
            
        except Exception as e:
            # Fallback to synchronous logging
            try:
                fallback_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event_type": "audit_fallback",
                    "operation": operation,
                    "error": str(e),
                    "severity": "ERROR"
                }
                self.logger.error(json.dumps(fallback_entry))
            except:
                pass  # Last resort
    
    def log_security_event(self,
                          event_type: str,
                          description: str,
                          details: Dict[str, Any] = None,
                          severity: str = "WARNING"):
        """
        Log security-related events
        
        Args:
            event_type: Type of security event
            description: Human-readable description
            details: Additional details
            severity: Event severity
        """
        self.log_key_operation(
            operation=f"security_event_{event_type}",
            details={
                "description": description,
                "event_details": details or {},
                "category": "security"
            },
            severity=severity
        )
    
    def log_authentication_event(self,
                                event_type: str,
                                provider: str,
                                success: bool,
                                user_id: str = None,
                                source_ip: str = None,
                                details: Dict[str, Any] = None):
        """
        Log authentication-related events
        
        Args:
            event_type: Type of auth event (login, logout, key_access, etc.)
            provider: Provider name
            success: Whether the operation succeeded
            user_id: User identifier
            source_ip: Source IP address
            details: Additional details
        """
        self.log_key_operation(
            operation=f"auth_{event_type}",
            details={
                "provider": provider,
                "success": success,
                "auth_details": details or {},
                "category": "authentication"
            },
            severity="INFO" if success else "WARNING",
            user_id=user_id,
            source_ip=source_ip
        )
    
    def get_audit_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get audit summary for the specified time period
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Summary statistics
        """
        try:
            summary = {
                "session_id": self.session_id,
                "summary_time": datetime.utcnow().isoformat(),
                "period_hours": hours,
                "events": {
                    "total": 0,
                    "by_operation": {},
                    "by_severity": {},
                    "errors": 0
                }
            }
            
            # This is a simplified implementation
            # In a real system, you'd parse the log files
            log_file = self.log_dir / "audit.log"
            
            if log_file.exists():
                cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
                
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                            
                            if entry_time.timestamp() < cutoff_time:
                                continue
                            
                            summary["events"]["total"] += 1
                            
                            # Count by operation
                            operation = entry.get("operation", "unknown")
                            summary["events"]["by_operation"][operation] = \
                                summary["events"]["by_operation"].get(operation, 0) + 1
                            
                            # Count by severity
                            severity = entry.get("severity", "UNKNOWN")
                            summary["events"]["by_severity"][severity] = \
                                summary["events"]["by_severity"].get(severity, 0) + 1
                            
                            # Count errors
                            if severity in ["ERROR", "CRITICAL"]:
                                summary["events"]["errors"] += 1
                                
                        except (json.JSONDecodeError, ValueError):
                            continue
            
            return summary
            
        except Exception as e:
            return {
                "error": str(e),
                "summary_time": datetime.utcnow().isoformat()
            }
    
    def verify_log_integrity(self, log_file: str = None) -> Dict[str, Any]:
        """
        Verify the integrity of audit logs using HMAC signatures
        
        Args:
            log_file: Specific log file to verify (default: current audit.log)
        
        Returns:
            Verification results
        """
        if not self.enable_signing:
            return {
                "verified": False,
                "reason": "Signing is disabled",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        log_path = Path(log_file) if log_file else (self.log_dir / "audit.log")
        
        try:
            results = {
                "verified": True,
                "total_entries": 0,
                "verified_entries": 0,
                "failed_entries": 0,
                "unsigned_entries": 0,
                "errors": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if not log_path.exists():
                results["verified"] = False
                results["reason"] = "Log file not found"
                return results
            
            with open(log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = json.loads(line.strip())
                        results["total_entries"] += 1
                        
                        signature = entry.pop("_signature", None)
                        
                        if signature is None:
                            results["unsigned_entries"] += 1
                            continue
                        
                        # Verify signature
                        expected_signature = self._sign_entry(entry)
                        
                        if hmac.compare_digest(signature, expected_signature):
                            results["verified_entries"] += 1
                        else:
                            results["failed_entries"] += 1
                            results["errors"].append(f"Line {line_num}: Signature mismatch")
                        
                    except json.JSONDecodeError:
                        results["errors"].append(f"Line {line_num}: Invalid JSON")
                    except Exception as e:
                        results["errors"].append(f"Line {line_num}: {str(e)}")
            
            # Overall verification
            if results["failed_entries"] > 0 or len(results["errors"]) > 0:
                results["verified"] = False
            
            return results
            
        except Exception as e:
            return {
                "verified": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def export_audit_logs(self, 
                         output_file: str,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         include_signatures: bool = True) -> bool:
        """
        Export audit logs to a file with optional filtering
        
        Args:
            output_file: Output file path
            start_time: Start time filter
            end_time: End time filter
            include_signatures: Whether to include HMAC signatures
        
        Returns:
            True if successful
        """
        try:
            log_file = self.log_dir / "audit.log"
            
            if not log_file.exists():
                return False
            
            with open(log_file, 'r') as infile, open(output_file, 'w') as outfile:
                for line in infile:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply time filtering
                        if start_time or end_time:
                            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                            
                            if start_time and entry_time < start_time:
                                continue
                            if end_time and entry_time > end_time:
                                continue
                        
                        # Remove signature if requested
                        if not include_signatures:
                            entry.pop("_signature", None)
                        
                        outfile.write(json.dumps(entry) + '\n')
                        
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            self.log_key_operation("audit_export", {
                "output_file": output_file,
                "include_signatures": include_signatures,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            })
            
            return True
            
        except Exception as e:
            self.log_key_operation("audit_export_error", {
                "output_file": output_file,
                "error": str(e)
            }, severity="ERROR")
            return False
    
    def cleanup_old_logs(self, days: int = 90) -> Dict[str, Any]:
        """
        Clean up audit logs older than specified days
        
        Args:
            days: Number of days to retain
        
        Returns:
            Cleanup results
        """
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            cleaned_files = []
            total_size_freed = 0
            
            # Find old log files
            for log_file in self.log_dir.glob("audit.log.*"):
                try:
                    stat = log_file.stat()
                    if stat.st_mtime < cutoff_time:
                        size = stat.st_size
                        log_file.unlink()
                        cleaned_files.append(str(log_file))
                        total_size_freed += size
                except Exception as e:
                    continue
            
            result = {
                "cleaned_files": len(cleaned_files),
                "files": cleaned_files,
                "bytes_freed": total_size_freed,
                "retention_days": days,
                "cleanup_time": datetime.utcnow().isoformat()
            }
            
            self.log_key_operation("audit_cleanup", result)
            
            return result
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "cleanup_time": datetime.utcnow().isoformat()
            }
            
            self.log_key_operation("audit_cleanup_error", error_result, severity="ERROR")
            return error_result
    
    def __del__(self):
        """Destructor to clean shutdown"""
        try:
            # Signal shutdown to worker thread
            self.log_queue.put(None)
            
            # Log session end
            self.log_key_operation("audit_session_end", {
                "session_id": self.session_id,
                "duration_seconds": (datetime.utcnow() - self.start_time).total_seconds()
            })
            
            # Wait for worker to finish
            if hasattr(self, 'logging_thread'):
                self.logging_thread.join(timeout=2.0)
                
        except:
            pass  # Don't raise exceptions in destructor