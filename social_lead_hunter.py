import requests
import re
import csv
import sys
import os
import time
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ==============================================================
# UMISKILLS - SOCIAL & LINKEDIN LEAD HUNTER PRO v2.5
#                        by officialum1
# ==============================================================

MAX_WORKERS = 20
TIMEOUT = 6

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

EMAIL_PROVIDERS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "aol.com"
]

EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}\b')
PHONE_REGEX = re.compile(r'\(?\b[2-9][0-9]{2}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b')

BLOCKED_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".eot", ".ico",
    ".mp4", ".zip", ".pdf", ".map"
)

BLOCKED_DOMAINS = (
    "sentry.io", "wixpress.com", "example.com", "domain.com",
    "schema.org", "google.com", "yahoo.com/search", "bing.com"
)

lock = threading.Lock()
discovered_emails = set()
social_leads = []

def show(text, color=GREEN):
    print(color + text + RESET, flush=True)

def is_valid_email(email: str) -> bool:
    email = email.strip().lower().strip("<>\"'(),;:")
    if not email or "@" not in email:
        return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$', email):
        return False
    for ext in BLOCKED_EXTENSIONS:
        if email.endswith(ext):
            return False
    domain = email.split('@')[-1]
    for b in BLOCKED_DOMAINS:
        if domain == b or domain.endswith("." + b):
            return False
    tld = domain.split('.')[-1]
    if len(tld) < 2 or not tld.isalpha():
        return False
    return True

def extract_name_from_title(title: str, platform="LinkedIn"):
    # Common LinkedIn format: "John Doe - General Manager - ABC Motors | LinkedIn"
    # or "Jane Smith | Facebook"
    clean = title
    for suf in ["| LinkedIn", "- LinkedIn", "| Facebook", "- Facebook", "..."]:
        clean = clean.replace(suf, "")
    parts = re.split(r'[-–—|:]', clean)
    if parts:
        name_candidate = parts[0].strip()
        words = name_candidate.split()
        if len(words) >= 2 and len(words[0]) > 1:
            fn = words[0].strip(',.:;').capitalize()
            ln = words[1].strip(',.:;').capitalize()
            return fn, ln
        elif len(words) == 1 and len(words[0]) > 2:
            return words[0].strip(',.:;').capitalize(), "Executive"
    return "Valued", "Leader"

def query_search_engine(query_str, platform, niche_tag, city):
    results = []
    # Query Yahoo Search endpoint
    url = f"https://search.yahoo.com/search?p={quote_plus(query_str)}&b=1"
    headers = {
        "User-Agent": USER_AGENTS[hash(query_str) % len(USER_AGENTS)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # Parse search result items
            items = soup.select(".algo") or soup.select(".dd.algo") or soup.find_all("div", class_="Sr")
            for it in items:
                title_el = it.find("h3") or it.find("a")
                title_text = title_el.get_text(strip=True) if title_el else ""
                link_el = title_el.find("a") if title_el and title_el.name != "a" else title_el
                link = link_el.get("href", "") if link_el else ""

                snippet_el = it.find(class_="compText") or it.find(class_="fc-falcon") or it
                snippet_text = snippet_el.get_text() if snippet_el else ""

                combined_text = f"{title_text} {snippet_text}"
                found_emails = EMAIL_REGEX.findall(combined_text)
                found_phones = PHONE_REGEX.findall(combined_text)

                for em in found_emails:
                    em_clean = em.lower().strip("<>\"'(),;:")
                    if is_valid_email(em_clean):
                        fn, ln = extract_name_from_title(title_text, platform)
                        with lock:
                            if em_clean not in discovered_emails:
                                discovered_emails.add(em_clean)
                                lead_item = {
                                    "first_name": fn,
                                    "last_name": ln,
                                    "email": em_clean,
                                    "phone": found_phones[0] if found_phones else "",
                                    "platform": platform,
                                    "location": city.title(),
                                    "title_summary": title_text[:70],
                                    "url": link,
                                    "tags": f"{platform};{niche_tag};Verified;Lead"
                                }
                                social_leads.append(lead_item)
                                with open("clean_emails.txt", "a", encoding="utf-8") as f:
                                    f.write(em_clean + "\n")
                                show(f"[{platform.upper()} LEAD +] {fn} {ln} <{em_clean}>  <-- [{title_text[:40]}]")
    except Exception:
        pass

def load_existing_crm_leads():
    existing = set()
    crm_file = "craigslist_crm_leads.csv"
    if os.path.exists(crm_file):
        try:
            with open(crm_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("email"):
                        existing.add(r["email"].strip().lower())
        except Exception:
            pass
    return existing

def main():
    show("=" * 65, color=CYAN)
    show("     UMISKILLS - SOCIAL & LINKEDIN LEAD HUNTER PRO v2.5", color=CYAN)
    show("                         by officialum1", color=CYAN)
    show("=" * 65, color=CYAN)

    existing_emails = load_existing_crm_leads()
    for e in existing_emails:
        discovered_emails.add(e)

    platform_mode = "LinkedIn"
    job_titles = ["Owner", "General Manager", "CEO", "Sales Director"]
    niche = "car dealership"
    niche_tag = "Automotive"
    city = "Miami, FL"

    if "--auto" in sys.argv or "-y" in sys.argv:
        show(f"\n[AUTO-MODE] Using defaults: {platform_mode} | {niche} | {city}", color=YELLOW)
    else:
        print("\nSelect Platform / Source to Harvest:")
        print(" [1] LinkedIn Decision Makers (Owners, CEOs, GMs - Default)")
        print(" [2] Facebook Business Pages (Dealerships, Local Businesses)")
        print(" [3] Combined (Both LinkedIn & Facebook)")
        print(" [4] Custom Search (Any Job Title + Niche + Location)")

        choice = input("\nEnter choice [1-4] (Press Enter for LinkedIn): ").strip()

        if choice == "2":
            platform_mode = "Facebook"
        elif choice == "3":
            platform_mode = "Both"
        elif choice == "4":
            custom_kw = input("Enter job title or keyword (e.g. Real Estate Broker, Dentist, CEO): ").strip()
            if custom_kw:
                job_titles = [custom_kw]
                niche = custom_kw
                niche_tag = "B2B"

        niche_in = input(f"Enter Niche/Industry (Default: '{niche}', e.g. Real Estate, Solar, Plumbers): ").strip()
        if niche_in:
            niche = niche_in
            niche_tag = "".join(filter(str.isalnum, niche_in.title()))

        city_in = input(f"Enter City/State (Default: '{city}', e.g. Dallas TX, Los Angeles CA, New York NY): ").strip()
        if city_in:
            city = city_in

    queries = []
    # Build LinkedIn Queries
    if platform_mode in ("LinkedIn", "Both"):
        for jt in job_titles:
            for prov in EMAIL_PROVIDERS:
                q = f'site:linkedin.com/in/ "{jt}" "{niche}" "{city}" "@{prov}"'
                queries.append((q, "LinkedIn"))

    # Build Facebook Queries
    if platform_mode in ("Facebook", "Both"):
        for prov in EMAIL_PROVIDERS:
            q = f'site:facebook.com "{niche}" "{city}" "@{prov}"'
            queries.append((q, "Facebook"))
            q2 = f'site:facebook.com "{niche}" "{city}" "contact email"'
            queries.append((q2, "Facebook"))

    total_queries = len(queries)
    show(f"\n[INFO] Generated {total_queries} search dorks for {niche.title()} in {city}...", color=CYAN)
    show(f"[INFO] Multi-threaded harvesting with {MAX_WORKERS} workers in parallel...\n")

    done = 0
    start_count = len(social_leads)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(query_search_engine, q[0], q[1], niche_tag, city) for q in queries]
        for f in as_completed(futures):
            done += 1
            if done % 5 == 0 or done == total_queries:
                new_found = len(social_leads) - start_count
                show(f"[PROGRESS] {done}/{total_queries} dorks executed ({(done/total_queries)*100:.1f}%) | New leads harvested: {new_found}", color=CYAN)

    new_leads_count = len(social_leads) - start_count

    # 1. Save detailed social sheet
    social_csv = "social_leads.csv"
    file_exists = os.path.exists(social_csv)
    with open(social_csv, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["first_name", "last_name", "email", "phone", "platform", "location", "title_summary", "url", "tags"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(social_leads)

    # 2. Append directly to master CRM leads CSV (email,first_name,last_name,tags)
    crm_csv = "craigslist_crm_leads.csv"
    with open(crm_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for ld in social_leads:
            writer.writerow([ld["email"], ld["first_name"], ld["last_name"], ld["tags"]])

    show("\n" + "=" * 65, color=CYAN)
    show("SOCIAL LEAD HARVESTING COMPLETE!", color=CYAN)
    show(f"New Decision-Maker Leads Added: {new_leads_count}")
    show(f"Updated CRM File: {crm_csv} (Zero-Bounce format)")
    show(f"Updated Social Leads Sheet: {social_csv}")
    show("=" * 65, color=CYAN)

if __name__ == "__main__":
    main()
