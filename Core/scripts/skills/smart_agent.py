import os
from pathlib import Path
from openai import OpenAI
from dotenv import dotenv_values

# Robustly find the .env file at the Project Root
REPO_ROOT = Path(__file__).parent.parent.parent.parent
ENV_PATH = REPO_ROOT / ".env"

class SmartAgent:
    def __init__(self, handbook_path: Path):
        # Load OpenAI Key
        config = dotenv_values(ENV_PATH)
        self.api_key = config.get("OPENAI_API_KEY")
        
        if not self.api_key:
            # Fallback to os.environ
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        self.handbook_path = handbook_path
        
        # Configure the OpenAI client (Default OpenAI endpoint)
        self.client = OpenAI(api_key=self.api_key)
        
        # Using GPT-4o-mini for optimal speed and reasoning
        self.model = "gpt-4o-mini"

    def get_handbook_rules(self):
        """Read the Rules of Engagement from Obsidian."""
        try:
            if self.handbook_path.exists():
                return self.handbook_path.read_text(encoding='utf-8')
            return "Be professional and polite."
        except Exception:
            return "Be professional and polite."

    def analyze_and_draft(self, message_content: str, metadata: dict):
        """Analyze message and generate a ultra-short reply based on handbook rules."""
        rules = self.get_handbook_rules()
        
        system_prompt = f"""
You are a Personal AI Employee (Digital FTE). 
Draft a response based on the rules below.

CRITICAL RULES FROM COMPANY HANDBOOK:
{rules}

STRICT CONSTRAINT:
Your response MUST be exactly ONE short sentence long. Do not include signatures, greetings, or extra words.

INSTRUCTIONS:
1. Acknowledge receipt or answer the question directly.
2. If sensitive, state you are waiting for human approval.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Incoming Message Content: {message_content}"}
                ],
                max_tokens=50 # Strict limit to save tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating draft: {e}"

if __name__ == "__main__":
    agent = SmartAgent(REPO_ROOT / "AI_Employee_Vault" / "Company_Handbook.md")
    test_msg = "Hey, I need to pay the invoice for the last project. Can you send me the bank details?"
    print(f"Testing Ultra-Short Agent with message: '{test_msg}'\n")
    print("--- AI RESPONSE ---")
    print(agent.analyze_and_draft(test_msg, {"source": "Test", "from": "Client", "subject": "Invoice"}))
    print("-------------------")
