# GitHub MCP Integration Guide

## Overview

The GitHub MCP (Model Context Protocol) provides comprehensive GitHub CLI access for LocalAgent and its autonomous agents. This enables secure repository management, issue tracking, pull request workflows, and automation through GitHub's official CLI tool (`gh`).

## Features

### 🏗️ **Core Capabilities**
- **Repository Management**: Create, clone, fork, and list repositories
- **Issue Management**: Create, list, close, and comment on issues
- **Pull Request Workflow**: Create, list, merge, and review pull requests
- **GitHub Actions**: List and trigger workflow runs
- **Releases**: Create and manage releases
- **Gists**: Create and manage code snippets
- **Search**: Search repositories and issues across GitHub
- **Authentication**: Check and manage GitHub CLI authentication

### 🔒 **Security Features**
- **Safe Command Execution**: All commands are validated and logged
- **Path Resolution**: Automatic detection of `gh` CLI installation
- **Command Length Limits**: Prevents command injection attacks
- **Authentication Validation**: Ensures proper GitHub access before operations
- **Error Handling**: Comprehensive error handling and logging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Enhanced CLI Interface                     │
│              (localagent_interactive_enhanced.py)          │
└────────────────────────┬───────────────────────────────────┘
                         │ GitHub Commands (gh *)
┌────────────────────────▼───────────────────────────────────┐
│                   GitHub MCP Server                        │
│                  (mcp/github_mcp.py)                       │
│  ┌─────────────────┬─────────────────┬─────────────────┐  │
│  │   Repository    │   Issue & PR    │   Workflow &    │  │
│  │   Management    │   Management    │   Release Mgmt  │  │
│  └─────────────────┴─────────────────┴─────────────────┘  │
└────────────────────────┬───────────────────────────────────┘
                         │ Safe gh CLI Execution
┌────────────────────────▼───────────────────────────────────┐
│              GitHub CLI (gh) - System Level                │
│              Authenticated with GitHub.com                 │
└─────────────────────────────────────────────────────────────┘
```

## Installation & Setup

### Prerequisites

1. **GitHub CLI Installation**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update && sudo apt install gh
   
   # Or download from: https://cli.github.com/
   ```

2. **GitHub Authentication**
   ```bash
   gh auth login
   # Follow the interactive authentication process
   # Choose HTTPS or SSH, and authenticate via web browser
   ```

3. **Verify Installation**
   ```bash
   gh auth status
   # Should show authenticated status with your username
   ```

## CLI Usage

### Available Commands

```bash
# Authentication Management
gh auth status              # Check authentication status

# Repository Operations
gh repo list               # List your repositories (latest 10)
gh repo create <name>      # Create new repository

# Issue Management
gh issue list              # List open issues (latest 10)
gh issue create <title>    # Create new issue (interactive)

# Pull Request Management
gh pr list                 # List open pull requests (latest 10)
gh pr create               # Create new pull request (interactive)
```

### Command Examples

```bash
# Initialize LocalAgent with GitHub features
clix
> init

# Check GitHub authentication
> gh auth status
✓ Authenticated as: your-username
Token valid for: ['repo', 'workflow', 'gist']

# List your repositories
> gh repo list
┌─────────────────────┬──────────────────────┬─────────┬───────┐
│ Name                │ Description          │ Private │ Stars │
├─────────────────────┼──────────────────────┼─────────┼───────┤
│ my-awesome-project  │ An awesome project   │ No      │ 42    │
│ secret-work        │ Private work repo     │ Yes     │ 0     │
└─────────────────────┴──────────────────────┴─────────┴───────┘

# Create a new repository
> gh repo create my-new-project
Creating repository: my-new-project
✓ Repository 'my-new-project' created successfully!
URL: https://github.com/username/my-new-project

# List and create issues
> gh issue list
┌────────┬─────────────────────────────────┬───────┬──────────────┐
│ Number │ Title                           │ State │ Labels       │
├────────┼─────────────────────────────────┼───────┼──────────────┤
│ 15     │ Fix authentication bug          │ open  │ bug, urgent  │
│ 14     │ Add dark mode support           │ open  │ enhancement  │
└────────┴─────────────────────────────────┴───────┴──────────────┘

> gh issue create Add new feature
Issue description (optional): Implement user dashboard
Labels (comma-separated, optional): feature, ui
Creating issue: Add new feature
✓ Issue #16 created successfully!
URL: https://github.com/username/repo/issues/16
```

## Pattern System Integration

The GitHub MCP integrates with LocalAgent's pattern system providing 4 pre-built GitHub workflow patterns:

### 1. **GitHub PR Workflow Pattern** (`github_pr_workflow`)
**Purpose**: Complete pull request workflow from branch creation to merge

**Capabilities**:
- Creates feature branches automatically
- Commits changes with proper messages
- Creates pull requests with descriptions
- Integrates with task management system

**Use Cases**:
- Feature development workflows
- Code review processes
- Team collaboration automation

### 2. **GitHub Issue Triage Pattern** (`github_issue_triage`)
**Purpose**: Automated issue categorization and management

**Capabilities**:
- Uses HRM (Hierarchical Reasoning Model) for intelligent categorization
- Automatically labels issues (bug, enhancement, question)
- Assesses priority levels based on content analysis
- Adds automated triage comments

**Use Cases**:
- Repository maintenance
- Large-scale issue management
- Community project automation

### 3. **GitHub Release Pattern** (`github_release`)
**Purpose**: Automated release creation and deployment

**Capabilities**:
- Creates releases with proper versioning
- Triggers test workflows before release
- Generates release notes automatically
- Integrates with deployment workflows
- Tracks workflow state through phases

**Use Cases**:
- Continuous deployment pipelines
- Version management
- Release automation

### 4. **GitHub Repository Setup Pattern** (`github_repo_setup`)
**Purpose**: Complete repository initialization with best practices

**Capabilities**:
- Creates repositories with proper configuration
- Sets up branch protection rules
- Creates initial issues and templates
- Configures CI/CD workflows
- Adds collaborators and permissions

**Use Cases**:
- Project initialization
- Repository standardization
- Team onboarding

### Pattern Usage Examples

```bash
# Get pattern recommendations
> pattern recommend "Create pull request for bug fix"
Recommended Pattern: github_pr_workflow (confidence: 87%)
Reasoning: PR workflow pattern optimal for branch-based development

# Execute specific pattern
> pattern execute github_pr_workflow
Executing pattern: GitHub PR Workflow
Context required:
- branch_name: feature/auth-fix
- pr_title: Fix authentication bug
- pr_body: Resolves issue with JWT token validation
✓ Pattern execution complete

# Auto-select and execute optimal pattern
> pattern recommend "Setup new project repository with CI/CD"
Recommended Pattern: github_repo_setup (confidence: 92%)
Reasoning: Repository setup pattern includes CI/CD configuration
```

## Agent Access

Autonomous agents can access GitHub functionality through the MCP interface:

### Python Agent Integration

```python
# Agent code example
async def agent_create_release():
    """Agent creates a release automatically"""
    from mcp.github_mcp import create_github_server
    
    # Initialize GitHub MCP
    github = await create_github_server({'cli_path': 'gh'})
    
    # Check authentication
    auth_status = await github.check_auth()
    if not auth_status.get('authenticated', False):
        return {'error': 'GitHub authentication required'}
    
    # Create release
    release = await github.release_create(
        tag='v1.2.0',
        title='Release v1.2.0',
        notes='Bug fixes and performance improvements',
        draft=False,
        prerelease=False
    )
    
    return {'success': True, 'release_url': release.html_url if release else None}
```

### Pattern-Based Agent Workflow

```python
# Using intelligent pattern selection
async def agent_handle_issue_workflow():
    """Agent automatically handles issue triage and PR creation"""
    from mcp.patterns import intelligent_selector, PatternSelectionContext
    
    # Create context for issue handling
    context = PatternSelectionContext(
        query="Analyze open issues and create pull requests for bugs",
        performance_requirements={"latency": "medium", "throughput": "high"},
        available_mcps=["github", "hrm", "task"]
    )
    
    # Get pattern recommendation
    recommendation = await intelligent_selector.select_pattern(context)
    
    if recommendation.pattern_id == "github_issue_triage":
        # Execute triage pattern
        result = await execute_pattern("github_issue_triage", {
            'limit': 30,
            'auto_label': True,
            'create_tasks': True
        })
        return result
```

## Security & Best Practices

### 🔒 **Security Considerations**

1. **Authentication**: Always verify GitHub authentication before operations
2. **Command Validation**: All commands are validated and length-limited
3. **Safe Execution**: Commands run through secure subprocess execution
4. **Audit Trail**: All operations are logged with timestamps
5. **Error Handling**: Comprehensive error handling prevents information leakage

### 📋 **Best Practices**

1. **Repository Management**:
   - Use descriptive repository names and descriptions
   - Set appropriate privacy levels
   - Configure branch protection for main branches

2. **Issue Management**:
   - Use clear, actionable issue titles
   - Apply relevant labels for better organization
   - Include detailed descriptions for complex issues

3. **Pull Request Workflow**:
   - Create feature branches for all changes
   - Write descriptive commit messages
   - Include PR descriptions explaining changes
   - Request appropriate reviewers

4. **Release Management**:
   - Follow semantic versioning (v1.2.3)
   - Include comprehensive release notes
   - Test thoroughly before releases
   - Tag releases consistently

### 🚨 **Error Handling**

Common error scenarios and solutions:

```bash
# Authentication Issues
Error: Not authenticated with GitHub
Solution: Run 'gh auth login' to authenticate

# Permission Issues  
Error: Resource not accessible
Solution: Check repository permissions or organization access

# Network Issues
Error: Request timeout
Solution: Check internet connection and GitHub status

# Command Issues
Error: Invalid command syntax
Solution: Check command format and required parameters
```

## Configuration

### GitHub MCP Configuration

```json
{
  "cli_path": "gh",                    // Path to gh CLI (auto-detected)
  "allow_destructive": false,          // Allow destructive operations
  "require_confirmation": true,        // Require confirmation for sensitive operations
  "max_command_length": 1000,         // Maximum command length for security
  "state_file": ".github_mcp_state.json"  // State persistence file
}
```

### Integration with Docker

For containerized deployment:

```yaml
# docker-compose.yml additions
services:
  localagent:
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}  # Optional: set token directly
    volumes:
      - ~/.gitconfig:/root/.gitconfig:ro  # Git configuration
      - ~/.config/gh:/root/.config/gh:ro  # GitHub CLI authentication
```

## Monitoring & Debugging

### Command History

All GitHub operations are logged and can be reviewed:

```python
# Access command history
github_mcp.command_history
# Returns list of executed commands with timestamps
```

### State Persistence

The MCP maintains state in `.github_mcp_state.json`:
- Command history (last 100 commands)
- Authentication status cache
- Configuration settings

### Logging

Enable detailed logging for debugging:

```python
import logging
logging.getLogger('mcp.github_mcp').setLevel(logging.DEBUG)
```

## Integration Examples

### Automated Issue-to-PR Workflow

```python
async def auto_issue_to_pr(issue_number: int):
    """Automatically create PR from issue"""
    # Get issue details
    issues = await github.issue_list(state="open")
    issue = next((i for i in issues if i.number == issue_number), None)
    
    if issue and 'bug' in issue.labels:
        # Create PR using pattern
        result = await execute_pattern("github_pr_workflow", {
            'branch_name': f'fix/issue-{issue_number}',
            'pr_title': f'Fix: {issue.title}',
            'pr_body': f'Closes #{issue_number}\n\n{issue.body}'
        })
        return result
```

### Release Automation

```python
async def automated_release_workflow():
    """Complete release workflow with testing"""
    result = await execute_pattern("github_release", {
        'tag': 'v1.3.0',
        'title': 'LocalAgent v1.3.0',
        'notes': 'GitHub MCP integration and pattern system',
        'run_tests': True,
        'test_workflow': 'ci.yml',
        'auto_deploy': True,
        'deploy_workflow': 'deploy.yml',
        'environment': 'production'
    })
    return result
```

## Troubleshooting

### Common Issues

1. **GitHub CLI Not Found**
   - Install GitHub CLI: https://cli.github.com/
   - Ensure `gh` is in PATH
   - Verify installation: `gh --version`

2. **Authentication Failed**
   - Run: `gh auth login`
   - Check token scopes: `gh auth status`
   - Ensure required permissions (repo, workflow, etc.)

3. **Repository Access Denied**
   - Check repository exists and is accessible
   - Verify organization permissions
   - Ensure correct repository name format (owner/repo)

4. **Pattern Execution Failed**
   - Check all required MCPs are available
   - Verify Docker resource constraints
   - Review pattern prerequisites

### Support & Resources

- **GitHub CLI Documentation**: https://cli.github.com/manual/
- **GitHub API Documentation**: https://docs.github.com/en/rest
- **LocalAgent Patterns**: See `docs/MCP_PATTERN_SYSTEM_GUIDE.md`
- **Issue Reporting**: Create issue in LocalAgent repository

## Conclusion

The GitHub MCP provides comprehensive GitHub integration for LocalAgent, enabling:
- ✅ **Secure** repository and workflow management
- ✅ **Intelligent** pattern-based automation
- ✅ **Scalable** agent-driven operations
- ✅ **Flexible** CLI and programmatic access
- ✅ **Robust** error handling and logging

This integration transforms LocalAgent into a powerful GitHub automation platform, suitable for individual developers, teams, and large-scale repository management.