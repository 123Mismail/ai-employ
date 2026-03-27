import os
import xmlrpc.client
from pathlib import Path
from dotenv import dotenv_values

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Robustly find the .env file at the Project Root
REPO_ROOT = Path(__file__).parent.parent.parent.parent
ENV_PATH = REPO_ROOT / ".env"

class OdooSkill:
    def __init__(self):
        # Manually load values to avoid 'embedded null' errors in python-dotenv
        config = {}
        if ENV_PATH.exists():
            config = dotenv_values(ENV_PATH)
            
        self.url = config.get("ODOO_URL", "http://localhost:8069")
        self.db = config.get("ODOO_DB", "odoo")
        self.username = config.get("ODOO_USERNAME")
        self.password = config.get("ODOO_PASSWORD")
        self.uid = None
        self.is_mock = not all([self.username, self.password])

    def connect(self):
        if DRY_RUN:
            logger.info("[DRY_RUN] Would connect to Odoo.")
            return True
        if self.is_mock:
            return True

        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            return self.uid is not None
        except Exception as e:
            print(f"Odoo Connection Error: {e}")
            return False

    def get_version(self):
        if self.is_mock: return "Odoo 19.0 (MOCK)"
        common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        return common.version()

    def list_customers(self):
        if self.is_mock: return [{"name": "Mock Customer", "id": 1}]
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
         
        return models.execute_kw(self.db, self.uid, self.password, 'res.partner', 'search_read', [[]], {'fields': ['name', 'email'], 'limit': 5})

    def list_calendar_events(self):
        if self.is_mock: return [{"name": "Mock Meeting", "start": "2026-03-24 10:00:00"}]
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        return models.execute_kw(self.db, self.uid, self.password, 'calendar.event', 'search_read', [[]], {'fields': ['name', 'start', 'stop'], 'limit': 5})

    def create_calendar_event(self, name, start_date, duration=1.0):
        if self.is_mock:
            print(f"MOCK: Created calendar event '{name}' at {start_date}")
            return 8888
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        event_id = models.execute_kw(self.db, self.uid, self.password, 'calendar.event', 'create', [{
            'name': name,
            'start': start_date,
            'stop': start_date, 
            'duration': duration,
        }])
       
        return event_id

    def create_draft_invoice(self, partner_id, amount, description):
        if self.is_mock:
             
            return 9999
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        invoice_id = models.execute_kw(self.db, self.uid, self.password, 'account.move', 'create', [{
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': amount,
            })]
        }])
         
        return invoice_id

if __name__ == "__main__":
    odoo = OdooSkill()
    if odoo.connect():
        print(f"Connected to {odoo.get_version()}")
