import requests
import re
import csv
import sys
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ==============================================================
# UMISKILLS - MULTI-NICHE & CRAIGSLIST LEAD HUNTER PRO v3.0
#                        by officialum1
# ==============================================================

MAX_WORKERS = 30
TIMEOUT = 7

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}\b')
OBFUSCATED_EMAIL_REGEX = re.compile(r'([a-zA-Z0-9._%+-]+(?:\s*\[at\]\s*|\s*\(at\)\s*)[a-zA-Z0-9.-]+(?:\s*\[dot\]\s*|\s*\(dot\)\s*)[a-zA-Z]{2,63})', re.IGNORECASE)
PHONE_REGEX = re.compile(r'\(?\b[2-9][0-9]{2}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b')
URL_REGEX = re.compile(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:/[^\s\"\'<>]*)?', re.IGNORECASE)
PLAIN_DOMAIN_REGEX = re.compile(r'\b(?:www\.)([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', re.IGNORECASE)

BLOCKED_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".eot", ".ico",
    ".mp4", ".zip", ".pdf", ".map", ".ts", ".jsx", ".tsx"
)

BLOCKED_DOMAINS = (
    "craigslist.org",
    "craigslist.com",
    "sentry.io",
    "wixpress.com",
    "schema.org",
    "google.com",
    "googleapis.com",
    "gstatic.com",
    "cloudflare.com",
    "example.com",
    "domain.com",
    "mysite.com",
    "test.com"
)

lock = threading.Lock()
discovered_emails = set()
discovered_domains = set()
leads_data = []

def show(text, color=GREEN):
    print(color + text + RESET, flush=True)

def is_valid_email(email: str) -> bool:
    email = email.strip().lower()
    if not email:
        return False
    email = email.strip("<>\"'(),;:")
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

def clean_domain(domain_str):
    d = domain_str.strip().lower()
    d = d.replace("https://", "").replace("http://", "").split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d

def fetch_emails_from_dealer_site(domain):
    emails = set()
    base_urls = [f"https://www.{domain}", f"https://{domain}", f"http://{domain}"]
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    resp_text = ""
    contact_urls = []
    
    for b_url in base_urls:
        try:
            r = session.get(b_url, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                resp_text = r.text
                final_url = r.url
                
                soup = BeautifulSoup(resp_text, "html.parser")
                for a in soup.find_all("a", href=True):
                    h = a["href"].strip()
                    if h.lower().startswith("mailto:"):
                        m = h.split(":", 1)[1].split("?")[0].strip()
                        if is_valid_email(m):
                            emails.add(m.lower().strip("<>\"'(),;:"))
                    elif any(k in h.lower() for k in ["contact", "about", "staff", "sales", "team", "management"]):
                        full_c = urljoin(final_url, h)
                        if clean_domain(full_c) == domain:
                            contact_urls.append(full_c)
                break
        except Exception:
            continue

    if resp_text:
        for em in EMAIL_REGEX.findall(resp_text):
            if is_valid_email(em):
                emails.add(em.lower().strip("<>\"'(),;:"))

    for c_url in list(dict.fromkeys(contact_urls))[:2]:
        try:
            cr = session.get(c_url, timeout=TIMEOUT, allow_redirects=True)
            if cr.status_code == 200:
                for em in EMAIL_REGEX.findall(cr.text):
                    if is_valid_email(em):
                        emails.add(em.lower().strip("<>\"'(),;:"))
                csoup = BeautifulSoup(cr.text, "html.parser")
                for a in csoup.find_all("a", href=True):
                    h = a["href"].strip()
                    if h.lower().startswith("mailto:"):
                        m = h.split(":", 1)[1].split("?")[0].strip()
                        if is_valid_email(m):
                            emails.add(m.lower().strip("<>\"'(),;:"))
        except Exception:
            continue

    return emails

def process_craigslist_post(item, niche_tag="Automotive"):
    post_url = item["url"]
    title = item.get("title", "")
    price = item.get("price", "")
    location = item.get("location", "")

    found_emails = set()
    found_phones = set()
    dealer_domains = set()

    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        r = session.get(post_url, timeout=TIMEOUT)
        if r.status_code == 200:
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            body_tag = soup.find("section", id="postingbody")
            body_text = body_tag.get_text() if body_tag else html

            for em in EMAIL_REGEX.findall(body_text):
                if is_valid_email(em):
                    found_emails.add(em.lower().strip("<>\"'(),;:"))

            for a in soup.find_all("a", href=True):
                h = a["href"].strip()
                if h.lower().startswith("mailto:"):
                    m = h.split(":", 1)[1].split("?")[0].strip()
                    if is_valid_email(m):
                        found_emails.add(m.lower().strip("<>\"'(),;:"))

            for ob in OBFUSCATED_EMAIL_REGEX.findall(body_text):
                clean_ob = re.sub(r'\s*\[at\]\s*|\s*\(at\)\s*', '@', ob, flags=re.IGNORECASE)
                clean_ob = re.sub(r'\s*\[dot\]\s*|\s*\(dot\)\s*', '.', clean_ob, flags=re.IGNORECASE)
                if is_valid_email(clean_ob):
                    found_emails.add(clean_ob.lower().strip("<>\"'(),;:"))

            for ph in PHONE_REGEX.findall(body_text):
                digits = re.sub(r'\D', '', ph)
                if len(digits) == 10 and not digits.startswith("798"):
                    found_phones.add(ph.strip())

            for link in URL_REGEX.findall(body_text):
                d = clean_domain(link)
                if d and not any(b in d for b in BLOCKED_DOMAINS) and "." in d:
                    dealer_domains.add(d)

            for link in PLAIN_DOMAIN_REGEX.findall(body_text):
                d = clean_domain(link)
                if d and not any(b in d for b in BLOCKED_DOMAINS) and "." in d:
                    dealer_domains.add(d)

    except Exception:
        pass

    for d in dealer_domains:
        d_emails = fetch_emails_from_dealer_site(d)
        for de in d_emails:
            found_emails.add(de)

    with lock:
        for em in found_emails:
            if em not in discovered_emails:
                discovered_emails.add(em)
                with open("clean_emails.txt", "a", encoding="utf-8") as f:
                    f.write(em + "\n")
                show(f"[EMAIL +] {em}  <-- [{', '.join(dealer_domains) or 'Direct Post'}]  <-- [{title[:30]}]")

        if found_emails or found_phones or dealer_domains:
            leads_data.append({
                "Title": title,
                "Price": price,
                "Location": location,
                "Emails": "; ".join(found_emails),
                "Phones": "; ".join(found_phones),
                "Dealer_Domains": "; ".join(dealer_domains),
                "Post_URL": post_url,
                "Niche_Tag": niche_tag
            })

def parse_name_from_email(email):
    local = email.split('@')[0].lower()
    for prefix in ['sales', 'info', 'support', 'contact', 'admin', 'help', 'office']:
        if local == prefix or local.startswith(prefix + '.'):
            domain_part = email.split('@')[1].split('.')[0]
            return domain_part.capitalize(), "Business"
    clean = re.sub(r'[^a-zA-Z.]', ' ', local).strip()
    parts = clean.split('.') if '.' in clean else clean.split()
    if len(parts) >= 2:
        return parts[0].capitalize(), parts[1].capitalize()
    elif len(parts) == 1 and len(parts[0]) > 2:
        return parts[0].capitalize(), "Executive"
    return "Valued", "Client"

def main():
    show("=" * 65, color=CYAN)
    show("   UMISKILLS - MULTI-NICHE & CRAIGSLIST LEAD HUNTER PRO v3.0", color=CYAN)
    show("                         by officialum1", color=CYAN)
    show("=" * 65, color=CYAN)

    city = "miami"
    cat_code = "cta"
    niche_name = "Cars & Trucks"
    niche_tag = "Automotive"
    max_pages = 2

    # Check CLI arguments or prompt
    if len(sys.argv) > 1:
        city = sys.argv[1].lower().strip()
        if len(sys.argv) > 2:
            cat_code = sys.argv[2].lower().strip()
    else:
        print("\nSelect Niche to Scrape:")
        print(" [1] Cars & Auto Dealerships (Default)")
        print(" [2] Real Estate & Property Dealers")
        print(" [3] Services & Local Contractors (Repair, Plumbing, Roofing, etc.)")
        print(" [4] Commercial Equipment & Heavy Machinery")
        print(" [5] Custom Keyword Search")
        
        choice = input("\nEnter choice [1-5] (Press Enter for Cars): ").strip()
        if choice == "2":
            cat_code = "rea"
            niche_name = "Real Estate"
            niche_tag = "RealEstate"
        elif choice == "3":
            cat_code = "bbb"
            niche_name = "Services & Contractors"
            niche_tag = "Services"
        elif choice == "4":
            cat_code = "maa"
            niche_name = "Equipment & Machinery"
            niche_tag = "Equipment"
        elif choice == "5":
            kw = input("Enter keyword (e.g. car detailing, solar, roofing): ").strip()
            cat_code = f"sss?query={requests.utils.quote(kw)}"
            niche_name = f"Keyword: {kw}"
            niche_tag = "Custom"
        else:
            cat_code = "cta"
            niche_name = "Cars & Trucks"
            niche_tag = "Automotive"

        city_in = input(f"Enter city/region (Default: miami, e.g. newyork, dallas, houston, chicago): ").strip().lower()
        if city_in:
            city = city_in.replace(" ", "")

    show(f"\nTargeting Niche: {niche_name} | City: {city.upper()} | Workers: {MAX_WORKERS}", color=CYAN)
    show("Fetching live listings from Craigslist...")

    listings = []
    session = requests.Session()
    session.headers.update(HEADERS)

    # Scrape multiple pages
    for page in range(max_pages):
        page_offset = page * 120
        sep = "&" if "?" in cat_code else "?"
        url = f"https://{city}.craigslist.org/search/{cat_code}{sep}s={page_offset}"
        show(f"Fetching: {url} ...")
        try:
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                found_count = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if "/d/" in href or ".html" in href:
                        if href.startswith("/"):
                            href = f"https://{city}.craigslist.org{href}"
                        title = a.get_text(strip=True) or a.get("title", "")
                        if len(title) > 3 and not any(l["url"] == href for l in listings):
                            listings.append({
                                "url": href,
                                "title": title,
                                "price": "",
                                "location": city.title()
                            })
                            found_count += 1
                show(f"Page {page + 1}: Found {found_count} new listings.")
            else:
                show(f"Failed to fetch page {page + 1} (HTTP {r.status_code})", color=YELLOW)
        except Exception as e:
            show(f"Network error on page {page + 1}: {e}", color=YELLOW)
            break

    total = len(listings)
    if total == 0:
        show(f"No listings found for city '{city}' with category '{cat_code}'. Try another city or category.", color=YELLOW)
        return

    show(f"\nExtracted total {total} listings.")
    show(f"Scanning listings + Dealership/Company websites with {MAX_WORKERS} workers in parallel...")
    show("-" * 65)

    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_craigslist_post, item, niche_tag) for item in listings]
        for f in as_completed(futures):
            done += 1
            if done % 20 == 0 or done == total:
                pct = (done / total) * 100
                show(f"[PROGRESS] {done}/{total} posts analyzed ({pct:.1f}%) | Emails found: {len(discovered_emails)} | Leads logged: {len(leads_data)}", color=CYAN)

    # 1. Save Full Details
    csv_file = "craigslist_leads.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Title", "Price", "Location", "Emails", "Phones", "Dealer_Domains", "Post_URL", "Niche_Tag"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads_data)

    # 2. Save Exact CRM Format
    crm_csv = "craigslist_crm_leads.csv"
    crm_rows = []
    for em in sorted(discovered_emails):
        fn, ln = parse_name_from_email(em)
        crm_rows.append({
            "email": em,
            "first_name": fn,
            "last_name": ln,
            "tags": f"{niche_tag};Verified;Lead"
        })

    with open(crm_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["email", "first_name", "last_name", "tags"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(crm_rows)

    show("\n" + "=" * 65, color=CYAN)
    show("EXTRACTION & CRM EXPORT COMPLETE!", color=CYAN)
    show(f"Total Listings Scanned: {done}")
    show(f"Unique Verified Emails Harvested: {len(discovered_emails)}")
    show(f"Full Leads Export: {csv_file}")
    show(f"CRM Ready File:    {crm_csv} ({len(crm_rows)} leads)")
    show("=" * 65, color=CYAN)

if __name__ == "__main__":
    main()
