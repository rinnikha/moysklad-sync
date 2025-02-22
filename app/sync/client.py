import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class MoySkladClient:
    def __init__(self, api_token, api_url):
        self.api_token = api_token
        self.api_url = api_url
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Accept-Encoding": "gzip"
        })

        return session
    
    def get_orders(self, counterparty_meta_ids, order_states, start_date):
        """Fetch orders for specific counterparties from MS1."""
        orders = []
        limit = 100
        offset = 0

        try:
            filter = ""
            # Build proper filter query
            agent_parts = [
                f"https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{id}" for id in counterparty_meta_ids]
            agent_query = ";agent=".join(agent_parts) if len(agent_parts) > 1 else f"{agent_parts[0]};"

            filter += f"agent={agent_query}"

            if order_states:
                state_parts = [
                    f"https://api.moysklad.ru/api/remap/1.2/entity/counterparty/metadata/states/{state}" for state in order_states]
                state_query = ";state=".join(state_parts) if len(state_parts) > 1 else f"{state_parts[0]};"
                filter += f";state={state_query}"

            if start_date:
                filter += f";moment>={start_date}"
            
            while True:
                response = self.session.get(
                    f"{self.api_url}/api/remap/1.2/entity/customerorder",
                    params={
                        "filter": filter,
                        "limit": limit,
                        "offset": offset
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                batch = data.get("rows", [])
                orders.extend(batch)
                
                # Check if we need to fetch more
                if len(batch) < limit:
                    break
                
                offset += limit
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"API Error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []
        
        return orders
        
    def get_product_sku(self, product_id, is_bundle=False):
        """Get article (SKU) for a product from MS1"""
        try:

            response = self.session.get(f"{self.api_url}/api/remap/1.2/entity/{'product' if not is_bundle else 'bundle'}/{product_id}")

            response.raise_for_status()
            product = response.json()

            # Get article from custom attribute

            article = product.get('article')

            return article

        except Exception as e:
            logger.error(f"Failed to get product sku: {str(e)}")
            return None

    def get_order_positions(self, order_id):
        """Fetch positions for a specific order"""
        positions = []
        try:
            limit = 100
            offset = 0

            while True:
                response = self.session.get(
                    f"{self.api_url}/api/remap/1.2/entity/customerorder/{order_id}/positions",
                    params={
                        "limit": limit,
                        "offset": offset
                    }
                )

                response.raise_for_status()
                
                data = response.json()
                positions.extend(data.get("rows", []))
                
                if len(data.get("rows", [])) < limit:
                    break
                offset += limit

        except Exception as e:
            logger.error(f"Failed to fetch positions for order {order_id}: {str(e)}")
            return []
        
        return positions
        
    def find_product_meta_by_sku(self, sku, is_bundle=False):
        """Find product in MS by SKU"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/remap/1.2/entity/{'product' if not is_bundle else 'bundle'}",
                params={"filter": f"article={sku}"}
            )
            response.raise_for_status()
            products = response.json().get('rows', [])
            return products[0]['meta'] if products else None
        except Exception as e:
            logger.error(f"Product search failed for sku {sku}: {str(e)}")
            return None
        
    def create_purchase_order(self, order_data):
        """Create a purchase order in MS2."""
        try:
            response = self.session.post(
                f"{self.api_url}/api/remap/1.2/entity/purchaseorder",
                json=order_data
            )

            json_r = response.json()
            response.raise_for_status()
            return { 'success': 1, 'purchase': json_r }
        except Exception as e:
            logger.error(f"Failed to create purchase order: {str(e)}")
            return { 'success': 0, 'purchase_id': '', 'error_msg': json_r['error'][0]['error'] }
        
    def get_product(self, product_id):
        """Get product details from MS1."""
        try:
            response = self.session.get(f"{self.api_url}/api/remap/1.2/entity/product/{product_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch product {product_id}: {str(e)}")
            return None
        
    def get_product_by_sku(self, sku):
        """Find product in MS2 by SKU"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/remap/1.2/entity/product",
                params={'filter': f"code={sku}"}
            )
            response.raise_for_status()
            products = response.json().get('rows', [])
            return products[0]['id'] if products else None
        except Exception as e:
            logger.error(f"Failed to find product by SKU {sku}: {str(e)}")
            return None
        
    def create_product(self, product_data):
        """Create product in MS2."""
        try:
            response = self.session.post(
                f"{self.api_url}/api/remap/1.2/entity/product",
                json=product_data
            )
            response.raise_for_status()
            return response.json().get("id")
        except Exception as e:
            logger.error(f"Failed to create product: {str(e)}")
            return None
        
    def search_counterparties(self, search_term):
        """Search counterparties in MS1"""
        params = {
            "filter": f"name~{search_term}",
            "limit": 10
        }
        response = self.session.get(
            f"{self.api_url}/api/remap/1.2/entity/counterparty",
            params=params
        )
        return response.json().get('rows', [])
    
    def search_groups(self, search_term):
        """Search groups in MS2"""
        params = {
            "search": f"{search_term}",
            "limit": 10
        }
        response = self.session.get(
            f"{self.api_url}/api/remap/1.2/entity/group",
            params=params
        )
        return response.json().get('rows', [])
    
    def search_organizations(self, search_term):
        
        """Search organizations in MS2"""
        params = {
            "search": f"{search_term}",
            "limit": 10
        }
        response = self.session.get(
            f"{self.api_url}/api/remap/1.2/entity/organization",
            params=params
        )
        return response.json().get('rows', [])

    def search_employees(self, search_term):
        """Search employees (owners) in MS2"""
        params = {
            "filter": f"name~{search_term}",
            "limit": 10
        }
        response = self.session.get(
            f"{self.api_url}/api/remap/1.2/entity/employee",
            params=params
        )
        return response.json().get('rows', [])

    def search_stores(self, search_term):
        """Search stores in MS2"""
        params = {
            "filter": f"name~{search_term}",
            "limit": 10
        }
        response = self.session.get(
            f"{self.api_url}/api/remap/1.2/entity/store",
            params=params
        )
        return response.json().get('rows', [])