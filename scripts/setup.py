"""
LocalAgent CLI Setup Configuration
Modern CLI toolkit with plugin support
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
project_root = this_directory.parent
long_description = (project_root / "README.md").read_text()

# Read requirements
requirements = []
requirements_path = project_root / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="localagent-cli",
    version="2.0.0",
    description="Modern multi-provider LLM orchestration CLI with plugin architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LocalAgent Team",
    author_email="team@localagent.dev",
    url="https://github.com/localagent/localagent-cli",
    
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    
    # Entry points for CLI commands and plugins
    entry_points={
        "console_scripts": [
            "localagent=app.cli.core.app:main",
            "la=app.cli.core.app:main",  # Short alias
            "localagent-dev=app.cli.core.app:main",  # Development alias
            "cli=scripts.localagent_interactive_simple:interactive_simple",  # Working interactive chat
            "clix=scripts.localagent_interactive_enhanced:interactive_enhanced",  # Enhanced full CLI with all features
        ],
        
        # Built-in command plugins
        "localagent.plugins.commands": [
            "system-info=app.cli.plugins.builtin.builtin_plugins:SystemInfoPlugin",
            "config-manager=app.cli.plugins.builtin.builtin_plugins:ConfigurationPlugin",
        ],
        
        # Built-in provider plugins
        "localagent.plugins.providers": [
            "ollama=app.llm_providers.ollama_provider:OllamaProvider",
            "openai=app.llm_providers.openai_provider:OpenAIProvider",
            "gemini=app.llm_providers.gemini_provider:GeminiProvider",
            "perplexity=app.llm_providers.perplexity_provider:PerplexityProvider",
        ],
        
        # Built-in UI plugins
        "localagent.plugins.ui": [
            "display-manager=app.cli.ui.display:create_display_manager",
            "progress-manager=app.cli.ui.display:WorkflowProgressManager",
        ],
        
        # Built-in workflow plugins
        "localagent.plugins.workflow": [
            "workflow-debug=app.cli.plugins.builtin.builtin_plugins:WorkflowDebugPlugin",
            "orchestration-bridge=app.cli.integration.enhanced_orchestration_bridge:EnhancedOrchestrationBridge",
        ],
        
        # Built-in tools plugins
        "localagent.plugins.tools": [
            "command-registry=app.cli.core.enhanced_command_registration:EnhancedCommandRegistry",
            "provider-integration=app.cli.integration.enhanced_provider_integration:EnhancedProviderIntegration",
        ],
        
        # Built-in integration plugins
        "localagent.plugins.integrations": [
            "mcp-memory=app.orchestration.mcp_integration:MCPIntegration",
            "workflow-engine=app.orchestration.workflow_engine:WorkflowEngine",
        ],
    },
    
    # Package data
    include_package_data=True,
    package_data={
        "app.cli": [
            "templates/*.yaml",
            "templates/*.json",
            "config/*.yaml",
            "plugins/builtin/*.py",
        ],
        "app": [
            "orchestration/*.yaml",
            "orchestration/agents/*.yaml",
        ],
        "workflows": [
            "*.yaml",
        ],
        "templates": [
            "*.yaml",
        ],
    },
    
    # Manifest file support
    zip_safe=False,
    
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Framework :: FastAPI",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    
    # Keywords
    keywords=[
        "cli", "llm", "ai", "orchestration", "typer", "rich", 
        "plugin", "automation", "workflow", "ollama", "openai",
        "gemini", "perplexity", "multi-provider"
    ],
    
    # Extra dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-typer>=0.0.14",
            "black>=23.0.0",
            "pylint>=3.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocs-typer>=0.0.3",
        ],
        "monitoring": [
            "prometheus-client>=0.18.0",
            "grafana-api>=1.0.3",
        ],
        "all": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0", 
            "pytest-typer>=0.0.14",
            "black>=23.0.0",
            "pylint>=3.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.0.0",
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocs-typer>=0.0.3",
            "prometheus-client>=0.18.0",
            "grafana-api>=1.0.3",
        ]
    },
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/localagent/localagent-cli/issues",
        "Source": "https://github.com/localagent/localagent-cli",
        "Documentation": "https://localagent.readthedocs.io",
        "Changelog": "https://github.com/localagent/localagent-cli/blob/main/CHANGELOG.md",
    },
)