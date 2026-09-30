import os


os.environ["JWT_SECRET"] = "test-secret-at-least-thirty-two-characters"
os.environ["ADMIN_PASSWORD"] = "test-admin"
os.environ["VIEWER_PASSWORD"] = "test-viewer"
os.environ["DATABASE_URL"] = "sqlite:///./backend/instance/test_impact_ledger.db"
