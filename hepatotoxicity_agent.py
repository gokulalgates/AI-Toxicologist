"""
CLI-based chatbot agent for Key Characteristics (KCs) of Human Hepatotoxicants
Based on the framework by Rusyn et al.
Enhanced with RAG (Retrieval-Augmented Generation) and multi-model ensemble.
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from config import get_config

# Add scripts directory to path for imports
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from agent_pubmed_downloader import AgentPubMedDownloader
from agent_rag_system import AgentRAGSystem


class HepatotoxicityAgent:
    """Expert agent for classifying chemicals based on Key Characteristics of Hepatotoxicants."""

    def __init__(self, model_names=None, use_rag=True, rag_top_k=5, email=None, api_key=None):
        """
        Initialize the hepatotoxicity agent with multi-model support and RAG.
        
        Args:
            model_names (list): List of Ollama model names to use (ensemble)
            use_rag (bool): Whether to use RAG for retrieval-augmented generation
            rag_top_k (int): Number of top abstracts to retrieve for RAG
            email (str): Email for NCBI Entrez API
            api_key (str): Optional NCBI API key for higher rate limits
        """
        config = get_config()

        # Default models (use available ones)
        if model_names is None:
            model_names = config.llm.default_models

        self.model_names = model_names
        self.use_rag = use_rag
        self.email = email or config.search.entrez_email
        self.api_key = api_key
        self.chat_history = []
        self.system_prompt = self._get_system_prompt()

        # Initialize LLM models
        self.models = {}
        for model_name in self.model_names:
            try:
                self.models[model_name] = ChatOllama(
                    model=model_name,
                    temperature=config.llm.temperature
                )
            except Exception as e:
                print(f"Warning: Could not initialize model {model_name}: {e}")

        if not self.models:
            raise RuntimeError("No models could be initialized. Please ensure Ollama is running and models are available.")

        # Initialize RAG system if enabled
        self.rag_system = None
        self.pubmed_downloader = None
        if use_rag:
            try:
                self.rag_system = AgentRAGSystem(top_k=rag_top_k)
                self.pubmed_downloader = AgentPubMedDownloader(email=self.email, api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize RAG system: {e}")
                print("Continuing without RAG...")
                self.use_rag = False

        # Cache for downloaded abstracts per chemical
        self.chemical_abstracts_cache = {}

        # Initialize with system message
        self.chat_history.append(SystemMessage(content=self.system_prompt))

    def _extract_chemical_name(self, query: str) -> Optional[str]:
        """
        Extract chemical name from user query.
        Simple heuristic: look for capitalized words or common chemical patterns.
        
        Args:
            query (str): User query
            
        Returns:
            str: Extracted chemical name or None
        """
        # Common patterns for chemical queries
        patterns = [
            r"predict.*toxicity.*of\s+([A-Z][A-Za-z0-9]+)",  # "predict toxicity of PFOA"
            r"analyze\s+([A-Z][A-Za-z0-9]+)",  # "analyze Acetaminophen"
            r"what.*about\s+([A-Z][A-Za-z0-9]+)",  # "what about PFOA"
            r"([A-Z][A-Za-z0-9]+).*hepatotox",  # "PFOA hepatotoxicity"
            r"([A-Z][A-Za-z0-9]+).*toxicity",  # "PFOA toxicity"
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                chemical = match.group(1).strip()
                # Filter out common false positives
                if chemical.lower() not in ['the', 'this', 'that', 'what', 'how', 'predict', 'analyze']:
                    return chemical

        # Fallback: look for capitalized words (likely chemical names)
        words = query.split()
        for word in words:
            # Check if word starts with capital and has alphanumeric characters
            if word and word[0].isupper() and word.replace('.', '').replace('-', '').isalnum():
                if len(word) > 2 and word.lower() not in ['the', 'this', 'that', 'what', 'how']:
                    return word

        return None

    def _download_chemical_abstracts(self, chemical_name: str, max_results=200):
        """
        Download PubMed abstracts for a specific chemical.
        
        Args:
            chemical_name (str): Name of the chemical
            max_results (int): Maximum number of abstracts to download
        """
        if not self.pubmed_downloader:
            print("Warning: PubMed downloader not initialized")
            return []

        # Check cache first
        if chemical_name in self.chemical_abstracts_cache:
            print(f"Using cached abstracts for {chemical_name}")
            return self.chemical_abstracts_cache[chemical_name]

        print(f"\nDownloading PubMed abstracts for {chemical_name}...")
        abstracts = self.pubmed_downloader.search_chemical_abstracts(
            chemical_name=chemical_name,
            max_results=max_results
        )

        if abstracts:
            # Cache the abstracts
            self.chemical_abstracts_cache[chemical_name] = abstracts

            # Get current number of abstracts before adding
            start_index = len(self.rag_system.abstracts)

            # Add to RAG system
            self.rag_system.add_abstracts(abstracts)

            # Generate embeddings only for new abstracts
            print(f"Generating embeddings for {len(abstracts)} new abstracts...")
            self.rag_system.generate_embeddings(start_index=start_index)

            print(f"RAG system updated with {len(abstracts)} abstracts for {chemical_name}\n")

        return abstracts

    def _get_system_prompt(self):
        """Generate the system prompt with expert knowledge about Key Characteristics."""
        return """You are an expert toxicologist specializing in Key Characteristics (KCs) of Human Hepatotoxicants based on the framework by Rusyn et al.

Your role is to analyze user-provided chemical names or mechanistic data and classify the evidence into 12 specific Key Characteristics (KCs).

KEY CHARACTERISTICS DEFINITIONS:

KC1 (Reactive): Is reactive or metabolized to reactive moieties (electrophiles) [Source: Rusyn et al.].

KC2 (Cell Death): Causes apoptosis (mitochondrial/lysosomal permeabilization) or necrosis.

KC3 (Proliferation): Affects liver cell proliferation or tissue regeneration (compensatory or direct induction).

KC4 (Transport): Disrupts transport function (inhibits transporters or alters expression/localization).

KC5 (Oxidative Stress): Induces oxidative stress (ROS imbalance, antioxidant depletion).

KC6 (Immune Response): Triggers immune-mediated responses (innate or adaptive, Kupffer cell activation).

KC7 (Mitochondrial Dysfunction): Causes mitochondrial dysfunction (loss of membrane potential, ATP depletion, uncoupling).

KC8 (Stress Signaling): Activates stress signaling pathways (kinase cascades like JNK, ER stress).

KC9 (Cholestasis): Causes cholestasis (bile acid accumulation or duct injury). Note: This is the only liver-specific KC.

KC10 (Cytoskeleton): Disrupts cellular cytoskeleton (keratin networks, ballooning, Mallory-Denk bodies).

KC11 (Fibrosis): Causes liver fibrosis (stellate cell activation, collagen deposition).

KC12 (Metabolism): Disrupts liver metabolism (lipids, proteins, urea cycle).

OPERATIONAL RULES (CONSTRAINT CHECKLIST):

1. There is NO minimum number of KCs required to label a chemical as a hepatotoxicant. Some chemicals have many KCs (like Acetaminophen), while others have few.

2. KC9 (Cholestasis) is the ONLY organ-specific characteristic. All other KCs (like mitochondrial dysfunction) can occur in other organs as well.

3. Your task is to systematically identify and organize the mechanistic data provided by the user into these 12 KC categories.

4. When analyzing a chemical, provide clear reasoning for each KC that applies, citing specific evidence from the user's input and any provided research abstracts.

5. If insufficient information is provided, clearly state which KCs cannot be determined and why.

6. When research evidence is provided, cite the PMIDs and integrate this evidence into your analysis.

Respond in a clear, structured manner that helps users understand how their chemical or data maps to these Key Characteristics."""

    def _retrieve_context(self, query: str) -> str:
        """
        Retrieve relevant context from PubMed abstracts using RAG.
        Automatically downloads abstracts for the chemical if detected.
        
        Args:
            query (str): User query
            
        Returns:
            str: Formatted context string
        """
        if not self.use_rag or not self.rag_system:
            return ""

        try:
            # Extract chemical name from query
            chemical_name = self._extract_chemical_name(query)

            # Download abstracts for this chemical if found
            if chemical_name:
                self._download_chemical_abstracts(chemical_name)

            # Retrieve relevant abstracts
            relevant_abstracts = self.rag_system.retrieve_relevant_abstracts(query)

            if relevant_abstracts:
                context = self.rag_system.format_context(relevant_abstracts)
                return context
            else:
                return ""

        except Exception as e:
            print(f"Warning: RAG retrieval failed: {str(e)}")
            return ""

    def _query_model(self, model_name: str, messages: List) -> Optional[str]:
        """
        Query a single model.
        
        Args:
            model_name (str): Name of the model
            messages (list): List of message objects
            
        Returns:
            str: Model response or None if error
        """
        if model_name not in self.models:
            print(f"Warning: Model {model_name} not available")
            return None

        try:
            model = self.models[model_name]
            response = model.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Error with model {model_name}: {str(e)}")
            return None

    def _ensemble_response(self, responses: List[str]) -> str:
        """
        Combine responses from multiple models (simple averaging/consensus).
        
        Args:
            responses (list): List of model responses
            
        Returns:
            str: Combined response
        """
        if not responses:
            return "Error: No valid responses from models."

        # Filter out None responses
        valid_responses = [r for r in responses if r is not None]

        if not valid_responses:
            return "Error: All models failed to respond."

        # For now, return the first valid response
        # In a more sophisticated implementation, you could:
        # - Use voting/consensus
        # - Weight by model confidence
        # - Combine insights from all models
        if len(valid_responses) == 1:
            return valid_responses[0]

        # Simple combination: use first response, note that multiple models were consulted
        combined = f"[Analysis using {len(valid_responses)} models]\n\n"
        combined += valid_responses[0]

        # Add note about ensemble if multiple models
        if len(valid_responses) > 1:
            combined += f"\n\n[Note: This response was generated using an ensemble of {len(valid_responses)} models for improved accuracy.]"

        return combined

    def chat(self, user_input: str) -> str:
        """
        Process user input and return agent response using RAG and ensemble models.
        
        Args:
            user_input (str): User's question or chemical information
            
        Returns:
            str: Agent's response
        """
        # Retrieve relevant context if RAG is enabled
        context = ""
        if self.use_rag:
            context = self._retrieve_context(user_input)

        # Prepare user message with context
        if context:
            enhanced_input = f"{user_input}\n\n{context}"
        else:
            enhanced_input = user_input

        # Add user message to history
        self.chat_history.append(HumanMessage(content=enhanced_input))

        # Query all models (ensemble)
        responses = []
        for model_name in self.model_names:
            response = self._query_model(model_name, self.chat_history)
            if response:
                responses.append(response)

        # Combine responses
        assistant_message = self._ensemble_response(responses)

        # Add assistant response to history
        self.chat_history.append(AIMessage(content=assistant_message))

        return assistant_message

    def reset_chat(self):
        """Reset chat history while keeping system prompt."""
        self.chat_history = [SystemMessage(content=self.system_prompt)]

    def download_pubmed_abstracts(self, max_results=1000):
        """
        Download PubMed abstracts for RAG system.
        
        Args:
            max_results (int): Maximum number of abstracts to download
        """
        if not self.pubmed_downloader:
            print("Error: PubMed downloader not initialized")
            return

        print("Downloading PubMed abstracts...")
        abstracts = self.pubmed_downloader.search_hepatotoxicity_abstracts(max_results=max_results)

        if abstracts:
            self.pubmed_downloader.save_abstracts(abstracts, "pubmed_abstracts.json")

            # Reload RAG system
            if self.rag_system:
                self.rag_system.load_abstracts("pubmed_abstracts.json")
                print("Generating embeddings...")
                self.rag_system.generate_embeddings()
                self.rag_system.save_embeddings("embeddings.npy")
                self.use_rag = True
                print("RAG system ready!")
        else:
            print("No abstracts downloaded. Please check your query or network connection.")


def main():
    """Main execution loop for the CLI chatbot."""
    print("=" * 70)
    print("Hepatotoxicity Key Characteristics (KCs) Expert Agent")
    print("Enhanced with RAG and Multi-Model Ensemble")
    print("Based on the framework by Rusyn et al.")
    print("=" * 70)
    print("\nThis agent will help you classify chemicals based on 12 Key Characteristics.")
    print("The agent will automatically download PubMed abstracts for chemicals you query.")
    print("Commands:")
    print("  - Type your question (e.g., 'predict the toxicity of PFOA')")
    print("  - Type 'exit' to quit.\n")

    config = get_config()

    # Get email for NCBI API
    email = input(f"Enter your email for NCBI Entrez API (default: {config.search.entrez_email}): ").strip()
    if not email:
        email = config.search.entrez_email

    # Try to load API key from file
    api_key = None
    api_key_files = ["APIKEY", ".ncbi_api_key", "ncbi_api_key.txt", "api_key.txt"]

    for key_file in api_key_files:
        key_path = os.path.join(os.path.dirname(__file__), key_file)
        if os.path.exists(key_path):
            try:
                with open(key_path) as f:
                    api_key = f.read().strip()
                if api_key:
                    print(f"Loaded API key from {key_file}")
                    break
            except Exception as e:
                print(f"Warning: Could not read API key from {key_file}: {str(e)}")

    # If no API key file found, ask user
    if not api_key:
        api_key_input = input("Enter your NCBI API key (optional, press Enter to skip): ").strip()
        if api_key_input:
            api_key = api_key_input
            print("API key provided. Using higher rate limits.")
        else:
            print("No API key provided. Using standard rate limits.")
            print("Tip: Create a file named 'APIKEY', '.ncbi_api_key', or 'ncbi_api_key.txt' in this folder to auto-load your API key.")
    else:
        print("Using API key for higher rate limits.")

    # Initialize agent with RAG and multiple models
    try:
        agent = HepatotoxicityAgent(
            model_names=config.llm.default_models,
            use_rag=True,
            rag_top_k=5,
            email=email,
            api_key=api_key
        )
    except Exception as e:
        print(f"Error initializing agent: {e}")
        print("Please ensure Ollama is running and models are available.")
        return

    print("\nRAG system ready! The agent will automatically download PubMed abstracts")
    print("for chemicals mentioned in your queries.\n")

    # Main interaction loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            # Check for exit command
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nThank you for using the Hepatotoxicity KC Expert Agent. Goodbye!")
                break

            # Skip empty input
            if not user_input:
                continue

            # Get agent response
            print("\nAgent: ", end="", flush=True)
            response = agent.chat(user_input)
            print(response)
            print()  # Add blank line for readability

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Please try again or type 'exit' to quit.\n")


if __name__ == "__main__":
    main()
