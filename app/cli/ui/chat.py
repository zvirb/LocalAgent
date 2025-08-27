"""
Interactive Chat Session Interface
Rich-based chat interface for direct LLM interaction
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.align import Align
from rich.layout import Layout
from rich.live import Live

from ..core.config import LocalAgentConfig
from .display import DisplayManager


class ChatMessage:
    """Represents a single chat message"""
    
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.role = role  # 'user', 'assistant', 'system'
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create message from dictionary"""
        timestamp = datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=timestamp,
            metadata=data.get('metadata', {})
        )


class ChatSession:
    """Manages a chat session with message history"""
    
    def __init__(self, session_name: str, provider: str, model: Optional[str] = None):
        self.session_name = session_name
        self.provider = provider
        self.model = model
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """Add a message to the session"""
        message = ChatMessage(role, content, metadata=metadata)
        self.messages.append(message)
        return message
    
    def get_history(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get message history with optional limit"""
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()
    
    def clear_history(self) -> None:
        """Clear message history"""
        self.messages.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization"""
        return {
            'session_name': self.session_name,
            'provider': self.provider,
            'model': self.model,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata,
            'messages': [msg.to_dict() for msg in self.messages]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create session from dictionary"""
        session = cls(
            session_name=data['session_name'],
            provider=data['provider'],
            model=data.get('model')
        )
        session.created_at = datetime.fromisoformat(data['created_at'])
        session.metadata = data.get('metadata', {})
        session.messages = [ChatMessage.from_dict(msg) for msg in data.get('messages', [])]
        return session


class InteractiveChatSession:
    """
    Interactive chat interface with Rich formatting
    Provides a conversational interface to LLM providers
    """
    
    def __init__(self, config: LocalAgentConfig, provider: Optional[str] = None,
                 model: Optional[str] = None, session_name: Optional[str] = None,
                 display_manager: Optional[DisplayManager] = None):
        self.config = config
        self.console = Console()
        self.display_manager = display_manager or DisplayManager(self.console)
        
        # Session configuration
        self.provider = provider or config.default_provider
        self.model = model
        self.session_name = session_name or f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Session state
        self.session = ChatSession(self.session_name, self.provider, self.model)
        self.is_running = False
        self.provider_instance = None
        
        # UI settings
        self.show_timestamps = True
        self.show_metadata = False
        self.auto_save = True
        self.max_display_messages = 10
    
    async def start(self) -> None:
        """Start the interactive chat session"""
        await self._initialize_session()
        
        if not self.provider_instance:
            self.display_manager.print_error("Failed to initialize provider")
            return
        
        self._display_welcome()
        
        try:
            self.is_running = True
            await self._chat_loop()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Chat session ended by user[/yellow]")
        except Exception as e:
            self.display_manager.print_error(f"Chat session error: {e}")
        finally:
            await self._cleanup_session()
    
    async def _initialize_session(self) -> None:
        """Initialize the chat session and provider"""
        self.display_manager.print_info(f"Initializing chat session with {self.provider}")
        
        try:
            # This would integrate with the actual provider system
            # For now, we'll simulate provider initialization
            await asyncio.sleep(0.5)  # Simulate initialization delay
            
            # Mock provider instance
            self.provider_instance = MockProviderInterface(self.provider, self.model)
            
            self.display_manager.print_success(f"Connected to {self.provider}")
            
            if self.model:
                self.display_manager.print_info(f"Using model: {self.model}")
            
            # Load previous session if it exists
            await self._load_session_history()
            
        except Exception as e:
            self.display_manager.print_error(f"Failed to initialize provider: {e}")
    
    def _display_welcome(self) -> None:
        """Display welcome message and instructions"""
        welcome_text = f"""
[bold blue]LocalAgent Interactive Chat[/bold blue]

[cyan]Session:[/cyan] {self.session_name}
[cyan]Provider:[/cyan] {self.provider}
[cyan]Model:[/cyan] {self.model or 'Default'}

[dim]Commands:[/dim]
• [bold]/help[/bold] - Show help
• [bold]/clear[/bold] - Clear conversation history
• [bold]/save[/bold] - Save session
• [bold]/load <name>[/bold] - Load session
• [bold]/settings[/bold] - Show/modify settings
• [bold]/history[/bold] - Show message history
• [bold]/export[/bold] - Export conversation
• [bold]/quit[/bold] or [bold]Ctrl+C[/bold] - Exit

Start chatting by typing your message!
        """
        
        panel = Panel(welcome_text, title="🤖 Chat Session", border_style="blue")
        self.console.print(panel)
    
    async def _chat_loop(self) -> None:
        """Main chat interaction loop"""
        while self.is_running:
            try:
                # Get user input
                user_input = await self._get_user_input()
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    await self._handle_command(user_input)
                    continue
                
                # Add user message
                self.session.add_message('user', user_input)
                
                # Get AI response
                await self._get_ai_response(user_input)
                
                # Auto-save if enabled
                if self.auto_save:
                    await self._save_session()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.display_manager.print_error(f"Error in chat loop: {e}")
    
    async def _get_user_input(self) -> str:
        """Get user input with prompt formatting"""
        # Display recent conversation
        await self._display_recent_messages()
        
        # User input prompt
        prompt_text = f"[bold green]You[/bold green] [{datetime.now().strftime('%H:%M')}]"
        
        try:
            user_input = Prompt.ask(prompt_text, console=self.console)
            return user_input
        except (KeyboardInterrupt, EOFError):
            self.is_running = False
            return ""
    
    async def _get_ai_response(self, user_input: str) -> None:
        """Get response from AI provider"""
        # Show typing indicator
        with self.display_manager.create_simple_progress("🤖 Thinking..."):
            try:
                # Get response from provider
                response = await self.provider_instance.generate_response(
                    user_input, 
                    self.session.get_history()
                )
                
                # Add AI response
                ai_message = self.session.add_message('assistant', response['content'], response.get('metadata'))
                
                # Display response
                self._display_ai_message(ai_message)
                
            except Exception as e:
                self.display_manager.print_error(f"Failed to get AI response: {e}")
                # Add error message to session
                self.session.add_message('system', f"Error: {e}")
    
    def _display_ai_message(self, message: ChatMessage) -> None:
        """Display AI response message"""
        timestamp = message.timestamp.strftime('%H:%M') if self.show_timestamps else ""
        header = f"[bold blue]Assistant[/bold blue] [{timestamp}]" if timestamp else "[bold blue]Assistant[/bold blue]"
        
        # Format content (support markdown if it looks like markdown)
        content = message.content
        if self._is_markdown_content(content):
            formatted_content = Markdown(content)
        elif self._is_code_content(content):
            # Extract language and code
            language, code = self._extract_code_content(content)
            formatted_content = Syntax(code, language, theme="monokai", line_numbers=True)
        else:
            formatted_content = Text(content)
        
        # Create response panel
        response_panel = Panel(
            formatted_content,
            title=header,
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(response_panel)
        
        # Show metadata if enabled
        if self.show_metadata and message.metadata:
            metadata_text = "\n".join([f"{k}: {v}" for k, v in message.metadata.items()])
            metadata_panel = Panel(
                metadata_text,
                title="Response Metadata",
                border_style="dim",
                padding=(0, 1)
            )
            self.console.print(metadata_panel)
    
    def _is_markdown_content(self, content: str) -> bool:
        """Check if content appears to be markdown"""
        markdown_indicators = ['#', '*', '`', '[]', '()', '---', '```']
        return any(indicator in content for indicator in markdown_indicators)
    
    def _is_code_content(self, content: str) -> bool:
        """Check if content appears to be code"""
        return content.strip().startswith('```') and content.strip().endswith('```')
    
    def _extract_code_content(self, content: str) -> Tuple[str, str]:
        """Extract language and code from code block"""
        lines = content.strip().split('\n')
        if lines[0].startswith('```'):
            language = lines[0][3:].strip() or 'text'
            code = '\n'.join(lines[1:-1])
            return language, code
        return 'text', content
    
    async def _display_recent_messages(self) -> None:
        """Display recent conversation messages"""
        recent_messages = self.session.get_history(limit=self.max_display_messages)
        
        if not recent_messages:
            return
        
        # Only show the most recent few messages to avoid clutter
        display_messages = recent_messages[-3:]  # Last 3 messages
        
        for message in display_messages:
            if message.role == 'user':
                timestamp = message.timestamp.strftime('%H:%M') if self.show_timestamps else ""
                header = f"[dim]You [{timestamp}]:[/dim]" if timestamp else "[dim]You:[/dim]"
                self.console.print(f"{header} {message.content}")
            elif message.role == 'assistant':
                # Don't re-display assistant messages as they were already shown
                pass
    
    async def _handle_command(self, command: str) -> None:
        """Handle chat commands"""
        parts = command.strip().split()
        cmd = parts[0].lower()
        
        if cmd == '/help':
            await self._show_help()
        elif cmd == '/clear':
            await self._clear_history()
        elif cmd == '/save':
            await self._save_session_manual()
        elif cmd == '/load':
            session_name = parts[1] if len(parts) > 1 else None
            await self._load_session_manual(session_name)
        elif cmd == '/settings':
            await self._show_settings()
        elif cmd == '/history':
            await self._show_history()
        elif cmd == '/export':
            format_type = parts[1] if len(parts) > 1 else 'json'
            await self._export_session(format_type)
        elif cmd == '/quit':
            self.is_running = False
        else:
            self.display_manager.print_warning(f"Unknown command: {cmd}. Type /help for available commands.")
    
    async def _show_help(self) -> None:
        """Show help information"""
        help_text = """
[bold]Available Commands:[/bold]

[cyan]/help[/cyan] - Show this help message
[cyan]/clear[/cyan] - Clear conversation history
[cyan]/save[/cyan] - Save current session
[cyan]/load <name>[/cyan] - Load a saved session
[cyan]/settings[/cyan] - Show/modify session settings
[cyan]/history[/cyan] - Show full message history
[cyan]/export <format>[/cyan] - Export conversation (json/md/txt)
[cyan]/quit[/cyan] - Exit chat session

[bold]Tips:[/bold]
• Use Ctrl+C to exit at any time
• Messages are auto-saved if enabled
• Markdown and code blocks are automatically formatted
• Use /settings to customize display options
        """
        
        help_panel = Panel(help_text, title="Chat Help", border_style="cyan")
        self.console.print(help_panel)
    
    async def _clear_history(self) -> None:
        """Clear conversation history"""
        confirm = Prompt.ask("Clear conversation history? [y/N]", default="n")
        if confirm.lower() == 'y':
            self.session.clear_history()
            self.display_manager.print_success("Conversation history cleared")
        else:
            self.display_manager.print_info("Clear cancelled")
    
    async def _save_session_manual(self) -> None:
        """Manually save session"""
        try:
            await self._save_session()
            self.display_manager.print_success(f"Session '{self.session_name}' saved")
        except Exception as e:
            self.display_manager.print_error(f"Failed to save session: {e}")
    
    async def _load_session_manual(self, session_name: Optional[str]) -> None:
        """Manually load a session"""
        if not session_name:
            # List available sessions
            sessions = await self._list_saved_sessions()
            if not sessions:
                self.display_manager.print_info("No saved sessions found")
                return
            
            self.display_manager.print_info("Available sessions:")
            for session in sessions:
                self.console.print(f"  • {session}")
            
            session_name = Prompt.ask("Enter session name to load")
        
        if session_name:
            try:
                await self._load_session(session_name)
                self.display_manager.print_success(f"Session '{session_name}' loaded")
            except Exception as e:
                self.display_manager.print_error(f"Failed to load session: {e}")
    
    async def _show_settings(self) -> None:
        """Show and modify session settings"""
        settings_table = Table(title="Chat Session Settings", show_header=True, header_style="bold magenta")
        settings_table.add_column("Setting", style="cyan", width=20)
        settings_table.add_column("Value", style="white", width=15)
        settings_table.add_column("Description", style="blue")
        
        settings_table.add_row("show_timestamps", "✓" if self.show_timestamps else "✗", "Show message timestamps")
        settings_table.add_row("show_metadata", "✓" if self.show_metadata else "✗", "Show response metadata")
        settings_table.add_row("auto_save", "✓" if self.auto_save else "✗", "Auto-save session")
        settings_table.add_row("max_display_messages", str(self.max_display_messages), "Max messages to display")
        
        self.console.print(settings_table)
    
    async def _show_history(self) -> None:
        """Show full message history"""
        messages = self.session.get_history()
        
        if not messages:
            self.display_manager.print_info("No messages in history")
            return
        
        history_table = Table(title=f"Chat History - {self.session_name}", show_header=True, header_style="bold magenta")
        history_table.add_column("Time", style="dim", width=8)
        history_table.add_column("Role", style="cyan", width=10)
        history_table.add_column("Message", style="white")
        
        for message in messages:
            timestamp = message.timestamp.strftime('%H:%M:%S')
            role = message.role.title()
            content = message.content[:100] + "..." if len(message.content) > 100 else message.content
            
            history_table.add_row(timestamp, role, content)
        
        self.console.print(history_table)
    
    async def _export_session(self, format_type: str = 'json') -> None:
        """Export conversation in specified format"""
        try:
            filename = f"{self.session_name}_export.{format_type}"
            filepath = self.config.config_dir / filename
            
            if format_type == 'json':
                await self._export_json(filepath)
            elif format_type == 'md':
                await self._export_markdown(filepath)
            elif format_type == 'txt':
                await self._export_text(filepath)
            else:
                self.display_manager.print_error(f"Unsupported export format: {format_type}")
                return
            
            self.display_manager.print_success(f"Conversation exported to {filepath}")
            
        except Exception as e:
            self.display_manager.print_error(f"Failed to export session: {e}")
    
    async def _export_json(self, filepath: Path) -> None:
        """Export session as JSON"""
        from ..io.atomic import AtomicFileManager
        await AtomicFileManager.write_json(filepath, self.session.to_dict())
    
    async def _export_markdown(self, filepath: Path) -> None:
        """Export session as Markdown"""
        content = f"# Chat Session: {self.session_name}\n\n"
        content += f"**Provider:** {self.provider}  \n"
        content += f"**Model:** {self.model or 'Default'}  \n"
        content += f"**Created:** {self.session.created_at.strftime('%Y-%m-%d %H:%M:%S')}  \n\n"
        content += "---\n\n"
        
        for message in self.session.messages:
            timestamp = message.timestamp.strftime('%H:%M:%S')
            role = "**You**" if message.role == 'user' else "**Assistant**"
            content += f"## {role} [{timestamp}]\n\n"
            content += f"{message.content}\n\n"
        
        from ..io.atomic import AtomicFileManager
        await AtomicFileManager.write_text(filepath, content)
    
    async def _export_text(self, filepath: Path) -> None:
        """Export session as plain text"""
        content = f"Chat Session: {self.session_name}\n"
        content += f"Provider: {self.provider}\n"
        content += f"Model: {self.model or 'Default'}\n"
        content += f"Created: {self.session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += "=" * 50 + "\n\n"
        
        for message in self.session.messages:
            timestamp = message.timestamp.strftime('%H:%M:%S')
            role = "You" if message.role == 'user' else "Assistant"
            content += f"[{timestamp}] {role}: {message.content}\n\n"
        
        from ..io.atomic import AtomicFileManager
        await AtomicFileManager.write_text(filepath, content)
    
    async def _save_session(self) -> None:
        """Save session to file"""
        session_file = self.config.config_dir / "chat_sessions" / f"{self.session_name}.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        from ..io.atomic import AtomicFileManager
        await AtomicFileManager.write_json(session_file, self.session.to_dict())
    
    async def _load_session_history(self) -> None:
        """Load existing session history if available"""
        session_file = self.config.config_dir / "chat_sessions" / f"{self.session_name}.json"
        
        if session_file.exists():
            try:
                import json
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                loaded_session = ChatSession.from_dict(session_data)
                self.session = loaded_session
                
                if self.session.messages:
                    self.display_manager.print_info(f"Loaded {len(self.session.messages)} previous messages")
            
            except Exception as e:
                self.display_manager.print_warning(f"Could not load session history: {e}")
    
    async def _load_session(self, session_name: str) -> None:
        """Load a specific saved session"""
        session_file = self.config.config_dir / "chat_sessions" / f"{session_name}.json"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session '{session_name}' not found")
        
        import json
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        self.session = ChatSession.from_dict(session_data)
        self.session_name = session_name
    
    async def _list_saved_sessions(self) -> List[str]:
        """List all saved session names"""
        sessions_dir = self.config.config_dir / "chat_sessions"
        
        if not sessions_dir.exists():
            return []
        
        sessions = []
        for session_file in sessions_dir.glob("*.json"):
            sessions.append(session_file.stem)
        
        return sorted(sessions)
    
    async def _cleanup_session(self) -> None:
        """Cleanup session resources"""
        if self.auto_save and self.session.messages:
            await self._save_session()
        
        self.display_manager.print_info("Chat session ended")


class MockProviderInterface:
    """
    Mock provider interface for demonstration
    In real implementation, this would integrate with actual providers
    """
    
    def __init__(self, provider: str, model: Optional[str] = None):
        self.provider = provider
        self.model = model
    
    async def generate_response(self, user_input: str, history: List[ChatMessage]) -> Dict[str, Any]:
        """Generate a mock response"""
        # Simulate processing time
        await asyncio.sleep(1)
        
        # Mock response based on provider
        responses = {
            'ollama': f"[Ollama/{self.model or 'default'}] This is a simulated response to: {user_input}",
            'openai': f"[OpenAI/{self.model or 'gpt-4'}] This is a simulated response to: {user_input}",
            'gemini': f"[Gemini/{self.model or 'gemini-pro'}] This is a simulated response to: {user_input}",
            'perplexity': f"[Perplexity/{self.model or 'default'}] This is a simulated response to: {user_input}"
        }
        
        response_text = responses.get(self.provider, f"[{self.provider}] Simulated response: {user_input}")
        
        return {
            'content': response_text,
            'metadata': {
                'provider': self.provider,
                'model': self.model,
                'tokens_used': len(user_input.split()) * 2,
                'response_time': 1.0
            }
        }