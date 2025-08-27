#!/usr/bin/env python3
"""
HRM MCP (Hierarchical Reasoning Model) Server
Independent implementation for LocalAgent project
Provides hierarchical reasoning, decision-making, and context management
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import yaml

@dataclass
class ReasoningNode:
    """A node in the hierarchical reasoning tree"""
    node_id: str
    level: int  # 0=root, 1=strategic, 2=tactical, 3=operational
    decision: str
    confidence: float
    evidence: List[str]
    children: List['ReasoningNode'] = None
    parent_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

class HRM_MCP:
    """
    Hierarchical Reasoning Model MCP Server
    Provides multi-level reasoning and decision-making capabilities
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.reasoning_tree: Dict[str, ReasoningNode] = {}
        self.decision_history: List[Dict[str, Any]] = []
        self.context_layers: Dict[int, Dict[str, Any]] = {
            0: {},  # Strategic layer
            1: {},  # Tactical layer  
            2: {},  # Operational layer
            3: {}   # Implementation layer
        }
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize the HRM MCP server"""
        self.logger.info("Initializing HRM MCP Server")
        
        # Load any saved state
        state_file = Path(self.config.get('state_file', '.hrm_state.json'))
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.decision_history = state.get('history', [])
                    self.logger.info(f"Loaded {len(self.decision_history)} historical decisions")
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
                
        return True
        
    async def reason(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        level: int = 0
    ) -> ReasoningNode:
        """
        Perform hierarchical reasoning on a query
        
        Args:
            query: The question or decision to reason about
            context: Additional context for reasoning
            level: The reasoning level (0=strategic, 1=tactical, 2=operational, 3=implementation)
            
        Returns:
            ReasoningNode with the reasoning result
        """
        # Generate node ID
        node_id = f"node_{len(self.reasoning_tree)}_{datetime.now().timestamp()}"
        
        # Perform reasoning based on level
        decision, confidence, evidence = await self._perform_reasoning(query, context, level)
        
        # Create reasoning node
        node = ReasoningNode(
            node_id=node_id,
            level=level,
            decision=decision,
            confidence=confidence,
            evidence=evidence
        )
        
        # Store in tree
        self.reasoning_tree[node_id] = node
        
        # If not implementation level, create child nodes
        if level < 3:
            child_queries = await self._decompose_query(query, decision, level)
            for child_query in child_queries:
                child_node = await self.reason(child_query, context, level + 1)
                child_node.parent_id = node_id
                node.children.append(child_node)
                
        # Store in history
        self.decision_history.append({
            'timestamp': node.timestamp.isoformat(),
            'query': query,
            'decision': decision,
            'confidence': confidence,
            'level': level
        })
        
        return node
        
    async def _perform_reasoning(
        self,
        query: str,
        context: Dict[str, Any],
        level: int
    ) -> Tuple[str, float, List[str]]:
        """
        Core reasoning logic
        
        Returns:
            Tuple of (decision, confidence, evidence)
        """
        # Layer-specific reasoning
        if level == 0:  # Strategic
            return await self._strategic_reasoning(query, context)
        elif level == 1:  # Tactical
            return await self._tactical_reasoning(query, context)
        elif level == 2:  # Operational
            return await self._operational_reasoning(query, context)
        else:  # Implementation
            return await self._implementation_reasoning(query, context)
            
    async def _strategic_reasoning(self, query: str, context: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """High-level strategic reasoning"""
        # Analyze for strategic patterns
        evidence = []
        confidence = 0.8
        
        if "workflow" in query.lower():
            decision = "Execute 12-phase unified workflow for comprehensive solution"
            evidence.append("Query involves workflow orchestration")
            confidence = 0.95
        elif "fix" in query.lower() or "debug" in query.lower():
            decision = "Apply systematic debugging approach with root cause analysis"
            evidence.append("Query involves problem resolution")
            confidence = 0.85
        elif "implement" in query.lower() or "create" in query.lower():
            decision = "Design and implement new functionality with testing"
            evidence.append("Query involves new feature development")
            confidence = 0.9
        else:
            decision = "Analyze requirements and provide structured solution"
            evidence.append("General query requiring analysis")
            confidence = 0.75
            
        return decision, confidence, evidence
        
    async def _tactical_reasoning(self, query: str, context: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Mid-level tactical reasoning"""
        evidence = []
        
        # Determine tactical approach
        if "parallel" in query.lower() or "multiple" in query.lower():
            decision = "Use parallel execution strategy with multiple agents"
            evidence.append("Task suitable for parallelization")
            confidence = 0.85
        elif "sequential" in query.lower() or "step" in query.lower():
            decision = "Use sequential execution with dependency management"
            evidence.append("Task requires ordered steps")
            confidence = 0.8
        else:
            decision = "Use hybrid approach with parallel and sequential phases"
            evidence.append("Mixed execution pattern optimal")
            confidence = 0.75
            
        return decision, confidence, evidence
        
    async def _operational_reasoning(self, query: str, context: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Operational level reasoning"""
        evidence = []
        
        # Determine operational details
        if context and context.get('project_type') == 'python':
            decision = "Use Python-specific tools and testing frameworks"
            evidence.append("Python project detected")
            confidence = 0.9
        elif context and context.get('project_type') == 'node':
            decision = "Use Node.js toolchain and npm scripts"
            evidence.append("Node.js project detected")
            confidence = 0.9
        else:
            decision = "Use language-agnostic tools and approaches"
            evidence.append("Mixed or unknown project type")
            confidence = 0.7
            
        return decision, confidence, evidence
        
    async def _implementation_reasoning(self, query: str, context: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Implementation level reasoning"""
        evidence = []
        
        # Specific implementation decisions
        decision = f"Execute: {query[:100]}..."
        evidence.append("Direct implementation task")
        confidence = 0.95
        
        return decision, confidence, evidence
        
    async def _decompose_query(self, query: str, decision: str, level: int) -> List[str]:
        """Decompose a query into sub-queries for the next level"""
        sub_queries = []
        
        if level == 0:  # Strategic -> Tactical
            if "workflow" in decision.lower():
                sub_queries = [
                    "Initialize environment and validate configuration",
                    "Execute research and discovery phase",
                    "Perform implementation with parallel agents",
                    "Validate and test results"
                ]
            elif "debug" in decision.lower():
                sub_queries = [
                    "Reproduce the issue",
                    "Identify root cause",
                    "Implement fix",
                    "Verify resolution"
                ]
        elif level == 1:  # Tactical -> Operational
            if "parallel" in decision.lower():
                sub_queries = [
                    "Identify independent tasks",
                    "Allocate resources",
                    "Coordinate execution",
                    "Merge results"
                ]
            else:
                sub_queries = [
                    "Define execution order",
                    "Setup dependencies",
                    "Execute tasks",
                    "Validate outputs"
                ]
        elif level == 2:  # Operational -> Implementation
            sub_queries = [
                f"Implement: {query}",
                f"Test: {query}",
                f"Document: {query}"
            ]
            
        return sub_queries
        
    async def get_decision_path(self, node_id: str) -> List[ReasoningNode]:
        """Get the complete decision path from root to a specific node"""
        path = []
        current = self.reasoning_tree.get(node_id)
        
        while current:
            path.insert(0, current)
            if current.parent_id:
                current = self.reasoning_tree.get(current.parent_id)
            else:
                break
                
        return path
        
    async def explain_reasoning(self, node_id: str) -> str:
        """Generate a human-readable explanation of the reasoning"""
        node = self.reasoning_tree.get(node_id)
        if not node:
            return "No reasoning found for this ID"
            
        explanation = f"## Reasoning Explanation\n\n"
        explanation += f"**Decision:** {node.decision}\n"
        explanation += f"**Confidence:** {node.confidence:.2%}\n"
        explanation += f"**Level:** {['Strategic', 'Tactical', 'Operational', 'Implementation'][node.level]}\n\n"
        
        if node.evidence:
            explanation += "**Evidence:**\n"
            for e in node.evidence:
                explanation += f"- {e}\n"
                
        if node.children:
            explanation += "\n**Sub-decisions:**\n"
            for child in node.children:
                explanation += f"- {child.decision} (confidence: {child.confidence:.2%})\n"
                
        return explanation
        
    async def save_state(self):
        """Save the current state to disk"""
        state_file = Path(self.config.get('state_file', '.hrm_state.json'))
        
        state = {
            'history': self.decision_history[-100:],  # Keep last 100 decisions
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.info(f"Saved HRM state to {state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            
    async def get_confidence_metrics(self) -> Dict[str, float]:
        """Get confidence metrics across all decisions"""
        if not self.decision_history:
            return {}
            
        confidences = [d['confidence'] for d in self.decision_history]
        
        return {
            'average_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'total_decisions': len(self.decision_history)
        }

# Convenience function for standalone usage
async def create_hrm_server(config: Dict[str, Any] = None):
    """Create and initialize an HRM MCP server"""
    server = HRM_MCP(config)
    await server.initialize()
    return server

if __name__ == "__main__":
    # Test the HRM MCP
    async def test():
        hrm = await create_hrm_server()
        
        # Test reasoning
        result = await hrm.reason(
            "Fix the authentication bug in the login system",
            context={'project_type': 'python'}
        )
        
        print(await hrm.explain_reasoning(result.node_id))
        print("\nConfidence Metrics:", await hrm.get_confidence_metrics())
        
        await hrm.save_state()
        
    asyncio.run(test())