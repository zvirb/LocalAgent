#!/usr/bin/env python3
"""
GitHub MCP (Model Context Protocol) Server
Provides GitHub CLI access and repository management for agents
Designed for Docker container deployment with gh CLI
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

@dataclass
class GitHubRepository:
    """GitHub repository information"""
    owner: str
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool = False
    default_branch: str = "main"
    clone_url: Optional[str] = None
    ssh_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GitHubIssue:
    """GitHub issue representation"""
    number: int
    title: str
    state: str  # open, closed
    body: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GitHubPullRequest:
    """GitHub pull request representation"""
    number: int
    title: str
    state: str  # open, closed, merged
    base_branch: str
    head_branch: str
    body: Optional[str] = None
    draft: bool = False
    mergeable: Optional[bool] = None
    created_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class GitHubOperation(str, Enum):
    """GitHub operation types"""
    # Repository operations
    REPO_CREATE = "repo_create"
    REPO_CLONE = "repo_clone"
    REPO_FORK = "repo_fork"
    REPO_DELETE = "repo_delete"
    
    # Issue operations
    ISSUE_CREATE = "issue_create"
    ISSUE_LIST = "issue_list"
    ISSUE_VIEW = "issue_view"
    ISSUE_CLOSE = "issue_close"
    ISSUE_COMMENT = "issue_comment"
    
    # PR operations
    PR_CREATE = "pr_create"
    PR_LIST = "pr_list"
    PR_VIEW = "pr_view"
    PR_MERGE = "pr_merge"
    PR_CLOSE = "pr_close"
    PR_REVIEW = "pr_review"
    
    # Workflow operations
    WORKFLOW_LIST = "workflow_list"
    WORKFLOW_RUN = "workflow_run"
    WORKFLOW_VIEW = "workflow_view"
    
    # Release operations
    RELEASE_CREATE = "release_create"
    RELEASE_LIST = "release_list"
    
    # Gist operations
    GIST_CREATE = "gist_create"
    GIST_LIST = "gist_list"

class GitHubMCP:
    """
    GitHub MCP Server - Provides GitHub CLI access for agents
    Wraps gh CLI commands with safety checks and structured outputs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.authenticated = False
        self.current_repo: Optional[GitHubRepository] = None
        self.command_history: List[Dict[str, Any]] = []
        self.state_file = Path(self.config.get('state_file', '.github_mcp_state.json'))
        
        # Safety settings
        self.allow_destructive = self.config.get('allow_destructive', False)
        self.require_confirmation = self.config.get('require_confirmation', True)
        self.max_command_length = self.config.get('max_command_length', 1000)
        
        # CLI path (will be set during initialization)
        self.cli_path = self.config.get('cli_path', 'gh')
        
    async def initialize(self):
        """Initialize GitHub MCP server and check authentication"""
        self.logger.info("Initializing GitHub MCP Server")
        
        # Check if gh CLI is available
        if not await self._check_gh_cli():
            raise RuntimeError("GitHub CLI (gh) not found. Please install: https://cli.github.com/")
        
        # Check authentication status
        self.authenticated = await self._check_authentication()
        if not self.authenticated:
            self.logger.warning("GitHub CLI not authenticated. Run: gh auth login")
        else:
            self.logger.info("GitHub CLI authenticated successfully")
        
        # Load saved state
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.command_history = state.get('history', [])[-100:]  # Keep last 100
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
        
        return True
    
    async def _check_gh_cli(self) -> bool:
        """Check if gh CLI is installed"""
        try:
            # Check if gh CLI is available using which/where
            import shutil
            gh_path = shutil.which('gh')
            
            if not gh_path:
                return False
                
            # Store the full path for later use
            self.cli_path = gh_path
            
            # Test the CLI
            result = await self._run_command([gh_path, "--version"])
            return result[0] if result else False
        except Exception as e:
            self.logger.warning(f"Failed to check gh CLI: {e}")
            return False
    
    async def _check_authentication(self) -> bool:
        """Check if gh CLI is authenticated"""
        try:
            result = await self._run_command([self.cli_path, "auth", "status"])
            return result[0] if result else False
        except:
            return False
    
    async def check_auth(self) -> Dict[str, Any]:
        """
        Get detailed authentication status for agents/CLI
        Returns authentication information including username and scopes
        """
        try:
            # Check basic auth status
            success, stdout, stderr = await self._run_command([self.cli_path, "auth", "status", "--show-token"])
            
            if not success:
                return {
                    'authenticated': False,
                    'error': stderr or 'Not authenticated',
                    'username': None,
                    'scopes': []
                }
            
            # Parse the output to extract user info
            lines = stdout.split('\n')
            username = None
            scopes = []
            
            for line in lines:
                if 'account' in line.lower() and '(' not in line:
                    # Extract username from line like "✓ Logged in to github.com account username (keyring)"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'account' and i + 1 < len(parts):
                            username = parts[i + 1]
                            break
                elif 'token scopes:' in line.lower():
                    # Extract scopes from line like "- Token scopes: 'repo', 'workflow', 'gist'"
                    scope_part = line.split('scopes:')[-1].strip()
                    # Parse quoted scopes
                    import re
                    scopes = re.findall(r"'([^']*)'", scope_part)
            
            return {
                'authenticated': True,
                'username': username,
                'scopes': scopes,
                'raw_output': stdout
            }
            
        except Exception as e:
            return {
                'authenticated': False,
                'error': str(e),
                'username': None,
                'scopes': []
            }
    
    async def _run_command(
        self, 
        command: List[str], 
        timeout: int = 30,
        check: bool = True
    ) -> Tuple[bool, str, str]:
        """
        Run a gh CLI command safely
        Returns: (success, stdout, stderr)
        """
        # Safety check
        command_str = ' '.join(command)
        if len(command_str) > self.max_command_length:
            return False, "", "Command too long"
        
        # Record command
        self._record_command(command_str)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Use wait_for for timeout instead
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            success = process.returncode == 0 if check else True
            return success, stdout.decode(), stderr.decode()
            
        except asyncio.TimeoutError:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def _record_command(self, command: str):
        """Record command in history"""
        self.command_history.append({
            'command': command,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 100 commands
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]
    
    # Repository Operations
    
    async def repo_create(
        self, 
        name: str, 
        description: str = "",
        private: bool = False,
        auto_init: bool = True
    ) -> Optional[GitHubRepository]:
        """Create a new GitHub repository"""
        if not self.authenticated:
            self.logger.error("Not authenticated")
            return None
        
        cmd = [self.cli_path, "repo", "create", name]
        
        if description:
            cmd.extend(["--description", description])
        
        if private:
            cmd.append("--private")
        else:
            cmd.append("--public")
        
        if auto_init:
            cmd.append("--add-readme")
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            # Parse repository info
            repo = GitHubRepository(
                owner="",  # Will be filled from API
                name=name,
                full_name=name,
                description=description,
                private=private,
                default_branch="main"
            )
            self.current_repo = repo
            self.logger.info(f"Created repository: {name}")
            return repo
        else:
            self.logger.error(f"Failed to create repository: {stderr}")
            return None
    
    async def repo_clone(self, repo_name: str, path: Optional[str] = None) -> bool:
        """Clone a GitHub repository"""
        cmd = [self.cli_path, "repo", "clone", repo_name]
        
        if path:
            cmd.append(path)
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Cloned repository: {repo_name}")
            return True
        else:
            self.logger.error(f"Failed to clone repository: {stderr}")
            return False
    
    async def repo_fork(self, repo_name: str, clone: bool = True) -> bool:
        """Fork a GitHub repository"""
        cmd = [self.cli_path, "repo", "fork", repo_name]
        
        if clone:
            cmd.append("--clone")
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Forked repository: {repo_name}")
            return True
        else:
            self.logger.error(f"Failed to fork repository: {stderr}")
            return False
    
    async def repo_list(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List user's repositories"""
        cmd = [self.cli_path, "repo", "list", "--limit", str(limit), "--json", 
               "name,description,isPrivate,defaultBranchRef,createdAt,updatedAt"]
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                repos = json.loads(stdout)
                return repos
            except json.JSONDecodeError:
                return []
        return []
    
    # Issue Operations
    
    async def issue_create(
        self,
        title: str,
        body: str = "",
        labels: List[str] = None,
        assignees: List[str] = None,
        repo: Optional[str] = None
    ) -> Optional[GitHubIssue]:
        """Create a new issue"""
        cmd = [self.cli_path, "issue", "create", "--title", title]
        
        if body:
            cmd.extend(["--body", body])
        
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        
        if assignees:
            cmd.extend(["--assignee", ",".join(assignees)])
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            # Extract issue number from output
            import re
            match = re.search(r'#(\d+)', stdout)
            if match:
                issue_num = int(match.group(1))
                issue = GitHubIssue(
                    number=issue_num,
                    title=title,
                    state="open",
                    body=body,
                    labels=labels or [],
                    assignees=assignees or []
                )
                self.logger.info(f"Created issue #{issue_num}: {title}")
                return issue
        
        self.logger.error(f"Failed to create issue: {stderr}")
        return None
    
    async def issue_list(
        self,
        state: str = "open",
        limit: int = 30,
        labels: List[str] = None,
        assignee: Optional[str] = None,
        repo: Optional[str] = None
    ) -> List[GitHubIssue]:
        """List issues"""
        cmd = [self.cli_path, "issue", "list", "--state", state, "--limit", str(limit),
               "--json", "number,title,state,body,labels,assignees,createdAt,updatedAt"]
        
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        
        if assignee:
            cmd.extend(["--assignee", assignee])
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                issues_data = json.loads(stdout)
                issues = []
                for data in issues_data:
                    issue = GitHubIssue(
                        number=data['number'],
                        title=data['title'],
                        state=data['state'],
                        body=data.get('body', ''),
                        labels=[l['name'] for l in data.get('labels', [])],
                        assignees=[a['login'] for a in data.get('assignees', [])]
                    )
                    issues.append(issue)
                return issues
            except (json.JSONDecodeError, KeyError):
                return []
        return []
    
    async def issue_close(self, issue_number: int, repo: Optional[str] = None) -> bool:
        """Close an issue"""
        cmd = [self.cli_path, "issue", "close", str(issue_number)]
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Closed issue #{issue_number}")
            return True
        else:
            self.logger.error(f"Failed to close issue: {stderr}")
            return False
    
    async def issue_comment(
        self, 
        issue_number: int, 
        comment: str,
        repo: Optional[str] = None
    ) -> bool:
        """Add a comment to an issue"""
        cmd = [self.cli_path, "issue", "comment", str(issue_number), "--body", comment]
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Added comment to issue #{issue_number}")
            return True
        else:
            self.logger.error(f"Failed to add comment: {stderr}")
            return False
    
    # Pull Request Operations
    
    async def pr_create(
        self,
        title: str,
        body: str = "",
        base: str = "main",
        head: Optional[str] = None,
        draft: bool = False,
        repo: Optional[str] = None
    ) -> Optional[GitHubPullRequest]:
        """Create a pull request"""
        cmd = [self.cli_path, "pr", "create", "--title", title, "--base", base]
        
        if body:
            cmd.extend(["--body", body])
        
        if head:
            cmd.extend(["--head", head])
        
        if draft:
            cmd.append("--draft")
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            # Extract PR number from output
            import re
            match = re.search(r'#(\d+)', stdout)
            if match:
                pr_num = int(match.group(1))
                pr = GitHubPullRequest(
                    number=pr_num,
                    title=title,
                    state="open",
                    base_branch=base,
                    head_branch=head or "",
                    body=body,
                    draft=draft
                )
                self.logger.info(f"Created PR #{pr_num}: {title}")
                return pr
        
        self.logger.error(f"Failed to create PR: {stderr}")
        return None
    
    async def pr_list(
        self,
        state: str = "open",
        limit: int = 30,
        base: Optional[str] = None,
        repo: Optional[str] = None
    ) -> List[GitHubPullRequest]:
        """List pull requests"""
        cmd = [self.cli_path, "pr", "list", "--state", state, "--limit", str(limit),
               "--json", "number,title,state,baseRefName,headRefName,body,isDraft,createdAt"]
        
        if base:
            cmd.extend(["--base", base])
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                prs_data = json.loads(stdout)
                prs = []
                for data in prs_data:
                    pr = GitHubPullRequest(
                        number=data['number'],
                        title=data['title'],
                        state=data['state'],
                        base_branch=data['baseRefName'],
                        head_branch=data['headRefName'],
                        body=data.get('body', ''),
                        draft=data.get('isDraft', False)
                    )
                    prs.append(pr)
                return prs
            except (json.JSONDecodeError, KeyError):
                return []
        return []
    
    async def pr_merge(
        self,
        pr_number: int,
        merge_method: str = "merge",  # merge, squash, rebase
        delete_branch: bool = True,
        repo: Optional[str] = None
    ) -> bool:
        """Merge a pull request"""
        if not self.allow_destructive and self.require_confirmation:
            self.logger.warning("Merge operation requires confirmation")
            return False
        
        cmd = [self.cli_path, "pr", "merge", str(pr_number), f"--{merge_method}"]
        
        if delete_branch:
            cmd.append("--delete-branch")
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Merged PR #{pr_number}")
            return True
        else:
            self.logger.error(f"Failed to merge PR: {stderr}")
            return False
    
    async def pr_review(
        self,
        pr_number: int,
        action: str = "approve",  # approve, comment, request-changes
        body: str = "",
        repo: Optional[str] = None
    ) -> bool:
        """Review a pull request"""
        cmd = [self.cli_path, "pr", "review", str(pr_number), f"--{action}"]
        
        if body:
            cmd.extend(["--body", body])
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Reviewed PR #{pr_number}: {action}")
            return True
        else:
            self.logger.error(f"Failed to review PR: {stderr}")
            return False
    
    # Workflow Operations
    
    async def workflow_list(self, repo: Optional[str] = None) -> List[Dict[str, Any]]:
        """List GitHub Actions workflows"""
        cmd = [self.cli_path, "workflow", "list", "--json", "name,state,id"]
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                workflows = json.loads(stdout)
                return workflows
            except json.JSONDecodeError:
                return []
        return []
    
    async def workflow_run(
        self,
        workflow: str,
        ref: str = "main",
        inputs: Dict[str, str] = None,
        repo: Optional[str] = None
    ) -> bool:
        """Trigger a workflow run"""
        cmd = [self.cli_path, "workflow", "run", workflow, "--ref", ref]
        
        if inputs:
            for key, value in inputs.items():
                cmd.extend([f"--field", f"{key}={value}"])
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Triggered workflow: {workflow}")
            return True
        else:
            self.logger.error(f"Failed to trigger workflow: {stderr}")
            return False
    
    async def workflow_view(
        self,
        run_id: Optional[int] = None,
        repo: Optional[str] = None
    ) -> Dict[str, Any]:
        """View workflow run details"""
        cmd = [self.cli_path, "run", "view"]
        
        if run_id:
            cmd.append(str(run_id))
        
        cmd.extend(["--json", "status,conclusion,name,displayTitle,workflowName"])
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {}
        return {}
    
    # Release Operations
    
    async def release_create(
        self,
        tag: str,
        title: str = "",
        notes: str = "",
        draft: bool = False,
        prerelease: bool = False,
        repo: Optional[str] = None
    ) -> bool:
        """Create a release"""
        cmd = [self.cli_path, "release", "create", tag]
        
        if title:
            cmd.extend(["--title", title])
        
        if notes:
            cmd.extend(["--notes", notes])
        
        if draft:
            cmd.append("--draft")
        
        if prerelease:
            cmd.append("--prerelease")
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            self.logger.info(f"Created release: {tag}")
            return True
        else:
            self.logger.error(f"Failed to create release: {stderr}")
            return False
    
    async def release_list(
        self,
        limit: int = 10,
        repo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List releases"""
        cmd = [self.cli_path, "release", "list", "--limit", str(limit),
               "--json", "tagName,name,publishedAt,isDraft,isPrerelease"]
        
        if repo:
            cmd.extend(["--repo", repo])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return []
        return []
    
    # Gist Operations
    
    async def gist_create(
        self,
        files: List[str],
        description: str = "",
        public: bool = True
    ) -> Optional[str]:
        """Create a gist"""
        cmd = [self.cli_path, "gist", "create"]
        
        cmd.extend(files)
        
        if description:
            cmd.extend(["--desc", description])
        
        if public:
            cmd.append("--public")
        else:
            cmd.append("--private")
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            # Extract gist URL from output
            if "https://gist.github.com" in stdout:
                url = stdout.strip()
                self.logger.info(f"Created gist: {url}")
                return url
        
        self.logger.error(f"Failed to create gist: {stderr}")
        return None
    
    async def gist_list(self, limit: int = 30, public: bool = True) -> List[Dict[str, Any]]:
        """List gists"""
        cmd = [self.cli_path, "gist", "list", "--limit", str(limit)]
        
        if public:
            cmd.append("--public")
        else:
            cmd.append("--secret")
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            # Parse the text output (gh gist list doesn't support JSON)
            gists = []
            for line in stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        gists.append({
                            'id': parts[0],
                            'description': parts[1] if len(parts) > 1 else '',
                            'files': parts[2] if len(parts) > 2 else '',
                            'visibility': 'public' if public else 'secret'
                        })
            return gists
        return []
    
    # Utility Operations
    
    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user info"""
        cmd = [self.cli_path, "api", "user"]
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return None
        return None
    
    async def search_repos(
        self,
        query: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Search for repositories"""
        cmd = [self.cli_path, "search", "repos", query, "--limit", str(limit),
               "--json", "fullName,description,isPrivate,stargazersCount,updatedAt"]
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return []
        return []
    
    async def search_issues(
        self,
        query: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Search for issues"""
        cmd = [self.cli_path, "search", "issues", query, "--limit", str(limit),
               "--json", "repository,number,title,state,createdAt"]
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return []
        return []
    
    async def run_api_command(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Run arbitrary GitHub API command (with safety checks)"""
        if not self.authenticated:
            self.logger.error("Not authenticated")
            return None
        
        # Safety check for destructive operations
        if method in ["DELETE", "PUT", "POST", "PATCH"] and not self.allow_destructive:
            self.logger.warning(f"Destructive operation {method} blocked")
            return None
        
        cmd = [self.cli_path, "api", endpoint, "--method", method]
        
        if data:
            cmd.extend(["--field", json.dumps(data)])
        
        success, stdout, stderr = await self._run_command(cmd)
        
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {'response': stdout}
        else:
            self.logger.error(f"API call failed: {stderr}")
            return None
    
    async def get_command_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get command execution history"""
        return self.command_history[-limit:]
    
    async def save_state(self):
        """Save current state to disk"""
        try:
            state = {
                'history': self.command_history[-100:],
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info(f"Saved GitHub MCP state to {self.state_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False

# Convenience function for standalone usage
async def create_github_server(config: Dict[str, Any] = None):
    """Create and initialize a GitHub MCP server"""
    server = GitHubMCP(config)
    await server.initialize()
    return server

if __name__ == "__main__":
    # Test the GitHub MCP
    async def test():
        github = await create_github_server()
        
        if github.authenticated:
            print("✓ GitHub CLI authenticated")
            
            # Get current user
            user = await github.get_current_user()
            if user:
                print(f"✓ Logged in as: {user.get('login')}")
            
            # List repositories
            repos = await github.repo_list(limit=5)
            print(f"✓ Found {len(repos)} repositories")
            
            # List issues
            issues = await github.issue_list(limit=5)
            print(f"✓ Found {len(issues)} open issues")
            
            # Get command history
            history = await github.get_command_history(limit=5)
            print(f"✓ Executed {len(history)} commands")
            
            await github.save_state()
        else:
            print("✗ Not authenticated. Run: gh auth login")
    
    asyncio.run(test())