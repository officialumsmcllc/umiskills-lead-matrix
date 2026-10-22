@echo off
title UMISKILLS - CRM LEAD EXPORTER (by officialum1)
color 0A
cd /d "%~dp0"
cls
echo ==============================================================
echo             UMISKILLS - CRM LEAD EXPORTER v2.5
echo                       by officialum1
echo ==============================================================
echo.
echo Exporting clean leads to CRM format: (email,first_name,last_name,tags)...
echo.
if exist craigslist_leads.csv (
    python export_crm_format.py craigslist_leads.csv craigslist_crm_leads.csv "Automotive;Craigslist;Lead"
)
if exist clean_emails.txt (
    python export_crm_format.py clean_emails.txt all_leads_crm_formatted.csv "B2B;Verified;Lead"
)
echo.
echo [DONE] Exported successfully! Check craigslist_crm_leads.csv and all_leads_crm_formatted.csv
pause
