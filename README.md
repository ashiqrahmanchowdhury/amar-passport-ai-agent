# 🏗️ Amar Passport AI Agent

A CrewAI-based **Multi-Agent System (MAS)** that acts as a Virtual Consular Officer for Bangladesh's e-Passport system. Given an applicant's age, profession, and delivery preference, it produces a full **Passport Readiness Report** — in **English and Bangla** — covering eligibility, fees, and required documents.

> Built for **Module 23: Building "Amar Passport" AI Agent** assignment.

## 🤖 The Crew

| Agent | Role | Responsibility |
|---|---|---|
| **Policy Guardian** | Bangladesh Passport Policy Expert | Determines validity (5/10 years) and required ID (NID / Birth Registration) based on age, and flags any policy inconsistency |
| **Fee Calculator** | Financial Auditor | Calculates the exact BDT fee (15% VAT included) using the 2026 fee structure |
| **Document Architect** | Documentation Officer | Builds a customized document checklist (minors, government employees, name changes, etc.) |
| **Report Writer** | Bilingual Consular Report Writer | Combines everything into one final Markdown report |

Agents run on a **local Ollama model (`llama3.2`)** — no external API key required.

## ⚙️ How It Works

1. Python (`utils.py`) computes all authoritative numbers first — validity, fee, and documents — directly from `local_db.json`. This avoids LLM hallucination on numeric fields, since small local models can be unreliable with exact figures.
2. CrewAI agents (`agents.py`, `tasks.py`) reason over these confirmed values, demonstrating agent "thinking" via `verbose=True`.
3. A guaranteed-accurate **Python-generated final report** (English Markdown table + Bangla summary) is printed alongside the agents' own report, so the output is both explainable (via the crew) and reliable (via direct computation).

## 🛠️ Key Features

- ✅ **3+ specialized agents** with descriptive personas (role, goal, backstory)
- ✅ **Task delegation** — Policy Guardian's output is passed as `context` to the Fee Calculator and Document Architect
- ✅ **Bilingual output** — English Markdown table + natural Bangla summary
- ✅ **Error handling** — flags inconsistent requests (e.g., a 15-year-old requesting a 10-year passport) and auto-corrects
- ✅ **Fallback logic** — attempts a live portal lookup first, falls back to `local_db.json` when it fails
- ✅ **Two input modes** — structured Q&A, or describe your situation in one natural-language sentence (e.g. the assignment's example scenario) and the system extracts age, profession, pages, and delivery urgency automatically
- ✅ Handles minors, adults, seniors (65+), government employees, and name-change cases

## 📁 Project Structure

```
├── agents.py       # Agent definitions (Policy Guardian, Fee Calculator, Document Architect, Report Writer)
├── tasks.py        # Task chain with context-based delegation
├── utils.py        # Core logic: policy rules, fee lookup, document checklist, fallback, bilingual report builders
├── app.py          # Entry point — collects input, runs the crew, prints the final report
├── local_db.json   # 2026 fee structure + required documents database
└── requirements.txt
```

## 🚀 Setup & Run

```bash
pip install crewai crewai-tools
```

Install [Ollama](https://ollama.com) and pull the model:
```bash
ollama pull llama3.2
```

Run:
```bash
python app.py
```

You'll first be asked to choose an input mode:
- **`S`** — structured questions (age, profession, pages, delivery, etc. asked one by one)
- **`F`** — describe your situation in one sentence (e.g. *"I am a 24-year-old private sector employee..."*) and the system extracts the details automatically

Either way, you'll also be asked for: requested validity, city, and whether you changed your name.

## 📝 Example

**Input:** 24-year-old private sector employee, 64-page passport, express delivery, 10-year validity, has NID, Dhaka.

**Output:**

| Field | Value |
|---|---|
| Validity | 10 Years |
| Delivery Type | Express |
| Total Fee | 11902.5 BDT |
| Documents Needed | NID Card, Application Summary, Payment Slip, Profession Proof |

Plus a Bangla summary with the same information.

## ⚠️ Error Handling Example

Input: 15-year-old requesting a 10-year passport →

> ⚠️ **Policy Flag:** Policy Violation: Applicants under 18 cannot receive a 10-year passport.

The system auto-corrects to the allowed 5-year validity for all downstream calculations.

---

**Author:** ASHIQ RAHMAN CHOWDHURY