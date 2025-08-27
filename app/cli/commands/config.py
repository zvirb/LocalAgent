"""
Configuration Command Implementation
Manages LocalAgent configuration through CLI
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base import InteractiveCommand, CommandResult, CommandStatus
from ..core.context import CLIContext
from ..ui.display import DisplayManager


class ConfigCommand(InteractiveCommand):
    """
    Command for managing LocalAgent configuration
    Handles configuration display, validation, export, and interactive editing
    """
    
    @property
    def name(self) -> str:
        return "config"
    
    @property
    def description(self) -> str:
        return "Manage LocalAgent configuration settings"
    
    @property 
    def aliases(self) -> List[str]:
        return ["cfg", "settings"]
    
    async def execute(self, show: bool = False, validate: bool = False,
                     export: Optional[str] = None, edit: bool = False,
                     reset: bool = False, **kwargs) -> CommandResult:
        """Execute configuration management command"""
        
        try:
            if reset:
                return await self._reset_configuration()
            
            if edit:
                return await self._edit_configuration_interactive()
            
            if show or not any([validate, export, edit, reset]):
                return await self._show_configuration()
            
            if validate:
                return await self._validate_configuration()
            
            if export:
                return await self._export_configuration(export)
            
            return self._create_success_result("Configuration operation completed")
            
        except Exception as e:
            return self._create_error_result(f"Configuration command failed: {e}", str(e))
    
    async def _show_configuration(self) -> CommandResult:
        """Display current configuration"""
        try:
            self.display_manager.display_config(self.context.config)
            
            # Additional configuration details
            config_info = {
                'config_file': str(self.context.config.config_file) if self.context.config.config_file else 'Default',
                'providers_count': len(self.context.config.providers),
                'enabled_providers_count': len(self.context.config.get_enabled_providers()),
                'plugins_count': len(self.context.config.plugins.enabled_plugins)
            }
            
            return self._create_success_result("Configuration displayed", config_info)
            
        except Exception as e:
            return self._create_error_result(f"Failed to display configuration: {e}")
    
    async def _validate_configuration(self) -> CommandResult:
        """Validate current configuration"""
        try:
            from ..core.config import ConfigurationManager
            
            config_manager = ConfigurationManager()
            validation_result = await config_manager.validate_configuration()
            
            self.display_manager.display_validation_results(validation_result)
            
            if validation_result['valid']:
                return self._create_success_result(
                    "Configuration is valid",
                    validation_result
                )
            else:
                return self._create_partial_result(
                    f"Configuration has {len(validation_result['errors'])} errors",
                    validation_result
                )
            
        except Exception as e:
            return self._create_error_result(f"Configuration validation failed: {e}")
    
    async def _export_configuration(self, export_path: str) -> CommandResult:
        """Export configuration to file"""
        try:
            from ..core.config import ConfigurationManager
            
            config_manager = ConfigurationManager()
            export_file = Path(export_path)
            
            # Determine format from file extension
            if export_file.suffix.lower() == '.yaml' or export_file.suffix.lower() == '.yml':
                format_type = 'yaml'
            else:
                format_type = 'json'
            
            await config_manager.export_configuration(export_file, format_type)
            
            self.display_manager.print_success(f"Configuration exported to {export_path}")
            
            return self._create_success_result(
                f"Configuration exported to {export_path}",
                {"export_path": export_path, "format": format_type}
            )
            
        except Exception as e:
            return self._create_error_result(f"Failed to export configuration: {e}")
    
    async def _edit_configuration_interactive(self) -> CommandResult:
        """Edit configuration interactively"""
        try:
            self.display_manager.print_info("Interactive Configuration Editor")
            
            # Show current configuration first
            self.display_manager.display_config(self.context.config)
            
            # Configuration sections that can be edited
            sections = {
                "basic": "Basic settings (log level, debug mode)",
                "providers": "LLM provider configurations", 
                "orchestration": "Workflow orchestration settings",
                "mcp": "Memory/Context/Protocol settings",
                "plugins": "Plugin system settings"
            }
            
            self.display_manager.display_choices_table("Configuration Sections", sections)
            
            section = await self.get_user_choice(
                "Which section would you like to edit?",
                list(sections.keys()),
                "basic"
            )
            
            if section == "basic":
                return await self._edit_basic_settings()
            elif section == "providers":
                return await self._edit_provider_settings()
            elif section == "orchestration":
                return await self._edit_orchestration_settings()
            elif section == "mcp":
                return await self._edit_mcp_settings()
            elif section == "plugins":
                return await self._edit_plugin_settings()
            else:
                return self._create_error_result("Invalid section selected")
            
        except Exception as e:
            return self._create_error_result(f"Interactive configuration edit failed: {e}")
    
    async def _edit_basic_settings(self) -> CommandResult:
        """Edit basic configuration settings"""
        try:
            self.display_manager.print_info("Editing Basic Settings")
            
            # Log level
            log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            current_log_level = self.context.config.log_level
            
            new_log_level = await self.get_user_choice(
                f"Log level (current: {current_log_level})",
                log_levels,
                current_log_level
            )
            
            # Debug mode
            current_debug = self.context.config.debug_mode
            new_debug = await self.confirm_action(
                f"Enable debug mode? (current: {current_debug})",
                current_debug
            )
            
            # Update configuration
            self.context.config.log_level = new_log_level
            self.context.config.debug_mode = new_debug
            
            # Save changes
            await self._save_configuration_changes()
            
            self.display_manager.print_success("Basic settings updated")
            return self._create_success_result("Basic settings updated successfully")
            
        except Exception as e:
            return self._create_error_result(f"Failed to edit basic settings: {e}")
    
    async def _edit_provider_settings(self) -> CommandResult:
        """Edit provider configuration settings"""
        try:
            self.display_manager.print_info("Editing Provider Settings")
            
            # Show current providers
            enabled_providers = self.context.config.get_enabled_providers()
            self.display_manager.print_info(f"Currently enabled providers: {', '.join(enabled_providers)}")
            
            # Provider management options
            actions = {
                "add": "Add new provider",
                "configure": "Configure existing provider", 
                "enable": "Enable provider",
                "disable": "Disable provider",
                "set_default": "Set default provider"
            }
            
            self.display_manager.display_choices_table("Provider Actions", actions)
            
            action = await self.get_user_choice(
                "What would you like to do?",
                list(actions.keys())
            )
            
            if action == "add":
                return await self._add_new_provider()
            elif action == "configure":
                return await self._configure_existing_provider()
            elif action == "enable":
                return await self._enable_provider()
            elif action == "disable":
                return await self._disable_provider()
            elif action == "set_default":
                return await self._set_default_provider()
            
            return self._create_success_result("Provider settings operation completed")
            
        except Exception as e:
            return self._create_error_result(f"Failed to edit provider settings: {e}")
    
    async def _add_new_provider(self) -> CommandResult:
        """Add a new provider configuration"""
        available_providers = ["ollama", "openai", "gemini", "perplexity"]
        existing_providers = list(self.context.config.providers.keys())
        
        new_providers = [p for p in available_providers if p not in existing_providers]
        
        if not new_providers:
            return self._create_error_result("All supported providers are already configured")
        
        provider_name = await self.get_user_choice(
            "Which provider would you like to add?",
            new_providers
        )
        
        # Use provider configuration wizard
        from ..ui.prompts import ProviderConfigurationWizard
        
        wizard = ProviderConfigurationWizard(self.console)
        provider_config = await wizard.configure_provider(provider_name)
        
        if provider_config:
            self.context.config.providers[provider_name] = provider_config
            await self._save_configuration_changes()
            
            self.display_manager.print_success(f"Provider {provider_name} added successfully")
            return self._create_success_result(f"Provider {provider_name} added")
        else:
            return self._create_error_result("Provider configuration cancelled")
    
    async def _configure_existing_provider(self) -> CommandResult:
        """Configure an existing provider"""
        existing_providers = list(self.context.config.providers.keys())
        
        if not existing_providers:
            return self._create_error_result("No providers configured")
        
        provider_name = await self.get_user_choice(
            "Which provider would you like to configure?",
            existing_providers
        )
        
        # Use provider configuration wizard
        from ..ui.prompts import ProviderConfigurationWizard
        
        wizard = ProviderConfigurationWizard(self.console)
        provider_config = await wizard.configure_provider(provider_name)
        
        if provider_config:
            self.context.config.providers[provider_name] = provider_config
            await self._save_configuration_changes()
            
            self.display_manager.print_success(f"Provider {provider_name} reconfigured successfully")
            return self._create_success_result(f"Provider {provider_name} reconfigured")
        else:
            return self._create_error_result("Provider configuration cancelled")
    
    async def _enable_provider(self) -> CommandResult:
        """Enable a provider"""
        disabled_providers = [
            name for name, config in self.context.config.providers.items()
            if not config.enabled
        ]
        
        if not disabled_providers:
            return self._create_error_result("All providers are already enabled")
        
        provider_name = await self.get_user_choice(
            "Which provider would you like to enable?",
            disabled_providers
        )
        
        self.context.config.providers[provider_name].enabled = True
        await self._save_configuration_changes()
        
        self.display_manager.print_success(f"Provider {provider_name} enabled")
        return self._create_success_result(f"Provider {provider_name} enabled")
    
    async def _disable_provider(self) -> CommandResult:
        """Disable a provider"""
        enabled_providers = self.context.config.get_enabled_providers()
        
        if len(enabled_providers) <= 1:
            return self._create_error_result("Cannot disable all providers - at least one must remain enabled")
        
        provider_name = await self.get_user_choice(
            "Which provider would you like to disable?",
            enabled_providers
        )
        
        # Check if this is the default provider
        if provider_name == self.context.config.default_provider:
            # Need to set a new default
            other_providers = [p for p in enabled_providers if p != provider_name]
            new_default = await self.get_user_choice(
                f"Provider {provider_name} is the default. Choose new default:",
                other_providers
            )
            self.context.config.default_provider = new_default
        
        self.context.config.providers[provider_name].enabled = False
        await self._save_configuration_changes()
        
        self.display_manager.print_success(f"Provider {provider_name} disabled")
        return self._create_success_result(f"Provider {provider_name} disabled")
    
    async def _set_default_provider(self) -> CommandResult:
        """Set default provider"""
        enabled_providers = self.context.config.get_enabled_providers()
        current_default = self.context.config.default_provider
        
        provider_name = await self.get_user_choice(
            f"Choose default provider (current: {current_default})",
            enabled_providers,
            current_default
        )
        
        self.context.config.default_provider = provider_name
        await self._save_configuration_changes()
        
        self.display_manager.print_success(f"Default provider set to {provider_name}")
        return self._create_success_result(f"Default provider set to {provider_name}")
    
    async def _edit_orchestration_settings(self) -> CommandResult:
        """Edit orchestration configuration"""
        self.display_manager.print_info("Editing Orchestration Settings")
        
        current_config = self.context.config.orchestration
        
        # Max parallel agents
        new_max_agents = self.prompts.ask_integer(
            f"Maximum parallel agents (current: {current_config.max_parallel_agents})",
            current_config.max_parallel_agents,
            min_val=1,
            max_val=50
        )
        
        # Max workflow iterations
        new_max_iterations = self.prompts.ask_integer(
            f"Maximum workflow iterations (current: {current_config.max_workflow_iterations})",
            current_config.max_workflow_iterations,
            min_val=1,
            max_val=10
        )
        
        # Evidence collection
        new_evidence = await self.confirm_action(
            f"Enable evidence collection? (current: {current_config.enable_evidence_collection})",
            current_config.enable_evidence_collection
        )
        
        # Update configuration
        self.context.config.orchestration.max_parallel_agents = new_max_agents
        self.context.config.orchestration.max_workflow_iterations = new_max_iterations
        self.context.config.orchestration.enable_evidence_collection = new_evidence
        
        await self._save_configuration_changes()
        
        self.display_manager.print_success("Orchestration settings updated")
        return self._create_success_result("Orchestration settings updated successfully")
    
    async def _edit_mcp_settings(self) -> CommandResult:
        """Edit MCP configuration"""
        self.display_manager.print_info("Editing MCP Settings")
        
        current_config = self.context.config.mcp
        
        # Redis URL
        new_redis_url = self.prompts.ask_text(
            f"Redis URL (current: {current_config.redis_url})",
            current_config.redis_url
        )
        
        # Memory retention
        new_retention = self.prompts.ask_integer(
            f"Memory retention days (current: {current_config.memory_retention_days})",
            current_config.memory_retention_days,
            min_val=1,
            max_val=365
        )
        
        # Update configuration
        self.context.config.mcp.redis_url = new_redis_url
        self.context.config.mcp.memory_retention_days = new_retention
        
        await self._save_configuration_changes()
        
        self.display_manager.print_success("MCP settings updated")
        return self._create_success_result("MCP settings updated successfully")
    
    async def _edit_plugin_settings(self) -> CommandResult:
        """Edit plugin configuration"""
        self.display_manager.print_info("Editing Plugin Settings")
        
        current_config = self.context.config.plugins
        
        # Auto load plugins
        new_auto_load = await self.confirm_action(
            f"Auto-load enabled plugins? (current: {current_config.auto_load_plugins})",
            current_config.auto_load_plugins
        )
        
        # Allow dev plugins
        new_allow_dev = await self.confirm_action(
            f"Allow development plugins? (current: {current_config.allow_dev_plugins})",
            current_config.allow_dev_plugins
        )
        
        # Update configuration
        self.context.config.plugins.auto_load_plugins = new_auto_load
        self.context.config.plugins.allow_dev_plugins = new_allow_dev
        
        await self._save_configuration_changes()
        
        self.display_manager.print_success("Plugin settings updated")
        return self._create_success_result("Plugin settings updated successfully")
    
    async def _reset_configuration(self) -> CommandResult:
        """Reset configuration to defaults"""
        confirmed = await self.confirm_action(
            "This will reset ALL configuration to defaults. Are you sure?",
            False
        )
        
        if not confirmed:
            return self._create_error_result("Configuration reset cancelled")
        
        try:
            # Create new default configuration
            from ..core.config import LocalAgentConfig
            
            default_config = LocalAgentConfig()
            
            # Keep the config directory
            default_config.config_dir = self.context.config.config_dir
            
            # Save default configuration
            from ..core.config import ConfigurationManager
            config_manager = ConfigurationManager()
            await config_manager.save_configuration(default_config)
            
            # Update context
            self.context.config = default_config
            
            self.display_manager.print_success("Configuration reset to defaults")
            return self._create_success_result("Configuration reset to defaults")
            
        except Exception as e:
            return self._create_error_result(f"Failed to reset configuration: {e}")
    
    async def _save_configuration_changes(self):
        """Save configuration changes to file"""
        from ..core.config import ConfigurationManager
        
        config_manager = ConfigurationManager(self.context.config.config_file)
        await config_manager.save_configuration(self.context.config)
    
    def get_help_text(self) -> str:
        """Get detailed help for config command"""
        return """
config - Manage LocalAgent configuration

USAGE:
    localagent config [OPTIONS]

OPTIONS:
    --show             Show current configuration (default)
    --validate         Validate configuration settings
    --export <file>    Export configuration to file
    --edit             Edit configuration interactively  
    --reset            Reset configuration to defaults

EXAMPLES:
    localagent config
    localagent config --validate
    localagent config --export my-config.yaml
    localagent config --edit
    localagent config --reset

CONFIGURATION SECTIONS:
    Basic Settings     Log level, debug mode
    Providers         LLM provider configurations
    Orchestration     Workflow execution settings
    MCP               Memory/Context/Protocol settings
    Plugins           Plugin system configuration

Use --edit for an interactive configuration wizard that guides
you through modifying settings step by step.
        """