from src.core.models import AnalysisResult, ImpactAssessment, AffectedComponent, EffortEstimation
from src.core.llm import MistralLLM

class ImpactAnalysisAgent:
    def __init__(self, llm: MistralLLM):
        self.llm = llm
        self.system_prompt = """
        You are a Senior Oracle Database Solutions Architect.
        Your input is a structured AnalysisResult containing functional requirements.
        Your goal is to perform a technical Impact Analysis.
        
        Strict Guidelines:
        1. Map requirements to technical components (Tables, Views, Packages, APIs, Jobs).
        2. Focus on standard Oracle RDBMS architecture and best practices.
        3. Identify any new modules, services, or modifications to existing schema.
        4. Estimate complexity and risk based on technical feasibility and impact on the database.

        Output strictly in valid JSON matching the ImpactAssessment schema.
        """

    def assess(self, requirements: AnalysisResult) -> ImpactAssessment:
        prompt = f"""
        {self.system_prompt}
        
        --- REQUIREMENTS START ---
        {requirements.model_dump_json(indent=2)}
        --- REQUIREMENTS END ---
        
        Perform the impact analysis now.
        """
        
        return self.llm.generate_structured(prompt, ImpactAssessment)

if __name__ == "__main__":
    import os
    import sys
    import json
    import argparse
    from src.core.models import FunctionalRequirement

    # Argument parser to accept AnalysisResult JSON file
    parser = argparse.ArgumentParser(description="Run Impact Analysis on Requirements JSON.")
    parser.add_argument("file_path", nargs="?", help="Path to the AnalysisResult JSON file")
    args = parser.parse_args()

    # Mock/Real LLM setup
    if not os.environ.get("MISTRAL_API_KEY"):
        print("WARNING: MISTRAL_API_KEY not set. Using mock response.")
        class MockLLM:
            def generate_structured(self, prompt, model):
                return ImpactAssessment(
                    affected_components=[
                        AffectedComponent(component_name="STDT_PF_FUND_MASTER", component_type="Table", nature_of_change="Modify")
                    ],
                    schema_changes=["ALTER TABLE STDT_PF_FUND_MASTER ADD VINTAGE_YEAR DATE"],
                    code_changes=["FCIS_PF_PKG.body"],
                    effort_estimation=EffortEstimation(complexity="Medium", person_days=10, justification="Table change + Logic"),
                    overall_risk="Medium",
                    mitigation_strategies=["Backup before DDL"]
                )
        llm = MockLLM()
    else:
        llm = MistralLLM()

    agent = ImpactAnalysisAgent(llm)

    # Load requirements
    if args.file_path:
        try:
            with open(args.file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            # Reconstruct Pydantic object
            requirements = AnalysisResult(**data)
            print(f"Loaded requirements from {args.file_path}...", file=sys.stderr)
        except Exception as e:
            print(f"Error loading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Check if stdin has data
        if not sys.stdin.isatty():
            try:
                print("Reading requirements from stdin...", file=sys.stderr)
                data = json.load(sys.stdin)
                requirements = AnalysisResult(**data)
            except Exception as e:
                print(f"Error reading from stdin: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("No input file or stdin provided. Using dummy data...", file=sys.stderr)
            # create valid dummy data conforming to the 13-point schema
            requirements = AnalysisResult(
            business_objective="Dummy Objective",
            client_type="Dummy Client",
            regulatory_constraints=[],
            in_scope=[],
            out_of_scope=[],
            functional_rules=[
                 FunctionalRequirement(id="FR-DUMMY", description="Dummy Req", acceptance_criteria=["AC1"], priority="Low")
            ],
            data_entities=[],
            known_fcis_touchpoints=[],
            customization_constraints=[],
            performance_sla="N/A",
            audit_and_logging=[],
            historical_issues=[],
            risk_tolerance="Low"
        )

    # Run assessment
    if requirements.conversation_response:
        print(f"Skipping Impact Analysis: Input was conversational ('{requirements.conversation_response[:50]}...').", file=sys.stderr)
        # return empty impact but valid JSON
        assessment = ImpactAssessment(
            affected_components=[], schema_changes=[], code_changes=[], 
            effort_estimation=EffortEstimation(complexity="N/A", person_days=0, justification="Conversational Input"),
            overall_risk="Low", mitigation_strategies=[]
        )
    else:
        assessment = agent.assess(requirements)
    
    print(assessment.model_dump_json(indent=2))
