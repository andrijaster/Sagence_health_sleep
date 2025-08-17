"""
Main script to run automated conversations between patient simulator and sleep consultation agent.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from conversation_orchestrator import ConversationOrchestrator

def main():
    """Main function to run the conversation testing."""
    parser = argparse.ArgumentParser(description="Run automated sleep consultation conversations")
    parser.add_argument("--num-conversations", "-n", type=int, default=5, 
                       help="Number of conversations to run (default: 5)")
    parser.add_argument("--max-turns", "-t", type=int, default=50,
                       help="Maximum turns per conversation (default: 50)")
    parser.add_argument("--output-db", "-o", type=str, default="test/test_agent/conversation_results.db",
                       help="Output database path (default: test/test_agent/conversation_results.db)")
    parser.add_argument("--api-key", "-k", type=str, default=None,
                       help="OpenAI API key (default: from environment)")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OpenAI API key not found. Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    print("🏥 Sleep Consultation Agent Testing")
    print("=" * 50)
    print(f"📊 Configuration:")
    print(f"   Number of conversations: {args.num_conversations}")
    print(f"   Max turns per conversation: {args.max_turns}")
    print(f"   Output database: {args.output_db}")
    print(f"   API key: {'✓ Provided' if api_key else '❌ Missing'}")
    
    try:
        # Initialize orchestrator
        orchestrator = ConversationOrchestrator(api_key, args.output_db)
        
        # Run conversations
        results = orchestrator.run_multiple_conversations(
            num_conversations=args.num_conversations,
            max_turns_per_conversation=args.max_turns
        )
        
        print(f"\n✅ Testing completed! Results saved to {args.output_db}")
        print(f"📝 Use the evaluation script to analyze results:")
        print(f"   python test/test_agent/evaluate_conversations.py --db {args.output_db}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()