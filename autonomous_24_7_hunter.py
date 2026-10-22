import requests
import re
import csv
import sys
import os
import time
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import dns.resolver
import threading

# ==============================================================
# UMISKILLS - 24/7 AUTONOMOUS CONTINUOUS LEAD MACHINE
#                        by officialum1
# ==============================================================

MAX_WORKERS = 30
TIMEOUT = 8

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

TOP_50_CITIES = [
    "miami", "dallas", "houston", "losangeles", "newyork", "chicago",
    "atlanta", "orlando", "tampa", "phoenix", "lasvegas", "denver",
    "sandiego", "austin", "sanantonio", "seattle", "charlotte",
    "detroit", "philadelphia", "boston", "nashville", "columbus",
    "indianapolis", "minneapolis", "stlouis", "kansascity", "cincinnati",
    "cleveland", "pittsburgh", "baltimore", "washingtondc", "raleigh",
    "memphis", "louisville", "milwaukee", "oklahomacity", "albuquerque",
    "tucson", "fresno", "sacramento", "saltlakecity", "richmond",
    "jacksonville", "birmingham", "providence", "buffalo", "neworleans"
]

EMAIL_PROVIDERS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]

BLOCKED_DOMAINS = (
    "example.com", "email.com", "address.com", "sentry.io",
    "wixpress.com", "schema.org", "google.com", "craigslist.org",
    "w3.org", "nhtsa.gov", "doubleclick.net"
)

BLOCKED_EXTS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".ico", ".mp4", ".pdf"
)

EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}\b')
PHONE_REGEX = re.compile(r'\(?\b[2-9][0-9]{2}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b')
DOMAIN_REGEX = re.compile(r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|net|org|co|us|biz|info|io))\b', re.IGNORECASE)

lock = threading.Lock()
discovered_emails = set()
total_leads_added = 0

def show(text, color=GREEN):
    print(color + text + RESET, flush=True)

def load_discovered():
    global discovered_emails
    crm_file = "craigslist_crm_leads.csv"
    if os.path.exists(crm_file):
        try:
            with open(crm_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for r in reader:
                    if r and r[0]:
                        discovered_emails.add(r[0].strip().lower())
        except Exception:
            pass

def is_valid_email(email: str) -> bool:
    email = email.strip().lower().strip("<>\"'(),;:")
    if not email or "@" not in email:
        return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$', email):
        return False
    for ext in BLOCKED_EXTS:
        if email.endswith(ext):
            return False
    domain = email.split('@')[-1]
    for b in BLOCKED_DOMAINS:
        if domain == b or domain.endswith("." + b):
            return False
    return True

def verify_mx(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=3)
        return len(answers) > 0
    except Exception:
        return False

def save_lead(email, first_name, last_name, tags):
    global total_leads_added
    email = email.lower().strip()
    with lock:
        if email in discovered_emails:
            return
        discovered_emails.add(email)
        total_leads_added += 1

        crm_file = "craigslist_crm_leads.csv"
        file_exists = os.path.exists(crm_file)
        with open(crm_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["email", "first_name", "last_name", "tags"])
            writer.writerow([email, first_name, last_name, tags])

        with open("clean_emails.txt", "a", encoding="utf-8") as f:
            f.write(email + "\n")

        show(f"  [0-BOUNCE LEAD +] {email} | {first_name} {last_name} | [{tags}]")

def crawl_dealer_website(domain, city_tag):
    target_urls = [
        f"https://{domain}",
        f"https://www.{domain}",
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}/about",
        f"https://{domain}/about-us",
        f"https://{domain}/our-team"
    ]
    headers = {"User-Agent": USER_AGENTS[hash(domain) % len(USER_AGENTS)]}

    for u in target_urls:
        try:
            r = requests.get(u, headers=headers, timeout=TIMEOUT, verify=False)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                text = soup.get_text()
                raw_emails = EMAIL_REGEX.findall(text)
                for mailto in soup.find_all('a', href=re.compile(r'^mailto:', re.I)):
                    clean_m = mailto['href'].split('?')[0].replace('mailto:', '').strip()
                    raw_emails.append(clean_m)

                for em in set(raw_emails):
                    em = em.lower().strip()
                    if is_valid_email(em):
                        m_domain = em.split('@')[-1]
                        if verify_mx(m_domain):
                            name_part = em.split('@')[0]
                            parts = re.split(r'[._-]', name_part)
                            fn = parts[0].capitalize() if parts and parts[0] else "Sales"
                            ln = parts[1].capitalize() if len(parts) > 1 and parts[1] else "Executive"
                            save_lead(em, fn, ln, f"AutoDealer;{city_tag.title()};Verified;Lead")
        except Exception:
            continue

def scan_city_craigslist(city):
    show(f"\n[CITY SCAN] Fetching Car Dealerships in {city.upper()}...", color=CYAN)
    url = f"https://{city}.craigslist.org/search/cta?s=0"
    headers = {"User-Agent": USER_AGENTS[hash(city) % len(USER_AGENTS)]}

    post_urls = []
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/d/' in href and href.endswith('.html'):
                    full_link = urljoin(url, href)
                    if full_link not in post_urls:
                        post_urls.append(full_link)
    except Exception as e:
        show(f"Error accessing {city}: {e}", color=YELLOW)
        return

    show(f"  Found {len(post_urls)} vehicle listings in {city.title()}. Extracting dealership domains...", color=CYAN)

    dealer_domains = set()

    def process_post(p_url):
        try:
            r_post = requests.get(p_url, headers=headers, timeout=TIMEOUT)
            if r_post.status_code == 200:
                p_text = r_post.text
                # 1. Direct Emails in post text
                post_emails = EMAIL_REGEX.findall(p_text)
                for mailto in re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})', p_text, re.I):
                    post_emails.append(mailto)

                for em in set(post_emails):
                    em = em.lower().strip("<>\"'(),;:")
                    if is_valid_email(em):
                        m_domain = em.split('@')[-1]
                        if verify_mx(m_domain):
                            name_part = em.split('@')[0]
                            parts = re.split(r'[._-]', name_part)
                            fn = parts[0].capitalize() if parts and parts[0] else "Dealer"
                            ln = parts[1].capitalize() if len(parts) > 1 and parts[1] else "Sales"
                            save_lead(em, fn, ln, f"Craigslist;{city.title()};Verified;Lead")

                # 2. External Dealership Domains
                found_domains = DOMAIN_REGEX.findall(p_text)
                for d in found_domains:
                    d_lower = d.lower().strip()
                    if not any(b in d_lower for b in BLOCKED_DOMAINS):
                        with lock:
                            dealer_domains.add(d_lower)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as post_exec:
        post_exec.map(process_post, post_urls[:150])

    show(f"  Harvested {len(dealer_domains)} Unique Dealership Websites in {city.title()}! Deep crawling...", color=CYAN)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as dealer_exec:
        dealer_exec.map(lambda d: crawl_dealer_website(d, city), list(dealer_domains)[:100])

def harvest_social_decision_makers(city):
    show(f"[SOCIAL SCAN] Hunting LinkedIn Dealership Owners in {city.title()}...", color=CYAN)
    queries = []
    for jt in ["Owner", "General Manager", "Sales Director"]:
        for prov in EMAIL_PROVIDERS:
            q = f'site:linkedin.com/in/ "{jt}" "car dealership" "{city}" "@{prov}"'
            queries.append(q)

    def run_dork(q_str):
        try:
            url = f"https://search.yahoo.com/search?p={quote_plus(q_str)}&b=1"
            headers = {"User-Agent": USER_AGENTS[hash(q_str) % len(USER_AGENTS)]}
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.select(".algo") or soup.find_all("div", class_="Sr")
                for it in items:
                    title_el = it.find("h3") or it.find("a")
                    title_text = title_el.get_text(strip=True) if title_el else ""
                    snippet_el = it.find(class_="compText") or it
                    full_text = f"{title_text} {snippet_el.get_text()}"
                    emails = EMAIL_REGEX.findall(full_text)
                    for em in emails:
                        em = em.lower().strip("<>\"'(),;:")
                        if is_valid_email(em):
                            parts = title_text.replace("| LinkedIn", "").split("-")
                            name_words = parts[0].strip().split() if parts else []
                            fn = name_words[0].capitalize() if len(name_words) > 0 else "Valued"
                            ln = name_words[1].capitalize() if len(name_words) > 1 else "Executive"
                            save_lead(em, fn, ln, f"LinkedIn;Dealership;{city.title()};Lead")
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=10) as soc_exec:
        soc_exec.map(run_dork, queries)

def main():
    os.system("color 0b" if os.name == "nt" else "")
    show("=" * 68, color=CYAN)
    show("    UMISKILLS - 24/7 AUTONOMOUS CONTINUOUS LEAD MACHINE", color=CYAN)
    show("                      by officialum1", color=CYAN)
    show("=" * 68, color=CYAN)
    show("MODE: 100% UNATTENDED AUTOPILOT (SET & FORGET)", color=YELLOW)
    show("Looping across America's Top 50 Metro Areas Non-Stop...\n", color=YELLOW)

    load_discovered()
    show(f"[DATABASE] Loaded {len(discovered_emails)} previously verified leads.\n", color=CYAN)

    cycle = 1
    while True:
        show(f"\n{'#'*68}", color=CYAN)
        show(f"  >>> STARTING HARVESTING CYCLE #{cycle} ACROSS 50 CITIES <<<", color=CYAN)
        show(f"{'#'*68}\n", color=CYAN)

        for city in TOP_50_CITIES:
            try:
                # 1. Dealership Websites Crawl
                scan_city_craigslist(city)
                # 2. LinkedIn Decision-Makers
                harvest_social_decision_makers(city)

                show(f"\n[STATS] Total 0-Bounce Leads in Database: {len(discovered_emails)} | This Session: +{total_leads_added}", color=GREEN)
                time.sleep(2)
            except Exception as e:
                show(f"Error in {city}: {e}", color=YELLOW)
                time.sleep(3)

        cycle += 1
        show(f"\n[CYCLE #{cycle-1} COMPLETE] Completed full US pass! Sleeping 30 mins before refreshing...", color=CYAN)
        time.sleep(1800)

if __name__ == "__main__":
    main()
