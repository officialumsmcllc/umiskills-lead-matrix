import csv
import sys
import os
import re

# ==============================================================
# UMISKILLS - CRM LEAD EXPORTER (by officialum1)
# Formats into: email,first_name,last_name,tags
# ==============================================================

ROLE_NAMES = {
    "sales": ("Sales", "Team"),
    "info": ("Info", "Desk"),
    "contact": ("Contact", "Support"),
    "support": ("Support", "Team"),
    "admin": ("Admin", "Office"),
    "helpdesk": ("Help", "Desk"),
    "billing": ("Billing", "Dept"),
    "marketing": ("Marketing", "Team"),
    "hrd": ("HR", "Department"),
    "secretary": ("Secretary", "Office"),
    "press": ("Press", "Media"),
    "commercial": ("Commercial", "Team"),
    "editorial": ("Editorial", "Desk"),
    "redaksi": ("Redaksi", "Editorial"),
    "fleetsales": ("Fleet", "Sales"),
    "autoparts": ("Auto", "Parts"),
    "wheelsandglass": ("Parts", "Specialist"),
    "trkbuyer": ("Truck", "Buyer")
}

def parse_name_from_email(email: str):
    user_part = email.split("@")[0].strip().lower()
    
    # 1. Known role addresses
    if user_part in ROLE_NAMES:
        return ROLE_NAMES[user_part]
    
    # 2. Check for dots, underscores, dashes (e.g. sarah.connor, john_wick)
    for sep in [".", "_", "-"]:
        if sep in user_part:
            parts = [p for p in user_part.split(sep) if p]
            if len(parts) >= 2:
                first = parts[0].capitalize()
                last = parts[1].capitalize()
                # Clean any digits
                first = re.sub(r'\d+', '', first)
                last = re.sub(r'\d+', '', last)
                if first and last:
                    return first, last
            elif len(parts) == 1:
                first = re.sub(r'\d+', '', parts[0].capitalize())
                return first or "Member", "Lead"

    # 3. Single name (e.g. benji, krisnaadi)
    clean_name = re.sub(r'\d+', '', user_part).capitalize()
    if clean_name and len(clean_name) >= 2:
        return clean_name, "Contact"

    return "Valued", "Customer"

def export_crm_leads(input_file: str, output_csv: str, default_tag: str = "Car-Dealer;Verified"):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    records = []
    seen = set()

    # Determine file type
    if input_file.endswith(".csv"):
        # Read from existing Craigslist leads or other CSV
        with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                emails_str = row.get("Emails", "") or row.get("Email", "")
                if not emails_str:
                    continue
                for em in emails_str.split(";"):
                    em = em.strip().lower()
                    if em and "@" in em and em not in seen:
                        seen.add(em)
                        first, last = parse_name_from_email(em)
                        # Tag with location/category if available
                        tag = default_tag
                        loc = row.get("Location", "")
                        if loc:
                            tag += f";{loc.replace(',', ' ')}"
                        records.append({
                            "email": em,
                            "first_name": first,
                            "last_name": last,
                            "tags": tag
                        })
    else:
        # Read plain text email list
        with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                em = line.strip().lower()
                if em and "@" in em and em not in seen:
                    seen.add(em)
                    first, last = parse_name_from_email(em)
                    records.append({
                        "email": em,
                        "first_name": first,
                        "last_name": last,
                        "tags": default_tag
                    })

    # Write formatted CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "first_name", "last_name", "tags"])
        writer.writeheader()
        writer.writerows(records)

    print(f"[Done] Successfully exported {len(records)} leads to {output_csv}")

if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "clean_emails.txt"
    out = sys.argv[2] if len(sys.argv) > 2 else "crm_leads_formatted.csv"
    tag = sys.argv[3] if len(sys.argv) > 3 else "Car-Dealer;Automotive;Verified"
    export_crm_leads(inp, out, tag)
