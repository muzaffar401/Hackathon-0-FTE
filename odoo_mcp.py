# Install Odoo Community: https://www.odoo.com/documentation
# Or use Docker: docker run -p 8069:8069 odoo:17

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Odoo connection settings from environment
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USER = os.getenv("ODOO_USER", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")

# Vault path for saving summaries
VAULT_PATH = Path(__file__).parent / "Accounting"


def _make_jsonrpc_request(endpoint, params, method="call"):
    """
    Internal helper to make JSON-RPC requests to Odoo.
    """
    url = f"{ODOO_URL}/jsonrpc"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            print(f"{Fore.RED}[ERROR] Odoo API Error: {result['error'].get('message', 'Unknown error')}")
            return None
        
        return result.get("result")
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}[ERROR] Connection failed to Odoo at {ODOO_URL}")
        return None
    except requests.exceptions.Timeout:
        print(f"{Fore.RED}[ERROR] Request timed out connecting to Odoo")
        return None
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Unexpected error: {str(e)}")
        return None


def authenticate():
    """
    Authenticate with Odoo and return the user ID (uid).
    Returns None if authentication fails.
    """
    try:
        params = {
            "db": ODOO_DB,
            "username": ODOO_USER,
            "password": ODOO_PASSWORD
        }
        
        result = _make_jsonrpc_request("/web/session/authenticate", params, method="call")
        
        if result and "uid" in result:
            uid = result["uid"]
            if uid:
                print(f"{Fore.GREEN}[SUCCESS] Authenticated with Odoo. UID: {uid}")
                return uid
            else:
                print(f"{Fore.RED}[ERROR] Authentication failed - invalid credentials")
                _alert_auth_error("Authentication failed - invalid credentials")
                return None
        else:
            print(f"{Fore.RED}[ERROR] No UID returned from authentication")
            _alert_auth_error("No UID returned from authentication")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Authentication exception: {str(e)}")
        _alert_auth_error(f"Authentication exception: {str(e)}")
        return None


def _alert_auth_error(error_message):
    """
    Create an alert file in /Needs_Action/ when auth fails.
    """
    try:
        needs_action_path = Path(__file__).parent / "Needs_Action"
        needs_action_path.mkdir(parents=True, exist_ok=True)
        
        alert_file = needs_action_path / "ODOO_AUTH_ERROR.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        content = f"""# Odoo Authentication Error

**Timestamp:** {timestamp}

**Error:** {error_message}

**Action Required:**
Please check your Odoo credentials in the `.env` file:
- ODOO_URL
- ODOO_DB
- ODOO_USER
- ODOO_PASSWORD

Ensure the Odoo server is running and accessible.
"""
        with open(alert_file, "w") as f:
            f.write(content)
        
        print(f"{Fore.YELLOW}[ALERT] Auth error logged to {alert_file}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to write auth error alert: {str(e)}")


def get_invoices(state="open"):
    """
    Fetch invoices from Odoo.
    
    Args:
        state: Filter by invoice state ('open', 'paid', 'draft', 'cancel')
    
    Returns:
        List of invoices with: id, name, partner_name, amount_total, state, invoice_date_due
    """
    try:
        uid = authenticate()
        if not uid:
            return None
        
        # Define domain filter
        domain = []
        if state:
            domain.append(["state", "=", state])
        
        # Define fields to retrieve
        fields_list = ["id", "name", "partner_id", "amount_total", "state", "invoice_date_due"]
        
        params = {
            "db": ODOO_DB,
            "uid": uid,
            "password": ODOO_PASSWORD,
            "model": "account.move",
            "domain": domain,
            "fields": fields_list
        }
        
        result = _make_jsonrpc_request("/web/dataset/search_read", params, method="call")
        
        if not result:
            print(f"{Fore.YELLOW}[WARNING] No invoices found with state='{state}'")
            return []
        
        invoices = []
        for inv in result.get("records", []):
            # Handle partner_id which may be a tuple [id, name] or just id
            partner_name = ""
            if inv.get("partner_id"):
                if isinstance(inv["partner_id"], list) and len(inv["partner_id"]) >= 2:
                    partner_name = inv["partner_id"][1]
                else:
                    partner_name = str(inv["partner_id"])
            
            invoices.append({
                "id": inv.get("id"),
                "name": inv.get("name", ""),
                "partner_name": partner_name,
                "amount_total": inv.get("amount_total", 0.0),
                "state": inv.get("state", ""),
                "invoice_date_due": inv.get("invoice_date_due", "")
            })
        
        print(f"{Fore.GREEN}[SUCCESS] Retrieved {len(invoices)} invoices with state='{state}'")
        return invoices
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error fetching invoices: {str(e)}")
        return None


def create_invoice_draft(customer_name, amount, description, due_date, dry_run=None):
    """
    Create a draft invoice in Odoo.
    
    Args:
        customer_name: Name of the customer
        amount: Invoice amount
        description: Invoice line description
        due_date: Due date (YYYY-MM-DD format)
        dry_run: If True, log only without creating. Checks DRY_RUN env var if None.
    
    Returns:
        Invoice ID if created, None otherwise
    """
    # Check dry run mode
    if dry_run is None:
        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    if dry_run:
        print(f"{Fore.YELLOW}[DRY RUN] Would create draft invoice:")
        print(f"  Customer: {customer_name}")
        print(f"  Amount: {amount}")
        print(f"  Description: {description}")
        print(f"  Due Date: {due_date}")
        return -1  # Return -1 to indicate dry run
    
    try:
        uid = authenticate()
        if not uid:
            return None
        
        # First, find or create the partner
        partner_params = {
            "db": ODOO_DB,
            "uid": uid,
            "password": ODOO_PASSWORD,
            "model": "res.partner",
            "domain": [["name", "=", customer_name]]
        }
        
        partner_result = _make_jsonrpc_request("/web/dataset/search_read", partner_params, method="call")
        
        partner_id = None
        if partner_result and partner_result.get("records"):
            partner_id = partner_result["records"][0]["id"]
        else:
            # Create new partner
            create_result = _make_jsonrpc_request("/web/dataset/call_kw", {
                "db": ODOO_DB,
                "uid": uid,
                "password": ODOO_PASSWORD,
                "model": "res.partner",
                "method": "create",
                "args": [[{"name": customer_name}]],
                "kwargs": {}
            }, method="call")
            
            if create_result:
                partner_id = create_result
                print(f"{Fore.GREEN}[SUCCESS] Created new partner: {customer_name} (ID: {partner_id})")
            else:
                print(f"{Fore.RED}[ERROR] Failed to create partner: {customer_name}")
                return None
        
        # Create the invoice
        invoice_values = {
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_date_due": due_date,
            "invoice_line_ids": [
                [0, 0, {
                    "name": description,
                    "quantity": 1,
                    "price_unit": amount
                }]
            ]
        }
        
        create_invoice_params = {
            "db": ODOO_DB,
            "uid": uid,
            "password": ODOO_PASSWORD,
            "model": "account.move",
            "method": "create",
            "args": [[invoice_values]],
            "kwargs": {}
        }
        
        result = _make_jsonrpc_request("/web/dataset/call_kw", create_invoice_params, method="call")
        
        if result:
            invoice_id = result
            print(f"{Fore.GREEN}[SUCCESS] Created draft invoice ID: {invoice_id}")
            return invoice_id
        else:
            print(f"{Fore.RED}[ERROR] Failed to create invoice")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error creating invoice: {str(e)}")
        return None


def get_monthly_revenue(year, month):
    """
    Fetch all paid invoices for a specific month.
    
    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
    
    Returns:
        Dict with: total_revenue, invoice_count, avg_invoice_value
    """
    try:
        uid = authenticate()
        if not uid:
            return None
        
        # Calculate date range for the month
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        # Domain: paid invoices within the month
        domain = [
            ["state", "=", "posted"],
            ["move_type", "=", "out_invoice"],
            ["invoice_date", ">=", start_date],
            ["invoice_date", "<", end_date]
        ]
        
        params = {
            "db": ODOO_DB,
            "uid": uid,
            "password": ODOO_PASSWORD,
            "model": "account.move",
            "domain": domain,
            "fields": ["amount_total"]
        }
        
        result = _make_jsonrpc_request("/web/dataset/search_read", params, method="call")
        
        total_revenue = 0.0
        invoice_count = 0
        
        if result and result.get("records"):
            for inv in result["records"]:
                total_revenue += inv.get("amount_total", 0.0)
                invoice_count += 1
        
        avg_invoice_value = total_revenue / invoice_count if invoice_count > 0 else 0.0
        
        revenue_data = {
            "total_revenue": round(total_revenue, 2),
            "invoice_count": invoice_count,
            "avg_invoice_value": round(avg_invoice_value, 2)
        }
        
        print(f"{Fore.GREEN}[SUCCESS] Monthly revenue for {year}-{month:02d}: ${total_revenue:.2f} ({invoice_count} invoices)")
        return revenue_data
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error fetching monthly revenue: {str(e)}")
        return None


def get_overdue_invoices():
    """
    Fetch all invoices past their due date.
    
    Returns:
        List of overdue invoices with: client name, amount, days overdue
    """
    try:
        uid = authenticate()
        if not uid:
            return None
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Domain: open invoices with due date before today
        domain = [
            ["state", "in", ["open", "posted"]],
            ["move_type", "=", "out_invoice"],
            ["invoice_date_due", "<", today],
            ["payment_state", "=", "not_paid"]
        ]
        
        params = {
            "db": ODOO_DB,
            "uid": uid,
            "password": ODOO_PASSWORD,
            "model": "account.move",
            "domain": domain,
            "fields": ["id", "name", "partner_id", "amount_total", "amount_residual", "invoice_date_due"]
        }
        
        result = _make_jsonrpc_request("/web/dataset/search_read", params, method="call")
        
        overdue_list = []
        today_date = datetime.now()
        
        if result and result.get("records"):
            for inv in result["records"]:
                # Handle partner_id
                partner_name = ""
                if inv.get("partner_id"):
                    if isinstance(inv["partner_id"], list) and len(inv["partner_id"]) >= 2:
                        partner_name = inv["partner_id"][1]
                    else:
                        partner_name = str(inv["partner_id"])
                
                # Calculate days overdue
                days_overdue = 0
                if inv.get("invoice_date_due"):
                    try:
                        due_date = datetime.strptime(inv["invoice_date_due"], "%Y-%m-%d")
                        days_overdue = (today_date - due_date).days
                    except ValueError:
                        days_overdue = 0
                
                overdue_list.append({
                    "id": inv.get("id"),
                    "name": inv.get("name", ""),
                    "client_name": partner_name,
                    "amount": inv.get("amount_total", 0.0),
                    "amount_due": inv.get("amount_residual", 0.0),
                    "days_overdue": days_overdue
                })
        
        print(f"{Fore.GREEN}[SUCCESS] Found {len(overdue_list)} overdue invoices")
        return overdue_list
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error fetching overdue invoices: {str(e)}")
        return None


def get_expenses(month, year):
    """
    Fetch vendor bills (expenses) for a specific month.
    
    Args:
        month: Month (1-12)
        year: Year (e.g., 2024)
    
    Returns:
        Dict with: total_expenses, by_category breakdown
    """
    try:
        uid = authenticate()
        if not uid:
            return None
        
        # Calculate date range for the month
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        # Domain: vendor bills within the month
        domain = [
            ["state", "=", "posted"],
            ["move_type", "in", ["in_invoice", "in_refund"]],
            ["invoice_date", ">=", start_date],
            ["invoice_date", "<", end_date]
        ]
        
        params = {
            "db": ODOO_DB,
            "uid": uid,
            "password": ODOO_PASSWORD,
            "model": "account.move",
            "domain": domain,
            "fields": ["id", "name", "partner_id", "amount_total", "invoice_line_ids"]
        }
        
        result = _make_jsonrpc_request("/web/dataset/search_read", params, method="call")
        
        total_expenses = 0.0
        by_category = {}
        
        if result and result.get("records"):
            for bill in result["records"]:
                amount = bill.get("amount_total", 0.0)
                total_expenses += amount
                
                # Get vendor name for category breakdown
                vendor_name = "Other"
                if bill.get("partner_id"):
                    if isinstance(bill["partner_id"], list) and len(bill["partner_id"]) >= 2:
                        vendor_name = bill["partner_id"][1]
                    else:
                        vendor_name = str(bill["partner_id"])
                
                # Categorize by vendor type (simplified categorization)
                category = _categorize_vendor(vendor_name)
                
                if category not in by_category:
                    by_category[category] = {"total": 0.0, "count": 0, "vendors": set()}
                
                by_category[category]["total"] += amount
                by_category[category]["count"] += 1
                by_category[category]["vendors"].add(vendor_name)
        
        # Convert sets to lists for JSON serialization
        by_category_serializable = {}
        for cat, data in by_category.items():
            by_category_serializable[cat] = {
                "total": round(data["total"], 2),
                "count": data["count"],
                "vendors": list(data["vendors"])
            }
        
        expenses_data = {
            "total_expenses": round(total_expenses, 2),
            "by_category": by_category_serializable
        }
        
        print(f"{Fore.GREEN}[SUCCESS] Monthly expenses for {year}-{month:02d}: ${total_expenses:.2f}")
        return expenses_data
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error fetching expenses: {str(e)}")
        return None


def _categorize_vendor(vendor_name):
    """
    Categorize vendors into expense categories.
    """
    vendor_lower = vendor_name.lower()
    
    # Technology/Software
    tech_keywords = ["software", "tech", "cloud", "aws", "azure", "google", "microsoft", "adobe", "github"]
    if any(kw in vendor_lower for kw in tech_keywords):
        return "Technology"
    
    # Utilities
    utility_keywords = ["electric", "water", "gas", "utility", "power", "internet", "telecom", "phone"]
    if any(kw in vendor_lower for kw in utility_keywords):
        return "Utilities"
    
    # Office/Supplies
    office_keywords = ["office", "supply", "stationery", "furniture", "equipment"]
    if any(kw in vendor_lower for kw in office_keywords):
        return "Office Supplies"
    
    # Professional Services
    service_keywords = ["legal", "law", "consulting", "accounting", "audit", "advisory"]
    if any(kw in vendor_lower for kw in service_keywords):
        return "Professional Services"
    
    # Rent/Facilities
    rent_keywords = ["rent", "lease", "property", "real estate", "building"]
    if any(kw in vendor_lower for kw in rent_keywords):
        return "Rent & Facilities"
    
    # Marketing
    marketing_keywords = ["marketing", "advertising", "media", "social", "seo", "google ads"]
    if any(kw in vendor_lower for kw in marketing_keywords):
        return "Marketing"
    
    return "Other Expenses"


def generate_financial_summary(month, year):
    """
    Generate a comprehensive financial summary for a given month.
    
    Args:
        month: Month (1-12)
        year: Year (e.g., 2024)
    
    Returns:
        Dict with: revenue, expenses, profit, overdue_count, overdue_amount
    """
    try:
        print(f"{Fore.CYAN}[INFO] Generating financial summary for {year}-{month:02d}...")
        
        # Fetch revenue data
        revenue_data = get_monthly_revenue(year, month)
        if not revenue_data:
            revenue_data = {"total_revenue": 0.0, "invoice_count": 0, "avg_invoice_value": 0.0}
        
        # Fetch expenses data
        expenses_data = get_expenses(month, year)
        if not expenses_data:
            expenses_data = {"total_expenses": 0.0, "by_category": {}}
        
        # Fetch overdue invoices
        overdue_list = get_overdue_invoices()
        if not overdue_list:
            overdue_list = []
        
        # Calculate totals
        total_revenue = revenue_data.get("total_revenue", 0.0)
        total_expenses = expenses_data.get("total_expenses", 0.0)
        profit = total_revenue - total_expenses
        
        overdue_count = len(overdue_list)
        overdue_amount = sum(inv.get("amount_due", inv.get("amount", 0.0)) for inv in overdue_list)
        
        summary = {
            "period": f"{year}-{month:02d}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "revenue": {
                "total_revenue": round(total_revenue, 2),
                "invoice_count": revenue_data.get("invoice_count", 0),
                "avg_invoice_value": revenue_data.get("avg_invoice_value", 0.0)
            },
            "expenses": {
                "total_expenses": round(total_expenses, 2),
                "by_category": expenses_data.get("by_category", {})
            },
            "profit": round(profit, 2),
            "profit_margin": round((profit / total_revenue * 100) if total_revenue > 0 else 0.0, 2),
            "overdue": {
                "count": overdue_count,
                "total_amount": round(overdue_amount, 2),
                "invoices": overdue_list
            }
        }
        
        print(f"{Fore.GREEN}[SUCCESS] Financial summary generated:")
        print(f"  Revenue: ${total_revenue:.2f}")
        print(f"  Expenses: ${total_expenses:.2f}")
        print(f"  Profit: ${profit:.2f}")
        print(f"  Overdue: {overdue_count} invoices (${overdue_amount:.2f})")
        
        return summary
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error generating financial summary: {str(e)}")
        return None


def save_summary_to_vault(summary_dict):
    """
    Save financial summary to a markdown file in the vault.
    
    Args:
        summary_dict: Dictionary containing financial summary data
    
    Returns:
        Path to saved file, or None if failed
    """
    try:
        if not summary_dict:
            print(f"{Fore.RED}[ERROR] No summary data to save")
            return None
        
        # Create vault directory if it doesn't exist
        VAULT_PATH.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        period = summary_dict.get("period", datetime.now().strftime("%Y-%m"))
        filename = f"{period}_summary.md"
        filepath = VAULT_PATH / filename
        
        # Build markdown content
        revenue = summary_dict.get("revenue", {})
        expenses = summary_dict.get("expenses", {})
        profit = summary_dict.get("profit", 0.0)
        profit_margin = summary_dict.get("profit_margin", 0.0)
        overdue = summary_dict.get("overdue", {})
        
        content = f"""# Financial Summary - {period}

**Generated:** {summary_dict.get("generated_at", "N/A")}

---

## Revenue Overview

| Metric | Value |
|--------|-------|
| Total Revenue | ${revenue.get("total_revenue", 0):,.2f} |
| Invoice Count | {revenue.get("invoice_count", 0)} |
| Avg Invoice Value | ${revenue.get("avg_invoice_value", 0):,.2f} |

---

## Expenses Overview

| Metric | Value |
|--------|-------|
| Total Expenses | ${expenses.get("total_expenses", 0):,.2f} |

### Expenses by Category

| Category | Total | Count | Vendors |
|----------|-------|-------|---------|
"""
        
        by_category = expenses.get("by_category", {})
        for category, data in sorted(by_category.items(), key=lambda x: x[1].get("total", 0), reverse=True):
            vendors_str = ", ".join(data.get("vendors", [])[:3])  # Show first 3 vendors
            if len(data.get("vendors", [])) > 3:
                vendors_str += f" (+{len(data.get('vendors', [])) - 3} more)"
            content += f"| {category} | ${data.get('total', 0):,.2f} | {data.get('count', 0)} | {vendors_str} |\n"
        
        content += f"""
---

## Profit & Loss

| Metric | Value |
|--------|-------|
| Total Revenue | ${revenue.get("total_revenue", 0):,.2f} |
| Total Expenses | ${expenses.get("total_expenses", 0):,.2f} |
| **Net Profit** | **${profit:,.2f}** |
| Profit Margin | {profit_margin:.1f}% |

---

## Overdue Invoices

| Metric | Value |
|--------|-------|
| Count | {overdue.get("count", 0)} |
| Total Amount Due | ${overdue.get("total_amount", 0):,.2f} |

### Overdue Invoice Details

| Invoice | Client | Amount Due | Days Overdue |
|---------|--------|------------|--------------|
"""
        
        overdue_invoices = overdue.get("invoices", [])
        if overdue_invoices:
            for inv in sorted(overdue_invoices, key=lambda x: x.get("days_overdue", 0), reverse=True):
                content += f"| {inv.get('name', 'N/A')} | {inv.get('client_name', 'N/A')} | ${inv.get('amount_due', inv.get('amount', 0)):,.2f} | {inv.get('days_overdue', 0)} |\n"
        else:
            content += "| - | No overdue invoices | - | - |\n"
        
        content += """
---

*Report generated by odoo_mcp.py*
"""
        
        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"{Fore.GREEN}[SUCCESS] Summary saved to {filepath}")
        return str(filepath)
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error saving summary to vault: {str(e)}")
        return None


# Example usage / testing
if __name__ == "__main__":
    print(f"{Fore.CYAN}=== Odoo MCP Tool ===")
    print(f"URL: {ODOO_URL}")
    print(f"Database: {ODOO_DB}")
    print(f"User: {ODOO_USER}")
    print()
    
    # Test authentication
    print(f"{Fore.CYAN}--- Testing Authentication ---")
    uid = authenticate()
    
    if uid:
        # Test getting invoices
        print(f"\n{Fore.CYAN}--- Testing Get Invoices ---")
        invoices = get_invoices(state="open")
        
        # Test monthly revenue
        print(f"\n{Fore.CYAN}--- Testing Monthly Revenue ---")
        current = datetime.now()
        revenue = get_monthly_revenue(current.year, current.month)
        
        # Test expenses
        print(f"\n{Fore.CYAN}--- Testing Expenses ---")
        expenses = get_expenses(current.month, current.year)
        
        # Test overdue invoices
        print(f"\n{Fore.CYAN}--- Testing Overdue Invoices ---")
        overdue = get_overdue_invoices()
        
        # Test full summary
        print(f"\n{Fore.CYAN}--- Testing Financial Summary ---")
        summary = generate_financial_summary(current.month, current.year)
        
        if summary:
            print(f"\n{Fore.CYAN}--- Testing Save Summary ---")
            save_summary_to_vault(summary)
    else:
        print(f"{Fore.RED}Authentication failed. Check your .env credentials.")
