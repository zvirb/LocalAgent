"""
Natural Language Processing for Command Parsing
===============================================

Converts natural language descriptions into CLI commands and workflow actions.
Uses lightweight NLP models optimized for 60+ FPS performance.
"""

import asyncio
import time
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import json

# Import behavior tracking for learning
from .behavior_tracker import BehaviorTracker

@dataclass
class Intent:
    """Parsed intent from natural language"""
    action: str  # Primary action (create, list, run, analyze, etc.)
    target: Optional[str] = None  # Target object (file, service, etc.)
    modifiers: List[str] = field(default_factory=list)  # Adjectives/adverbs
    parameters: Dict[str, str] = field(default_factory=dict)  # Extracted parameters
    confidence: float = 0.0
    entities: List[Dict[str, str]] = field(default_factory=list)  # Named entities

@dataclass
class CommandTranslation:
    """Translation result from natural language to command"""
    original_text: str
    parsed_intent: Intent
    suggested_command: str
    confidence: float
    alternatives: List[str] = field(default_factory=list)
    explanation: str = ""
    estimated_success_rate: float = 0.8

class NaturalLanguageProcessor:
    """
    Lightweight NLP processor for CLI command translation
    Optimized for speed and accuracy without heavy ML models
    """
    
    def __init__(self, behavior_tracker: Optional[BehaviorTracker] = None, config_dir: Optional[Path] = None):
        self.behavior_tracker = behavior_tracker
        self.config_dir = config_dir or Path.home() / ".localagent"
        self.logger = logging.getLogger("NaturalLanguageProcessor")
        
        # Intent recognition patterns
        self.action_patterns = {}
        self.entity_patterns = {}
        self.command_templates = {}
        
        # Performance tracking
        self.processing_times = []
        self.translation_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize NLP components
        asyncio.create_task(self._initialize_nlp_system())
    
    async def _initialize_nlp_system(self):
        """Initialize the NLP processing system"""
        try:
            # Load linguistic patterns and templates
            await self._load_action_patterns()
            await self._load_entity_patterns()
            await self._load_command_templates()
            
            # Build vocabulary from user commands if behavior tracker available
            if self.behavior_tracker:
                await self._learn_from_user_history()
            
            self.logger.info("Natural language processor initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP system: {e}")
    
    async def parse_natural_language(self, text: str, context: Optional[Dict[str, Any]] = None) -> CommandTranslation:
        """Parse natural language text into CLI command"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{text}:{hash(str(context or {}))}"
            if cache_key in self.translation_cache:
                cached_result, timestamp = self.translation_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    return cached_result
            
            # Clean and normalize text
            normalized_text = self._normalize_text(text)
            
            # Parse intent
            intent = await self._parse_intent(normalized_text, context)
            
            # Generate command
            command = await self._generate_command(intent, context)
            
            # Generate alternatives
            alternatives = await self._generate_alternatives(intent, context)
            
            # Create translation result
            translation = CommandTranslation(
                original_text=text,
                parsed_intent=intent,
                suggested_command=command,
                confidence=intent.confidence,
                alternatives=alternatives,
                explanation=self._generate_explanation(intent, command),
                estimated_success_rate=self._estimate_success_rate(intent, command)
            )
            
            # Cache result
            self.translation_cache[cache_key] = (translation, time.time())
            
            # Track performance
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            
            if processing_time > 16.0:  # Must maintain 60+ FPS
                self.logger.warning(f"NLP processing took {processing_time:.1f}ms (target: <16ms)")
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Failed to parse natural language: {e}")
            return CommandTranslation(
                original_text=text,
                parsed_intent=Intent(action="unknown", confidence=0.0),
                suggested_command="# Unable to parse command",
                confidence=0.0,
                explanation="Failed to understand the request"
            )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize input text for processing"""
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove common filler words
        filler_words = ['please', 'can you', 'could you', 'would you', 'i want to', 'i need to', 'help me']
        for filler in filler_words:
            normalized = normalized.replace(filler, ' ').strip()
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    async def _parse_intent(self, text: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """Parse intent from normalized text"""
        intent = Intent(action="unknown", confidence=0.0)
        
        # Extract action using patterns
        best_action, action_confidence = self._extract_action(text)
        intent.action = best_action
        intent.confidence = action_confidence
        
        # Extract target
        intent.target = self._extract_target(text, intent.action)
        
        # Extract modifiers (adjectives/adverbs)
        intent.modifiers = self._extract_modifiers(text)
        
        # Extract parameters
        intent.parameters = self._extract_parameters(text, intent.action)
        
        # Extract entities
        intent.entities = self._extract_entities(text)
        
        # Apply context if available
        if context:
            intent = self._apply_context(intent, context)
        
        return intent
    
    def _extract_action(self, text: str) -> Tuple[str, float]:
        """Extract primary action from text"""
        best_action = "unknown"
        best_confidence = 0.0
        
        # Check against action patterns
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                if isinstance(pattern, str):
                    # Simple substring match
                    if pattern in text:
                        confidence = len(pattern) / len(text)
                        if confidence > best_confidence:
                            best_action = action
                            best_confidence = confidence
                else:
                    # Regular expression pattern
                    if re.search(pattern, text):
                        confidence = 0.8  # High confidence for regex matches
                        if confidence > best_confidence:
                            best_action = action
                            best_confidence = confidence
        
        return best_action, min(best_confidence, 1.0)
    
    def _extract_target(self, text: str, action: str) -> Optional[str]:
        """Extract target object from text based on action"""
        
        # Action-specific target extraction
        if action in ["create", "make", "build"]:
            # Look for "create a/an X" patterns
            create_patterns = [
                r"create (?:a |an |the )?([a-zA-Z][a-zA-Z0-9_-]*)",
                r"make (?:a |an |the )?([a-zA-Z][a-zA-Z0-9_-]*)",
                r"build (?:a |an |the )?([a-zA-Z][a-zA-Z0-9_-]*)"
            ]
            
            for pattern in create_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        
        elif action in ["list", "show", "display"]:
            # Look for "list X" or "show X" patterns
            list_patterns = [
                r"list (?:all )?(?:the )?([a-zA-Z][a-zA-Z0-9_-]*)",
                r"show (?:me )?(?:all )?(?:the )?([a-zA-Z][a-zA-Z0-9_-]*)",
                r"display (?:all )?(?:the )?([a-zA-Z][a-zA-Z0-9_-]*)"
            ]
            
            for pattern in list_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        
        elif action in ["run", "execute", "start"]:
            # Look for "run X" patterns
            run_patterns = [
                r"run (?:the )?([a-zA-Z][a-zA-Z0-9_.-]*)",
                r"execute (?:the )?([a-zA-Z][a-zA-Z0-9_.-]*)",
                r"start (?:the )?([a-zA-Z][a-zA-Z0-9_.-]*)"
            ]
            
            for pattern in run_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        
        elif action in ["analyze", "check", "test"]:
            # Look for what to analyze
            analyze_patterns = [
                r"analyze (?:the )?([a-zA-Z][a-zA-Z0-9_.-]*)",
                r"check (?:the )?([a-zA-Z][a-zA-Z0-9_.-]*)",
                r"test (?:the )?([a-zA-Z][a-zA-Z0-9_.-]*)"
            ]
            
            for pattern in analyze_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        
        # Generic target extraction - look for nouns after action words
        words = text.split()
        action_words = self.action_patterns.get(action, [])
        
        for i, word in enumerate(words):
            if any(action_word in word for action_word in action_words):
                # Look for the next significant word
                for j in range(i + 1, min(len(words), i + 4)):  # Look ahead max 3 words
                    candidate = words[j]
                    if len(candidate) > 2 and candidate not in ['the', 'a', 'an', 'with', 'for', 'to']:
                        return candidate
        
        return None
    
    def _extract_modifiers(self, text: str) -> List[str]:
        """Extract modifiers (adjectives/adverbs) from text"""
        modifiers = []
        
        # Common modifiers that affect command behavior
        modifier_patterns = {
            'recursive': ['recursive', 'recursively', 'all subdirectories'],
            'verbose': ['verbose', 'detailed', 'with details'],
            'quiet': ['quiet', 'silently', 'without output'],
            'force': ['force', 'forcefully', 'overwrite'],
            'dry-run': ['dry run', 'preview', 'simulate'],
            'interactive': ['interactive', 'interactively', 'ask me'],
            'quick': ['quick', 'fast', 'quickly'],
            'secure': ['secure', 'securely', 'with encryption']
        }
        
        for modifier, patterns in modifier_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    modifiers.append(modifier)
                    break
        
        return modifiers
    
    def _extract_parameters(self, text: str, action: str) -> Dict[str, str]:
        """Extract command parameters from text"""
        parameters = {}
        
        # File extensions
        file_ext_match = re.search(r'\.([a-zA-Z0-9]+)\b', text)
        if file_ext_match:
            parameters['file_extension'] = file_ext_match.group(1)
        
        # Numbers (counts, sizes, etc.)
        number_matches = re.findall(r'\b(\d+)\b', text)
        if number_matches:
            parameters['number'] = number_matches[0]
        
        # Quoted strings (names, paths)
        quoted_matches = re.findall(r'"([^"]*)"', text)
        if quoted_matches:
            parameters['quoted_text'] = quoted_matches[0]
        
        # File paths
        path_matches = re.findall(r'([~/][\w/.-]*)', text)
        if path_matches:
            parameters['path'] = path_matches[0]
        
        # Provider names
        providers = ['ollama', 'openai', 'gemini', 'claude', 'perplexity']
        for provider in providers:
            if provider in text:
                parameters['provider'] = provider
                break
        
        # Time expressions
        time_patterns = {
            'minutes': r'(\d+)\s*(?:minute|min)',
            'hours': r'(\d+)\s*(?:hour|hr)',
            'days': r'(\d+)\s*(?:day)',
            'seconds': r'(\d+)\s*(?:second|sec)'
        }
        
        for time_unit, pattern in time_patterns.items():
            match = re.search(pattern, text)
            if match:
                parameters['time'] = f"{match.group(1)} {time_unit}"
                break
        
        return parameters
    
    def _extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract named entities from text"""
        entities = []
        
        # File/directory names
        file_pattern = r'\b([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)\b'
        file_matches = re.findall(file_pattern, text)
        for match in file_matches:
            entities.append({'type': 'file', 'value': match})
        
        # URLs
        url_pattern = r'https?://[\w.-]+(?:/[\w.-]*)*'
        url_matches = re.findall(url_pattern, text)
        for match in url_matches:
            entities.append({'type': 'url', 'value': match})
        
        # Email addresses  
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, text)
        for match in email_matches:
            entities.append({'type': 'email', 'value': match})
        
        # Version numbers
        version_pattern = r'\bv?(\d+\.\d+(?:\.\d+)?)\b'
        version_matches = re.findall(version_pattern, text)
        for match in version_matches:
            entities.append({'type': 'version', 'value': match})
        
        return entities
    
    def _apply_context(self, intent: Intent, context: Dict[str, Any]) -> Intent:
        """Apply contextual information to improve intent parsing"""
        
        # Use current directory if no path specified
        if 'current_directory' in context and not intent.target:
            if intent.action in ['list', 'show', 'analyze']:
                intent.target = context['current_directory']
        
        # Use recent commands to improve confidence
        if 'recent_commands' in context:
            recent = context['recent_commands']
            if recent and intent.action in recent[-3:]:  # Used recently
                intent.confidence = min(1.0, intent.confidence * 1.2)
        
        # Use workflow phase context
        if 'workflow_phase' in context:
            phase = context['workflow_phase']
            phase_actions = {
                'research': ['analyze', 'search', 'inspect', 'list'],
                'planning': ['create', 'design', 'plan', 'configure'],
                'execution': ['run', 'execute', 'build', 'deploy'],
                'testing': ['test', 'validate', 'check', 'verify']
            }
            
            for phase_name, actions in phase_actions.items():
                if phase_name in phase.lower() and intent.action in actions:
                    intent.confidence = min(1.0, intent.confidence * 1.1)
        
        return intent
    
    async def _generate_command(self, intent: Intent, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate CLI command from parsed intent"""
        
        action = intent.action
        target = intent.target
        modifiers = intent.modifiers
        parameters = intent.parameters
        
        # Use command templates
        if action in self.command_templates:
            template = self.command_templates[action]
            
            # Fill in template
            command = template.get('base_command', action)
            
            # Add target if specified
            if target and 'target_pattern' in template:
                command = template['target_pattern'].format(command=command, target=target)
            elif target:
                command = f"{command} {target}"
            
            # Apply modifiers
            if modifiers:
                for modifier in modifiers:
                    if modifier in template.get('modifier_flags', {}):
                        flag = template['modifier_flags'][modifier]
                        command = f"{command} {flag}"
            
            # Apply parameters
            for param, value in parameters.items():
                if param in template.get('parameter_flags', {}):
                    flag = template['parameter_flags'][param]
                    command = f"{command} {flag} {value}"
            
            return command.strip()
        
        # Fallback: generate basic command
        command_parts = [action]
        
        if target:
            command_parts.append(target)
        
        # Add common flags based on modifiers
        flag_mapping = {
            'recursive': '-r',
            'verbose': '-v',
            'quiet': '-q',
            'force': '-f',
            'interactive': '-i'
        }
        
        for modifier in modifiers:
            if modifier in flag_mapping:
                command_parts.append(flag_mapping[modifier])
        
        return ' '.join(command_parts)
    
    async def _generate_alternatives(self, intent: Intent, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate alternative command interpretations"""
        alternatives = []
        
        action = intent.action
        target = intent.target
        
        # Generate variations based on common command synonyms
        action_synonyms = {
            'create': ['make', 'new', 'touch', 'mkdir'],
            'list': ['ls', 'show', 'find', 'search'],
            'run': ['execute', 'start', 'launch'],
            'analyze': ['inspect', 'check', 'examine'],
            'remove': ['delete', 'rm', 'unlink']
        }
        
        if action in action_synonyms:
            for synonym in action_synonyms[action]:
                alt_intent = Intent(action=synonym, target=target, modifiers=intent.modifiers, parameters=intent.parameters)
                alt_command = await self._generate_command(alt_intent, context)
                if alt_command not in alternatives:
                    alternatives.append(alt_command)
        
        # Generate variations with different flag combinations
        if intent.modifiers:
            # Version without modifiers
            no_mod_intent = Intent(action=action, target=target, parameters=intent.parameters)
            no_mod_command = await self._generate_command(no_mod_intent, context)
            alternatives.append(no_mod_command)
            
            # Version with different modifier combinations
            if len(intent.modifiers) > 1:
                for modifier in intent.modifiers:
                    single_mod_intent = Intent(
                        action=action, 
                        target=target, 
                        modifiers=[modifier],
                        parameters=intent.parameters
                    )
                    single_mod_command = await self._generate_command(single_mod_intent, context)
                    if single_mod_command not in alternatives:
                        alternatives.append(single_mod_command)
        
        return alternatives[:5]  # Limit to top 5 alternatives
    
    def _generate_explanation(self, intent: Intent, command: str) -> str:
        """Generate human-readable explanation of the command"""
        
        action = intent.action
        target = intent.target
        modifiers = intent.modifiers
        
        explanation_parts = []
        
        # Action explanation
        action_explanations = {
            'create': f"Create {target}" if target else "Create",
            'list': f"List {target}" if target else "List items",
            'run': f"Run {target}" if target else "Execute command",
            'analyze': f"Analyze {target}" if target else "Perform analysis",
            'remove': f"Remove {target}" if target else "Delete items",
            'search': f"Search for {target}" if target else "Search",
            'copy': f"Copy {target}" if target else "Copy files",
            'move': f"Move {target}" if target else "Move files"
        }
        
        base_explanation = action_explanations.get(action, f"{action.title()} {target if target else ''}")
        explanation_parts.append(base_explanation.strip())
        
        # Modifier explanations
        if modifiers:
            modifier_explanations = {
                'recursive': "recursively through subdirectories",
                'verbose': "with detailed output",
                'quiet': "silently without output",
                'force': "forcefully overwriting existing files",
                'interactive': "with user confirmation prompts",
                'dry-run': "in simulation mode (no actual changes)"
            }
            
            mod_explanations = []
            for modifier in modifiers:
                if modifier in modifier_explanations:
                    mod_explanations.append(modifier_explanations[modifier])
            
            if mod_explanations:
                explanation_parts.append(", ".join(mod_explanations))
        
        return " ".join(explanation_parts) + f". Generated command: '{command}'"
    
    def _estimate_success_rate(self, intent: Intent, command: str) -> float:
        """Estimate likelihood of command success"""
        base_rate = 0.8
        
        # Higher confidence intents are more likely to succeed
        success_rate = base_rate * intent.confidence
        
        # Commands with clear targets are more likely to succeed
        if intent.target:
            success_rate *= 1.1
        
        # Simple commands (fewer parts) are more likely to succeed
        command_parts = len(command.split())
        if command_parts <= 3:
            success_rate *= 1.05
        elif command_parts > 6:
            success_rate *= 0.9
        
        # Commands with recognized patterns are more likely to succeed
        if intent.action in self.command_templates:
            success_rate *= 1.15
        
        return min(1.0, success_rate)
    
    async def _learn_from_user_history(self):
        """Learn patterns from user command history"""
        if not self.behavior_tracker:
            return
        
        try:
            # Get recent command interactions
            recent_interactions = await self.behavior_tracker.get_recent_patterns(
                hours=168,  # Last week
                interaction_types=['command_execution']
            )
            
            # Extract patterns from successful commands
            successful_commands = [
                interaction.command for interaction in recent_interactions
                if interaction.success and interaction.command
            ]
            
            # Update command templates based on successful patterns
            command_frequency = defaultdict(int)
            for command in successful_commands:
                parts = command.split()
                if parts:
                    base_command = parts[0]
                    command_frequency[base_command] += 1
            
            # Update action patterns with frequently used commands
            for command, freq in command_frequency.items():
                if freq > 3:  # Used multiple times
                    if command not in self.action_patterns:
                        self.action_patterns[command] = [command]
            
            self.logger.info(f"Learned from {len(successful_commands)} user commands")
            
        except Exception as e:
            self.logger.warning(f"Failed to learn from user history: {e}")
    
    async def _load_action_patterns(self):
        """Load action recognition patterns"""
        self.action_patterns = {
            'create': [
                'create', 'make', 'new', 'generate', 'build',
                r'create\s+(?:a|an|the)?\s*\w+',
                r'make\s+(?:a|an|the)?\s*\w+'
            ],
            'list': [
                'list', 'show', 'display', 'ls', 'dir',
                r'show\s+(?:me\s+)?(?:all\s+)?',
                r'list\s+(?:all\s+)?'
            ],
            'run': [
                'run', 'execute', 'start', 'launch', 'invoke',
                r'run\s+(?:the\s+)?\w+',
                r'execute\s+(?:the\s+)?\w+'
            ],
            'search': [
                'search', 'find', 'locate', 'look for',
                r'search\s+for',
                r'find\s+(?:all\s+)?'
            ],
            'analyze': [
                'analyze', 'check', 'examine', 'inspect', 'review',
                r'analyze\s+(?:the\s+)?\w+',
                r'check\s+(?:the\s+)?\w+'
            ],
            'remove': [
                'remove', 'delete', 'rm', 'unlink', 'destroy',
                r'delete\s+(?:the\s+)?\w+',
                r'remove\s+(?:all\s+)?'
            ],
            'copy': [
                'copy', 'cp', 'duplicate', 'clone',
                r'copy\s+\w+\s+to',
                r'duplicate\s+(?:the\s+)?\w+'
            ],
            'move': [
                'move', 'mv', 'relocate', 'transfer',
                r'move\s+\w+\s+to',
                r'relocate\s+(?:the\s+)?\w+'
            ],
            'test': [
                'test', 'validate', 'verify', 'check',
                r'test\s+(?:the\s+)?\w+',
                r'validate\s+(?:the\s+)?\w+'
            ],
            'install': [
                'install', 'setup', 'deploy', 'configure',
                r'install\s+(?:the\s+)?\w+',
                r'setup\s+(?:a\s+)?\w+'
            ]
        }
    
    async def _load_entity_patterns(self):
        """Load entity recognition patterns"""
        self.entity_patterns = {
            'file': [
                r'\b([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)\b',
                r'"([^"]*\.[a-zA-Z0-9]+)"'
            ],
            'directory': [
                r'\b([a-zA-Z0-9_.-]+/)\b',
                r'"([^"]*/)"'
            ],
            'url': [
                r'https?://[\w.-]+(?:/[\w.-]*)*',
                r'www\.[\w.-]+(?:/[\w.-]*)*'
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'version': [
                r'\bv?(\d+\.\d+(?:\.\d+)?)\b'
            ],
            'number': [
                r'\b(\d+)\b'
            ]
        }
    
    async def _load_command_templates(self):
        """Load command generation templates"""
        self.command_templates = {
            'list': {
                'base_command': 'ls',
                'target_pattern': '{command} {target}',
                'modifier_flags': {
                    'recursive': '-R',
                    'verbose': '-l',
                    'all': '-a'
                }
            },
            'create': {
                'base_command': 'mkdir',
                'target_pattern': '{command} {target}',
                'modifier_flags': {
                    'recursive': '-p',
                    'verbose': '-v'
                }
            },
            'remove': {
                'base_command': 'rm',
                'target_pattern': '{command} {target}',
                'modifier_flags': {
                    'recursive': '-r',
                    'force': '-f',
                    'interactive': '-i'
                }
            },
            'copy': {
                'base_command': 'cp',
                'target_pattern': '{command} {target}',
                'modifier_flags': {
                    'recursive': '-r',
                    'verbose': '-v',
                    'interactive': '-i'
                }
            },
            'move': {
                'base_command': 'mv',
                'target_pattern': '{command} {target}',
                'modifier_flags': {
                    'verbose': '-v',
                    'interactive': '-i'
                }
            },
            'search': {
                'base_command': 'find',
                'target_pattern': '{command} . -name "{target}"',
                'parameter_flags': {
                    'file_extension': '-name "*.{}"'
                }
            },
            'analyze': {
                'base_command': 'file',
                'target_pattern': '{command} {target}',
                'modifier_flags': {
                    'verbose': '-v'
                }
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get NLP processor performance metrics"""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) \
                             if self.processing_times else 0
        
        return {
            'avg_processing_time_ms': avg_processing_time,
            'fps_compliant': all(t <= 16.0 for t in self.processing_times),
            'action_patterns_count': len(self.action_patterns),
            'entity_patterns_count': len(self.entity_patterns),
            'command_templates_count': len(self.command_templates),
            'cache_size': len(self.translation_cache),
            'total_translations': len(self.processing_times)
        }


# Convenience functions
def create_nlp_processor(behavior_tracker: Optional[BehaviorTracker] = None,
                        config_dir: Optional[Path] = None) -> NaturalLanguageProcessor:
    """Create NLP processor with optional behavior tracker integration"""
    return NaturalLanguageProcessor(behavior_tracker, config_dir)

async def parse_command(text: str, context: Optional[Dict[str, Any]] = None) -> CommandTranslation:
    """Quick function to parse natural language to command"""
    processor = NaturalLanguageProcessor()
    await processor._initialize_nlp_system()
    return await processor.parse_natural_language(text, context)