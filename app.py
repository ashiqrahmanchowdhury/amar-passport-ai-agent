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