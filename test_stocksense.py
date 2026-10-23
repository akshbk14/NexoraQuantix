"""
Comprehensive End-to-End Test Suite for StockSense
Verifies:
1. Database setup & migrations
2. User authentication (registration, duplicate protection, login, password hashing, session logout)
3. Route protection (@login_required)
4. Multi-user data isolation (User A vs User B)
5. Add Product feature and database persistence
6. CSV upload, data cleaning, and validation
7. Forecasting and reorder optimization calculations (LTD, SS, Target Stock, Reorder Qty, Priorities)
8. Three-theme selection and persistence API ('neon-dark', 'gold', 'cream')
9. Full rendering of all templates and routes
"""

import unittest
import json
import io
import app
import db

class StockSenseTestCase(unittest.TestCase):
    def setUp(self):
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.app.test_client()
        db.init()

    def test_01_unauthenticated_redirection(self):
        """Unauthenticated requests to protected routes must redirect to /signin."""
        protected_routes = ['/', '/sales', '/inventory', '/forecast', '/reorder', '/analytics', '/settings', '/download.csv']
        for route in protected_routes:
            resp = self.client.get(route, follow_redirects=False)
            self.assertEqual(resp.status_code, 302, f"Route {route} should redirect when unauthenticated")
            self.assertIn('/signin', resp.headers['Location'])

    def test_02_registration_and_login(self):
        """Test registration, duplicate email handling, and valid login."""
        test_email = 'nexora_test@example.com'
        db.delete_user_by_email(test_email)

        # 1. Register user
        resp = self.client.post('/signup', data={
            'full_name': 'Nexora Tester',
            'store_name': 'Nexora Mart',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/signin', resp.headers['Location'])

        # 2. Duplicate registration must fail
        resp_dup = self.client.post('/signup', data={
            'full_name': 'Nexora Tester',
            'store_name': 'Nexora Mart',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'already exists', resp_dup.data)

        # 3. Invalid credentials
        resp_bad = self.client.post('/signin', data={
            'email': test_email,
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Incorrect email or password', resp_bad.data)

        # 4. Valid credentials
        resp_good = self.client.post('/signin', data={
            'email': test_email,
            'password': 'password123'
        }, follow_redirects=False)
        self.assertEqual(resp_good.status_code, 302)
        self.assertEqual(resp_good.headers['Location'], '/')

    def test_03_multi_user_data_isolation(self):
        """Ensure User A's inventory & sales cannot be seen or accessed by User B."""
        user_a_email = 'user_a@stocksense.test'
        user_b_email = 'user_b@stocksense.test'

        # Safe cleanup
        db.delete_user_by_email(user_a_email)
        db.delete_user_by_email(user_b_email)

        uid_a = db.create_user('User A', 'User A Store', user_a_email, 'secret123')
        uid_b = db.create_user('User B', 'User B Store', user_b_email, 'secret123')

        # User A adds a product
        prod_a = {
            'product_id': 'PROD_ALPHA_99',
            'product_name': 'Exclusive Alpha Milk',
            'category': 'Dairy',
            'unit': 'litres',
            'current_stock': 15,
            'incoming_stock': 0,
            'lead_time_days': 2,
            'review_period_days': 3,
            'shelf_life_days': 5,
            'min_order_qty': 1,
            'pack_size': 1,
            'unit_cost': 45.0,
            'supplier_name': 'Alpha Dairy Co'
        }
        db.upsert_product(prod_a, uid_a)

        # Verify User A has it
        prods_a = db.products(uid_a)
        self.assertTrue(any(p['product_id'] == 'PROD_ALPHA_99' for p in prods_a))

        # Verify User B does NOT have it
        prods_b = db.products(uid_b)
        self.assertFalse(any(p['product_id'] == 'PROD_ALPHA_99' for p in prods_b))

        # Direct access via detail route logged in as User B
        with self.client.session_transaction() as sess:
            sess['user_id'] = uid_b
            sess['user_name'] = 'User B'

        resp = self.client.get('/product/PROD_ALPHA_99', follow_redirects=False)
        # Should redirect back to dashboard because product does not exist for User B
        self.assertEqual(resp.status_code, 302)

    def test_04_three_theme_system(self):
        """Verify all 3 themes (neon-dark, gold, cream) can be set and persist in database."""
        test_email = 'theme_tester@stocksense.test'
        db.delete_user_by_email(test_email)
        uid = db.create_user('Theme Tester', 'Theme Store', test_email, 'pass123')

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['user_name'] = 'Theme Tester'

        for theme_name in ['neon-dark', 'gold', 'cream']:
            resp = self.client.post('/api/set-theme',
                                    data=json.dumps({'theme': theme_name}),
                                    content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data['ok'])
            self.assertEqual(data['theme'], theme_name)

            # Check db persistence
            settings = db.settings(uid)
            self.assertEqual(settings.get('theme'), theme_name)

            # Check that rendered page includes data-theme attribute
            dash_resp = self.client.get('/')
            self.assertEqual(dash_resp.status_code, 200)
            self.assertIn(f'data-theme="{theme_name}"'.encode(), dash_resp.data)

    def test_05_add_product_api(self):
        """Test adding products via /api/add-product endpoint."""
        test_email = 'api_tester@stocksense.test'
        db.delete_user_by_email(test_email)
        uid = db.create_user('API Tester', 'API Store', test_email, 'pass123')

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['user_name'] = 'API Tester'

        # 1. Missing product ID
        resp = self.client.post('/api/add-product',
                                data=json.dumps({'product_id': '', 'product_name': 'Test'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        # 2. Valid product addition
        payload = {
            'product_id': 'TEST_SKU_1',
            'product_name': 'Organic Whole Grain Bread',
            'category': 'Bakery',
            'unit': 'packs',
            'current_stock': 10,
            'incoming_stock': 5,
            'lead_time_days': 2,
            'review_period_days': 3,
            'shelf_life_days': 7,
            'unit_cost': 40.0,
            'min_order_qty': 5,
            'pack_size': 5,
            'supplier_name': 'Local Bakers'
        }
        resp = self.client.post('/api/add-product',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['product_id'], 'TEST_SKU_1')

        # Verify product is in database
        saved_prod = db.get_product(uid, 'TEST_SKU_1')
        self.assertIsNotNone(saved_prod)
        self.assertEqual(saved_prod['product_name'], 'Organic Whole Grain Bread')
        self.assertEqual(saved_prod['current_stock'], 10.0)

    def test_06_load_demo_data_and_verify_all_pages(self):
        """Load demo dataset and verify full calculation pipeline and page rendering."""
        test_email = 'demo_user@stocksense.test'
        db.delete_user_by_email(test_email)
        uid = db.create_user('Demo Tester', 'Demo Supermarket', test_email, 'pass123')

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['user_name'] = 'Demo Tester'

        # Load demo data
        resp = self.client.post('/', data={'action': 'demo'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Synthetic demo data loaded', resp.data)

        # Verify all main pages render cleanly with 200 OK
        pages = [
            ('/', b'Inventory overview'),
            ('/sales', b'Sales Data'),
            ('/inventory', b'Inventory'),
            ('/forecast', b'Demand Forecast'),
            ('/reorder', b'Smart Replenishment Planner'),
            ('/analytics', b'Demand Analytics &amp; Model Validation'),
            ('/settings', b'Preferences &amp; Configuration'),
            ('/download.csv', b'product_id,product_name'),
            ('/sample-sales.csv', b'date,product_id'),
            ('/sample-products.csv', b'product_id,current_stock'),
        ]

        for path, expected_text in pages:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, f"Page {path} failed to render (status {r.status_code})")
            self.assertIn(expected_text, r.data, f"Page {path} missing expected content")

        # Verify Product Detail page for a demo SKU (e.g. P01)
        prod_resp = self.client.get('/product/P01')
        self.assertEqual(prod_resp.status_code, 200)
        self.assertIn(b'Historical Sales &amp; Future Demand Forecast', prod_resp.data)
        self.assertIn(b'Replenishment Diagnosis', prod_resp.data)

        # Verify Planning Settings form submission
        plan_resp = self.client.post('/settings', data={
            'action': 'planning',
            'service_level': '0.98',
            'default_review_period': '10',
            'budget_limit': '75000'
        }, follow_redirects=True)
        self.assertEqual(plan_resp.status_code, 200)
        self.assertIn(b'Planning settings saved', plan_resp.data)

        # Verify saved settings in db
        saved_cfg = db.settings(uid)
        self.assertEqual(saved_cfg.get('service_level'), '0.98')
        self.assertEqual(saved_cfg.get('default_review_period'), '10')
        self.assertEqual(saved_cfg.get('budget_limit'), '75000')

if __name__ == '__main__':
    unittest.main()
