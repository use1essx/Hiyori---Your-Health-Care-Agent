#!/usr/bin/env python3
"""
Healthcare AI V2 - Interactive Chat Client
Real user chat interface to test the AI system
"""

import asyncio
import json
import uuid
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
import colorama
from colorama import Fore, Back, Style
import readline  # For better input experience

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

class HealthcareAIChatClient:
    """Interactive chat client for Healthcare AI V2"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session_id = str(uuid.uuid4())
        self.user_id = f"test_user_{int(datetime.now().timestamp())}"
        self.conversation_history = []
        self.session = None
        self.current_agent = None
        
        # Agent type mapping
        self.agent_types = {
            "1": "illness_monitor",
            "2": "mental_health", 
            "3": "safety_guardian",
            "4": "wellness_coach"
        }
        
        self.agent_names = {
            "illness_monitor": "慧心助手 (Illness Monitor)",
            "mental_health": "小星星 (Mental Health)",
            "safety_guardian": "Safety Guardian",
            "wellness_coach": "Wellness Coach"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def check_server_status(self) -> bool:
        """Check if the Healthcare AI server is running"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"{Fore.GREEN}✓ Server is running: {data.get('status', 'Unknown')}")
                    return True
                else:
                    print(f"{Fore.RED}✗ Server returned status {response.status}")
                    return False
        except Exception as e:
            print(f"{Fore.RED}✗ Cannot connect to server: {e}")
            print(f"{Fore.YELLOW}Make sure the server is running on {self.base_url}")
            return False
    
    def display_welcome(self):
        """Display welcome message and instructions"""
        print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*70)
        print(f"{Fore.CYAN}{Style.BRIGHT}🏥 Healthcare AI V2 - Interactive Chat Client")
        print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*70)
        print(f"{Fore.WHITE}Session ID: {Fore.YELLOW}{self.session_id}")
        print(f"{Fore.WHITE}User ID: {Fore.YELLOW}{self.user_id}")
        print()
        print(f"{Fore.GREEN}Available Commands:")
        print(f"{Fore.WHITE}  /help     - Show this help message")
        print(f"{Fore.WHITE}  /agents   - List available AI agents")
        print(f"{Fore.WHITE}  /switch   - Switch to a specific agent")
        print(f"{Fore.WHITE}  /status   - Check system status")
        print(f"{Fore.WHITE}  /history  - Show conversation history")
        print(f"{Fore.WHITE}  /clear    - Clear conversation history")
        print(f"{Fore.WHITE}  /quit     - Exit the chat client")
        print()
        print(f"{Fore.MAGENTA}Available AI Agents:")
        for num, agent_type in self.agent_types.items():
            agent_name = self.agent_names.get(agent_type, agent_type.title())
            print(f"{Fore.WHITE}  {num}. {Fore.CYAN}{agent_name}")
        print()
        print(f"{Fore.GREEN}Just start typing to chat with the AI!")
        print(f"{Fore.YELLOW}The system will automatically select the best agent for your question.")
        print("="*70)
        print()
    
    async def send_message(self, message: str, preferred_agent: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to the Healthcare AI system"""
        payload = {
            "user_input": message,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "language_preference": "auto",
            "preferred_agent": preferred_agent
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/agents/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"HTTP {response.status}: {error_text}",
                        "success": False
                    }
        except Exception as e:
            return {
                "error": f"Connection error: {str(e)}",
                "success": False
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/health/detailed") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}", "success": False}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}", "success": False}
    
    def format_response(self, response: Dict[str, Any]) -> str:
        """Format the AI response for display"""
        if not response.get("success", True):
            return f"{Fore.RED}Error: {response.get('error', 'Unknown error')}"
        
        # Extract response data
        agent_type = response.get("agent_type", "unknown")
        agent_name = self.agent_names.get(agent_type, agent_type.title())
        content = response.get("response", response.get("content", "No response"))
        confidence = response.get("confidence", 0)
        urgency = response.get("urgency_level", "low")
        processing_time = response.get("processing_time_ms", 0)
        
        # Update current agent
        self.current_agent = agent_type
        
        # Format the response
        output = []
        output.append(f"{Fore.BLUE}┌─ {Style.BRIGHT}{agent_name} {Style.RESET_ALL}{Fore.BLUE}─")
        output.append(f"{Fore.BLUE}│ {Fore.GREEN}Confidence: {confidence:.1%} {Fore.BLUE}│ {Fore.YELLOW}Urgency: {urgency} {Fore.BLUE}│ {Fore.CYAN}Time: {processing_time}ms")
        output.append(f"{Fore.BLUE}└─")
        output.append("")
        
        # Format the main content with proper line wrapping
        content_lines = content.split('\n')
        for line in content_lines:
            if len(line) > 80:
                # Simple word wrap
                words = line.split(' ')
                current_line = ""
                for word in words:
                    if len(current_line + word + " ") > 80:
                        output.append(f"{Fore.WHITE}{current_line.strip()}")
                        current_line = word + " "
                    else:
                        current_line += word + " "
                if current_line.strip():
                    output.append(f"{Fore.WHITE}{current_line.strip()}")
            else:
                output.append(f"{Fore.WHITE}{line}")
        
        # Add HK facilities if present
        hk_facilities = response.get("hk_facilities", [])
        if hk_facilities:
            output.append("")
            output.append(f"{Fore.MAGENTA}🏥 Hong Kong Healthcare Facilities:")
            for facility in hk_facilities[:3]:  # Show top 3
                name = facility.get("name_en", "Unknown")
                district = facility.get("district", "Unknown")
                services = facility.get("services_offered", [])
                output.append(f"{Fore.CYAN}  • {name} ({district})")
                if services:
                    output.append(f"{Fore.WHITE}    Services: {', '.join(services[:3])}")
        
        # Add suggested actions if present
        suggested_actions = response.get("suggested_actions", [])
        if suggested_actions:
            output.append("")
            output.append(f"{Fore.GREEN}💡 Suggested Actions:")
            for action in suggested_actions[:3]:
                output.append(f"{Fore.WHITE}  • {action}")
        
        return "\n".join(output)
    
    def handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if should continue, False if should exit"""
        command = command.lower().strip()
        
        if command == "/help":
            self.display_welcome()
            return True
        
        elif command == "/agents":
            print(f"{Fore.MAGENTA}Available AI Agents:")
            for num, agent_type in self.agent_types.items():
                agent_name = self.agent_names.get(agent_type, agent_type.title())
                current = " (current)" if agent_type == self.current_agent else ""
                print(f"{Fore.WHITE}  {num}. {Fore.CYAN}{agent_name}{Fore.YELLOW}{current}")
            return True
        
        elif command == "/switch":
            print(f"{Fore.MAGENTA}Select an agent:")
            for num, agent_type in self.agent_types.items():
                agent_name = self.agent_names.get(agent_type, agent_type.title())
                print(f"{Fore.WHITE}  {num}. {Fore.CYAN}{agent_name}")
            
            choice = input(f"{Fore.GREEN}Enter agent number (1-4): ").strip()
            if choice in self.agent_types:
                selected_agent = self.agent_types[choice]
                agent_name = self.agent_names.get(selected_agent, selected_agent.title())
                print(f"{Fore.GREEN}✓ Switched to {agent_name}")
                self.current_agent = selected_agent
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1-4.")
            return True
        
        elif command == "/status":
            print(f"{Fore.YELLOW}Checking system status...")
            asyncio.create_task(self._show_status())
            return True
        
        elif command == "/history":
            if not self.conversation_history:
                print(f"{Fore.YELLOW}No conversation history yet.")
            else:
                print(f"{Fore.MAGENTA}Conversation History:")
                for i, entry in enumerate(self.conversation_history, 1):
                    print(f"{Fore.CYAN}{i}. You: {Fore.WHITE}{entry['user']}")
                    print(f"   {Fore.GREEN}AI:  {Fore.WHITE}{entry['ai'][:100]}...")
            return True
        
        elif command == "/clear":
            self.conversation_history.clear()
            print(f"{Fore.GREEN}✓ Conversation history cleared.")
            return True
        
        elif command in ["/quit", "/exit"]:
            print(f"{Fore.YELLOW}Goodbye! Thanks for testing Healthcare AI V2! 👋")
            return False
        
        else:
            print(f"{Fore.RED}Unknown command: {command}")
            print(f"{Fore.WHITE}Type /help for available commands.")
            return True
    
    async def _show_status(self):
        """Show system status (async helper)"""
        status = await self.get_system_status()
        if status.get("success", True):
            print(f"{Fore.GREEN}✓ System Status: {status.get('status', 'Unknown')}")
            components = status.get("components", {})
            for component, info in components.items():
                status_color = Fore.GREEN if info.get("healthy") else Fore.RED
                print(f"  {status_color}• {component}: {info.get('status', 'Unknown')}")
        else:
            print(f"{Fore.RED}✗ Could not get system status: {status.get('error')}")
    
    async def chat_loop(self):
        """Main chat loop"""
        print(f"{Fore.GREEN}🚀 Starting chat session...")
        print(f"{Fore.WHITE}Type your message and press Enter. Use /help for commands.")
        print()
        
        while True:
            try:
                # Get user input
                user_input = input(f"{Fore.GREEN}You: {Fore.WHITE}").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    should_continue = self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue
                
                # Send message to AI
                print(f"{Fore.YELLOW}🤔 Thinking...")
                response = await self.send_message(user_input, self.current_agent)
                
                # Display response
                formatted_response = self.format_response(response)
                print(formatted_response)
                print()
                
                # Store in history
                if response.get("success", True):
                    ai_content = response.get("response", response.get("content", ""))
                    self.conversation_history.append({
                        "user": user_input,
                        "ai": ai_content,
                        "timestamp": datetime.now().isoformat(),
                        "agent": response.get("agent_type", "unknown")
                    })
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Chat interrupted. Type /quit to exit properly.")
                continue
            except EOFError:
                print(f"\n{Fore.YELLOW}Goodbye! Thanks for testing Healthcare AI V2! 👋")
                break
            except Exception as e:
                print(f"{Fore.RED}Unexpected error: {e}")
                continue
    
    async def run(self):
        """Run the chat client"""
        # Check server status
        if not await self.check_server_status():
            print(f"{Fore.RED}Cannot start chat client - server is not available.")
            print(f"{Fore.YELLOW}Please start the Healthcare AI V2 server first:")
            print(f"{Fore.WHITE}  cd healthcare_ai_v2")
            print(f"{Fore.WHITE}  python start.py")
            return
        
        # Display welcome
        self.display_welcome()
        
        # Start chat loop
        await self.chat_loop()

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Healthcare AI V2 Chat Client")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Healthcare AI server URL (default: http://localhost:8000)")
    args = parser.parse_args()
    
    async with HealthcareAIChatClient(args.url) as client:
        await client.run()

if __name__ == "__main__":
    asyncio.run(main())
