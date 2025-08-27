"""
Comprehensive Input Validation Framework
CVE-2024-LOCALAGENT-004 Mitigation: Comprehensive input validation and sanitization
"""

import re
import html
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import urlparse
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

# Import existing security components for audit logging
try:
    import sys
    sys.path.append('/home/marku/Documents/programming/LocalProgramming')
    from app.security.audit import AuditLogger
except ImportError:
    AuditLogger = None


class ValidationLevel(Enum):
    """Validation strictness levels"""
    STRICT = "strict"
    NORMAL = "normal"
    PERMISSIVE = "permissive"


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


@dataclass
class ValidationRule:
    """Validation rule definition"""
    name: str
    validator: Callable[[Any], bool]
    message: str
    required: bool = True
    sanitizer: Optional[Callable[[Any], Any]] = None


class InputValidator:
    """
    Comprehensive input validation and sanitization framework
    
    Features:
    - Multiple validation levels (strict, normal, permissive)
    - Built-in validators for common data types
    - Custom validation rules
    - Input sanitization
    - Security-focused validation (SQL injection, XSS, path traversal)
    - Comprehensive audit logging
    - Configuration via JSON/YAML
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger() if AuditLogger else None
        
        # Built-in validation rules
        self.built_in_rules = {
            'email': ValidationRule(
                name='email',
                validator=self._validate_email,
                message='Invalid email format',
                sanitizer=self._sanitize_email
            ),
            'url': ValidationRule(
                name='url',
                validator=self._validate_url,
                message='Invalid URL format',
                sanitizer=self._sanitize_url
            ),
            'api_key': ValidationRule(
                name='api_key',
                validator=self._validate_api_key,
                message='Invalid API key format',
                sanitizer=self._sanitize_api_key
            ),
            'provider_name': ValidationRule(
                name='provider_name',
                validator=self._validate_provider_name,
                message='Invalid provider name',
                sanitizer=self._sanitize_provider_name
            ),
            'file_path': ValidationRule(
                name='file_path',
                validator=self._validate_file_path,
                message='Invalid or unsafe file path',
                sanitizer=self._sanitize_file_path
            ),
            'json_data': ValidationRule(
                name='json_data',
                validator=self._validate_json,
                message='Invalid JSON format',
                sanitizer=self._sanitize_json
            ),
            'command': ValidationRule(
                name='command',
                validator=self._validate_command,
                message='Unsafe command detected',
                sanitizer=self._sanitize_command
            ),
            'sql_safe': ValidationRule(
                name='sql_safe',
                validator=self._validate_sql_safe,
                message='Potential SQL injection detected',
                sanitizer=self._sanitize_sql
            ),
            'xss_safe': ValidationRule(
                name='xss_safe',
                validator=self._validate_xss_safe,
                message='Potential XSS attack detected',
                sanitizer=self._sanitize_html
            )
        }
        
        # Custom rules registry
        self.custom_rules: Dict[str, ValidationRule] = {}
        
        # Validation statistics
        self.stats = {
            'validations_performed': 0,
            'validations_failed': 0,
            'sanitizations_performed': 0,
            'security_violations_detected': 0
        }
        
        if self.audit_logger:
            self.audit_logger.log_key_operation("input_validator_initialized", {
                "validation_level": self.level.value,
                "built_in_rules_count": len(self.built_in_rules),
                "custom_rules_count": len(self.custom_rules)
            })
    
    def _validate_email(self, value: str) -> bool:
        """Validate email address format"""
        if not isinstance(value, str):
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, value) is not None
    
    def _sanitize_email(self, value: str) -> str:
        """Sanitize email address"""
        if not isinstance(value, str):
            return ""
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>"\'\\\r\n]', '', value.strip().lower())
        return sanitized
    
    def _validate_url(self, value: str) -> bool:
        """Validate URL format"""
        if not isinstance(value, str):
            return False
        
        try:
            parsed = urlparse(value)
            return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
        except Exception:
            return False
    
    def _sanitize_url(self, value: str) -> str:
        """Sanitize URL"""
        if not isinstance(value, str):
            return ""
        
        try:
            parsed = urlparse(value.strip())
            if parsed.scheme in ['http', 'https']:
                return parsed.geturl()
        except Exception:
            pass
        
        return ""
    
    def _validate_api_key(self, value: str) -> bool:
        """Validate API key format"""
        if not isinstance(value, str):
            return False
        
        # Basic validation: length and character set
        if len(value) < 10 or len(value) > 500:
            return False
        
        # Should not contain control characters or spaces
        if re.search(r'[\x00-\x1f\x7f-\x9f\s]', value):
            return False
        
        # Should not be a common placeholder
        placeholder_patterns = [
            r'^(your|test|demo|example|placeholder)',
            r'(key|token|secret)$',
            r'^(abc|123|xxx)',
        ]
        
        value_lower = value.lower()
        for pattern in placeholder_patterns:
            if re.search(pattern, value_lower):
                return False
        
        return True
    
    def _sanitize_api_key(self, value: str) -> str:
        """Sanitize API key (minimal processing to preserve validity)"""
        if not isinstance(value, str):
            return ""
        
        # Only strip whitespace
        return value.strip()
    
    def _validate_provider_name(self, value: str) -> bool:
        """Validate provider name"""
        if not isinstance(value, str):
            return False
        
        # Length check
        if len(value) < 1 or len(value) > 50:
            return False
        
        # Character set: alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            return False
        
        return True
    
    def _sanitize_provider_name(self, value: str) -> str:
        """Sanitize provider name"""
        if not isinstance(value, str):
            return ""
        
        # Keep only allowed characters
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', value.strip().lower())
        return sanitized[:50]  # Limit length
    
    def _validate_file_path(self, value: str) -> bool:
        """Validate file path for security (prevent path traversal)"""
        if not isinstance(value, str):
            return False
        
        try:
            path = Path(value)
            
            # Check for path traversal attempts
            dangerous_patterns = ['../', '..\\\\', '~/', '~\\\\']
            for pattern in dangerous_patterns:
                if pattern in value:
                    return False
            
            # Check for absolute paths starting with sensitive directories
            if path.is_absolute():
                sensitive_dirs = ['/etc', '/usr', '/bin', '/sbin', '/root', '/sys', '/proc']
                for sensitive_dir in sensitive_dirs:
                    if str(path).startswith(sensitive_dir):
                        if self.level == ValidationLevel.STRICT:
                            return False
            
            return True
            
        except Exception:
            return False
    
    def _sanitize_file_path(self, value: str) -> str:
        """Sanitize file path"""
        if not isinstance(value, str):
            return ""
        
        try:
            # Remove dangerous characters
            sanitized = re.sub(r'[<>"|?*\x00-\x1f]', '', value)
            
            # Remove path traversal patterns
            sanitized = re.sub(r'\.\./|\.\.\\\\', '', sanitized)
            
            # Normalize path
            path = Path(sanitized).resolve()
            return str(path)
            
        except Exception:
            return ""
    
    def _validate_json(self, value: Union[str, dict, list]) -> bool:
        """Validate JSON data"""
        if isinstance(value, (dict, list)):
            return True
        
        if isinstance(value, str):
            try:
                json.loads(value)
                return True
            except json.JSONDecodeError:
                return False
        
        return False
    
    def _sanitize_json(self, value: Union[str, dict, list]) -> Union[str, dict, list]:
        """Sanitize JSON data"""
        if isinstance(value, (dict, list)):
            return value
        
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return json.dumps(parsed)  # Re-serialize to ensure valid format
            except json.JSONDecodeError:
                return "{}"
        
        return "{}"
    
    def _validate_command(self, value: str) -> bool:
        """Validate command for safety (prevent command injection)"""
        if not isinstance(value, str):
            return False
        
        # Dangerous command patterns
        dangerous_patterns = [
            r';.*rm\s+',  # Command chaining with rm
            r'&&.*rm\s+',  # Command chaining with rm
            r'\|\|.*rm\s+',  # Command chaining with rm
            r'`.*`',  # Command substitution
            r'\$\(',  # Command substitution
            r'\${',  # Variable substitution
            r'>\s*/dev/',  # Redirecting to devices
            r'<\s*/dev/',  # Reading from devices
            r'>\s*/etc/',  # Redirecting to system configs
            r'curl.*\|',  # Curl piping
            r'wget.*\|',  # Wget piping
            r'nc\s+',  # Netcat
            r'ncat\s+',  # Ncat
        ]
        
        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, value_lower):
                return False
        
        return True
    
    def _sanitize_command(self, value: str) -> str:
        """Sanitize command (very restrictive)"""
        if not isinstance(value, str):
            return ""
        
        # For security, only allow very basic commands
        allowed_commands = ['ls', 'pwd', 'echo', 'cat', 'grep', 'find', 'head', 'tail']
        
        words = value.split()
        if words and words[0] in allowed_commands:
            # Basic sanitization - remove dangerous characters
            sanitized = re.sub(r'[;&|`$<>(){}]', '', value)
            return sanitized
        
        return ""  # Block command if not in allowed list
    
    def _validate_sql_safe(self, value: str) -> bool:
        """Validate string is safe from SQL injection"""
        if not isinstance(value, str):
            return False
        
        # SQL injection patterns
        sql_patterns = [
            r"'.*'",  # Single quotes
            r'".*"',  # Double quotes
            r'union\s+select',  # UNION SELECT
            r'drop\s+table',  # DROP TABLE
            r'delete\s+from',  # DELETE FROM
            r'insert\s+into',  # INSERT INTO
            r'update\s+.*set',  # UPDATE SET
            r'--',  # SQL comments
            r'/\*.*\*/',  # SQL block comments
            r'xp_',  # Extended stored procedures
            r'sp_',  # Stored procedures
        ]
        
        value_lower = value.lower()
        for pattern in sql_patterns:
            if re.search(pattern, value_lower):
                return False
        
        return True
    
    def _sanitize_sql(self, value: str) -> str:
        """Sanitize string to prevent SQL injection"""
        if not isinstance(value, str):
            return ""
        
        # Escape single quotes
        sanitized = value.replace("'", "''")
        
        # Remove SQL comments
        sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
        
        return sanitized
    
    def _validate_xss_safe(self, value: str) -> bool:
        """Validate string is safe from XSS attacks"""
        if not isinstance(value, str):
            return False
        
        # XSS patterns
        xss_patterns = [
            r'<script',  # Script tags
            r'javascript:',  # JavaScript protocol
            r'on\w+\s*=',  # Event handlers
            r'<iframe',  # Iframe tags
            r'<object',  # Object tags
            r'<embed',  # Embed tags
            r'<link',  # Link tags
            r'<meta',  # Meta tags
            r'<style',  # Style tags
        ]
        
        value_lower = value.lower()
        for pattern in xss_patterns:
            if re.search(pattern, value_lower):
                return False
        
        return True
    
    def _sanitize_html(self, value: str) -> str:
        """Sanitize HTML to prevent XSS"""
        if not isinstance(value, str):
            return ""
        
        # HTML escape
        sanitized = html.escape(value)
        
        # Remove dangerous attributes
        sanitized = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def add_custom_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule"""
        self.custom_rules[rule.name] = rule
        
        if self.audit_logger:
            self.audit_logger.log_key_operation("custom_rule_added", {
                "rule_name": rule.name,
                "required": rule.required
            })
    
    def validate(self, 
                value: Any,
                rules: List[str],
                field_name: str = None,
                sanitize: bool = True) -> Dict[str, Any]:
        """
        Validate value against specified rules
        
        Args:
            value: Value to validate
            rules: List of rule names to apply
            field_name: Name of the field being validated
            sanitize: Whether to sanitize the value
        
        Returns:
            Dictionary with validation results and sanitized value
        """
        try:
            self.stats['validations_performed'] += 1
            
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'sanitized_value': value,
                'applied_rules': [],
                'field_name': field_name
            }
            
            for rule_name in rules:
                # Get rule from built-in or custom rules
                rule = self.built_in_rules.get(rule_name) or self.custom_rules.get(rule_name)
                
                if not rule:
                    result['warnings'].append(f"Unknown validation rule: {rule_name}")
                    continue
                
                result['applied_rules'].append(rule_name)
                
                # Apply validation
                try:
                    is_valid = rule.validator(value)
                    
                    if not is_valid:
                        result['valid'] = False
                        result['errors'].append(rule.message)
                        self.stats['validations_failed'] += 1
                        
                        # Log security violations
                        if rule_name in ['sql_safe', 'xss_safe', 'command']:
                            self.stats['security_violations_detected'] += 1
                            
                            if self.audit_logger:
                                self.audit_logger.log_security_event(
                                    "validation_security_violation",
                                    f"Security violation detected in field '{field_name}' using rule '{rule_name}'",
                                    {
                                        "field_name": field_name,
                                        "rule_name": rule_name,
                                        "value_type": type(value).__name__,
                                        "value_length": len(str(value)) if value else 0
                                    },
                                    "WARNING"
                                )
                    
                    # Apply sanitization if requested and available
                    if sanitize and rule.sanitizer:
                        try:
                            result['sanitized_value'] = rule.sanitizer(result['sanitized_value'])
                            self.stats['sanitizations_performed'] += 1
                        except Exception as e:
                            result['warnings'].append(f"Sanitization failed for rule {rule_name}: {e}")
                            
                except Exception as e:
                    result['warnings'].append(f"Rule {rule_name} execution failed: {e}")
            
            # Audit log for validation
            if self.audit_logger and (not result['valid'] or result['warnings']):
                self.audit_logger.log_key_operation("validation_completed", {
                    "field_name": field_name,
                    "rules": rules,
                    "valid": result['valid'],
                    "error_count": len(result['errors']),
                    "warning_count": len(result['warnings'])
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Validation failed for field {field_name}: {e}")
            return {
                'valid': False,
                'errors': [f"Validation system error: {e}"],
                'warnings': [],
                'sanitized_value': value,
                'applied_rules': [],
                'field_name': field_name
            }
    
    def validate_dict(self, 
                     data: Dict[str, Any],
                     schema: Dict[str, List[str]],
                     sanitize: bool = True) -> Dict[str, Any]:
        """
        Validate dictionary against schema
        
        Args:
            data: Dictionary to validate
            schema: Dictionary mapping field names to validation rules
            sanitize: Whether to sanitize values
        
        Returns:
            Dictionary with validation results and sanitized data
        """
        try:
            result = {
                'valid': True,
                'errors': {},
                'warnings': {},
                'sanitized_data': {},
                'field_results': {}
            }
            
            # Validate each field
            for field_name, rules in schema.items():
                value = data.get(field_name)
                
                field_result = self.validate(value, rules, field_name, sanitize)
                result['field_results'][field_name] = field_result
                
                if not field_result['valid']:
                    result['valid'] = False
                    result['errors'][field_name] = field_result['errors']
                
                if field_result['warnings']:
                    result['warnings'][field_name] = field_result['warnings']
                
                result['sanitized_data'][field_name] = field_result['sanitized_value']
            
            # Copy non-validated fields
            for field_name, value in data.items():
                if field_name not in schema:
                    result['sanitized_data'][field_name] = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"Dictionary validation failed: {e}")
            return {
                'valid': False,
                'errors': {'_system': [f"Validation system error: {e}"]},
                'warnings': {},
                'sanitized_data': data,
                'field_results': {}
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            **self.stats,
            'validation_level': self.level.value,
            'built_in_rules_count': len(self.built_in_rules),
            'custom_rules_count': len(self.custom_rules),
            'success_rate': (
                (self.stats['validations_performed'] - self.stats['validations_failed']) /
                max(self.stats['validations_performed'], 1)
            ) * 100
        }
    
    def reset_statistics(self) -> None:
        """Reset validation statistics"""
        self.stats = {
            'validations_performed': 0,
            'validations_failed': 0,
            'sanitizations_performed': 0,
            'security_violations_detected': 0
        }
        
        if self.audit_logger:
            self.audit_logger.log_key_operation("validation_stats_reset", {})


# Convenience functions for common validations

def validate_api_key(api_key: str, level: ValidationLevel = ValidationLevel.NORMAL) -> Dict[str, Any]:
    """Quick API key validation"""
    validator = InputValidator(level)
    return validator.validate(api_key, ['api_key'], 'api_key')

def validate_provider_config(config: Dict[str, Any], level: ValidationLevel = ValidationLevel.NORMAL) -> Dict[str, Any]:
    """Quick provider configuration validation"""
    validator = InputValidator(level)
    
    schema = {
        'api_key': ['api_key'],
        'base_url': ['url'],
        'provider_name': ['provider_name']
    }
    
    return validator.validate_dict(config, schema)

def validate_user_input(user_input: str, level: ValidationLevel = ValidationLevel.NORMAL) -> Dict[str, Any]:
    """Quick user input validation (XSS and SQL safe)"""
    validator = InputValidator(level)
    return validator.validate(user_input, ['xss_safe', 'sql_safe'], 'user_input')