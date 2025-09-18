"""
Configuration Profile Model
Service-specific configuration management for BookFairy services
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json
import os


class ConfigSource(Enum):
    """Sources of configuration data"""
    ENVIRONMENT_VARIABLE = "env_var"
    CONFIG_FILE = "file"
    DATABASE = "database"
    VAULT = "vault"  # Secrets management
    KUBERNETES_CONFIGMAP = "k8s_configmap"
    KUBERNETES_SECRET = "k8s_secret"
    AZURE_KEY_VAULT = "azure_key_vault"
    AWS_SECRETS_MANAGER = "aws_secrets"


class ConfigSecurityLevel(Enum):
    """Security classification of configuration values"""
    PUBLIC = "public"          # Safe to be public
    INTERNAL = "internal"      # Internal use only
    SENSITIVE = "sensitive"    # Contains sensitive data
    SECRET = "secret"          # Must be encrypted/secure
    HIGHLY_SENSITIVE = "highly_sensitive"  # Greatest protection needed


@dataclass
class ConfigValue:
    """Represents a single configuration value with metadata"""

    key: str
    value: Any
    value_type: str = "string"  # string, int, float, bool, json

    # Source and security
    source: ConfigSource = ConfigSource.ENVIRONMENT_VARIABLE
    security_level: ConfigSecurityLevel = ConfigSecurityLevel.PUBLIC

    # Metadata
    description: Optional[str] = None
    required: bool = False
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None

    # Audit and versioning
    last_updated: datetime = field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None
    version: int = 1
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize configuration value"""
        # Auto-detect value type if not specified
        if self.value_type == "string":
            if isinstance(self.value, dict) or isinstance(self.value, list):
                self.value_type = "json"
            elif isinstance(self.value, bool):
                self.value_type = "bool"
            elif isinstance(self.value, int):
                self.value_type = "int"
            elif isinstance(self.value, float):
                self.value_type = "float"

    def is_sensitive(self) -> bool:
        """Check if configuration value contains sensitive data"""
        return self.security_level in [
            ConfigSecurityLevel.SENSITIVE,
            ConfigSecurityLevel.SECRET,
            ConfigSecurityLevel.HIGHLY_SENSITIVE
        ]

    def validate_value(self) -> List[str]:
        """Validate the configuration value"""
        errors = []

        # Check if required field has value
        if self.required and (self.value is None or str(self.value).strip() == ""):
            errors.append(f"Required configuration '{self.key}' is missing or empty")

        # Type validation
        if self.value_type == "int" and not isinstance(self.value, int):
            try:
                self.value = int(self.value)
            except (ValueError, TypeError):
                errors.append(f"Configuration '{self.key}' must be an integer")

        elif self.value_type == "float" and not isinstance(self.value, (int, float)):
            try:
                self.value = float(self.value)
            except (ValueError, TypeError):
                errors.append(f"Configuration '{self.key}' must be a number")

        elif self.value_type == "bool" and not isinstance(self.value, bool):
            if isinstance(self.value, str):
                self.value = self.value.lower() in ('true', '1', 'yes', 'on')
            else:
                errors.append(f"Configuration '{self.key}' must be a boolean")

        # Pattern validation
        if self.validation_pattern and isinstance(self.value, str):
            import re
            if not re.match(self.validation_pattern, self.value):
                errors.append(f"Configuration '{self.key}' does not match required pattern")

        return errors

    def record_update(self, new_value: Any, updated_by: str, reason: Optional[str] = None):
        """Record configuration update for audit trail"""
        if self.value != new_value:
            # Add to audit trail
            self.audit_trail.append({
                "timestamp": datetime.utcnow().isoformat(),
                "previous_value": self._mask_value(self.value),
                "new_value": self._mask_value(new_value),
                "updated_by": updated_by,
                "reason": reason
            })

            # Update value and metadata
            self.value = new_value
            self.last_updated = datetime.utcnow()
            self.updated_by = updated_by
            self.version += 1

    def _mask_value(self, value: Any) -> Any:
        """Mask sensitive values for audit trail"""
        if self.is_sensitive():
            return "***MASKED***"
        return value

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "key": self.key,
            "value_type": self.value_type,
            "source": self.source.value,
            "security_level": self.security_level.value,
            "description": self.description,
            "required": self.required,
            "default_value": self.default_value,
            "validation_pattern": self.validation_pattern,
            "last_updated": self.last_updated.isoformat(),
            "updated_by": self.updated_by,
            "version": self.version,
            "audit_trail": self.audit_trail
        }

        # Handle sensitive values
        if include_sensitive or not self.is_sensitive():
            result["value"] = self.value
        else:
            result["value"] = "***MASKED***"

        return result


@dataclass
class ServiceConfigProfile:
    """Configuration profile for a specific BookFairy service"""

    service_name: str
    service_type: str  # discord-bot, lazylibrarian, etc.

    # Configuration values
    configurations: Dict[str, ConfigValue] = field(default_factory=dict)

    # Profile metadata
    profile_version: int = 1
    environment: str = "development"  # development, staging, production
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Profile management
    active: bool = True
    parent_profile: Optional[str] = None  # Inheritance support
    tags: List[str] = field(default_factory=list)

    # Governance
    audit_lens_applied: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize service configuration profile"""
        # Load default configurations for known service types
        if not self.configurations:
            self._load_default_configurations()

    def _load_default_configurations(self):
        """Load default configuration values for the service type"""
        defaults = self._get_service_defaults()

        for config_key, config_def in defaults.items():
            self.configurations[config_key] = ConfigValue(
                key=config_key,
                value=config_def.get("value"),
                value_type=config_def.get("type", "string"),
                source=ConfigSource.ENVIRONMENT_VARIABLE,
                security_level=ConfigSecurityLevel(config_def.get("security", "public")),
                description=config_def.get("description", ""),
                required=config_def.get("required", False),
                default_value=config_def.get("default")
            )

    def _get_service_defaults(self) -> Dict[str, Dict[str, Any]]:
        """Get default configuration values for service types"""
        service_defaults = {
            "discord-bot": {
                "DISCORD_TOKEN": {
                    "type": "string",
                    "security": "highly_sensitive",
                    "required": True,
                    "description": "Discord bot authentication token"
                },
                "DISCORD_GUILD_ID": {
                    "type": "string",
                    "security": "sensitive",
                    "required": False,
                    "description": "Primary Discord guild ID"
                },
                "API_PORT": {
                    "type": "int",
                    "security": "internal",
                    "required": True,
                    "value": 8080,
                    "default": 8080,
                    "description": "Internal API port"
                },
                "LOG_LEVEL": {
                    "type": "string",
                    "security": "public",
                    "required": False,
                    "value": "INFO",
                    "default": "INFO",
                    "description": "Logging verbosity level"
                },
                "MAX_WORKFLOWS": {
                    "type": "int",
                    "security": "internal",
                    "required": False,
                    "value": 10,
                    "default": 10,
                    "description": "Maximum concurrent workflows"
                }
            },
            "lazylibrarian": {
                "LAZYLIBRARIAN_API_KEY": {
                    "type": "string",
                    "security": "sensitive",
                    "required": True,
                    "description": "LazyLibrarian API key"
                },
                "LAZYLIBRARIAN_PORT": {
                    "type": "int",
                    "security": "internal",
                    "required": True,
                    "value": 5299,
                    "default": 5299,
                    "description": "LazyLibrarian web UI port"
                },
                "DOWNLOAD_DIR": {
                    "type": "string",
                    "security": "internal",
                    "required": False,
                    "value": "/downloads",
                    "default": "/downloads",
                    "description": "Download directory path"
                }
            },
            "redis": {
                "REDIS_PORT": {
                    "type": "int",
                    "security": "internal",
                    "required": True,
                    "value": 6379,
                    "default": 6379,
                    "description": "Redis server port"
                },
                "REDIS_PASSWORD": {
                    "type": "string",
                    "security": "highly_sensitive",
                    "required": False,
                    "description": "Redis authentication password"
                },
                "REDIS_DB": {
                    "type": "int",
                    "security": "internal",
                    "required": False,
                    "value": 0,
                    "default": 0,
                    "description": "Redis database number"
                }
            },
            "audiobookshelf": {
                "AUDIOBOOKSHELF_PORT": {
                    "type": "int",
                    "security": "internal",
                    "required": True,
                    "value": 13378,
                    "default": 13378,
                    "description": "Audiobookshelf web UI port"
                },
                "MEDIA_PATH": {
                    "type": "string",
                    "security": "internal",
                    "required": False,
                    "value": "/audiobooks",
                    "default": "/audiobooks",
                    "description": "Audiobook media directory"
                }
            }
        }

        return service_defaults.get(self.service_type, {})

    def get_config(self, key: str) -> Optional[Any]:
        """Get configuration value by key"""
        config = self.configurations.get(key)
        return config.value if config else None

    def set_config(self, key: str, value: Any, updated_by: str = "system",
                  reason: Optional[str] = None):
        """Set configuration value with audit trail"""
        if key in self.configurations:
            self.configurations[key].record_update(value, updated_by, reason)
        else:
            # Create new configuration
            self.configurations[key] = ConfigValue(
                key=key,
                value=value,
                updated_by=updated_by
            )

        self.last_updated = datetime.utcnow()

    def validate_all_configs(self) -> List[str]:
        """Validate all configuration values"""
        all_errors = []
        for config in self.configurations.values():
            errors = config.validate_value()
            all_errors.extend(errors)
        return all_errors

    def get_sensitive_configs(self) -> List[ConfigValue]:
        """Get all sensitive configuration values"""
        return [config for config in self.configurations.values() if config.is_sensitive()]

    def apply_audit_lens(self, lens_name: str) -> Dict[str, Any]:
        """Apply governance audit lens to configuration profile"""
        findings = []

        if lens_name == "safety-security":
            # Security audit lens
            for config in self.configurations.values():
                if config.is_sensitive() and config.source == ConfigSource.ENVIRONMENT_VARIABLE:
                    findings.append(f"Secure environment variable found: {config.key}")
                if config.required and config.value is None:
                    findings.append(f"Required configuration missing: {config.key}")

        elif lens_name == "performance":
            # Performance audit lens
            if self.service_type == "discord-bot" and self.get_config("MAX_WORKFLOWS") > 100:
                findings.append("High workflow concurrency may impact performance")

        self.audit_lens_applied.append(lens_name)

        return {
            "lens_name": lens_name,
            "service_name": self.service_name,
            "findings": findings,
            "score": (1.0 - len(findings) * 0.1) if len(findings) <= 10 else 0.0
        }

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export to dictionary"""
        return {
            "service_name": self.service_name,
            "service_type": self.service_type,
            "configurations": {
                key: config.to_dict(include_sensitive)
                for key, config in self.configurations.items()
            },
            "profile_version": self.profile_version,
            "environment": self.environment,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "active": self.active,
            "parent_profile": self.parent_profile,
            "tags": self.tags,
            "audit_lens_applied": self.audit_lens_applied
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfigProfile':
        """Create from dictionary"""
        # Parse datetime fields
        for datetime_field in ['created_at', 'last_updated']:
            if data.get(datetime_field):
                data[datetime_field] = datetime.fromisoformat(data[datetime_field])

        # Parse configurations
        configs_data = data.pop('configurations', {})
        configurations = {}
        for key, config_data in configs_data.items():
            configurations[key] = ConfigValue(**config_data)

        return cls(configurations=configurations, **data)


class ConfigRegistry:
    """Registry for managing configuration profiles"""

    def __init__(self):
        self.profiles: Dict[str, ServiceConfigProfile] = {}
        self.environment_configs: Dict[str, Dict[str, Any]] = {}

    def register_profile(self, profile: ServiceConfigProfile):
        """Register a configuration profile"""
        self.profiles[profile.service_name] = profile

    def get_profile(self, service_name: str) -> Optional[ServiceConfigProfile]:
        """Get configuration profile for a service"""
        return self.profiles.get(service_name)

    def load_from_environment(self, environment: str = "development"):
        """Load configuration values from environment variables"""
        self.environment_configs[environment] = dict(os.environ)

        # Update profiles with environment values
        for profile in self.profiles.values():
            self._apply_environment_to_profile(profile, environment)

    def _apply_environment_to_profile(self, profile: ServiceConfigProfile,
                                    environment: str):
        """Apply environment variables to profile configurations"""
        env_vars = self.environment_configs.get(environment, {})

        for config in profile.configurations.values():
            if config.source == ConfigSource.ENVIRONMENT_VARIABLE:
                env_value = env_vars.get(config.key)
                if env_value is not None:
                    profile.set_config(config.key, env_value, "environment_loader",
                                     "Loaded from environment variables")

    def validate_all_profiles(self) -> Dict[str, List[str]]:
        """Validate all configuration profiles"""
        validation_results = {}
        for profile in self.profiles.values():
            errors = profile.validate_all_configs()
            if errors:
                validation_results[profile.service_name] = errors
        return validation_results

    def apply_audit_lens_all_profiles(self, lens_name: str) -> List[Dict[str, Any]]:
        """Apply audit lens to all profiles"""
        results = []
        for profile in self.profiles.values():
            audit_result = profile.apply_audit_lens(lens_name)
            results.append(audit_result)
        return results
