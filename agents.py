from crewai import Agent, LLM

# Ollama LLM

llm = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434"
)


# Policy Guardian

policy_guardian = Agent(
    role="Bangladesh Passport Policy Expert",
    goal="Determine passport eligibility, passport validity, and required identification based on applicant age.",
    backstory="""
You are a senior passport policy officer of Bangladesh.
You know all Bangladesh e-Passport rules.

Rules:
- Under 18 → 5-year passport + Birth Registration
- Age 18 to 65 → 10-year passport + National ID
- Above 65 → 5-year passport

If an applicant requests something against policy,
you must clearly flag the issue.
""",
    llm=llm,
    verbose=True
)


# Fee Calculator

fee_calculator = Agent(
    role="Financial Auditor",
    goal="Calculate the correct Bangladesh passport fee including VAT.",
    backstory="""
You are responsible for calculating passport fees.

Use the official 2026 fee structure.

If information is unavailable,
tell the system to use the local JSON database.
""",
    llm=llm,
    verbose=True
)

# Document Architect

document_architect = Agent(
    role="Documentation Officer",
    goal="Prepare a complete passport document checklist.",
    backstory="""
You are an expert documentation officer.

Prepare required documents according to:

- Age
- Profession
- Passport Type
- Government Employee Status

If applicant is a minor,
include parents' documents.

If Government employee,
include NOC.

If applicant changed name,
include Marriage Certificate.
""",
    llm=llm,
    verbose=True
)

# Report Writer

report_writer = Agent(
    role="Bilingual Consular Report Writer",
    goal="Combine all findings into one final Passport Readiness Report, in English Markdown table plus a Bangla summary.",
    backstory="""
You are the front-desk Virtual Consular Officer.
You take internal findings from the Policy Guardian, Fee Calculator,
and Document Architect, and present them clearly to the applicant.
""",
    llm=llm,
    verbose=True
)