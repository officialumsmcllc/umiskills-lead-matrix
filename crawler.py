import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import threading
import os
import sys
import re

# ==============================================================
# UMISKILLS - LEAD MATRIX PRO v2.5 (by officialum1)
# High-Performance Web Crawler & Lead Hunter
# ==============================================================

MAX_WORKERS = 30
TIMEOUT = 6
MAX_TOTAL_SITES = 1000
MAX_PAGES_PER_SITE = 20

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

EMAIL_REGEX = re.compile(r'(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,63}\b')

# Blocked extensions from naive email extraction
BLOCKED_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".eot", ".ico",
    ".mp4", ".zip", ".pdf", ".map", ".ts", ".jsx", ".tsx"
)

# Tracker/bot domains to discard
BLOCKED_DOMAINS = (
    "sentry.io",
    "sentry-next.wixpress.com",
    "sentry.wixpress.com",
    "wixpress.com",
    "example.com",
    "domain.com",
    "schema.org",
    "placeholder.com",
    "yourdomain.com",
    "test.com"
)

CONTACT_WORDS = (
    "contact",
    "contact-us",
    "contactus",
    "support",
    "about",
    "help",
    "customer-service"
)

lock = threading.Lock()
seen_domains = set()
seen_contacts = set()
seen_emails = set()
queue = deque()
pages_done = 0

SITES_FILE = "websites.txt"
CONTACT_FILE = "contact_pages.txt"
EMAIL_FILE = "Emails.txt"
CLEAN_EMAIL_FILE = "clean_emails.txt"
ERROR_FILE = "errors.txt"

# ==========================================
# DISPLAY
# ==========================================

def show(text, color=GREEN):
    print(color + text + RESET, flush=True)

# ==========================================
# EMAIL VERIFICATION (ANTI-JUNK ENGINE)
# ==========================================

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
    for b_domain in BLOCKED_DOMAINS:
        if domain == b_domain or domain.endswith("." + b_domain):
            return False
    tld = domain.split('.')[-1]
    if len(tld) < 2 or not tld.isalpha():
        return False
    return True

# ==========================================
# SAVE UNIQUE
# ==========================================

def save_unique(filename, value, memory):
    value = value.strip()
    if not value:
        return False
    with lock:
        if value in memory:
            return False
        memory.add(value)
        with open(filename, "a", encoding="utf-8") as f:
            f.write(value + "\n")
    return True

# ==========================================
# DOMAIN CLEANER
# ==========================================

def clean_domain(url):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        p = urlparse(url)
        if not p.netloc:
            return None
        return p.netloc.lower().replace("www.", "")
    except Exception:
        return None

# ==========================================
# ADD WEBSITE
# ==========================================

def add_domain(url):
    domain = clean_domain(url)
    if not domain:
        return False
    with lock:
        if domain in seen_domains:
            return False
        if len(seen_domains) >= MAX_TOTAL_SITES:
            return False
        seen_domains.add(domain)
        queue.append("https://" + domain)
    if save_unique(SITES_FILE, "https://" + domain, set()):
        show(f"[WEBSITE +] https://{domain}")
    return True

# ==========================================
# SCAN SINGLE PAGE
# ==========================================

def scan(url):
    websites = set()
    contacts = set()
    emails = set()
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            return websites, contacts, emails

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # 1. Emails from body text
        for em in re.findall(EMAIL_REGEX, html):
            if is_valid_email(em):
                emails.add(em.lower().strip("<>\"'(),;:"))

        # 2. Emails from mailto: links
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            if href.lower().startswith("mailto:"):
                raw_mail = href.split(":", 1)[1].split("?")[0].strip()
                if is_valid_email(raw_mail):
                    emails.add(raw_mail.lower().strip("<>\"'(),;:"))
                continue

            target = urljoin(url, href)
            p = urlparse(target)
            if p.scheme not in ("http", "https"):
                continue

            domain = clean_domain(target)
            if not domain:
                continue

            websites.add("https://" + domain)
            text = a.get_text(" ", strip=True).lower()
            href_lower = href.lower()
            if any(word in text or word in href_lower for word in CONTACT_WORDS):
                contacts.add(target)

        return websites, contacts, emails
    except Exception as e:
        with open(ERROR_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url} | {e}\n")
        return set(), set(), set()

# ==========================================
# CRAWL SITE (RECURSIVE MODE)
# ==========================================

def crawl_site(start):
    global pages_done
    local_pages = set()
    page_queue = deque([start])

    while page_queue and len(local_pages) < MAX_PAGES_PER_SITE:
        batch = []
        while page_queue and len(batch) < MAX_WORKERS:
            page = page_queue.popleft()
            if page not in local_pages:
                local_pages.add(page)
                batch.append(page)
        if not batch:
            break

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_page = {executor.submit(scan, p): p for p in batch}
            for future in as_completed(future_to_page):
                try:
                    websites, contacts, emails = future.result()
                    for site in websites:
                        domain = clean_domain(site)
                        if not domain:
                            continue
                        with lock:
                            if domain not in seen_domains and len(seen_domains) < MAX_TOTAL_SITES:
                                seen_domains.add(domain)
                                queue.append("https://" + domain)
                                with open(SITES_FILE, "a", encoding="utf-8") as f:
                                    f.write("https://" + domain + "\n")
                                show(f"[WEBSITE +] {domain}")

                    for contact in contacts:
                        if save_unique(CONTACT_FILE, contact, seen_contacts):
                            show(f"[CONTACT +] {contact}")

                    for email in emails:
                        if save_unique(EMAIL_FILE, email, seen_emails):
                            save_unique(CLEAN_EMAIL_FILE, email, set())
                            show(f"[EMAIL +] {email}")

                    current_domain = clean_domain(start)
                    for site in websites:
                        domain = clean_domain(site)
                        if domain == current_domain and site not in local_pages:
                            page_queue.append(site)
                except Exception as e:
                    show(f"[ERROR] {e}", color=YELLOW)

# ==========================================
# NEW FEATURE: CONTACT PAGES SCANNER MODE
# ==========================================

def scan_single_contact_page(url):
    found = set()
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            return found

        html = response.text
        # 1. Body Text
        for em in re.findall(EMAIL_REGEX, html):
            if is_valid_email(em):
                found.add(em.lower().strip("<>\"'(),;:"))

        # 2. Mailto links
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                raw_mail = href.split(":", 1)[1].split("?")[0].strip()
                if is_valid_email(raw_mail):
                    found.add(raw_mail.lower().strip("<>\"'(),;:"))
    except Exception as e:
        with open(ERROR_FILE, "a", encoding="utf-8") as f:
            f.write(f"[CONTACT SCAN ERROR] {url} | {e}\n")
    return found

def scan_contact_pages_mode():
    show("=" * 65, color=CYAN)
    show("           UMISKILLS - CONTACT PAGES EMAIL HUNTER v2.5", color=CYAN)
    show("                        by officialum1", color=CYAN)
    show("=" * 65, color=CYAN)

    if not os.path.exists(CONTACT_FILE):
        show(f"ERROR: {CONTACT_FILE} not found!", color=YELLOW)
        return

    # Load contact URLs
    with open(CONTACT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        urls = [line.strip() for line in f if line.strip().startswith(("http://", "https://"))]

    urls = list(dict.fromkeys(urls))  # deduplicate preserving order
    total_urls = len(urls)
    show(f"Loaded {total_urls} unique contact pages to scan.")

    # Load existing emails into memory to avoid duplicate work
    known_emails = set()
    for ef in (EMAIL_FILE, CLEAN_EMAIL_FILE):
        if os.path.exists(ef):
            with open(ef, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    em = line.strip().lower()
                    if em:
                        known_emails.add(em)

    show(f"Already known emails in memory: {len(known_emails)}")
    show(f"Starting parallel scanner with {MAX_WORKERS} workers...")
    show("-" * 60)

    scanned_count = 0
    new_emails_found = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(scan_single_contact_page, u): u for u in urls}
        for future in as_completed(future_to_url):
            scanned_count += 1
            url = future_to_url[future]
            try:
                emails = future.result()
                for em in emails:
                    with lock:
                        if em not in known_emails:
                            known_emails.add(em)
                            new_emails_found += 1
                            with open(EMAIL_FILE, "a", encoding="utf-8") as ef:
                                ef.write(em + "\n")
                            with open(CLEAN_EMAIL_FILE, "a", encoding="utf-8") as cef:
                                cef.write(em + "\n")
                            show(f"[EMAIL +] {em}  <-- {url}")
            except Exception:
                pass

            if scanned_count % 50 == 0 or scanned_count == total_urls:
                pct = (scanned_count / total_urls) * 100
                show(f"[PROGRESS] {scanned_count}/{total_urls} pages ({pct:.1f}%) | New emails: {new_emails_found} | Total: {len(known_emails)}", color=CYAN)

    show("=" * 60, color=CYAN)
    show("DONE! Contact pages scan completed.", color=CYAN)
    show(f"Pages Scanned: {scanned_count}")
    show(f"New Verified Emails: {new_emails_found}")
    show(f"Total Database Emails: {len(known_emails)}")
    show(f"Saved to: {EMAIL_FILE} and {CLEAN_EMAIL_FILE}")
    show("=" * 60, color=CYAN)

# ==========================================
# LOAD START SITES
# ==========================================

def load_start_sites():
    if not os.path.exists("start_sites.txt"):
        show("ERROR: start_sites.txt not found", color=YELLOW)
        return []
    with open("start_sites.txt", "r", encoding="utf-8") as f:
        return [x.strip() for x in f if x.strip()]

# ==========================================
# RECURSIVE CRAWLER MODE
# ==========================================

def run_recursive_crawler():
    show("=" * 65)
    show("               UMISKILLS - LEAD MATRIX PRO v2.5")
    show("            High-Performance Web Crawler & Lead Hunter")
    show("                       by officialum1")
    show("=" * 65)
    show("Status: Licensed & Active | 24/7 Engine")
    show("Recursive discovery: ON")
    show("Live saving: ON")
    show(f"Workers: {MAX_WORKERS}")
    show(f"Max websites: {MAX_TOTAL_SITES}")
    show("=" * 65)

    starts = load_start_sites()
    if not starts:
        return

    for site in starts:
        domain = clean_domain(site)
        if not domain:
            continue
        with lock:
            if domain not in seen_domains:
                seen_domains.add(domain)
                queue.append("https://" + domain)
                with open(SITES_FILE, "a", encoding="utf-8") as f:
                    f.write("https://" + domain + "\n")
        show(f"[START +] {domain}")

    while True:
        with lock:
            if not queue:
                break
            site = queue.popleft()

        show(f"\n[CRAWLING] {site}")
        crawl_site(site)
        with lock:
            remaining = len(queue)
        show(f"[QUEUE] {remaining} sites")

    show("\n" + "=" * 60)
    show("DONE")
    show("=" * 60)
    show(f"Websites: {len(seen_domains)}")
    show(f"Contact pages: {len(seen_contacts)}")
    show(f"Emails: {len(seen_emails)}")
    show(f"Saved: {SITES_FILE}")
    show(f"Saved: {CONTACT_FILE}")
    show(f"Saved: {EMAIL_FILE}")
    show("=" * 60)

# ==========================================
# MAIN
# ==========================================

def main():
    os.system("cls" if os.name == "nt" else "clear")

    mode = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--contacts", "-c", "2"):
            mode = "2"
        elif arg in ("--crawl", "-w", "1"):
            mode = "1"

    if not mode:
        show("=" * 65, color=CYAN)
        show("               UMISKILLS - LEAD MATRIX PRO v2.5", color=CYAN)
        show("            High-Performance Web Crawler & Lead Hunter", color=CYAN)
        show("                       by officialum1", color=CYAN)
        show("=" * 65, color=CYAN)
        show("[1] Full Recursive Crawler (crawl websites from start_sites.txt)")
        show("[2] Contact Pages Deep Hunter (scan contact_pages.txt directly for emails)")
        show("-" * 60)
        try:
            if sys.stdin.isatty():
                ans = input("Select Mode [1 or 2, default: 2]: ").strip()
                mode = ans if ans in ("1", "2") else "2"
            else:
                mode = "2"
        except Exception:
            mode = "2"

    if mode == "2":
        scan_contact_pages_mode()
    else:
        run_recursive_crawler()

if __name__ == "__main__":
    main()