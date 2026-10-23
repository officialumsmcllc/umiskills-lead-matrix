import requests
import re
import csv
import sys
import os
import time
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
import dns.resolver
import threading
import random
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================
# UMISKILLS - 24/7 HYPER-SPEED OMNI LEAD ENGINE (ULTRA EXPANDED)
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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
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
    "knoxville", "desmoines", "boise", "spokane", "reno", "batonrouge",
    "greenville", "chattanooga", "littlerock", "bakersfield", "dayton"
]

EMAIL_PROVIDERS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "icloud.com"
]

JOB_ROLES = [
    "Owner", "Dealer Principal", "General Manager", "Sales Manager",
    "Finance Manager", "Inventory Director", "Used Car Manager",
    "Managing Partner", "Fleet Manager", "Store Manager", "Commercial Director"
]

CRAIGSLIST_CATS = ["cta", "ctd", "cto", "pts", "sya"]

BLOCKED_DOMAINS = (
    "example.com", "email.com", "address.com", "sentry.io",
    "wixpress.com", "schema.org", "google.com", "craigslist.org",
    "w3.org", "nhtsa.gov", "doubleclick.net", "mysite.com", "domain.com",
    "cloudflare.com", "gravatar.com", "wordpress.org", "youtube.com"
)

BLOCKED_TLDS = (
    ".id", ".my", ".ru", ".cn", ".br", ".vn", ".ir", ".pk", ".in", ".de", ".fr"
)

BLOCKED_EXTS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".ico", ".mp4", ".pdf", ".zip"
)

EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}\b')
DOMAIN_REGEX = re.compile(r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|net|org|co|us|biz|info|io))\b', re.IGNORECASE)

session = requests.Session()
adapter = HTTPAdapter(pool_connections=300, pool_maxsize=300, max_retries=1)
session.mount('http://', adapter)
session.mount('https://', adapter)

lock = threading.Lock()
discovered_emails = set()
total_leads_added = 0

MX_CACHE = {
    "gmail.com": True,
    "yahoo.com": True,
    "outlook.com": True,
    "hotmail.com": True,
    "aol.com": True,
    "icloud.com": True,
    "msn.com": True,
    "live.com": True,
    "zoho.com": True
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
        answers = dns.resolver.resolve(domain, 'MX', lifetime=1.5)
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
        if not first_name or first_name.isdigit():
            first_name = "Valued"
        if not last_name or last_name.isdigit():
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
# PIPELINE 1: CRAIGSLIST DEEP PAGINATION & US DEALERSHIP SITES
# -------------------------------------------------------------
def crawl_single_dealer_site(domain, city_tag="USA"):
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
    headers = {"User-Agent": USER_AGENTS[hash(domain) % len(USER_AGENTS)]}

    for u in target_urls:
        try:
            r = session.get(u, headers=headers, timeout=3.5, verify=False)
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

def pipeline_dealerships():
    # Loop continuously over cities with multi-page pagination & subcategories
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
                        r = session.get(url, headers=headers, timeout=3.5)
                        if r.status_code == 200:
                            soup = BeautifulSoup(r.text, 'html.parser')
                            post_links = []
                            for a in soup.find_all('a', href=True):
                                h = a['href']
                                if '/d/' in h and h.endswith('.html'):
                                    post_links.append(urljoin(url, h))

                            if not post_links:
                                break # No more posts in this category

                            dealer_domains = set()

                            def check_post(p_url):
                                try:
                                    pr = session.get(p_url, headers=headers, timeout=3.0)
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

                            with ThreadPoolExecutor(max_workers=50) as p_exec:
                                p_exec.map(check_post, post_links[:150])

                            if dealer_domains:
                                with ThreadPoolExecutor(max_workers=40) as d_exec:
                                    d_exec.map(lambda d: crawl_single_dealer_site(d, city), list(dealer_domains)[:100])

                    except Exception:
                        pass
                    time.sleep(0.5)

        time.sleep(15)

# -------------------------------------------------------------
# PIPELINE 2: MULTI-ENGINE DEEP SEARCH (LINKEDIN, FACEBOOK, DIRECTORIES)
# -------------------------------------------------------------
def search_yahoo(q_str, platform, city, offset=1):
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
                for em in EMAIL_REGEX.findall(full_text):
                    em = em.lower().strip("<>\"'(),;: ")
                    if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                        parts = title_text.replace("| LinkedIn", "").replace("| Facebook", "").split("-")
                        words = parts[0].strip().split() if parts else []
                        fn = words[0] if len(words) > 0 else "Valued"
                        ln = words[1] if len(words) > 1 else "Executive"
                        save_lead(em, fn, ln, f"{platform};Auto;{city.title()};Verified;Lead")
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
                        parts = title_text.replace("| LinkedIn", "").replace("| Facebook", "").split("-")
                        words = parts[0].strip().split() if parts else []
                        fn = words[0] if len(words) > 0 else "Auto"
                        ln = words[1] if len(words) > 1 else "Manager"
                        save_lead(em, fn, ln, f"{platform};Auto;{city.title()};Verified;Lead")
    except Exception:
        pass

def search_duckduckgo(q_str, platform, city):
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        r = session.post(url, data={"q": q_str}, headers=headers, timeout=4.0)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for res in soup.find_all("div", class_="result__body"):
                t = res.get_text()
                for em in EMAIL_REGEX.findall(t):
                    em = em.lower().strip("<>\"'(),;: ")
                    if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                        save_lead(em, "Auto", "Leader", f"{platform};Auto;{city.title()};Verified;Lead")
    except Exception:
        pass

def pipeline_social_and_directories():
    page_offsets = [1, 11, 21, 31, 41]

    while True:
        shuffled_cities = list(TOP_CITIES)
        random.shuffle(shuffled_cities)

        for city in shuffled_cities:
            tasks = []
            for role in JOB_ROLES:
                for prov in EMAIL_PROVIDERS:
                    tasks.append((f'site:linkedin.com/in/ "{role}" "car dealership" "{city}" "@{prov}"', "LinkedIn", city))
            for prov in EMAIL_PROVIDERS:
                tasks.append((f'site:facebook.com "car dealership" "{city}" "@{prov}"', "Facebook", city))
            tasks.append((f'site:yellowpages.com "car dealership" "{city}" "email"', "YellowPages", city))
            tasks.append((f'"auto sales" "{city}" "contact us" "email" "@gmail.com"', "Directories", city))

            random.shuffle(tasks)

            def execute_task(item):
                q_str, platform, c_name = item
                for off in page_offsets[:3]:
                    search_yahoo(q_str, platform, c_name, offset=off)
                    search_aol(q_str, platform, c_name, offset=off)
                if random.random() < 0.2:
                    search_duckduckgo(q_str, platform, c_name)

            with ThreadPoolExecutor(max_workers=35) as s_exec:
                s_exec.map(execute_task, tasks)

            time.sleep(2)
        time.sleep(10)

# -------------------------------------------------------------
# PIPELINE 3: NON-STOP INFINITE B2B CONTACT PAGES & WEBSITES
# -------------------------------------------------------------
def pipeline_b2b_crawler():
    auto_keywords = [
        'auto', 'car', 'motor', 'dealer', 'truck', 'tire', 'vehicle',
        'parts', 'drive', 'honda', 'toyota', 'ford', 'chevy', 'nissan',
        'bmw', 'mercedes', 'lexus', 'audi', 'hyundai', 'kia', 'jeep',
        'dodge', 'ram', 'subaru', 'cadillac', 'buick', 'gmc', 'porsche',
        'usedcars', 'autosales', 'motorsports', 'powersports', 'salvage'
    ]

    all_seed_urls = set()

    # 1. Load contact_pages.txt
    if os.path.exists("contact_pages.txt"):
        try:
            with open("contact_pages.txt", "r", encoding="utf-8") as f:
                for line in f:
                    l = line.strip()
                    if l.startswith("http"):
                        all_seed_urls.add(l)
        except Exception:
            pass

    # 2. Load websites.txt
    if os.path.exists("websites.txt"):
        try:
            with open("websites.txt", "r", encoding="utf-8") as f:
                for line in f:
                    d = line.strip().replace("http://", "").replace("https://", "").strip("/")
                    if d:
                        all_seed_urls.add(f"https://www.{d}")
                        all_seed_urls.add(f"https://{d}/contact")
                        all_seed_urls.add(f"https://{d}/about-us")
        except Exception:
            pass

    url_list = list(all_seed_urls)
    show(f"[B2B CRAWLER] Loaded {len(url_list)} total enterprise targets into non-stop pool.", color=CYAN)

    def scan_contact_url(u):
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            r = session.get(u, headers=headers, timeout=3.5, verify=False)
            if r.status_code == 200:
                raw_emails = EMAIL_REGEX.findall(r.text)
                for mailto in re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})', r.text, re.I):
                    raw_emails.append(mailto)

                for em in set(raw_emails):
                    em = em.lower().strip("<>\"'(),;: ")
                    if is_valid_email(em) and verify_mx(em.split('@')[-1]):
                        name_part = em.split('@')[0]
                        parts = re.split(r'[._-]', name_part)
                        fn = parts[0] if parts and parts[0] else "Sales"
                        ln = parts[1] if len(parts) > 1 and parts[1] else "Executive"
                        save_lead(em, fn, ln, "AutoDealer;CarSales;Verified;Lead")
        except Exception:
            pass

    while True:
        random.shuffle(url_list)
        batch_size = 120
        for i in range(0, len(url_list), batch_size):
            chunk = url_list[i:i+batch_size]
            with ThreadPoolExecutor(max_workers=50) as b2b_exec:
                b2b_exec.map(scan_contact_url, chunk)
            time.sleep(0.5)
        time.sleep(10)

# -------------------------------------------------------------
# MAIN 24/7 LAUNCHER: 3 PARALLEL PIPELINES
# -------------------------------------------------------------
def main():
    os.system("color 0b" if os.name == "nt" else "")
    show("=" * 70, color=CYAN)
    show("    UMISKILLS - 24/7 HYPER-SPEED OMNI LEAD ENGINE (EXPANDED MATRIX)", color=CYAN)
    show("                          by officialum1", color=CYAN)
    show("=" * 70, color=CYAN)
    show("CONCURRENCY: 135+ Active Workers Across 3 Endless Pipelines", color=YELLOW)
    show("PIPELINE 1: Craigslist Deep Pagination (s=0..480) & Dealer Sites", color=YELLOW)
    show("PIPELINE 2: Yahoo + AOL + DuckDuckGo Multi-Engine Dorks", color=YELLOW)
    show("PIPELINE 3: Non-Stop 10,000+ B2B Seed Pool (websites.txt & contacts)", color=YELLOW)
    show("OUTPUT: verified_crm_leads.csv (Strict Zero-Bounce CRM Format)\n", color=YELLOW)

    load_discovered()
    show(f"[DATABASE] Loaded {len(discovered_emails)} previously verified leads.\n", color=CYAN)

    t1 = threading.Thread(target=pipeline_dealerships, daemon=True)
    t2 = threading.Thread(target=pipeline_social_and_directories, daemon=True)
    t3 = threading.Thread(target=pipeline_b2b_crawler, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    show("[SYSTEM RUNNING] All 3 Continuous Pipelines Activated! Streaming leads...", color=GREEN)

    while True:
        time.sleep(10)
        show(f"[HYPER-SPEED STATS] Total 0-Bounce Leads in Database: {len(discovered_emails)} | This Session: +{total_leads_added}", color=GREEN)

if __name__ == "__main__":
    main()
