import os
import unittest
from fastapi.testclient import TestClient

# Ensure offline embeddings fallback
os.environ["HF_HUB_OFFLINE"] = "1"

from app.main import app

class TestEnterpriseHRApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["pinecone_configured"])

    def test_02_get_documents(self):
        response = self.client.get("/api/documents")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("documents", data)
        self.assertGreaterEqual(data["sample_kb_count"], 1)

    def test_03_get_stats(self):
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_queries", data)

    def test_04_get_audit_logs(self):
        response = self.client.get("/api/audit")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_05_root_template(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Enterprise HR Copilot", response.text)

if __name__ == "__main__":
    unittest.main()
