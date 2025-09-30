#!/usr/bin/env python3
"""
Healthcare AI V2 - OpenRouter API Key Setup
=============================================

This script helps you set up the OpenRouter API key required for AI functionality.
"""

import os
import sys

def setup_openrouter_api_key():
    """Guide user through OpenRouter API key setup"""
    
    print("🔑 Healthcare AI V2 - OpenRouter API Key Setup")
    print("=" * 60)
    print()
    
    # Check if already set
    current_key = os.getenv("OPENROUTER_API_KEY")
    if current_key:
        print(f"✅ OpenRouter API key is already set: {current_key[:10]}...")
        response = input("Do you want to update it? (y/N): ").strip().lower()
        if response != 'y':
            print("👍 Keeping existing API key.")
            return True
        print()
    
    print("🚀 To get your Healthcare AI V2 chatbot working, you need an OpenRouter API key.")
    print()
    print("📋 Steps to get your API key:")
    print("1. Go to: https://openrouter.ai/")
    print("2. Sign up for a free account")
    print("3. Go to 'API Keys' in your dashboard")
    print("4. Create a new API key")
    print("5. Copy the key (starts with 'sk-or-v1-')")
    print()
    
    # Get API key from user
    api_key = input("🔑 Paste your OpenRouter API key here: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return False
    
    if not api_key.startswith('sk-or-v1-'):
        print("⚠️  Warning: API key doesn't look like a valid OpenRouter key (should start with 'sk-or-v1-')")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    # Test the API key
    print("\n🧪 Testing API key...")
    try:
        import asyncio
        from src.ai.openrouter_client import OpenRouterClient
        
        async def test_key():
            client = OpenRouterClient()
            # Override the API key for testing
            client.api_key = api_key
            
            try:
                # Make a simple test request
                response = await client.make_request(
                    model_tier="free",
                    system_prompt="You are a helpful assistant.",
                    user_prompt="Say 'Hello' if you can hear me.",
                    max_tokens=50
                )
                return response.success
            except Exception as e:
                print(f"❌ API key test failed: {e}")
                return False
            finally:
                await client.close()
        
        # Run test
        test_result = asyncio.run(test_key())
        
        if test_result:
            print("✅ API key test successful!")
        else:
            print("❌ API key test failed. Please check your key.")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not test API key: {e}")
        print("   This might be normal if dependencies aren't installed yet.")
    
    # Set environment variable
    print(f"\n📝 Setting environment variable...")
    
    # Add to current environment
    os.environ["OPENROUTER_API_KEY"] = api_key
    
    # Create .env file
    env_file = ".env"
    env_lines = []
    
    # Read existing .env if it exists
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add the API key line
    api_key_line = f"OPENROUTER_API_KEY={api_key}\n"
    found = False
    
    for i, line in enumerate(env_lines):
        if line.startswith("OPENROUTER_API_KEY="):
            env_lines[i] = api_key_line
            found = True
            break
    
    if not found:
        env_lines.append(api_key_line)
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.writelines(env_lines)
    
    print(f"✅ API key saved to {env_file}")
    print(f"✅ Environment variable set for current session")
    
    print("\n🚀 Setup complete! Your Healthcare AI V2 chatbot should now work.")
    print("\n📋 Next steps:")
    print("1. Track API key: python track_api_key.py (check your setup)")
    print("2. Run: python test_model_update.py (to test the system)")
    print("3. Run: python demo_agent_system.py (for interactive demo)")
    print("4. Start the API: python -m uvicorn src.main:app --reload")
    print("5. Test chat: curl -X POST http://localhost:8000/api/v1/agents/chat -H 'Content-Type: application/json' -d '{\"message\": \"Hello!\"}'")
    
    print("\n🔍 Monitor your API key:")
    print("   python track_api_key.py --status     (check configuration)")
    print("   python track_api_key.py --test       (test connection)")
    print("   python track_api_key.py --json       (JSON output)")
    print("   curl http://localhost:8000/api/v1/health/api-key-status  (via API)")
    
    print("\n💡 For persistent setup across shell sessions, add this to your shell profile:")
    print(f"   export OPENROUTER_API_KEY={api_key[:10]}***[masked]")
    
    return True

def check_setup():
    """Check if the setup is complete"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        print("✅ OpenRouter API key is set and configured")
        return True
    else:
        print("❌ OpenRouter API key is not set")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_setup()
    else:
        try:
            success = setup_openrouter_api_key()
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print("\n\n👋 Setup cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n💥 Setup failed: {e}")
            sys.exit(1)
