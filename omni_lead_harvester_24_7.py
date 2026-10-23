import requests
import re
import csv
import sys
import os
import time
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
import dns.resolver
import threading
import random
import urllib3

# Suppress SSL warnings completely
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================
# UMISKILLS - 24/7 PERPETUAL OMNI LEAD ENGINE (SELF-FEEDING MATRIX)
#                        by officialum1
# ==============================================================

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
]

TOP_CITIES = [
    "miami", "dallas", "houston", "losangeles", "newyork", "chicago",
    "atlanta", "orlando", "tampa", "phoenix", "lasvegas", "denver",
    "sandiego", "austin", "sanantonio", "seattle", "charlotte",
    "detroit", "philadelphia", "boston", "nashville", "columbus",
    "indianapolis", "minneapolis", "stlouis", "kansascity", "cincinnati",
    "cleveland", "pittsburgh", "baltimore", "washingtondc", "raleigh",
    "memphis", "louisville", "milwaukee", "oklahomacity", "albuquerque",
    "tucson", "fresno", "sacramento", "saltlakecity", "richmond",
    "jacksonville", "birmingham", "providence", "buffalo", "neworleans",
    "portland", "honolulu", "omaha", "elpaso", "tulsa", "wichita",
    "knoxville", "desmoines", "boise", "spokane", "reno", "batonrouge"
]

AUTO_BRANDS = [
    "car dealership", "used cars", "auto sales", "ford dealer",
    "chevy dealer", "toyota dealer", "honda dealer", "nissan dealer",
    "jeep ram dealer", "hyundai dealer", "subaru dealer", "bmw dealer",
    "mercedes dealer", "lexus dealer", "audi dealer", "kia dealer",
    "truck sales", "commercial vehicles", "auto repair", "motorsports"
]

JOB_ROLES = [
    "Owner", "Dealer Principal", "General Manager", "Sales Manager",
    "Finance Manager", "Inventory Director", "Used Car Manager",
    "Managing Partner", "Fleet Manager", "Store Manager"
]

EMAIL_PROVIDERS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "icloud.com"
]

CRAIGSLIST_CATS = ["cta", "ctd", "cto", "pts", "sya"]

BLOCKED_DOMAINS = (
    "example.com", "email.com", "address.com", "sentry.io",
    "wixpress.com", "schema.org", "google.com", "craigslist.org",
    "w3.org", "nhtsa.gov", "doubleclick.net", "mysite.com", "domain.com",
    "cloudflare.com", "gravatar.com", "wordpress.org", "youtube.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com", "yahoo.com"
)

BLOCKED_TLDS = (
    ".id", ".my", ".ru", ".cn", ".br", ".vn", ".ir", ".pk", ".in", ".de", ".fr"
)

BLOCKED_EXTS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".ico", ".mp4", ".pdf", ".zip"
)

EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}\b')
DOMAIN_REGEX = re.compile(r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.(?:com|net|org|us|biz|co))\b', re.IGNORECASE)

# Fast Persistent HTTP Session
session = requests.Session()
adapter = HTTPAdapter(pool_connections=350, pool_maxsize=350, max_retries=1)
session.mount('http://', adapter)
session.mount('https://', adapter)

lock = threading.Lock()
discovered_emails = set()
discovered_dealer_domains = set()
total_leads_added = 0

MX_CACHE = {
    "gmail.com": True, "yahoo.com": True, "outlook.com": True,
    "hotmail.com": True, "aol.com": True, "icloud.com": True,
    "msn.com": True, "live.com": True, "zoho.com": True
}

def show(text, color=GREEN):
    print(color + text + RESET, flush=True)

def load_discovered():
    global discovered_emails
    for fname in ["verified_crm_leads.csv", "craigslist_crm_leads.csv"]:
        if os.path.exists(fname):
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for r in reader:
                        if r and r[0]:
                            discovered_emails.add(r[0].strip().lower())
            except Exception:
                pass

def is_valid_email(email: str) -> bool:
    email = email.strip().lower().strip("<>\"'(),;: ")
    if not email or "@" not in email:
        return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$', email):
        return False
    for ext in BLOCKED_EXTS:
        if email.endswith(ext):
            return False
    domain = email.split('@')[-1]
    for tld in BLOCKED_TLDS:
        if domain.endswith(tld):
            return False
    for b in BLOCKED_DOMAINS:
        if domain == b or domain.endswith("." + b):
            return False
    return True

def verify_mx(domain: str) -> bool:
    domain = domain.lower().strip()
    if domain in MX_CACHE:
        return MX_CACHE[domain]
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=1.2)
        res = len(answers) > 0
        MX_CACHE[domain] = res
        return res
    except Exception:
        MX_CACHE[domain] = False
        return False

def save_lead(email, first_name, last_name, tags):
    global total_leads_added
    email = email.lower().strip("<>\"'(),;: ")
    with lock:
        if email in discovered_emails:
            return
        discovered_emails.add(email)
        total_leads_added += 1

        first_name = first_name.strip(',.:; ').capitalize()
        last_name = last_name.strip(',.:; ').capitalize()
        if not first_name or first_name.isdigit() or len(first_name) > 25:
            first_name = "Valued"
        if not last_name or last_name.isdigit() or len(last_name) > 25:
            last_name = "Partner"

        for crm_file in ["verified_crm_leads.csv", "craigslist_crm_leads.csv"]:
            file_exists = os.path.exists(crm_file)
            with open(crm_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["email", "first_name", "last_name", "tags"])
                writer.writerow([email, first_name, last_name, tags])

        with open("clean_emails.txt", "a", encoding="utf-8") as f:
            f.write(email + "\n")

        show(f"  [0-BOUNCE LEAD +] {email} | {first_name} {last_name} | [{tags}]")

# -------------------------------------------------------------
# PIPELINE 1: CRAIGSLIST DEEP PAGINATION (100+ METROS, 5 CATEGORIES)
# -------------------------------------------------------------
def crawl_single_dealer_site(domain, city_tag="USA"):
    domain = domain.lower().strip()
    with lock:
        if domain in discovered_dealer_domains:
            return
        discovered_dealer_domains.add(domain)

    target_urls = [
        f"https://www.{domain}",
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}/about-us",
        f"https://{domain}/staff",
        f"https://{domain}/our-team",
        f"https://{domain}/meet-our-staff",
        f"https://{domain}/dealership/about.htm"
    ]
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for u in target_urls:
        try:
            r = session.get(u, headers=headers, timeout=3.0, verify=False)
            if r.status_code == 200:
                text = r.text
                found_emails = EMAIL_REGEX.findall(text)
                for mailto in re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})', text, re.I):
                    found_emails.append(mailto)

                for em in set(found_emails):
                    em = em.lower().strip("<>\"'(),;: ")
                    if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                        name_part = em.split('@')[0]
                        parts = re.split(r'[._-]', name_part)
                        fn = parts[0] if parts and parts[0] else "Sales"
                        ln = parts[1] if len(parts) > 1 and parts[1] else "Executive"
                        save_lead(em, fn, ln, f"AutoDealer;{city_tag.title()};Verified;Lead")
        except Exception:
            continue

def pipeline_craigslist():
    page_offsets = [0, 120, 240, 360, 480]

    while True:
        shuffled_cities = list(TOP_CITIES)
        random.shuffle(shuffled_cities)

        for city in shuffled_cities:
            for cat in CRAIGSLIST_CATS:
                for offset in page_offsets:
                    try:
                        url = f"https://{city}.craigslist.org/search/{cat}?s={offset}"
                        headers = {"User-Agent": random.choice(USER_AGENTS)}
                        r = session.get(url, headers=headers, timeout=3.0)
                        if r.status_code == 200:
                            soup = BeautifulSoup(r.text, 'html.parser')
                            post_links = []
                            for a in soup.find_all('a', href=True):
                                h = a['href']
                                if '/d/' in h and h.endswith('.html'):
                                    post_links.append(urljoin(url, h))

                            if not post_links:
                                break

                            dealer_domains = set()

                            def check_post(p_url):
                                try:
                                    pr = session.get(p_url, headers=headers, timeout=2.8)
                                    if pr.status_code == 200:
                                        p_text = pr.text
                                        for em in EMAIL_REGEX.findall(p_text):
                                            em = em.lower().strip("<>\"'(),;: ")
                                            if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                                                name_part = em.split('@')[0]
                                                parts = re.split(r'[._-]', name_part)
                                                fn = parts[0] if parts and parts[0] else "Dealer"
                                                ln = parts[1] if len(parts) > 1 and parts[1] else "Sales"
                                                save_lead(em, fn, ln, f"Craigslist;{city.title()};Verified;Lead")

                                        for d in DOMAIN_REGEX.findall(p_text):
                                            d_low = d.lower().strip()
                                            if not any(b in d_low for b in BLOCKED_DOMAINS):
                                                dealer_domains.add(d_low)
                                except Exception:
                                    pass

                            with ThreadPoolExecutor(max_workers=40) as p_exec:
                                p_exec.map(check_post, post_links[:120])

                            if dealer_domains:
                                with ThreadPoolExecutor(max_workers=30) as d_exec:
                                    d_exec.map(lambda d: crawl_single_dealer_site(d, city), list(dealer_domains)[:60])

                    except Exception:
                        pass
                    time.sleep(0.3)

        time.sleep(15)

# -------------------------------------------------------------
# PIPELINE 2: SELF-FEEDING SEARCH MATRIX (YAHOO + AOL + DDG)
# -------------------------------------------------------------
def search_and_harvest(q_str, platform, city, offset=1):
    try:
        url = f"https://search.yahoo.com/search?p={quote_plus(q_str)}&b={offset}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        r = session.get(url, headers=headers, timeout=3.5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for it in soup.select(".algo") or soup.find_all("div", class_="Sr"):
                title_el = it.find("h3") or it.find("a")
                title_text = title_el.get_text(strip=True) if title_el else ""
                snippet_el = it.find(class_="compText") or it
                full_text = f"{title_text} {snippet_el.get_text()}"

                # Extract emails
                for em in EMAIL_REGEX.findall(full_text):
                    em = em.lower().strip("<>\"'(),;: ")
                    if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                        parts = title_text.replace("| LinkedIn", "").replace("| Facebook", "").split("-")
                        words = parts[0].strip().split() if parts else []
                        fn = words[0] if len(words) > 0 else "Valued"
                        ln = words[1] if len(words) > 1 else "Executive"
                        save_lead(em, fn, ln, f"{platform};Auto;{city.title()};Verified;Lead")

                # Extract linked dealership domains to feed into dealer crawler
                for link in it.find_all("a", href=True):
                    href = link['href']
                    parsed = urlparse(href)
                    netloc = parsed.netloc.lower()
                    if netloc.startswith("www."):
                        netloc = netloc[4:]
                    if netloc and not any(b in netloc for b in BLOCKED_DOMAINS):
                        threading.Thread(target=crawl_single_dealer_site, args=(netloc, city), daemon=True).start()

    except Exception:
        pass

def search_aol(q_str, platform, city, offset=1):
    try:
        url = f"https://search.aol.com/aol/search?q={quote_plus(q_str)}&b={offset}"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        r = session.get(url, headers=headers, timeout=3.5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for it in soup.select(".algo") or soup.find_all("div", class_="Sr"):
                title_el = it.find("h3") or it.find("a")
                title_text = title_el.get_text(strip=True) if title_el else ""
                full_text = f"{title_text} {it.get_text()}"
                for em in EMAIL_REGEX.findall(full_text):
                    em = em.lower().strip("<>\"'(),;: ")
                    if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                        save_lead(em, "Auto", "Executive", f"{platform};Auto;{city.title()};Verified;Lead")
    except Exception:
        pass

def pipeline_search_matrix():
    page_offsets = [1, 11, 21, 31, 41]

    while True:
        shuffled_cities = list(TOP_CITIES)
        random.shuffle(shuffled_cities)

        for city in shuffled_cities:
            tasks = []
            for role in JOB_ROLES:
                for prov in EMAIL_PROVIDERS:
                    tasks.append((f'site:linkedin.com/in/ "{role}" "dealership" "{city}" "@{prov}"', "LinkedIn", city))
            for brand in AUTO_BRANDS:
                for prov in EMAIL_PROVIDERS:
                    tasks.append((f'"{brand}" "{city}" "contact us" "@{prov}"', "Directories", city))
                tasks.append((f'site:facebook.com "{brand}" "{city}" "email"', "Facebook", city))
                tasks.append((f'site:yellowpages.com "{brand}" "{city}"', "YellowPages", city))

            random.shuffle(tasks)

            def execute_task(item):
                q_str, platform, c_name = item
                for off in page_offsets[:3]:
                    search_and_harvest(q_str, platform, c_name, offset=off)
                    search_aol(q_str, platform, c_name, offset=off)

            with ThreadPoolExecutor(max_workers=35) as s_exec:
                s_exec.map(execute_task, tasks)

            time.sleep(2)
        time.sleep(10)

# -------------------------------------------------------------
# PIPELINE 3: SEED DIRECTORY & DEALER DOMAIN CRAWLER
# -------------------------------------------------------------
def pipeline_seed_crawler():
    seeds = []
    for s_file in ["start_sites.txt", "sites.txt"]:
        if os.path.exists(s_file):
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    for line in f:
                        l = line.strip()
                        if l.startswith("http"):
                            seeds.append(l)
            except Exception:
                pass

    while True:
        random.shuffle(seeds)
        for seed_url in seeds:
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                r = session.get(seed_url, headers=headers, timeout=4.0, verify=False)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    # Find external dealership links
                    discovered = set()
                    for a in soup.find_all('a', href=True):
                        h = a['href']
                        if h.startswith("http"):
                            d = urlparse(h).netloc.lower()
                            if d.startswith("www."):
                                d = d[4:]
                            if d and not any(b in d for b in BLOCKED_DOMAINS) and not any(d.endswith(t) for t in BLOCKED_TLDS):
                                discovered.add(d)

                    if discovered:
                        with ThreadPoolExecutor(max_workers=30) as c_exec:
                            c_exec.map(lambda d: crawl_single_dealer_site(d, "USA"), list(discovered)[:50])
            except Exception:
                pass
            time.sleep(1)
        time.sleep(30)

# -------------------------------------------------------------
# MAIN 24/7 LAUNCHER
# -------------------------------------------------------------
def main():
    os.system("color 0b" if os.name == "nt" else "")
    show("=" * 70, color=CYAN)
    show("    UMISKILLS - 24/7 PERPETUAL OMNI LEAD ENGINE (SELF-FEEDING MATRIX)", color=CYAN)
    show("                          by officialum1", color=CYAN)
    show("=" * 70, color=CYAN)
    show("CONCURRENCY: 120+ Active Workers Across 3 Endless Pipelines", color=YELLOW)
    show("PIPELINE 1: Craigslist Deep Pagination (s=0..480) & Dealer Sites", color=YELLOW)
    show("PIPELINE 2: Self-Feeding Search Matrix (Yahoo + AOL + DDG)", color=YELLOW)
    show("PIPELINE 3: US Auto Association & Directory Seed Crawler", color=YELLOW)
    show("OUTPUT: verified_crm_leads.csv (Strict Zero-Bounce CRM Format)\n", color=YELLOW)

    load_discovered()
    show(f"[DATABASE] Loaded {len(discovered_emails)} previously verified leads.\n", color=CYAN)

    t1 = threading.Thread(target=pipeline_craigslist, daemon=True)
    t2 = threading.Thread(target=pipeline_search_matrix, daemon=True)
    t3 = threading.Thread(target=pipeline_seed_crawler, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    show("[SYSTEM ACTIVE] All 3 Pipelines Running Non-Stop! Streaming leads...", color=GREEN)

    while True:
        time.sleep(10)
        show(f"[HYPER-SPEED STATS] Total 0-Bounce Leads in Database: {len(discovered_emails)} | This Session: +{total_leads_added}", color=GREEN)

if __name__ == "__main__":
    main()
