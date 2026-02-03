import pandas as pd
import json
import re
import os
from openai import OpenAI

# CONFIG: Load Key from Environment Variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("❌ API Key missing! Set OPENROUTER_API_KEY in your environment.")

def clean_and_parse_json(content):
    """
    Tries to clean markdown and parse JSON. 
    If it fails, it tries to 'repair' common JSON errors.
    """
    # 1. Remove markdown code blocks
    content = content.replace("```json", "").replace("```", "").strip()
    
    # 2. Try parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 3. Simple Repair: Look for the first '[' and the last ']'
    try:
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = content[start:end]
            return json.loads(json_str)
    except:
        pass
        
    return None

def analyze_gaps():
    print("🧠 Loading scraped data...")
    try:
        df = pd.read_csv("zipboard_help_data.csv")
        titles = df['Article Title'].tolist()
        print(f"✅ Loaded {len(titles)} articles.")
    except FileNotFoundError:
        print("❌ Error: zipboard_help_data.csv not found.")
        return

    print("🤖 Sending to NVIDIA Nemotron (via OpenRouter)...")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    prompt = f"""
    You are a Senior QA Automation Engineer for zipBoard.
    
    Here is our COMPLETE list of help articles:
    {titles}

    COMPETITOR INTELLIGENCE:
    Competitors like BugHerd and Marker.io excel in these areas:
    1. CI/CD Integrations (GitHub Actions, GitLab CI)
    2. Accessibility (WCAG) Audits
    3. AdBlocker/Extension Troubleshooting
    4. Enterprise Security (SSO, Whitelisting)
    5. Webhooks & API Automation

    TASK:
    Identify 5 specific documentation gaps where zipBoard is missing content compared to these standards.
    
    RETURN JSON ONLY. No explanation.
    Format:
    [
      {{
        "Gap ID": "GAP-001",
        "Category": "Integrations",
        "Gap Description": "...",
        "Priority": "High",
        "Suggested Title": "..."
      }}
    ]
    """

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://zipboard.co",
                "X-Title": "zipBoard Gap Analysis",
            },
            model="nvidia/nemotron-3-nano-30b-a3b:free", 
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        raw_content = completion.choices[0].message.content
        gaps = clean_and_parse_json(raw_content)

        if not gaps:
            print("❌ Error: Could not parse JSON from model response.")
            print("Raw Response:", raw_content[:500])
            return

        print("\n" + "="*40)
        print("      NVIDIA NEMOTRON ANALYSIS")
        print("="*40)
        for gap in gaps:
            print(f"[{gap['Gap ID']}] {gap['Suggested Title']} ({gap['Priority']})")
            print(f"   -> {gap['Gap Description']}")
            print("-" * 40)

        with open("gap_report.json", "w") as f:
            json.dump(gaps, f, indent=2)
        print("✅ Report saved to gap_report.json")

    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    analyze_gaps()