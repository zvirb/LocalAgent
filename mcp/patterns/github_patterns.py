#!/usr/bin/env python3
"""
GitHub-specific MCP Patterns for repository and workflow management
"""

import asyncio
from typing import Dict, Any, List, Optional
from mcp.patterns.pattern_registry import BasePattern, PatternDefinition, PatternCategory

# ============= GitHub MCP Patterns =============

class GitHubPRWorkflowPattern(BasePattern):
    """Complete PR workflow: create branch, commit, PR, review, merge"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GitHub PR workflow"""
        from mcp.github_mcp import create_github_server
        from mcp.task_mcp import create_task_server
        
        github = await create_github_server()
        task_mcp = await create_task_server()
        
        # Create tasks for workflow
        tasks = []
        
        # Task 1: Create feature branch
        task1 = await task_mcp.create_task(
            "Create feature branch",
            f"Branch: {context.get('branch_name', 'feature/new-feature')}",
            priority="high"
        )
        tasks.append(task1)
        
        # Task 2: Make changes and commit
        task2 = await task_mcp.create_task(
            "Commit changes",
            "Implement feature and commit",
            priority="high",
            dependencies=[task1.task_id]
        )
        tasks.append(task2)
        
        # Task 3: Create PR
        pr_title = context.get('pr_title', 'New Feature Implementation')
        pr_body = context.get('pr_body', 'Implements new feature as requested')
        
        pr = await github.pr_create(
            title=pr_title,
            body=pr_body,
            base=context.get('base_branch', 'main'),
            draft=context.get('draft', False)
        )
        
        if pr:
            task3 = await task_mcp.create_task(
                f"PR #{pr.number} created",
                pr_title,
                priority="medium"
            )
            tasks.append(task3)
        
        return {
            'pattern': 'github_pr_workflow',
            'pr_created': pr is not None,
            'pr_number': pr.number if pr else None,
            'tasks_created': len(tasks),
            'workflow_status': 'initiated'
        }
    
    async def validate_prerequisites(self) -> bool:
        """Check if GitHub is authenticated"""
        try:
            from mcp.github_mcp import create_github_server
            github = await create_github_server()
            return github.authenticated
        except:
            return False

class GitHubIssueTriagePattern(BasePattern):
    """Triage and manage GitHub issues"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute issue triage pattern"""
        from mcp.github_mcp import create_github_server
        from mcp.hrm_mcp import create_hrm_server
        
        github = await create_github_server()
        hrm = await create_hrm_server()
        
        # Get open issues
        issues = await github.issue_list(
            state="open",
            limit=context.get('limit', 30),
            repo=context.get('repo')
        )
        
        triaged = {
            'bug': [],
            'enhancement': [],
            'question': [],
            'needs_info': [],
            'priority_high': [],
            'priority_low': []
        }
        
        # Use HRM to analyze and categorize issues
        for issue in issues:
            # Analyze issue with HRM
            analysis = await hrm.reason(
                f"Analyze GitHub issue: {issue.title}\nBody: {issue.body[:200] if issue.body else 'No description'}",
                {'issue_number': issue.number, 'labels': issue.labels}
            )
            
            # Categorize based on analysis
            decision = analysis.decision.lower()
            
            if 'bug' in decision or 'error' in decision or 'fix' in decision:
                triaged['bug'].append(issue.number)
                # Add bug label if not present
                if 'bug' not in issue.labels:
                    await github.issue_comment(
                        issue.number,
                        "This issue has been automatically triaged as a bug.",
                        repo=context.get('repo')
                    )
            elif 'enhancement' in decision or 'feature' in decision:
                triaged['enhancement'].append(issue.number)
            elif 'question' in decision or 'help' in decision:
                triaged['question'].append(issue.number)
            
            # Priority assessment
            if analysis.confidence > 0.8:
                triaged['priority_high'].append(issue.number)
            elif analysis.confidence < 0.5:
                triaged['priority_low'].append(issue.number)
        
        return {
            'pattern': 'github_issue_triage',
            'total_issues': len(issues),
            'triaged': triaged,
            'bugs_found': len(triaged['bug']),
            'enhancements': len(triaged['enhancement']),
            'high_priority': len(triaged['priority_high'])
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class GitHubReleasePattern(BasePattern):
    """Automated release creation and deployment"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute release pattern"""
        from mcp.github_mcp import create_github_server
        from mcp.workflow_state_mcp import create_workflow_state_server
        
        github = await create_github_server()
        workflow_state = await create_workflow_state_server()
        
        # Create workflow execution for release
        execution = await workflow_state.create_execution(
            "GitHub Release Workflow",
            context
        )
        
        # Phase 1: Prepare release
        phase1 = await workflow_state.start_phase(execution.execution_id, "prepare_release")
        
        # Get latest tag or version
        tag = context.get('tag', 'v1.0.0')
        title = context.get('title', f'Release {tag}')
        notes = context.get('notes', 'Automated release')
        
        # Phase 2: Run tests (workflow)
        if context.get('run_tests', True):
            phase2 = await workflow_state.start_phase(execution.execution_id, "run_tests")
            
            # Trigger test workflow
            test_result = await github.workflow_run(
                workflow=context.get('test_workflow', 'tests.yml'),
                ref=context.get('ref', 'main')
            )
            
            await workflow_state.complete_phase(
                execution.execution_id,
                "run_tests",
                evidence=[{'type': 'test_run', 'triggered': test_result}]
            )
        
        # Phase 3: Create release
        phase3 = await workflow_state.start_phase(execution.execution_id, "create_release")
        
        release_created = await github.release_create(
            tag=tag,
            title=title,
            notes=notes,
            draft=context.get('draft', False),
            prerelease=context.get('prerelease', False),
            repo=context.get('repo')
        )
        
        await workflow_state.complete_phase(
            execution.execution_id,
            "create_release",
            evidence=[{'type': 'release', 'created': release_created}]
        )
        
        # Phase 4: Deploy (trigger deploy workflow)
        if context.get('auto_deploy', False):
            phase4 = await workflow_state.start_phase(execution.execution_id, "deploy")
            
            deploy_result = await github.workflow_run(
                workflow=context.get('deploy_workflow', 'deploy.yml'),
                ref=tag,
                inputs={'environment': context.get('environment', 'production')}
            )
            
            await workflow_state.complete_phase(
                execution.execution_id,
                "deploy",
                evidence=[{'type': 'deployment', 'triggered': deploy_result}]
            )
        
        progress = await workflow_state.get_execution_progress(execution.execution_id)
        
        return {
            'pattern': 'github_release',
            'tag': tag,
            'release_created': release_created,
            'workflow_execution': execution.execution_id,
            'progress': progress
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class GitHubRepoSetupPattern(BasePattern):
    """Complete repository setup with best practices"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Setup new repository with all configurations"""
        from mcp.github_mcp import create_github_server
        from mcp.coordination_mcp import create_coordination_server
        
        github = await create_github_server()
        coord = await create_coordination_server()
        
        repo_name = context.get('repo_name', 'new-project')
        description = context.get('description', 'A new project')
        
        # Register setup agents
        agents = []
        for agent_type in ['repo_creator', 'branch_protector', 'webhook_setup', 'ci_setup']:
            agent = await coord.register_agent(
                f"github_{agent_type}",
                agent_type,
                capabilities=[agent_type]
            )
            agents.append(agent)
        
        # Step 1: Create repository
        repo = await github.repo_create(
            name=repo_name,
            description=description,
            private=context.get('private', False),
            auto_init=True
        )
        
        results = {'repo_created': repo is not None}
        
        if repo:
            # Step 2: Setup branch protection (would require API)
            await coord.send_message(
                "github_branch_protector",
                "github_branch_protector",
                "task_request",
                {"action": "protect_main_branch", "repo": repo_name}
            )
            results['branch_protection'] = 'initiated'
            
            # Step 3: Create initial issues
            issues_created = []
            for issue_template in context.get('initial_issues', []):
                issue = await github.issue_create(
                    title=issue_template.get('title', 'Setup Task'),
                    body=issue_template.get('body', ''),
                    labels=issue_template.get('labels', []),
                    repo=repo_name
                )
                if issue:
                    issues_created.append(issue.number)
            
            results['issues_created'] = issues_created
            
            # Step 4: Setup CI/CD workflows (create .github/workflows)
            await coord.send_message(
                "github_ci_setup",
                "github_ci_setup",
                "task_request",
                {"action": "setup_workflows", "repo": repo_name}
            )
            results['ci_setup'] = 'initiated'
            
            # Step 5: Add collaborators if specified
            for collaborator in context.get('collaborators', []):
                # Would use API to add collaborators
                await coord.send_message(
                    "github_repo_creator",
                    "github_repo_creator",
                    "task_request",
                    {"action": "add_collaborator", "user": collaborator, "repo": repo_name}
                )
            
            results['collaborators'] = context.get('collaborators', [])
        
        return {
            'pattern': 'github_repo_setup',
            'repo_name': repo_name,
            'results': results,
            'agents_used': len(agents)
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

# Register GitHub patterns
def register_github_patterns(registry):
    """Register all GitHub patterns with the registry"""
    
    patterns = [
        (PatternDefinition(
            pattern_id="github_pr_workflow",
            name="GitHub PR Workflow",
            category=PatternCategory.PIPELINE,
            description="Complete PR workflow from branch to merge",
            use_cases=["Feature development", "Code review", "Collaboration"],
            required_mcps=["github", "task"],
            docker_requirements={"memory": "256MB", "cpu": "0.25"},
            performance_profile={"latency": "medium", "throughput": "medium"}
        ), GitHubPRWorkflowPattern),
        
        (PatternDefinition(
            pattern_id="github_issue_triage",
            name="GitHub Issue Triage",
            category=PatternCategory.EVENT_DRIVEN,
            description="Automatically triage and categorize issues",
            use_cases=["Issue management", "Bug tracking", "Priority assessment"],
            required_mcps=["github", "hrm"],
            docker_requirements={"memory": "512MB", "cpu": "0.5"},
            performance_profile={"latency": "medium", "throughput": "high"}
        ), GitHubIssueTriagePattern),
        
        (PatternDefinition(
            pattern_id="github_release",
            name="GitHub Release Automation",
            category=PatternCategory.SEQUENTIAL,
            description="Automated release creation and deployment",
            use_cases=["Release management", "Deployment automation", "Version control"],
            required_mcps=["github", "workflow_state"],
            docker_requirements={"memory": "512MB", "cpu": "0.5"},
            performance_profile={"latency": "high", "throughput": "low"}
        ), GitHubReleasePattern),
        
        (PatternDefinition(
            pattern_id="github_repo_setup",
            name="GitHub Repository Setup",
            category=PatternCategory.HIERARCHICAL,
            description="Complete repository setup with best practices",
            use_cases=["Project initialization", "Repository configuration", "Team setup"],
            required_mcps=["github", "coordination"],
            docker_requirements={"memory": "512MB", "cpu": "0.5"},
            performance_profile={"latency": "medium", "throughput": "low"}
        ), GitHubRepoSetupPattern)
    ]
    
    for pattern_def, pattern_class in patterns:
        registry.register_pattern(pattern_def, pattern_class)
    
    return len(patterns)