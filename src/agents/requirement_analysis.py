from src.core.llm import MistralLLM
from src.core.models import AnalysisResult, FunctionalRequirement, TechnicalImplication

class RequirementAnalysisAgent:
    def __init__(self, llm: MistralLLM):
        self.llm = llm
        self.system_prompt = """
        You are an expert Requirement Analysis Agent specialized in Oracle Database applications.
        Your goal is to analyze Business Requirement Documents (BRD) and Change Requests (CR) to extract structured requirements for Oracle SQL and PL/SQL development.
        However, if the user input is a GENERAL QUESTION or GREETING (e.g., "What is AI?", "Hello"), do NOT extract requirements. Instead, provide a helpful answer in the 'conversation_response' field and leave other fields empty.
        
        Constraints:
        - Do NOT propose schema or code changes.
        - Do NOT guess proprietary platform behavior.
        - Be conservative and precise.
        
        IF BRD/CR, extract into the following 15 specific categories:
        1. Business Objective
        2. Client Type
        3. Regulatory Constraints
        4. In-Scope
        5. Out-of-Scope
        6. Functional Requirements
        7. Non-Functional Requirements
        8. Business Rules
        9. Data Requirements
        10. Interface Requirements
        11. UI/UX Requirements
        12. Reporting Requirements
        13. Audit & Logging
        14. Historical Issues
        15. Risk Tolerance

        Analyze the provided BRD text and output the result in the specified JSON format.
        """

    def analyze(self, brd_text: str) -> AnalysisResult:
        prompt = f"""
        {self.system_prompt}
        
        --- BRD CONTENT START ---
        {brd_text}
        --- BRD CONTENT END ---
        
        Extract the requirements now.
        """
        
        # In a real scenario, we might want to chunk large BRDs, but for now we assume it fits in context.
        return self.llm.generate_structured(prompt, AnalysisResult)

if __name__ == "__main__":
    import os
    import sys
    import argparse

    # Argument parser for file input
    parser = argparse.ArgumentParser(description="Analyze a BRD file.")
    parser.add_argument("file_path", nargs="?", help="Path to the BRD text file")
    args = parser.parse_args()

    # Mock LLM for testing if no key provided
    if not os.environ.get("MISTRAL_API_KEY"):
        print("WARNING: MISTRAL_API_KEY not set. Using mock response.")
        
        class MockLLM:
            def generate_structured(self, prompt, model):
                return AnalysisResult(
                    business_objective="Mock Objective",
                    client_type="Mock Client",
                    regulatory_constraints=[],
                    in_scope=[],
                    out_of_scope=[],
                    functional_rules=[
                        FunctionalRequirement(id="FR-001", description="Mock functionality", acceptance_criteria=["Criteria 1"], priority="High")
                    ],
                    data_entities=[],
                    known_fcis_touchpoints=[],
                    customization_constraints=[],
                    performance_sla="N/A",
                    audit_and_logging=[],
                    historical_issues=[],
                    risk_tolerance="Low"
                )
        
        llm = MockLLM()
    else:
        llm = MistralLLM()
        
    agent = RequirementAnalysisAgent(llm)
    
    if args.file_path:
        try:
            with open(args.file_path, "r", encoding="utf-8") as f:
                brd_text = f.read()
            print(f"Analyzing BRD from: {args.file_path}...\n", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: File not found at {args.file_path}", file=sys.stderr)
            sys.exit(1)
    else:
        # Default sample if no file provided
        print("No file provided. Using default sample BRD...\n", file=sys.stderr)
        brd_text = "The system should allow users to create a new fund type 'Hedge Fund' with specific fee structures."

    result = agent.analyze(brd_text)
    print(result.model_dump_json(indent=2))
