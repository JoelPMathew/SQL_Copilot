from src.core.llm import MistralLLM
from src.core.models import ImpactAssessment, CodeGenerationResponse, GeneratedFile

class CodeGenerationAgent:
    def __init__(self, llm: MistralLLM, model: str = "codestral-latest"):
        self.llm = llm
        self.model = model
        self.system_prompt = """
        You are an Expert Oracle PL/SQL Developer specialized in Oracle Investor Services (FCIS).
        Your task is to generate production-ready code based on the Technical Impact Assessment provided.
        
        Guidelines:
        1. **Naming Conventions**: Follow consistent Oracle naming conventions.
        2. **Modularity**: Create separate files for DDL (Tables/Views), Logic (Packages/Procedures/Functions), and Data (DML).
        3. **Safety**: Use safe deployment patterns (CREATE OR REPLACE, existence checks).
        4. **Comments**: Add detailed comments explaining the business logic.
        5. **Error Handling**: Implement robust PL/SQL exception handling.
        
        Input: Impact Assessment JSON.
        Output: A list of files with their content.
        """

    def generate(self, impact: ImpactAssessment) -> CodeGenerationResponse:
        prompt = f"""
        {self.system_prompt}
        
        --- IMPACT ASSESSMENT START ---
        {impact.model_dump_json(indent=2)}
        --- IMPACT ASSESSMENT END ---
        
        Generate the required PL/SQL code, DDLs, and DMLs now.
        """
        
        # We use a specialized faster model (Codestral) for code generation
        return self.llm.generate_structured(prompt, CodeGenerationResponse, model_override=self.model)
