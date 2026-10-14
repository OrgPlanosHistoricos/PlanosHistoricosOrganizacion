import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import create_engine

from api.health_router import router


class DatabaseHealthTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_connected_executes_query(self):
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with patch('api.health_router.engine', engine):
            response = self.client.get('/health/database')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'database': 'connected'})
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_database_failure_returns_503_without_credentials(self):
        with patch('api.health_router.engine') as engine:
            engine.connect.side_effect = OperationalError('secret SQL', {}, Exception('password'))
            response = self.client.get('/health/database')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'database': 'disconnected'})


if __name__ == '__main__':
    unittest.main()
