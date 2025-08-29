"""
Interactive Autocomplete Prompt Component
=========================================

Provides real-time command autocomplete with keyboard navigation
for the LocalAgent CLI using Rich and InquirerPy integration.
"""

import asyncio
import sys
import os
from typing import List, Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# Rich components
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns

# Keyboard input handling
try:
    import readchar
    READCHAR_AVAILABLE = True
except ImportError:
    READCHAR_AVAILABLE = False

# Try to import InquirerPy for enhanced features
try:
    from inquirerpy import inquirer
    from inquirerpy.prompts.input import InputPrompt
    from inquirerpy.base import InquirerPyPrompt
    INQUIRERPY_AVAILABLE = True
except ImportError:
    INQUIRERPY_AVAILABLE = False

@dataclass
class AutocompleteState:
    """State management for autocomplete interaction"""
    input_text: str = ""
    cursor_position: int = 0
    suggestions: List[Tuple[str, float]] = None
    selected_index: int = 0
    show_suggestions: bool = False
    completed_text: Optional[str] = None

class AutocompletePrompt:
    """
    Interactive prompt with real-time autocomplete suggestions
    """
    
    def __init__(self, 
                 console: Console,
                 get_suggestions: Callable[[str], List[Tuple[str, float]]],
                 prompt_text: str = "> ",
                 max_suggestions: int = 10):
        
        self.console = console
        self.get_suggestions = get_suggestions
        self.prompt_text = prompt_text
        self.max_suggestions = max_suggestions
        
        self.state = AutocompleteState()
        
        # Keyboard shortcuts
        self.shortcuts = {
            'tab': self._handle_tab,
            'up': self._handle_up,
            'down': self._handle_down,
            'left': self._handle_left,
            'right': self._handle_right,
            'enter': self._handle_enter,
            'escape': self._handle_escape,
            'backspace': self._handle_backspace,
            'delete': self._handle_delete,
            'ctrl-c': self._handle_ctrl_c,
            'ctrl-d': self._handle_ctrl_d,
            'ctrl-w': self._handle_ctrl_w,
            'ctrl-u': self._handle_ctrl_u,
            'ctrl-k': self._handle_ctrl_k,
            'ctrl-a': self._handle_home,
            'ctrl-e': self._handle_end,
        }
    
    def _render_prompt(self) -> Table:
        """Render the prompt with current input and cursor"""
        table = Table(show_header=False, box=None, padding=0, expand=True)
        table.add_column()
        
        # Build prompt line with cursor
        prompt_line = Text(self.prompt_text, style="bold green")
        
        # Add input text with cursor visualization
        input_text = self.state.input_text
        cursor_pos = self.state.cursor_position
        
        if cursor_pos < len(input_text):
            # Cursor in middle of text
            before_cursor = input_text[:cursor_pos]
            at_cursor = input_text[cursor_pos]
            after_cursor = input_text[cursor_pos + 1:]
            
            prompt_line.append(before_cursor)
            prompt_line.append(at_cursor, style="reverse")
            prompt_line.append(after_cursor)
        else:
            # Cursor at end
            prompt_line.append(input_text)
            prompt_line.append("█", style="blink")
        
        table.add_row(prompt_line)
        
        return table
    
    def _render_suggestions(self) -> Optional[Panel]:
        """Render autocomplete suggestions panel"""
        if not self.state.show_suggestions or not self.state.suggestions:
            return None
        
        # Create suggestions table
        suggestions_table = Table(show_header=False, box=None, padding=(0, 1))
        suggestions_table.add_column("", width=2)  # Selection indicator
        suggestions_table.add_column("Command", style="cyan")
        suggestions_table.add_column("Confidence", style="dim")
        
        for i, (command, confidence) in enumerate(self.state.suggestions[:self.max_suggestions]):
            # Selection indicator
            indicator = "▶" if i == self.state.selected_index else " "
            
            # Highlight matching portion
            input_lower = self.state.input_text.lower()
            if input_lower in command.lower():
                idx = command.lower().index(input_lower)
                highlighted = Text()
                highlighted.append(command[:idx])
                highlighted.append(command[idx:idx+len(self.state.input_text)], style="bold yellow")
                highlighted.append(command[idx+len(self.state.input_text):])
                command_display = highlighted
            else:
                command_display = Text(command)
            
            # Confidence as percentage
            confidence_str = f"{confidence * 100:.0f}%"
            
            # Style selected row
            style = "bold" if i == self.state.selected_index else None
            suggestions_table.add_row(
                indicator, 
                command_display,
                confidence_str,
                style=style
            )
        
        # Add navigation hints
        hints = "[Tab] Complete  [↑↓] Navigate  [Enter] Accept  [Esc] Cancel"
        
        return Panel(
            suggestions_table,
            title="Suggestions",
            subtitle=hints,
            border_style="blue" if self.state.show_suggestions else "dim",
            expand=False
        )
    
    async def _update_suggestions(self):
        """Update suggestions based on current input"""
        if len(self.state.input_text) > 0:
            try:
                # Get suggestions from callback
                suggestions = await asyncio.create_task(
                    asyncio.to_thread(self.get_suggestions, self.state.input_text)
                )
                
                if suggestions:
                    self.state.suggestions = suggestions
                    self.state.show_suggestions = True
                    self.state.selected_index = 0
                else:
                    self.state.show_suggestions = False
            except Exception:
                self.state.show_suggestions = False
        else:
            self.state.show_suggestions = False
    
    # Keyboard handlers
    
    def _handle_tab(self) -> bool:
        """Handle Tab key - complete with selected suggestion"""
        if self.state.show_suggestions and self.state.suggestions:
            selected_command = self.state.suggestions[self.state.selected_index][0]
            self.state.input_text = selected_command
            self.state.cursor_position = len(selected_command)
            self.state.show_suggestions = False
        return False  # Continue
    
    def _handle_up(self) -> bool:
        """Handle Up arrow - navigate suggestions up"""
        if self.state.show_suggestions and self.state.suggestions:
            self.state.selected_index = max(0, self.state.selected_index - 1)
        return False
    
    def _handle_down(self) -> bool:
        """Handle Down arrow - navigate suggestions down"""
        if self.state.show_suggestions and self.state.suggestions:
            max_index = min(len(self.state.suggestions) - 1, self.max_suggestions - 1)
            self.state.selected_index = min(max_index, self.state.selected_index + 1)
        return False
    
    def _handle_left(self) -> bool:
        """Handle Left arrow - move cursor left"""
        self.state.cursor_position = max(0, self.state.cursor_position - 1)
        return False
    
    def _handle_right(self) -> bool:
        """Handle Right arrow - move cursor right"""
        self.state.cursor_position = min(len(self.state.input_text), self.state.cursor_position + 1)
        return False
    
    def _handle_enter(self) -> bool:
        """Handle Enter key - accept input or suggestion"""
        if self.state.show_suggestions and self.state.suggestions:
            # Accept selected suggestion
            selected_command = self.state.suggestions[self.state.selected_index][0]
            self.state.completed_text = selected_command
        else:
            # Accept current input
            self.state.completed_text = self.state.input_text
        return True  # Done
    
    def _handle_escape(self) -> bool:
        """Handle Escape key - hide suggestions or cancel"""
        if self.state.show_suggestions:
            self.state.show_suggestions = False
            return False
        else:
            # Cancel input
            self.state.completed_text = None
            return True
    
    def _handle_backspace(self) -> bool:
        """Handle Backspace - delete character before cursor"""
        if self.state.cursor_position > 0:
            self.state.input_text = (
                self.state.input_text[:self.state.cursor_position - 1] +
                self.state.input_text[self.state.cursor_position:]
            )
            self.state.cursor_position -= 1
        return False
    
    def _handle_delete(self) -> bool:
        """Handle Delete - delete character at cursor"""
        if self.state.cursor_position < len(self.state.input_text):
            self.state.input_text = (
                self.state.input_text[:self.state.cursor_position] +
                self.state.input_text[self.state.cursor_position + 1:]
            )
        return False
    
    def _handle_ctrl_c(self) -> bool:
        """Handle Ctrl+C - cancel input"""
        self.state.completed_text = None
        return True
    
    def _handle_ctrl_d(self) -> bool:
        """Handle Ctrl+D - EOF/exit if empty, delete if not"""
        if len(self.state.input_text) == 0:
            self.state.completed_text = None
            return True
        else:
            return self._handle_delete()
    
    def _handle_ctrl_w(self) -> bool:
        """Handle Ctrl+W - delete word before cursor"""
        if self.state.cursor_position > 0:
            # Find word boundary
            text_before = self.state.input_text[:self.state.cursor_position]
            words = text_before.rsplit(' ', 1)
            if len(words) == 1:
                # Delete everything before cursor
                self.state.input_text = self.state.input_text[self.state.cursor_position:]
                self.state.cursor_position = 0
            else:
                # Delete last word
                new_before = words[0] + ' ' if words[0] else ''
                self.state.input_text = new_before + self.state.input_text[self.state.cursor_position:]
                self.state.cursor_position = len(new_before)
        return False
    
    def _handle_ctrl_u(self) -> bool:
        """Handle Ctrl+U - delete from cursor to beginning"""
        self.state.input_text = self.state.input_text[self.state.cursor_position:]
        self.state.cursor_position = 0
        return False
    
    def _handle_ctrl_k(self) -> bool:
        """Handle Ctrl+K - delete from cursor to end"""
        self.state.input_text = self.state.input_text[:self.state.cursor_position]
        return False
    
    def _handle_home(self) -> bool:
        """Handle Home/Ctrl+A - move cursor to beginning"""
        self.state.cursor_position = 0
        return False
    
    def _handle_end(self) -> bool:
        """Handle End/Ctrl+E - move cursor to end"""
        self.state.cursor_position = len(self.state.input_text)
        return False
    
    def _handle_character(self, char: str) -> bool:
        """Handle regular character input"""
        self.state.input_text = (
            self.state.input_text[:self.state.cursor_position] +
            char +
            self.state.input_text[self.state.cursor_position:]
        )
        self.state.cursor_position += 1
        return False
    
    async def prompt_async(self, initial_text: str = "") -> Optional[str]:
        """Run the interactive autocomplete prompt (async version)"""
        self.state = AutocompleteState(input_text=initial_text, cursor_position=len(initial_text))
        
        if not READCHAR_AVAILABLE:
            # Fallback to simple input without autocomplete
            try:
                return input(self.prompt_text)
            except (KeyboardInterrupt, EOFError):
                return None
        
        # Initial suggestions
        await self._update_suggestions()
        
        # Create live display
        layout = Layout()
        
        with Live(layout, console=self.console, refresh_per_second=30) as live:
            while True:
                # Update display
                prompt_display = self._render_prompt()
                suggestions_display = self._render_suggestions()
                
                if suggestions_display:
                    layout.update(
                        Layout(name="main")
                        .split_column(
                            Layout(prompt_display, size=3),
                            Layout(suggestions_display)
                        )
                    )
                else:
                    layout.update(prompt_display)
                
                # Read keyboard input
                try:
                    key = readchar.readkey()
                    
                    # Map special keys
                    key_mapping = {
                        readchar.key.TAB: 'tab',
                        readchar.key.UP: 'up',
                        readchar.key.DOWN: 'down',
                        readchar.key.LEFT: 'left',
                        readchar.key.RIGHT: 'right',
                        readchar.key.ENTER: 'enter',
                        readchar.key.ESC: 'escape',
                        readchar.key.BACKSPACE: 'backspace',
                        readchar.key.DELETE: 'delete',
                        readchar.key.CTRL_C: 'ctrl-c',
                        readchar.key.CTRL_D: 'ctrl-d',
                        readchar.key.CTRL_W: 'ctrl-w',
                        readchar.key.CTRL_U: 'ctrl-u',
                        readchar.key.CTRL_K: 'ctrl-k',
                        readchar.key.CTRL_A: 'ctrl-a',
                        readchar.key.CTRL_E: 'ctrl-e',
                    }
                    
                    # Handle key
                    done = False
                    if key in key_mapping:
                        handler = self.shortcuts.get(key_mapping[key])
                        if handler:
                            done = handler()
                    elif len(key) == 1 and key.isprintable():
                        done = self._handle_character(key)
                    
                    # Update suggestions after input change
                    if not done:
                        await self._update_suggestions()
                    else:
                        break
                        
                except KeyboardInterrupt:
                    self.state.completed_text = None
                    break
                except Exception:
                    # Continue on error
                    pass
        
        # Clear and return result
        self.console.clear()
        return self.state.completed_text
    
    def prompt(self, initial_text: str = "") -> Optional[str]:
        """Run the interactive autocomplete prompt (sync version)"""
        return asyncio.run(self.prompt_async(initial_text))


class EnhancedAutocompletePrompt(AutocompletePrompt):
    """
    Enhanced autocomplete with InquirerPy integration when available
    """
    
    def __init__(self, 
                 console: Console,
                 get_suggestions: Callable,
                 prompt_text: str = "> ",
                 max_suggestions: int = 10,
                 command_intelligence = None):
        
        super().__init__(console, get_suggestions, prompt_text, max_suggestions)
        self.command_intelligence = command_intelligence
    
    async def prompt_with_intelligence(self, 
                                     context: Optional[Dict[str, Any]] = None,
                                     initial_text: str = "") -> Optional[str]:
        """Enhanced prompt with command intelligence integration"""
        
        if self.command_intelligence and INQUIRERPY_AVAILABLE:
            # Use InquirerPy with autocomplete
            try:
                # Create dynamic completer
                def completer(text):
                    if self.command_intelligence:
                        suggestions = asyncio.run(
                            self.command_intelligence.get_command_suggestions(
                                text,
                                context or {},
                                max_suggestions=self.max_suggestions
                            )
                        )
                        return [s.command for s in suggestions]
                    return []
                
                # Use InquirerPy's autocomplete prompt
                result = inquirer.text(
                    message=self.prompt_text,
                    default=initial_text,
                    completer=completer,
                    multicolumn_complete=True,
                    validate=lambda x: len(x.strip()) > 0,
                    instruction="(Type for suggestions, Tab to complete)"
                ).execute()
                
                # Record successful command
                if result and self.command_intelligence:
                    await self.command_intelligence.record_command_execution(
                        command=result,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                # Fallback to basic autocomplete
                pass
        
        # Use basic autocomplete
        result = await self.prompt_async(initial_text)
        
        # Record command if available
        if result and self.command_intelligence:
            await self.command_intelligence.record_command_execution(
                command=result,
                success=True
            )
        
        return result


def create_autocomplete_prompt(console: Console,
                              command_intelligence = None) -> EnhancedAutocompletePrompt:
    """Factory function to create autocomplete prompt with command intelligence"""
    
    # Create suggestion callback
    async def get_suggestions(partial: str) -> List[Tuple[str, float]]:
        if command_intelligence:
            # Use command intelligence for suggestions
            from ..intelligence.command_intelligence import CommandContext
            
            context = CommandContext(
                current_directory=os.getcwd(),
                recent_commands=[],
                available_providers=[],
                user_skill_level='intermediate'
            )
            
            suggestions = await command_intelligence.get_command_suggestions(
                partial,
                context,
                max_suggestions=10
            )
            
            return [(s.command, s.confidence) for s in suggestions]
        else:
            # Fallback to no suggestions
            return []
    
    return EnhancedAutocompletePrompt(
        console=console,
        get_suggestions=lambda p: asyncio.run(get_suggestions(p)),
        command_intelligence=command_intelligence
    )