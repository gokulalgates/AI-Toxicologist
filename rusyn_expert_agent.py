#!/usr/bin/env python3
"""
Engineering a High-Fidelity Computational Toxicologist: 
A System Architecture for Implementing the Key Characteristics of Human Hepatotoxicants
via Large Language Model Agents

Based on the Rusyn Expert Protocol specification.
"""

import logging
import sys
import ollama
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import httpx
import json
import re

logger = logging.getLogger(__name__)


# Configuration: Model Selection
# We default to a capable instruct model. Ensure this is pulled via `ollama pull llama3`
MODEL_NAME = "llama3"


# --- Pydantic Models for Structured Outputs ---
class KCAnalysis(BaseModel):
    """Structured output model for KC analysis."""
    chemical_name: str = Field(..., description="Name of the chemical being analyzed")
    detected_kcs: List[str] = Field(
        ..., 
        description="List of KCs identified (e.g., 'KC1', 'KC5')"
    )
    mechanistic_reasoning: str = Field(
        ..., 
        description="Detailed explanation linking mechanisms to KCs"
    )
    acute_vs_chronic: str = Field(
        ..., 
        description="Differentiation of time-dependent effects (acute vs chronic)"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score between 0.0 and 1.0"
    )
    causal_pathways: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Causal relationships between KCs (e.g., [{'source': 'KC1', 'target': 'KC7', 'mechanism': 'NAPQI binds mitochondrial proteins'}]"
    )


# --- The Rusyn Expert System Prompt ---
# This prompt embeds the 12 KCs and the "Few-Shot" examples derived from the paper.
SYSTEM_PROMPT = """You are an AI Expert in Hepatotoxicity, explicitly programmed with the framework from 'Key Characteristics of Human Hepatotoxicants' by Rusyn et al. (2021). 
Your goal is to identify and characterize liver toxicity hazards based strictly on mechanistic data.

**The 12 Key Characteristics (KCs) Definitions:**

1. **Bioactivation (KC1):** Is the agent reactive or metabolized to reactive moieties? (e.g., electrophiles binding to macromolecules). The liver is the primary organ for biotransformation. While metabolism generally facilitates excretion, it can paradoxically increase toxicity through bioactivation. Toxicity is often not inherent to the parent compound but arises from its conversion into reactive electrophiles that form covalent adducts with cellular macromolecules (proteins, DNA). Sensitivity is modulated by species, sex, and age-dependent differences in enzyme expression (e.g., CYP450 induction).

2. **Cell Death (KC2):** Causes apoptosis, necrosis, or necroptosis. Cell death is the ultimate determinant of liver injury outcomes. This encompasses apoptosis (death receptor-induced, mediated by mitochondrial/lysosomal permeabilization), necrosis (resulting from direct damage or pathogen infiltration), necroptosis, and pyroptosis. The agent must link the cell type injured to the functional deficit: hepatocyte injury impairs metabolism, while cholangiocyte (bile duct) injury triggers cholestasis.

3. **Proliferation (KC3):** Affects liver cell proliferation or tissue regeneration. The liver possesses a unique capacity for regeneration, which can be pathological or adaptive. Proliferation occurs via two primary pathways: compensatory proliferation in response to cell death (KC2) or direct induction of cell cycle mechanisms by receptor ligands (e.g., AhR, PPARs). Critical nuance: extensive or chronic injury can overwhelm the regenerative capacity of mature hepatocytes, necessitating the activation of liver progenitor cells.

4. **Transport (KC4):** Disrupts transport function. Hepatocytes are polarized cells that rely on transporters to move bile acids, nutrients, and xenobiotics against concentration gradients. Disruption occurs through direct inhibition of transporter proteins (e.g., BSEP, MRPs, NTCP) or alteration of their expression and subcellular localization. This KC is a primary driver of intracellular accumulation of toxic substrates (endobiotics or xenobiotics), often serving as the precursor to cholestasis.

5. **Oxidative Stress (KC5):** Induces oxidative stress. This represents a failure of homeostatic balance between pro-oxidant and antioxidant systems. Defined by an imbalance where the production of Reactive Oxygen Species (ROS) and reactive nitrogen species overwhelms cellular antioxidants (e.g., glutathione). Links to downstream effects: damage to lipids (peroxidation), proteins, and DNA, as well as triggering stress signaling pathways (KC8) and mitochondrial dysfunction (KC7).

6. **Immune Response (KC6):** Triggers immune-mediated responses. The liver acts as an immunological organ, containing a rich population of innate immune cells. This involves activation of innate cells (Kupffer cells, neutrophils, NK cells) and the adaptive immune system. Navigate the duality: inflammation can magnify injury (e.g., cytokine storms) but is also obligate for repair (e.g., neutrophils clearing necrotic debris). Specific attention to idiosyncratic Drug-Induced Liver Injury (DILI), which involves adaptive immune responses linked to HLA polymorphisms.

7. **Mitochondrial Dysfunction (KC7):** Causes mitochondrial dysfunction. Mitochondria are central to hepatocyte viability and are frequent targets of toxicity. This includes uncoupling of the electron transport chain, loss of membrane potential (MMP), inhibition of beta-oxidation, and depletion of ATP. KC7 is a "node" that connects initial insults (KC1) to cell death (KC2). It is a critical feature of toxicants causing fatty liver and cytolysis.

8. **Stress Signaling (KC8):** Activates stress signaling pathways. Cells possess complex sensor networks to detect and respond to macromolecular damage. This refers to activation of kinase cascades (e.g., JNK, MAPK) and the Unfolded Protein Response (UPR) in the endoplasmic reticulum (ER). These pathways are decision points; JNK activation, for instance, can drive mitochondrial permeabilization and apoptosis, serving as the bridge between stress (KC5) and death (KC2).

9. **Cholestasis (KC9):** Causes cholestasis. This is the ONLY organ-specific KC, referring to the impairment of bile formation or flow. Cholestasis results from functional failure of transporters (KC4) or physical injury to the bile duct epithelium (cholangiocytes). Identify clinical markers such as elevated bile acids or bilirubin as evidence. It distinguishes "cholestatic" injury patterns from "hepatocellular" ones.

10. **Cytoskeleton (KC10):** Disrupts cellular cytoskeleton. The structural integrity of hepatocytes relies on a dynamic network of microtubules and intermediate filaments. Toxicants may cause disassembly or cross-linking of keratin networks or actin filaments. Look for histological keywords like "ballooning degeneration" or "Mallory-Denk bodies," which are hallmarks of cytoskeletal collapse.

11. **Fibrosis (KC11):** Causes liver fibrosis. Fibrosis is the defining feature of chronic, progressive liver injury. This process is driven by activation of hepatic stellate cells (HSCs), which transdifferentiate into myofibroblasts and deposit excessive extracellular matrix (collagen). KC11 is a chronic outcome resulting from sustained inflammation (KC6) and cell death (KC2). It represents a failure of the resolution phase of repair.

12. **Metabolism (KC12):** Disrupts liver metabolism. The liver is the body's metabolic hub, and toxicity often manifests as metabolic derangement. Interference with lipid (fatty acid oxidation, synthesis), protein, or carbohydrate metabolism. Identify "Steatosis" (fatty liver) as a primary manifestation of KC12. This KC often precedes inflammation (steatohepatitis) and is tightly linked to mitochondrial dysfunction (KC7).

**Operational Rules for Analysis:**

- **Clustering:** Identify mechanistic clusters. (e.g., KC1 -> KC7 -> KC5 -> KC2 is a common cytotoxic pathway for Acetaminophen).
- **Temporality:** Distinguish between Acute effects (KC2, KC9) and Chronic effects (KC11, KC3 failure). Acute liver injury, particularly DILI, is characterized by rapid cascade: Bioactivation (KC1) → Mitochondrial Dysfunction (KC7) → Oxidative Stress (KC5) → Cell Death (KC2). Chronic toxicity reflects sustained insult: persistent Cell Death (KC2) → chronic Immune Response (KC6) → failure of regeneration (KC3) → Fibrosis (KC11).
- **Evidence Weight:** A chemical need not exhibit all KCs. Focus on the weight of evidence.
- **Uncertainty:** If a mechanism is unknown, state 'No evidence available'.
- **Chain-of-Thought:** Think step-by-step: First, identify if the chemical is bioactivated (KC1). Second, determine the primary cellular target (Mitochondria KC7, Transporters KC4). Third, determine the outcome (Death KC2 vs Fibrosis KC11). Finally, synthesize this into a risk profile.

**Benchmark Examples:**

- **Acetaminophen:** High relevance for KC1 (NAPQI bioactivation via CYP2E1), KC7 (Mitochondrial dysfunction - NAPQI binds mitochondrial proteins), KC5 (Oxidative Stress - glutathione depletion), KC2 (Necrosis - mitochondrial permeability transition), KC8 (JNK stress signaling), KC6 (Immune response for repair), KC3 (Compensatory proliferation), KC4 (Transport disruption), KC12 (Metabolic disruption). KC1 is the obligate initiating step. This is the archetype of acute necrosis.

- **Vinyl Chloride:** High relevance for KC1 (Bioactivation to chloroethylene oxide), KC12 (Steatohepatitis/TASH), KC11 (Fibrosis - chronic outcome), KC7 (Mitochondrial dysfunction), KC5 (Oxidative stress), KC6 (Chronic inflammation). This exemplifies chronic fibrosis progression. KC12 (steatosis) and KC11 (fibrosis) are dominant outcomes of chronic exposure.

- **Amoxicillin-Clavulanate:** High relevance for KC6 (Adaptive Immune/DILI - hapten formation), KC9 (Cholestasis - biliary epithelium targeting), KC1 (Reactive metabolites as haptens), KC2 (Delayed cell death). This represents immune idiosyncrasy, distinct from direct necrosis. Distinguish this "cholestatic/immune" profile from the "oxidative/necrotic" profile of APAP.

- **TCDD (Dioxins):** High relevance for KC3 (Proliferation via AhR activation), KC11 (Fibrosis), KC8 (Stress signaling via AhR), KC12 (Metabolic disruption), KC2 (Cell death), KC5 (Oxidative stress), KC6 (Inflammation), KC7 (Mitochondrial effects). Distinct due to lack of traditional metabolic activation (KC1 absent). Toxicity is driven by direct receptor activation rather than direct chemical reactivity.

**Your Analysis Format:**

When analyzing a chemical, provide:
1. The chemical name
2. List of detected KCs (e.g., ["KC1", "KC5", "KC7", "KC2"])
3. Detailed mechanistic reasoning explaining how each KC applies
4. Acute vs Chronic classification with temporal dynamics
5. Confidence score (0.0-1.0) based on evidence quality
6. Causal pathways showing how KCs interconnect (e.g., KC1 → KC7 → KC2)

Remember: You are strictly governed by this framework. Do not use general internet knowledge where it conflicts with this framework."""


class HepatotoxAgent:
    """
    A class-based wrapper for the Ollama client to manage state and enforce the expert persona.
    Implements the Rusyn Expert Protocol for high-fidelity hepatotoxicity analysis.
    """
    
    def __init__(self, model: str = MODEL_NAME):
        """
        Initialize the HepatotoxAgent.
        
        Args:
            model (str): Name of the Ollama model to use (default: "llama3")
        """
        self.model = model
        # Initialize the conversation history with the System Prompt.
        # This ensures the model 'remembers' the Rusyn framework throughout the session.
        self.history: List[Dict[str, str]] = [
            {
                'role': 'system',
                'content': SYSTEM_PROMPT
            }
        ]
    
    def chat(self, user_input: str, use_streaming: bool = True, use_structured: bool = False):
        """
        Sends user input to the model, streams the response to the console, and updates history.
        
        Args:
            user_input (str): User's question or chemical to analyze
            use_streaming (bool): Whether to stream the response (better UX)
            use_structured (bool): Whether to request structured JSON output (requires Pydantic)
            
        Returns:
            str: Full response from the model (or KCAnalysis object if use_structured=True)
        """
        # 1. Append the user's message to the history
        self.history.append({'role': 'user', 'content': user_input})
        
        try:
            # 2. Prepare options for the Ollama API
            options = {
                'temperature': 0.2,  # Lower temperature for more factual/deterministic outputs
                'num_ctx': 8192      # Ensure context window is large enough for the prompt + discussion
            }
            
            # 3. Call the Ollama API
            if use_streaming:
                # Stream=True provides a better UX for long scientific explanations
                stream = ollama.chat(
                    model=self.model,
                    messages=self.history,
                    stream=True,
                    options=options
                )
                
                full_response = ""
                
                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        full_response += content
                
                logger.info("Agent: %s", full_response)
            else:
                # Non-streaming mode
                response = ollama.chat(
                    model=self.model,
                    messages=self.history,
                    stream=False,
                    options=options
                )
                
                full_response = response['message']['content']
                logger.info("Agent: %s", full_response)
            
            # 4. Append the assistant's full response to the history
            # This is crucial for multi-turn reasoning (e.g., follow-up questions).
            self.history.append({'role': 'assistant', 'content': full_response})
            
            # 5. If structured output was requested, try to parse it
            if use_structured:
                try:
                    parsed = self._parse_structured_output(full_response)
                    return parsed
                except Exception as e:
                    logger.warning("Could not parse structured output: %s", e)
                    logger.info("Returning raw response instead.")
                    return full_response
            
            return full_response
            
        except httpx.ConnectError as e:
            # Handle connection errors (Ollama service not running)
            error_msg = (
                f"Could not connect to Ollama service. "
                f"Is 'ollama serve' running? Start it with: ollama serve. "
                f"Original error: {e}"
            )
            logger.error("%s", error_msg)
            # Remove the user message from history since it failed
            self.history.pop()
            raise ConnectionError("Ollama service not available") from e
            
        except ollama.ResponseError as e:
            # Handle specific API errors (e.g., model not found)
            if '404' in str(e) or 'not found' in str(e).lower():
                error_msg = (
                    f"Model '{self.model}' not found. "
                    f"Please pull the model first: ollama pull {self.model}. "
                    f"Original error: {e}"
                )
            else:
                error_msg = f"Ollama API error. Original error: {e}"
            logger.error("%s", error_msg)
            # Remove the user message from history since it failed
            self.history.pop()
            raise RuntimeError(f"Ollama API error: {str(e)}") from e
            
        except Exception as e:
            # Handle any other unexpected errors
            error_msg = (
                f"Unexpected error: {e}. "
                f"Please check your Ollama installation and model availability."
            )
            logger.error("%s", error_msg)
            # Remove the user message from history since it failed
            self.history.pop()
            raise
    
    def _parse_structured_output(self, response_text: str) -> Optional[KCAnalysis]:
        """
        Parse structured output from the model response.
        Attempts to extract JSON matching the KCAnalysis schema.
        
        Args:
            response_text (str): Raw response from the model
            
        Returns:
            KCAnalysis: Parsed structured output, or None if parsing fails
        """
        # Try to extract JSON from the response
        # Look for JSON code blocks first
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")
        
        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        
        # Validate and create Pydantic model
        return KCAnalysis(**data)
    
    def analyze_chemical(self, chemical_name: str, use_structured: bool = False) -> Dict:
        """
        Analyze a chemical and return structured results.
        This is a convenience method that formats the query appropriately.
        
        Args:
            chemical_name (str): Name of the chemical to analyze
            use_structured (bool): Whether to return structured KCAnalysis object
            
        Returns:
            dict or KCAnalysis: Analysis results with detected KCs and reasoning
        """
        if use_structured:
            schema = KCAnalysis.model_json_schema()
            schema_str = json.dumps(schema, indent=2)
            query = (
                f"Analyze the hepatotoxicity of {chemical_name}. "
                f"Identify which Key Characteristics apply and explain the mechanistic pathways. "
                f"\n\nReturn your analysis as a JSON object matching this schema:\n{schema_str}"
            )
        else:
            query = (
                f"Analyze the hepatotoxicity of {chemical_name}. "
                f"Identify which Key Characteristics apply and explain the mechanistic pathways."
            )
        
        response = self.chat(query, use_streaming=True, use_structured=use_structured)
        
        if use_structured and isinstance(response, KCAnalysis):
            return response
        
        # Extract structured information from the response
        return {
            'chemical': chemical_name,
            'response': response,
            'history_length': len(self.history)
        }
    
    def reset(self):
        """Reset the conversation history while keeping the system prompt."""
        self.history = [
            {
                'role': 'system',
                'content': SYSTEM_PROMPT
            }
        ]
        logger.info("Conversation history reset. System prompt retained.")
    
    def get_history_summary(self) -> Dict:
        """Get a summary of the conversation history."""
        return {
            'total_messages': len(self.history),
            'user_messages': sum(1 for msg in self.history if msg['role'] == 'user'),
            'assistant_messages': sum(1 for msg in self.history if msg['role'] == 'assistant'),
            'system_prompt_length': len(self.history[0]['content']) if self.history else 0
        }


def main():
    """Main execution loop for the CLI chatbot."""
    logger.info("=" * 80)
    logger.info("Engineering a High-Fidelity Computational Toxicologist")
    logger.info("Rusyn Expert Protocol Implementation")
    logger.info("=" * 80)
    logger.info("This agent implements the Key Characteristics framework from Rusyn et al. (2021).")
    logger.info("It functions as an expert toxicologist for hepatotoxicity classification.")
    logger.info("Commands:")
    logger.info("  - Type a chemical name or question (e.g., 'Analyze acetaminophen')")
    logger.info("  - Type 'reset' to clear conversation history")
    logger.info("  - Type 'exit' or 'quit' to end the session")
    logger.info("  - Type 'help' for more information")
    
    # Check if Ollama is available
    try:
        # Try to list models to verify connection
        models = ollama.list()
        logger.info("Connected to Ollama service")
        if models.get('models'):
            available_models = [m['name'] for m in models['models']]
            logger.info("Available models: %s", ", ".join(available_models[:5]))
            if MODEL_NAME not in available_models:
                logger.warning("Default model '%s' not found.", MODEL_NAME)
                logger.info("  Available models: %s", ", ".join(available_models))
                logger.info("  You can pull it with: ollama pull %s", MODEL_NAME)
    except Exception as e:
        logger.warning("Could not verify Ollama connection: %s", e)
        logger.info("  Make sure Ollama is running: ollama serve")
    
    # Initialize agent
    try:
        agent = HepatotoxAgent(model=MODEL_NAME)
    except Exception as e:
        logger.error("Error initializing agent: %s", e)
        logger.error("Please ensure Ollama is running and the model is available.")
        return
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_in = input("\033[1mYou:\033[0m ").strip()
            
            # Handle commands
            if user_in.lower() in ['exit', 'quit', 'q']:
                logger.info("Thank you for using the Rusyn Expert Agent. Goodbye!")
                break
            
            if user_in.lower() == 'reset':
                agent.reset()
                continue
            
            if user_in.lower() == 'help':
                logger.info("=" * 80)
                logger.info("HELP: Rusyn Expert Protocol Agent")
                logger.info("=" * 80)
                logger.info("This agent analyzes chemicals based on 12 Key Characteristics (KCs):")
                logger.info("  KC1: Bioactivation/Reactive metabolites")
                logger.info("  KC2: Cell Death")
                logger.info("  KC3: Proliferation/Regeneration")
                logger.info("  KC4: Transport Disruption")
                logger.info("  KC5: Oxidative Stress")
                logger.info("  KC6: Immune Response")
                logger.info("  KC7: Mitochondrial Dysfunction")
                logger.info("  KC8: Stress Signaling")
                logger.info("  KC9: Cholestasis (organ-specific)")
                logger.info("  KC10: Cytoskeleton Disruption")
                logger.info("  KC11: Fibrosis")
                logger.info("  KC12: Metabolism Disruption")
                logger.info("Example queries:")
                logger.info("  - 'Analyze acetaminophen'")
                logger.info("  - 'What are the key characteristics of vinyl chloride?'")
                logger.info("  - 'Compare the mechanisms of TCDD and amoxicillin-clavulanate'")
                logger.info("  - 'What about chronic exposure to carbon tetrachloride?'")
                logger.info("=" * 80)
                continue
            
            if not user_in:
                continue
            
            # Process the query
            agent.chat(user_in)
            
        except KeyboardInterrupt:
            logger.info("Session interrupted by user.")
            break
        except ConnectionError:
            logger.info("Please start Ollama service and try again.")
            logger.info("Run: ollama serve")
            break
        except Exception as e:
            logger.error("Error: %s", e)
            logger.info("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()
