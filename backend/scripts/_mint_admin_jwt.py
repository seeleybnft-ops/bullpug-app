"""Mint an admin JWT for one-off migration tests. Not for prod use."""
import os, sys, uuid, jwt
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
now = datetime.now(timezone.utc)
tok = jwt.encode({
    'wallet': 'qdegDgTVUwkoVonWDLjx3XfXJT1SZn6tqmpnJhU7Rjs',
    'scope': 'admin',
    'iat': int(now.timestamp()),
    'exp': int((now + timedelta(minutes=10)).timestamp()),
    'jti': str(uuid.uuid4()),
}, os.environ['JWT_SECRET'], algorithm='HS256')
print(tok)
