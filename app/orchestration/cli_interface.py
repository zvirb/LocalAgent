"""
CLI Interface for LocalAgent Orchestration
Provides command-line interface for workflow execution and agent management
"""

import asyncio
import argparse
import json
import sys
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from .orchestration_integration import LocalAgentOrchestrator

class LocalAgentCLI:
    """Command-line interface for LocalAgent orchestration"""
    
    def __init__(self):
        self.orchestrator: Optional[LocalAgentOrchestrator] = None

    def _load_agents_context(self, start_path: Optional[Path] = None) -> Optional[str]:
        """Collect AGENTS.md instructions from current and parent directories."""
        start = (start_path or Path.cwd()).resolve()
        directories = list(start.parents)[::-1] + [start]
        contents: List[str] = []
        for directory in directories:
            agents_file = directory / "AGENTS.md"
            if agents_file.exists():
                try:
                    contents.append(agents_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
        if contents:
            return "\n\n".join(contents)
        return None
        
    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser"""
        parser = argparse.ArgumentParser(
            description='LocalAgent Orchestration CLI',
            epilog='Example: localagent workflow "Fix authentication system"'
        )
        
        parser.add_argument(
            '--config',
            type=str,
            help='Configuration file path'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            title='Commands',
            description='Available orchestration commands'
        )
        
        # Workflow command
        workflow_parser = subparsers.add_parser(
            'workflow',
            help='Execute 12-phase workflow'
        )
        workflow_parser.add_argument(
            'prompt',
            type=str,
            help='User prompt describing the task'
        )
        workflow_parser.add_argument(
            '--context',
            type=str,
            help='JSON context data'
        )
        workflow_parser.add_argument(
            '--workflow-id',
            type=str,
            help='Custom workflow ID'
        )
        workflow_parser.add_argument(
            '--output',
            type=str,
            help='Output file for workflow report'
        )
        
        # Single agent command
        agent_parser = subparsers.add_parser(
            'agent',
            help='Execute single agent'
        )
        agent_parser.add_argument(
            'agent_type',
            type=str,
            help='Agent type to execute'
        )
        agent_parser.add_argument(
            'prompt',
            type=str,
            help='Task prompt for the agent'
        )
        agent_parser.add_argument(
            '--context',
            type=str,
            help='JSON context data'
        )
        
        # Parallel agents command
        parallel_parser = subparsers.add_parser(
            'parallel',
            help='Execute multiple agents in parallel'
        )
        parallel_parser.add_argument(
            'config',
            type=str,
            help='YAML configuration file for parallel execution'
        )
        
        # Status command
        status_parser = subparsers.add_parser(
            'status',
            help='Get current workflow status'
        )
        
        # Health command
        health_parser = subparsers.add_parser(
            'health',
            help='System health check'
        )
        
        # List agents command
        agents_parser = subparsers.add_parser(
            'agents',
            help='List available agents'
        )
        
        # List phases command
        phases_parser = subparsers.add_parser(
            'phases',
            help='List workflow phases'
        )
        
        # Initialize command
        init_parser = subparsers.add_parser(
            'init',
            help='Initialize orchestration system'
        )
        init_parser.add_argument(
            '--provider-config',
            type=str,
            help='Provider configuration file'
        )
        
        return parser
    
    async def initialize_orchestrator(self, config_path: Optional[str] = None) -> bool:
        """Initialize the orchestrator with provider manager"""
        try:
            # Import provider manager (assuming it's available in the main app)
            from app.llm_providers.provider_manager import ProviderManager
            
            # Load provider config
            provider_config = {}
            if config_path and Path(config_path).exists():
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                    provider_config = full_config.get('providers', {})
            
            # Create provider manager
            provider_manager = ProviderManager(provider_config)
            await provider_manager.initialize_providers()
            
            # Create orchestrator
            self.orchestrator = LocalAgentOrchestrator(config_path)
            success = await self.orchestrator.initialize(provider_manager)
            
            if success:
                print("✅ LocalAgent Orchestrator initialized successfully")
                return True
            else:
                print("❌ Failed to initialize orchestrator")
                return False
                
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
    
    async def cmd_workflow(self, args) -> int:
        """Execute 12-phase workflow command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            # Parse context if provided
            context = {}
            if args.context:
                context = json.loads(args.context)

            agents_md = self._load_agents_context()
            if agents_md:
                context.setdefault('agents_md', agents_md)
            
            print(f"🚀 Starting 12-phase workflow...")
            print(f"📝 Prompt: {args.prompt}")
            
            # Execute workflow
            result = await self.orchestrator.execute_12_phase_workflow(
                user_prompt=args.prompt,
                context=context,
                workflow_id=args.workflow_id
            )
            
            # Display results
            if result['success']:
                print(f"✅ Workflow completed successfully")
                print(f"📊 Phases completed: {result['execution_summary']['completed_phases']}/{result['execution_summary']['total_phases']}")
                print(f"⏱️  Total time: {result['execution_summary']['total_execution_time']:.2f}s")
                print(f"🎯 Evidence items: {result['evidence_summary']['total_evidence_items']}")
                
                # Show phase summaries
                print("\n📋 Phase Summary:")
                for phase in result['phase_summaries']:
                    status_emoji = "✅" if phase['status'] == 'completed' else "❌" if phase['status'] == 'failed' else "⏸️"
                    print(f"  {status_emoji} {phase['phase_id']}: {phase['phase_name']} ({phase['execution_time']:.1f}s)")
                
                # Show agent performance
                if result['agent_performance']:
                    print("\n🤖 Agent Performance:")
                    for agent_name, stats in result['agent_performance'].items():
                        success_rate = (stats['successes'] / stats['executions']) * 100 if stats['executions'] > 0 else 0
                        print(f"  {agent_name}: {stats['successes']}/{stats['executions']} ({success_rate:.1f}% success)")
                
            else:
                print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
                print(f"📊 Status: {result.get('status', 'unknown')}")
            
            # Save report if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"📄 Report saved to: {args.output}")
            
            return 0 if result['success'] else 1
            
        except Exception as e:
            print(f"❌ Workflow execution error: {e}")
            return 1
    
    async def cmd_agent(self, args) -> int:
        """Execute single agent command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            # Parse context if provided
            context = {}
            if args.context:
                context = json.loads(args.context)
            agents_md = self._load_agents_context()
            if agents_md:
                context.setdefault('agents_md', agents_md)

            print(f"🤖 Executing agent: {args.agent_type}")
            print(f"📝 Prompt: {args.prompt}")
            
            # Execute agent
            result = await self.orchestrator.execute_single_agent(
                agent_type=args.agent_type,
                prompt=args.prompt,
                context=context
            )
            
            # Display results
            if result['success']:
                print(f"✅ Agent execution completed")
                print(f"⏱️  Execution time: {result['execution_time']:.2f}s")
                print(f"🔧 Provider: {result['provider_used']}")
                print(f"📊 Tokens: {result['token_usage'].get('total_tokens', 0)}")
                print(f"🎯 Evidence items: {len(result['evidence'])}")
                
                # Show content summary
                content = result['content']
                if len(content) > 500:
                    print(f"\n📄 Content (first 500 chars):\n{content[:500]}...")
                else:
                    print(f"\n📄 Content:\n{content}")
                
                # Show evidence
                if result['evidence']:
                    print(f"\n🔍 Evidence:")
                    for i, evidence in enumerate(result['evidence'][:5]):
                        print(f"  {i+1}. {evidence.get('content', str(evidence))[:100]}")
                
            else:
                print(f"❌ Agent execution failed: {result.get('error', 'Unknown error')}")
            
            return 0 if result['success'] else 1
            
        except Exception as e:
            print(f"❌ Agent execution error: {e}")
            return 1
    
    async def cmd_parallel(self, args) -> int:
        """Execute parallel agents command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            print(f"🔄 Executing parallel agents from: {args.config}")
            
            # Execute parallel agents
            result = await self.orchestrator.cmd_parallel(args.config)
            
            # Display results
            if result['success']:
                print(f"✅ Parallel execution completed")
                print(f"📊 Successful agents: {result['successful_agents']}/{result['total_agents']}")
                
                # Show individual results
                print(f"\n🤖 Agent Results:")
                for i, agent_result in enumerate(result['results']):
                    status_emoji = "✅" if agent_result['success'] else "❌"
                    print(f"  {status_emoji} {agent_result['agent_type']}: {agent_result['execution_time']:.2f}s")
                    
                    if not agent_result['success'] and agent_result.get('error'):
                        print(f"      Error: {agent_result['error']}")
            else:
                print(f"❌ Parallel execution failed: {result.get('error', 'Unknown error')}")
            
            return 0 if result['success'] else 1
            
        except Exception as e:
            print(f"❌ Parallel execution error: {e}")
            return 1
    
    async def cmd_status(self, args) -> int:
        """Get workflow status command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            status = await self.orchestrator.cmd_status()
            
            if status.get('status') == 'no_active_workflow':
                print("ℹ️  No active workflow")
            else:
                print(f"📊 Workflow Status: {status.get('status', 'unknown')}")
                print(f"🆔 Workflow ID: {status.get('workflow_id', 'unknown')}")
                print(f"📍 Current phase: {status.get('current_phase', 'unknown')}")
                print(f"✅ Completed phases: {status.get('completed_phases', 0)}/{status.get('total_phases', 0)}")
                
                if status.get('execution_time'):
                    print(f"⏱️  Running for: {status['execution_time']:.2f}s")
            
            return 0
            
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return 1
    
    async def cmd_health(self, args) -> int:
        """System health check command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            health = await self.orchestrator.cmd_health()
            
            overall_health = health.get('overall_healthy', False)
            status_emoji = "✅" if overall_health else "❌"
            print(f"{status_emoji} System Health: {'Healthy' if overall_health else 'Unhealthy'}")
            
            # Agent adapter health
            if 'agent_adapter' in health:
                adapter = health['agent_adapter']
                adapter_emoji = "✅" if adapter.get('adapter_healthy', False) else "❌"
                print(f"  {adapter_emoji} Agent Adapter: {adapter.get('agents_loaded', 0)} agents loaded")
            
            # MCP integration health
            if 'mcp_integration' in health:
                mcp = health['mcp_integration']
                mcp_emoji = "✅" if mcp.get('overall_healthy', False) else "❌"
                print(f"  {mcp_emoji} MCP Integration")
                
                if 'redis' in mcp:
                    redis = mcp['redis']
                    redis_emoji = "✅" if redis.get('healthy', False) else "❌"
                    print(f"    {redis_emoji} Redis: {redis.get('redis_version', 'unknown')}")
            
            # Provider health
            if 'providers' in health:
                print(f"  🔌 Providers:")
                for provider_name, provider_health in health['providers'].items():
                    provider_emoji = "✅" if provider_health.get('healthy', False) else "❌"
                    print(f"    {provider_emoji} {provider_name}")
            
            return 0 if overall_health else 1
            
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return 1
    
    async def cmd_agents(self, args) -> int:
        """List available agents command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            result = await self.orchestrator.cmd_agents()
            
            print(f"🤖 Available Agents ({result['total_agents']}):")
            for agent in result['agents']:
                print(f"  • {agent['name']}: {agent['description']}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error listing agents: {e}")
            return 1
    
    async def cmd_phases(self, args) -> int:
        """List workflow phases command"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized. Run 'init' command first.")
            return 1
        
        try:
            result = await self.orchestrator.cmd_phases()
            
            print(f"📋 Workflow Phases ({result['total_phases']}):")
            for phase in result['phases']:
                agents_str = ", ".join(phase['agents']) if phase['agents'] else "No agents"
                print(f"  • {phase['phase_id']}: {phase['name']}")
                print(f"    {phase['description']}")
                print(f"    Agents: {agents_str}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error listing phases: {e}")
            return 1
    
    async def cmd_init(self, args) -> int:
        """Initialize orchestrator command"""
        try:
            print("🔧 Initializing LocalAgent Orchestrator...")
            
            success = await self.initialize_orchestrator(args.provider_config)
            
            return 0 if success else 1
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return 1
    
    async def run(self, args: List[str] = None) -> int:
        """Main CLI entry point"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        if not parsed_args.command:
            parser.print_help()
            return 1
        
        # Auto-initialize for most commands
        if parsed_args.command != 'init':
            success = await self.initialize_orchestrator(parsed_args.config)
            if not success:
                return 1
        
        # Dispatch to command handlers
        command_handlers = {
            'workflow': self.cmd_workflow,
            'agent': self.cmd_agent,
            'parallel': self.cmd_parallel,
            'status': self.cmd_status,
            'health': self.cmd_health,
            'agents': self.cmd_agents,
            'phases': self.cmd_phases,
            'init': self.cmd_init
        }
        
        handler = command_handlers.get(parsed_args.command)
        if handler:
            return await handler(parsed_args)
        else:
            print(f"❌ Unknown command: {parsed_args.command}")
            return 1

# CLI entry point function
async def main(args: List[str] = None):
    """Main entry point for the CLI"""
    cli = LocalAgentCLI()
    return await cli.run(args)

# Synchronous wrapper for command-line usage
def cli_main():
    """Synchronous CLI entry point"""
    return asyncio.run(main())

if __name__ == "__main__":
    sys.exit(cli_main())