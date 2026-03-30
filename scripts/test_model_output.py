"""
Test what models actually output for acetaminophen abstracts
"""

import json

from app import analyze_abstract_with_llm
from config import get_config

config = get_config()

# Get a real acetaminophen abstract from the results
print("="*80)
print("TESTING MODEL OUTPUT FOR ACETAMINOPHEN")
print("="*80)

# Read a sample abstract from study records
with open('results/acetaminophen/study_records.jsonl') as f:
    records = [json.loads(line) for line in f]

# Find a record with reasoning (meaning it was analyzed)
for record in records[:5]:
    title = record.get('metadata', {}).get('title', '')
    abstract = record.get('metadata', {}).get('abstract', '')
    reasoning = record.get('kc_analysis', {}).get('reasoning', '')

    if reasoning and len(reasoning) > 50:  # Has substantial reasoning
        print("\n📄 Testing with paper:")
        print(f"   Title: {title[:100]}...")
        print(f"   Abstract length: {len(abstract)} chars")
        print(f"   Reasoning length: {len(reasoning)} chars")

        # Check what KC statuses are in the record
        print("\n   Current KC statuses in record:")
        for i in range(1, 13):
            kc_status = record.get('kc_analysis', {}).get(f'kc{i}_status', 'NOT_FOUND')
            print(f"      KC{i}: {kc_status}")

        # Now test what the model actually outputs
        print("\n   🔬 Testing model output with llama3.2...")
        try:
            analysis, prompt_hash = analyze_abstract_with_llm(
                abstract_text=abstract[:2000] if abstract else "No abstract available",
                title=title,
                model_name="llama3.2",
                chemical_name="acetaminophen",
                search_terms=["acetaminophen", "paracetamol", "apap"]
            )

            print("\n   ✅ Model analysis received:")
            print(f"      Prompt hash: {prompt_hash[:50]}...")
            print("\n   KC Statuses from model:")
            for i in range(1, 13):
                kc_status = analysis.get(f'kc{i}_status', 'NOT_FOUND')
                print(f"      KC{i}: {kc_status}")

            print("\n   Reasoning from model:")
            reasoning_model = analysis.get('reasoning', 'N/A')
            print(f"      {reasoning_model[:200]}..." if len(str(reasoning_model)) > 200 else f"      {reasoning_model}")

            print("\n   Causal links from model:")
            causal_links = analysis.get('causal_links', [])
            print(f"      Found {len(causal_links)} causal links")
            for link in causal_links[:3]:
                print(f"         {link}")

            print("\n   Evidence quotes from model:")
            evidence_quotes = analysis.get('evidence_quotes', {})
            print(f"      Found quotes for {len(evidence_quotes)} KCs")
            for kc, quotes in list(evidence_quotes.items())[:3]:
                print(f"         {kc}: {len(quotes)} quotes")
                if quotes:
                    print(f"            Example: {quotes[0][:100]}...")

            break  # Only test first one

        except Exception as e:
            print(f"   ❌ Error testing model: {e}")
            import traceback
            traceback.print_exc()
            break

print("\n" + "="*80)
print("COMPARISON COMPLETE")
print("="*80)
