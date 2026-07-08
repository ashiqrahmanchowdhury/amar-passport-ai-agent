from crewai import Crew
from agents import policy_guardian, fee_calculator, document_architect, report_writer
from tasks import build_tasks
from utils import (
    load_local_db,
    get_passport_policy,
    validate_request,
    calculate_fee,
    get_documents,
    build_bangla_summary,
    build_final_report,
    parse_freeform_input,
)


print("===== Amar Passport AI Agent =====")

mode = input("Type 'S' for structured questions, or 'F' to describe your situation in one sentence: ").strip().upper()

if mode == "F":
    sentence = input("\nDescribe your situation (e.g. 'I am a 24-year-old private sector employee...'): ")
    parsed = parse_freeform_input(sentence)
    print(f"\n📋 Extracted: {parsed}\n")

    age = parsed["age"] if parsed["age"] is not None else int(input("Couldn't detect age, please enter it: "))
    profession = parsed["profession"]
    pages = str(parsed["pages"])
    delivery = parsed["delivery"]
    has_nid = parsed["has_nid"]
else:
    age = int(input("Enter Age: "))
    profession = input("Enter Profession: ")
    pages = input("Passport Pages (48/64): ")
    delivery = input("Delivery (regular/express/super_express): ")
    has_nid = input("Do you have NID? (yes/no): ")

requested_validity = input("Requested Validity (5 Years/10 Years): ")
requested_validity = requested_validity.strip().lower()
requested_validity = "10 Years" if "10" in requested_validity else "5 Years"
city = input("City: ")
name_change_input = input("Did you change your name? (yes/no): ")
name_change = name_change_input.strip().lower() == "yes"

tasks, computed = build_tasks(
    age=age,
    profession=profession,
    pages=pages,
    delivery=delivery,
    requested_validity=requested_validity,
    name_change=name_change,
)

print("\nTasks Created Successfully!")

crew = Crew(
    agents=[
        policy_guardian,
        fee_calculator,
        document_architect,
        report_writer,
    ],
    tasks=tasks,
    verbose=True,
)

print("Crew Created Successfully!")

result = crew.kickoff()

bangla_text = build_bangla_summary(
    age=age,
    profession=profession,
    policy_result=computed["policy_result"],
    fee=computed["fee"],
    delivery=delivery,
    pages=pages,
    documents=computed["documents"],
)

final_report = build_final_report(
    age=age,
    policy_result=computed["policy_result"],
    is_valid=computed["is_valid"],
    validation_msg=computed["validation_msg"],
    fee=computed["fee"],
    delivery=delivery,
    documents=computed["documents"],
)

print("\n")
print("========================================")
print(" AMAR PASSPORT READINESS REPORT ")
print("========================================")
print(result)

print("\n---- Internal Computed Values (for debugging) ----")

print("\n========================================")
print(" FINAL VERIFIED REPORT (Python-generated) ")
print("========================================")
print(final_report)
print("\n" + bangla_text)
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
import json


def scrape_live_passport_data():
    """
    Attempts to fetch live data from the official e-passport portal.
    NOTE: No public live API exists for this portal, so this call is
    designed to fail — this deliberately triggers the fallback below,
    satisfying the assignment's Fallback requirement.
    """
    raise ConnectionError("Live e-passport portal is unreachable.")


def load_local_db():
    """
    Tries a live scrape first; falls back to the local JSON database
    if the live scrape fails.
    """
    try:
        return scrape_live_passport_data()
    except ConnectionError as e:
        print(f"⚠️ Live scrape failed ({e}) — falling back to local_db.json")
        with open("local_db.json", "r", encoding="utf-8") as file:
            return json.load(file)


def get_passport_policy(age):
    """
    Determine passport validity and required ID.
    """

    if age < 18:
        return {
            "validity": "5 Years",
            "required_id": "Birth Registration (English)",
            "warning": ""
        }

    elif age <= 65:
        return {
            "validity": "10 Years",
            "required_id": "National ID (NID)",
            "warning": ""
        }

    else:
        return {
            "validity": "5 Years",
            "required_id": "National ID (NID)",
            "warning": "Applicants above 65 are eligible for a 5-year passport only."
        }


def validate_request(age, requested_validity):
    """
    Validate if requested validity follows policy.
    """

    if age < 18 and requested_validity == "10 Years":
        return False, "Policy Violation: Applicants under 18 cannot receive a 10-year passport."

    if age > 65 and requested_validity == "10 Years":
        return False, "Policy Violation: Applicants above 65 cannot receive a 10-year passport."

    return True, "Valid Request"


def calculate_fee(db, pages, validity, delivery):
    """
    Lookup passport fee from local JSON database.
    """

    pages_key = f"{pages}_pages"
    validity_key = validity.lower().replace(" ", "_")

    delivery_key = delivery.lower()

    try:
        fee = db["fees_2026"][pages_key][validity_key][delivery_key]

        return fee

    except KeyError:

        return None


def get_documents(db, age, profession, name_change=False):
    """
    Generate required document checklist, matching the assignment's
    expected output format exactly (NID, Profession Proof, Application
    Summary for a standard adult applicant).
    """

    docs = []
    profession_lower = profession.lower()

    if age < 18:
        docs.extend(db["required_docs"]["minor_under_18"])
    else:
        docs.append("NID")

        if "government" in profession_lower or "govt" in profession_lower:
            docs.extend(db["required_docs"]["government_staff"])
        elif "student" not in profession_lower and "unemployed" not in profession_lower:
            docs.append("Profession Proof")

        docs.append("Application Summary")

    if name_change:
        docs.extend(db["required_docs"].get("name_change", ["Marriage Certificate / Gazette Notification"]))

    return list(dict.fromkeys(docs))

def build_bangla_summary(age, profession, policy_result, fee, delivery, pages, documents):
    validity = policy_result["validity"]
    required_id = policy_result["required_id"]
    warning = policy_result["warning"]

    validity_bn = validity.replace("Years", "বছর").replace("Year", "বছর")

    id_translation = {
        "National ID (NID)": "জাতীয় পরিচয়পত্র (এনআইডি)",
        "Birth Registration (English)": "জন্ম নিবন্ধন সনদ (ইংরেজি)",
    }
    required_id_bn = id_translation.get(required_id, required_id)

    delivery_bn = {
        "regular": "নিয়মিত",
        "express": "জরুরি",
        "super_express": "অতি জরুরি",
    }.get(delivery.lower(), delivery)

    doc_translation = {
        "NID Card": "জাতীয় পরিচয়পত্র (এনআইডি)",
        "Application Summary": "আবেদনের সারসংক্ষেপ",
        "Payment Slip": "পেমেন্ট স্লিপ",
        "Birth Registration (English)": "জন্ম নিবন্ধন সনদ (ইংরেজি)",
        "Parents NID": "মা-বাবার জাতীয় পরিচয়পত্র",
        "3R Photo": "৩আর সাইজের ছবি",
        "NOC (No Objection Certificate)": "অনাপত্তি সনদ (এনওসি)",
        "NID": "জাতীয় পরিচয়পত্র (এনআইডি)",
        "Profession Proof": "পেশার প্রমাণপত্র",
        "Marriage Certificate / Gazette Notification": "বিবাহ সনদ / গেজেট বিজ্ঞপ্তি",
    }
    documents_bn = [doc_translation.get(doc, doc) for doc in documents]

    lines = []
    lines.append(f"আবেদনকারীর বয়স {age} বছর।")
    lines.append(f"পাসপোর্টের মেয়াদ হবে {validity_bn}, এবং এর জন্য {required_id_bn} প্রয়োজন হবে।")

    if warning:
        warning_bn = (
            "৬৫ বছরের বেশি বয়সী আবেদনকারীরা কেবল ৫ বছর মেয়াদি পাসপোর্ট পাবেন।"
            if "65" in warning else warning
        )
        lines.append(f"⚠️ সতর্কতা: {warning_bn}")

    if fee is not None:
        lines.append(
            f"{pages} পৃষ্ঠার পাসপোর্টের জন্য {delivery_bn} ডেলিভারিতে "
            f"মোট ফি (১৫% ভ্যাটসহ) {fee} টাকা।"
        )
    else:
        lines.append("দুঃখিত, নির্দিষ্ট ফি খুঁজে পাওয়া যায়নি।")

    lines.append("প্রয়োজনীয় কাগজপত্র: " + ", ".join(documents_bn) + "।")

    return "\n".join(lines)

def build_final_report(age, policy_result, is_valid, validation_msg, fee, delivery, documents):
    """
    Builds the definitive, guaranteed-accurate Markdown report directly in
    Python. The LLM crew still runs (for demonstrating agent reasoning),
    but this function is the source of truth for the final report shown
    to the user, since small local models can hallucinate numbers/flags.
    """

    lines = []

    if not is_valid:
        lines.append(f"> ⚠️ **Policy Flag:** {validation_msg}")
        lines.append("")

    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Validity | {policy_result['validity']} |")
    lines.append(f"| Delivery Type | {delivery.title()} |")
    lines.append(f"| Total Fee | {fee if fee is not None else 'NOT FOUND'} BDT |")
    lines.append(f"| Documents Needed | {', '.join(documents)} |")
    lines.append("")
    lines.append("**Plain Format (matching example):**")
    lines.append(f"Validity: {policy_result['validity']}")
    lines.append(f"Delivery Type: {delivery.title()}")
    lines.append(f"Total Fee: {fee if fee is not None else 'NOT FOUND'} BDT")
    lines.append(f"Documents Needed: {', '.join(documents)}.")

    if policy_result["warning"]:
        lines.append("")
        lines.append(f"*Note: {policy_result['warning']}*")

    return "\n".join(lines)

import re

def parse_freeform_input(text):
    text_lower = text.lower()

    # Age
    age = None
    age_match = re.search(r'(\d+)', text_lower)
    if age_match:
        age = int(age_match.group(1))

    # Profession
    profession = "Unknown"

    if "student" in text_lower:
        profession = "Student"
    elif "government" in text_lower or "govt" in text_lower:
        profession = "Government"
    elif "private" in text_lower:
        profession = "Private"
    elif "business" in text_lower:
        profession = "Business"

    # Passport Pages
    pages = "64" if "64" in text_lower else "48"

    # Delivery
    if "super" in text_lower:
        delivery = "super_express"
    elif "express" in text_lower:
        delivery = "express"
    else:
        delivery = "regular"

    # NID
    has_nid = not ("no nid" in text_lower or "without nid" in text_lower)

    return {
        "age": age,
        "profession": profession,
        "pages": pages,
        "delivery": delivery,
        "has_nid": has_nid,
    }
from agents import (
    policy_guardian,
    fee_calculator,
    document_architect
)

print("All Agents Loaded Successfully")
from utils import *

db = load_local_db()

policy = get_passport_policy(24)

print(policy)

fee = calculate_fee(
    db,
    64,
    "10 Years",
    "express"
)

print("Fee =", fee)

docs = get_documents(
    db,
    24,
    "Private Employee"
)

print(docs)
