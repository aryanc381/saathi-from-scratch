"""Generates all synthetic Saathi data: demo CRM rows, ML training CSVs and policy-clause PDFs.

Run from the repo root: python data/generate.py
Output is deterministic (seed 42). Every name, message and document is synthetic.
"""
import csv
import itertools
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

SEED = 42
AS_OF = date(2026, 10, 28)
ROOT = Path(__file__).parent
SEED_DIR = ROOT / "seed"
DOCS_DIR = ROOT / "docs"

AGENTS = [
    {"agent_id": "A-00", "name": "Priya Shah", "role": "supervisor", "products": ["health", "motor", "term"]},
    {"agent_id": "A-01", "name": "Meera Nair", "role": "agent", "products": ["health", "motor", "term"]},
    {"agent_id": "A-02", "name": "Vikram Rao", "role": "agent", "products": ["health", "term"]},
]

# policy.status is only ACTIVE or CANCELLED; the renewal state (in grace, lapsed) is computed in code from renewal_date.
CUSTOMERS = [
    {"customer_id": "C-204", "agent_id": "A-01", "name": "Anita Desai", "phone": "+91-90000-00204", "language": "en", "consent": True,
     "policy": {"product": "health", "tier": "Silver", "annual_premium_inr": 18000, "renewal_date": "2026-11-12", "status": "ACTIVE"}},
    {"customer_id": "C-311", "agent_id": "A-01", "name": "Rahul Verma", "phone": "+91-90000-00311", "language": "hi", "consent": True,
     "policy": {"product": "motor", "tier": "Comprehensive", "annual_premium_inr": 12500, "renewal_date": "2026-11-04", "status": "ACTIVE"}},
    {"customer_id": "C-118", "agent_id": "A-02", "name": "Sunita Kulkarni", "phone": "+91-90000-00118", "language": "mr", "consent": True,
     "policy": {"product": "health", "tier": "Gold", "annual_premium_inr": 32000, "renewal_date": "2026-09-27", "status": "ACTIVE"}},
    {"customer_id": "C-450", "agent_id": "A-01", "name": "Imran Sheikh", "phone": "+91-90000-00450", "language": "en", "consent": True,
     "policy": {"product": "term", "tier": "Standard", "annual_premium_inr": 24000, "renewal_date": "2026-10-23", "status": "ACTIVE"}},
    {"customer_id": "C-205", "agent_id": "A-01", "name": "Kavita Joshi", "phone": "+91-90000-00205", "language": "hi", "consent": False,
     "policy": {"product": "health", "tier": "Gold", "annual_premium_inr": 30000, "renewal_date": "2026-11-17", "status": "ACTIVE"}},
    {"customer_id": "C-999", "agent_id": "A-02", "name": "Deepak Menon", "phone": "+91-90000-00999", "language": "en", "consent": True,
     "policy": {"product": "term", "tier": "Standard", "annual_premium_inr": 21000, "renewal_date": "2027-01-26", "status": "CANCELLED"}},
]

# (days before AS_OF, channel, text) per customer: three synthetic interactions each.
INTERACTIONS = {
    "C-204": [(40, "call", "Asked how the Gold plan differs from Silver."), (18, "whatsapp", "Said the premium feels high this year."), (4, "call", "Wants a renewal reminder before the due date.")],
    "C-311": [(55, "email", "Reported a minor claim for a bumper repair."), (20, "call", "Asked about the no-claim bonus after the claim."), (6, "whatsapp", "Asked to renew the motor policy this week.")],
    "C-118": [(70, "call", "Asked about room rent limits on the Gold plan."), (35, "whatsapp", "Did not respond to the renewal notice."), (30, "email", "Opened the renewal email but took no action.")],
    "C-450": [(45, "call", "Asked about the grace period for the term plan."), (15, "email", "Asked to pay the premium in two instalments."), (8, "whatsapp", "Confirmed the nominee details are unchanged.")],
    "C-205": [(60, "call", "Asked what the Gold plan excludes."), (25, "whatsapp", "Compared two hospitals for cashless cover."), (10, "call", "Asked to stop promotional messages.")],
    "C-999": [(90, "call", "Asked to cancel the term policy."), (80, "email", "Confirmed the cancellation in writing."), (75, "whatsapp", "Asked about the refund timeline.")],
}

# (clause_id, product, version, title, text): one PDF per clause, so each indexed chunk maps to one citable clause.
CLAUSES = [
    ("HEALTH-SILVER-01", "health", "v1", "Silver plan: sum insured", "The Silver plan covers hospitalisation up to a sum insured of INR 5,00,000 per policy year, including room, nursing and doctor fees."),
    ("HEALTH-SILVER-02", "health", "v1", "Silver plan: room rent limit", "Room rent under the Silver plan is limited to 1 percent of the sum insured per day. Higher room rent reduces the claim proportionately."),
    ("HEALTH-GOLD-01", "health", "v1", "Gold plan: sum insured", "The Gold plan covers hospitalisation up to a sum insured of INR 10,00,000 per policy year, with no proportionate deduction on room rent."),
    ("HEALTH-GOLD-EXC-07", "health", "v1", "Gold plan: exclusion for cosmetic treatment", "The Gold plan does not cover cosmetic or aesthetic procedures unless they follow an accident covered under the policy."),
    ("HEALTH-PLATINUM-01", "health", "v1", "Platinum plan: sum insured", "The Platinum plan covers hospitalisation up to INR 25,00,000 per policy year and adds international emergency cover."),
    ("HEALTH-WAIT-01", "health", "v1", "Waiting period for pre-existing conditions", "Pre-existing conditions are covered only after 36 continuous months of renewals. Specific listed illnesses have a 24 month waiting period."),
    ("MOTOR-IDV-01", "motor", "v1", "Insured declared value", "The insured declared value is the market value of the vehicle at policy start, reduced each year by the standard depreciation schedule."),
    ("MOTOR-NCB-01", "motor", "v1", "No-claim bonus", "A no-claim bonus of 20 percent on the own-damage premium applies after one claim-free year and grows to 50 percent after five. A claim resets it."),
    ("MOTOR-ADDON-01", "motor", "v1", "Zero depreciation add-on", "The zero depreciation add-on pays the full cost of replaced parts without deducting depreciation, for up to two claims per policy year."),
    ("TERM-GRACE-01", "term", "v1", "Grace period for premium payment", "A grace period of 30 days applies for annual premiums. Cover continues during the grace period and lapses if the premium is unpaid after it."),
    ("TERM-FREELOOK-01", "term", "v1", "Free-look period", "A new term policy can be cancelled within 30 days of receipt for a refund of the premium, less stamp duty and medical costs."),
    ("TERM-REVIVAL-01", "term", "v1", "Revival of a lapsed policy", "A lapsed term policy can be revived within 24 months of the first unpaid premium by paying all dues with interest and submitting health proof."),
    ("RENEWAL-RULE-01", "health", "v1", "Renewal and grace rules", "A policy renews on its renewal date. Within 30 days after the date it is in grace and can still be renewed. After 30 days it is lapsed and needs a new proposal."),
]

INTENT_TEMPLATES = {
    "policy_info": ["What does the {tier} plan cover?", "Does the {product} policy cover {thing}?", "Explain the waiting period for {product} insurance",
                    "What is excluded under the {tier} plan?", "Is {thing} covered for this customer?", "Compare the {tier} and {tier2} plans"],
    "renewal": ["When does this policy renew?", "Is this customer in the grace period?", "Has the {product} policy lapsed?",
                "How many days are left to renew?", "Can this customer still renew the {product} policy?", "What happens if the renewal date is missed?",
                "Will a claim for {thing} affect the renewal?"],
    "claim": ["How do I file a claim for {thing}?", "What is the status of the claim?", "Which documents are needed to claim for {thing}?",
              "Will the {product} policy pay for {thing}?", "How long does a claim take to settle?", "Why was the claim for {thing} rejected?"],
    "premium": ["How much is the annual premium for the {tier} plan?", "Why did the {product} premium go up?", "Can the premium be paid in instalments?",
                "What is the premium difference between {tier} and {tier2}?", "Is there a discount on the {product} premium?", "What is the due date for the premium?"],
    "draft_message": ["Draft a renewal reminder for this customer", "Write a message about the {product} renewal", "Prepare a WhatsApp reminder for the {tier} plan",
                      "Draft a short email about the premium due date", "Write a polite message asking the customer to renew", "Create a reminder about the {product} grace period",
                      "Draft a message about {thing} for this customer"],
    "other": ["Hello", "Thanks for your help", "Who are you?", "What can you do?", "Good morning", "What is the weather today?",
              "Tell me a joke", "Okay, got it", "Goodbye", "How are you?",
              "Can you help me?", "Never mind", "Please wait a moment", "Nice to meet you", "See you later"],
}
PRODUCTS = ["health", "motor", "term"]
TIERS = ["Silver", "Gold", "Platinum"]
THINGS = ["surgery", "dental treatment", "a hospital stay", "an accident", "maternity", "a bumper repair", "theft", "a critical illness", "an eye operation"]
PREFIXES = ["", "Please ", "Quick question: ", "Hey, ", "I need to know: "]
SUFFIXES = ["", " thanks", " today"]

PER_LABEL = {"train": 167, "dev": 25, "test": 25}


# Writes rows to a JSON file with stable formatting.
def write_json(path, rows):
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# Writes rows to a CSV file using the given column order.
def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


# Builds the demo CRM tables: agents, customers, policies and interactions.
def build_crm():
    customers = [{k: v for k, v in c.items() if k != "policy"} for c in CUSTOMERS]
    policies = [{"policy_id": f"P-{c['customer_id'][2:]}", "customer_id": c["customer_id"], **c["policy"]} for c in CUSTOMERS]
    interactions = []
    n = 1
    for customer_id, items in INTERACTIONS.items():
        for days_before, channel, text in items:
            interactions.append({"interaction_id": f"I-{n:04d}", "customer_id": customer_id,
                                 "date": (AS_OF - timedelta(days=days_before)).isoformat(), "channel": channel, "text": text})
            n += 1
    return customers, policies, interactions


# Expands every intent template with slot values and adds polite prefixes and suffixes.
def expand_utterances(label):
    seen = set()
    for template in INTENT_TEMPLATES[label]:
        for product, tier, tier2, thing in itertools.product(PRODUCTS, TIERS, TIERS, THINGS):
            if tier == tier2:
                continue
            text = template.format(product=product, tier=tier, tier2=tier2, thing=thing)
            for prefix, suffix in itertools.product(PREFIXES, SUFFIXES):
                seen.add(prefix + text[0].lower() + text[1:] + suffix if prefix else text + suffix)
    return sorted(seen)


# Builds the intent classifier train, dev and test splits with no utterance shared between splits.
def build_intent(rng):
    splits = {name: [] for name in PER_LABEL}
    for label in INTENT_TEMPLATES:
        pool = expand_utterances(label)
        need = sum(PER_LABEL.values())
        assert len(pool) >= need, f"{label} has only {len(pool)} unique utterances"
        rng.shuffle(pool)
        start = 0
        for name, count in PER_LABEL.items():
            splits[name] += [{"text": t, "label": label} for t in pool[start:start + count]]
            start += count
    for rows in splits.values():
        rng.shuffle(rows)
    return splits


# Builds 1200 synthetic renewal rows; the label comes from a noisy logistic rule over the features.
def build_radar(rng):
    rows = []
    for i in range(1, 1201):
        days_to_renewal = rng.randint(-45, 90)
        annual_premium_inr = rng.randrange(8000, 120001, 500)
        interaction_count_90d = rng.randint(0, 12)
        days_since_last_interaction = rng.randint(0, 180)
        logit = (0.6 + 0.35 * interaction_count_90d - 0.02 * days_since_last_interaction
                 - 0.000012 * (annual_premium_inr - 40000) - 0.03 * max(-days_to_renewal, 0))
        renewed = int(rng.random() < 1 / (1 + math.exp(-logit)))
        rows.append({"customer_id": f"R-{i:04d}", "days_to_renewal": days_to_renewal, "annual_premium_inr": annual_premium_inr,
                     "interaction_count_90d": interaction_count_90d, "days_since_last_interaction": days_since_last_interaction, "renewed": renewed})
    return rows


# Writes one single-page PDF for a policy clause; invariant=1 keeps the bytes reproducible.
def write_clause_pdf(path, clause_id, product, version, title, text):
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    pdf.setTitle(title)
    y = 790
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(60, y, f"Clause {clause_id} ({version})")
    y -= 22
    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, y, f"Product: {product}   Title: {title}")
    y -= 30
    for line in simpleSplit(text, "Helvetica", 11, 475):
        pdf.drawString(60, y, line)
        y -= 16
    pdf.save()


# Writes every clause PDF plus manifest.json, which upload_blob.py uses for blob metadata.
def build_docs():
    DOCS_DIR.mkdir(exist_ok=True)
    manifest = []
    for clause_id, product, version, title, text in CLAUSES:
        file = f"{clause_id.lower()}.pdf"
        write_clause_pdf(DOCS_DIR / file, clause_id, product, version, title, text)
        manifest.append({"file": file, "clause_id": clause_id, "product": product, "version": version, "title": title})
    write_json(DOCS_DIR / "manifest.json", manifest)


# Writes every generated file: CRM JSON, ML CSVs and policy PDFs.
def main():
    rng = random.Random(SEED)
    SEED_DIR.mkdir(exist_ok=True)
    customers, policies, interactions = build_crm()
    write_json(SEED_DIR / "agents.json", AGENTS)
    write_json(SEED_DIR / "customers.json", customers)
    write_json(SEED_DIR / "policies.json", policies)
    write_json(SEED_DIR / "interactions.json", interactions)
    for name, rows in build_intent(rng).items():
        write_csv(SEED_DIR / f"intent_{name}.csv", ["text", "label"], rows)
    radar_columns = ["customer_id", "days_to_renewal", "annual_premium_inr", "interaction_count_90d", "days_since_last_interaction", "renewed"]
    write_csv(SEED_DIR / "radar.csv", radar_columns, build_radar(rng))
    build_docs()
    print(f"customers={len(customers)} interactions={len(interactions)} clauses={len(CLAUSES)}")


if __name__ == "__main__":
    main()
