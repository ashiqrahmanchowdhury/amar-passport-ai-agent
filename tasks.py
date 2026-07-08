from crewai import Task
from agents import policy_guardian, fee_calculator, document_architect, report_writer
from utils import load_local_db, get_passport_policy, validate_request, calculate_fee, get_documents


def build_tasks(age, profession, pages, delivery, requested_validity, name_change=False):
    """
    Runs the Python-side calculations first (accurate, no LLM guessing),
    then builds the CrewAI task chain around those confirmed numbers.
    """

    db = load_local_db()

    # --- Step 1: Python calculates everything precisely ---
    policy_result = get_passport_policy(age)
    is_valid, validation_msg = validate_request(age, requested_validity)
    fee = calculate_fee(db, pages, policy_result["validity"], delivery)
    documents = get_documents(db, age, profession, name_change)

    # --- Step 2: Build tasks using these confirmed values ---

    eligibility_task = Task(
        description=f"""
An applicant is {age} years old and requested a {requested_validity} passport.

The system has already computed the following from official policy rules:
- Allowed validity: {policy_result['validity']}
- Required ID: {policy_result['required_id']}
- Policy check: {"VALID" if is_valid else "INVALID"} - {validation_msg}
- Additional note: {policy_result['warning'] if policy_result['warning'] else "None"}

As the Policy Guardian, confirm these findings clearly in your own words.
If the request was INVALID, explicitly flag the inconsistency and state
that the corrected validity ({policy_result['validity']}) will be used
for all downstream calculations.
""",
        expected_output="A short, clear statement of: Validity, Required ID, and any Policy Flag/Warning.",
        agent=policy_guardian,
    )

    fee_task = Task(
        description=f"""
Using the CORRECTED validity confirmed by the Policy Guardian
({policy_result['validity']}), the applicant wants a {pages}-page
passport with '{delivery}' delivery.

The system has already looked up the exact fee from the official
2026 database:

Total Fee = {fee if fee is not None else "NOT FOUND in database — flag this to the applicant"} BDT

As the Financial Auditor, confirm this fee clearly. Do NOT recalculate
or guess a different number — simply confirm and present the figure above.
""",
        expected_output="A short confirmation stating the Total Fee in BDT.",
        agent=fee_calculator,
        context=[eligibility_task],
    )

    checklist_task = Task(
        description=f"""
Based on the applicant's age ({age}) and profession ('{profession}'),
and the required ID confirmed by the Policy Guardian, the system has
already generated this exact document checklist:

{documents}

As the Document Architect, present this checklist clearly as a list.
Do not add or remove items unless something is clearly missing given
the required ID above.
""",
        expected_output="A clean bullet-point list of required documents.",
        agent=document_architect,
        context=[eligibility_task],
    )

    report_task = Task(
        description=f"""
Combine the confirmed outputs of the Policy Guardian, Fee Calculator,
and Document Architect into ONE final Passport Readiness Report.

Use EXACTLY these confirmed values — do not change, guess, or add anything:
- Validity: {policy_result['validity']}
- Delivery Type: {delivery}
- Total Fee: {fee if fee is not None else "NOT FOUND"} BDT
- Documents Needed: {documents}
- Policy Flag: {validation_msg if not is_valid else "None"}

IMPORTANT: Ignore any conflicting statements from earlier agent outputs about
age restrictions or inconsistencies. The Policy Flag value given above
({validation_msg if not is_valid else "None"}) is the ONLY authoritative
source of truth. If it says "None", there is NO warning — do not invent one.

Requirements:
1. If there is a Policy Flag (not "None"), show it prominently at the top.
2. Present Validity, Delivery Type, Total Fee, and Documents Needed as a
   Markdown table, in English, using ONLY the values listed above.
3. Do NOT add any extra documents, fees, or notes beyond what is given above.
""",
        expected_output="A Markdown report: warning (if any) + an English Markdown table using only the given values.",
        agent=report_writer,
        context=[eligibility_task, fee_task, checklist_task],
    )

    return [eligibility_task, fee_task, checklist_task, report_task], {
        "policy_result": policy_result,
        "is_valid": is_valid,
        "validation_msg": validation_msg,
        "fee": fee,
        "documents": documents,
    }