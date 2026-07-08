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