import asyncio, os, sys
sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
import bcrypt, secrets

async def seed():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    email = f"phaseb-e2e-{int(datetime.now().timestamp())}@mailinator.com"
    code = "313131"
    now = datetime.now(timezone.utc)
    await c.auth_otps.insert_one({
        "email": email,
        "otp_hash": bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode(),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "used": False,
        "verify_attempts": 0,
    })
    print(f"{email}|{code}")

asyncio.run(seed())
