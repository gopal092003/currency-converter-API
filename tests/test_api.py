import unittest
from app.main import create_app

class APITestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app().test_client()
        self.app.testing = True

    def test_convert_success(self):
        response = self.app.get("/convert?amount=100&from=USD&to=INR")
        self.assertEqual(response.status_code, 200)

    def test_invalid_amount(self):
        response = self.app.get("/convert?amount=abc&from=USD&to=INR")
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()