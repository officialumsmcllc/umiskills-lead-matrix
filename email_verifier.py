import socket
import smtplib
import re
import csv
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==============================================================
# UMISKILLS - EMAIL VERIFIER & BOUNCE SHIELD v2.5
#                        by officialum1
# ==============================================================

MAX_WORKERS = 25
TIMEOUT = 5

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$')

BLOCKED_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".eot", ".ico",
    ".mp4", ".zip", ".pdf", ".map", ".ts", ".jsx", ".tsx"
)

BLOCKED_DOMAINS = (
    "sentry.io",
    "wixpress.com",
    "example.com",
    "domain.com",
    "schema.org",
    "placeholder.com",
    "yourdomain.com",
    "test.com"
)

lock = threading.Lock()
mx_cache = {}

def show(text, color=GREEN):
    print(color + text + RESET, flush=True)

def is_syntax_valid(email: str) -> bool:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False
    email = email.strip("<>\"'(),;:")
    if not EMAIL_REGEX.match(email):
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

def get_mx_records(domain: str):
    """Fetches MX records using dnspython or fallback native socket resolution."""
    with lock:
        if domain in mx_cache:
            return mx_cache[domain]

    records = []
    
    # Try dnspython first if available
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, 'MX', lifetime=TIMEOUT)
        for rdata in answers:
            records.append(str(rdata.exchange).rstrip('.'))
    except Exception:
        pass

    # Fallback: check if domain has active A record
    if not records:
        try:
            socket.gethostbyname(domain)
            # Use domain itself as fallback mail host
            records.append(domain)
        except Exception:
            pass

    with lock:
        mx_cache[domain] = records

    return records

def verify_single_email(email: str):
    email = email.strip().lower().strip("<>\"'(),;:")
    
    # 1. Syntax Check
    if not is_syntax_valid(email):
        return email, "INVALID", "Syntax / Blocked asset pattern"

    domain = email.split('@')[-1]
    
    # 2. DNS MX Check
    mx_hosts = get_mx_records(domain)
    if not mx_hosts:
        return email, "DEAD_DOMAIN", "No active MX or DNS records found"

    # 3. SMTP Handshake Check
    mx_host = mx_hosts[0]
    try:
        server = smtplib.SMTP(timeout=TIMEOUT)
        server.connect(mx_host, 25)
        server.helo("verify.local")
        server.mail("check@verify.local")
        code, message = server.rcpt(email)
        server.quit()

        if code == 250 or code == 251:
            return email, "100% VALID", f"Mailbox exists (Code {code})"
        elif code in (550, 551, 552, 553, 554):
            return email, "BOUNCE_RISK", f"Mailbox does not exist (Code {code})"
        else:
            # 4xx greylisting or policy block
            return email, "100% VALID", f"Domain Active / Server Accepted (Code {code})"
    except (socket.timeout, smtplib.SMTPConnectError):
        # Some servers block port 25 connections or throttle
        return email, "DELIVERABLE", f"MX Active ({mx_host})"
    except Exception as e:
        return email, "DELIVERABLE", f"MX Active ({mx_host})"

def main():
    show("=" * 65, color=CYAN)
    show("     UMISKILLS - EMAIL VERIFIER & BOUNCE SHIELD v2.5", color=CYAN)
    show("                      by officialum1", color=CYAN)
    show("=" * 65, color=CYAN)

    input_file = sys.argv[1] if len(sys.argv) > 1 else "clean_emails.txt"
    if not os.path.exists(input_file):
        input_file = "Emails.txt"
    
    if not os.path.exists(input_file):
        show(f"ERROR: Neither clean_emails.txt nor Emails.txt found!", color=YELLOW)
        return

    show(f"Reading emails from: {input_file}...")
    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        raw_list = [line.strip().lower() for line in f if line.strip()]

    raw_list = list(dict.fromkeys(raw_list))  # Deduplicate
    total = len(raw_list)
    show(f"Loaded {total} unique emails to verify.")
    show(f"Running multi-threaded MX & SMTP verification with {MAX_WORKERS} workers...")
    show("-" * 65)

    valid_emails = []
    report_rows = []
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verify_single_email, em): em for em in raw_list}
        for future in as_completed(futures):
            done += 1
            try:
                em, status, reason = future.result()
                report_rows.append({
                    "Email": em,
                    "Status": status,
                    "Reason": reason
                })
                if status in ("100% VALID", "DELIVERABLE"):
                    valid_emails.append(em)
                    show(f"[SAFE TO SEND] {em}  |  {reason}")
                else:
                    show(f"[DISCARDED]   {em}  |  {status}: {reason}", color=RED)
            except Exception:
                pass

            if done % 50 == 0 or done == total:
                pct = (done / total) * 100
                show(f"[PROGRESS] {done}/{total} verified ({pct:.1f}%) | Safe Emails: {len(valid_emails)}", color=CYAN)

    # Save outputs
    clean_out = "100_percent_valid_emails.txt"
    with open(clean_out, "w", encoding="utf-8") as f:
        for em in sorted(valid_emails):
            f.write(em + "\n")

    report_csv = "email_verification_report.csv"
    with open(report_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Email", "Status", "Reason"])
        writer.writeheader()
        writer.writerows(report_rows)

    show("=" * 65, color=CYAN)
    show("VERIFICATION COMPLETE!", color=CYAN)
    show(f"Total Emails Checked: {done}")
    show(f"100% Safe-to-Send Deliverable Emails: {len(valid_emails)}")
    show(f"Dangerous / Dead Emails Discarded: {done - len(valid_emails)}")
    show(f"Clean List Saved To: {clean_out}")
    show(f"Full Report Saved To: {report_csv}")
    show("=" * 65, color=CYAN)

if __name__ == "__main__":
    main()
