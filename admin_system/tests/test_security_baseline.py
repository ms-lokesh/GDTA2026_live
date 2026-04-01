import os
import unittest


class SecurityBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['CORS_ORIGINS'] = 'https://good.example.com'
        os.environ['REQUIRE_ORIGIN_FOR_STATE_CHANGING'] = 'True'
        os.environ['ENABLE_SECURITY_HEADERS'] = 'True'
        os.environ['SESSION_COOKIE_SECURE'] = 'True'

        from app import create_app
        cls.app = create_app()
        cls.app.testing = True
        cls.client = cls.app.test_client()

    def test_security_headers_present(self):
        response = self.client.get('/api')
        self.assertIn('Content-Security-Policy', response.headers)
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')

    def test_admin_post_blocks_untrusted_origin(self):
        response = self.client.post(
            '/api/admin/login',
            json={'username': 'x', 'password': 'y'},
            headers={'Origin': 'https://evil.example.com'}
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_post_allows_trusted_origin_to_reach_endpoint(self):
        response = self.client.post(
            '/api/admin/login',
            json={'username': 'x', 'password': 'y'},
            headers={'Origin': 'https://good.example.com'}
        )
        # Endpoint may still reject credentials, but origin gate should not block it
        self.assertNotEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()
