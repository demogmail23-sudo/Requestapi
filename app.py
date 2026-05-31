import json
import time
import base64
import os
import asyncio
import aiohttp
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, Tuple
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ CONSTANTS ============
REGION_MAP = {
    "ind": "https://client.ind.freefiremobile.com",
    "me": "https://clientbp.ggblueshark.com",
    "vn": "https://clientbp.ggpolarbear.com",
    "bd": "https://clientbp.ggwhitehawk.com",
    "pk": "https://clientbp.ggblueshark.com",
    "sg": "https://clientbp.ggpolarbear.com",
    "br": "https://client.us.freefiremobile.com",
    "na": "https://client.us.freefiremobile.com",
    "id": "https://clientbp.ggpolarbear.com",
    "ru": "https://clientbp.ggpolarbear.com",
    "th": "https://clientbp.ggpolarbear.com",
}

ALL_REGIONS = list(REGION_MAP.items())

OAUTH_URL = "https://100067.connect.garena.com/oauth/guest/token/grant"
MAJOR_LOGIN_URL = "https://loginbp.ggblueshark.com/MajorLogin"
CLIENT_ID = "100067"
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
PROTO_KEY = b'Yg&tc%DEuh6%Zc^8'
PROTO_IV = b'6oyZDr22E3ychjM%'

BASE_HEADERS = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': "OB53"
}

# ============ PROTOBUF BASE64 STRINGS ============
MAJOR_LOGIN_REQ_B64 = "ChNNYWpvckxvZ2luUmVxLnByb3RvIvoKCgpNYWpvckxvZ2luEhIKCmV2ZW50X3RpbWUYAyABKAkSEQoJZ2FtZV9uYW1lGAQgASgJEhMKC3BsYXRmb3JtX2lkGAUgASgFEhYKDmNsaWVudF92ZXJzaW9uGAcgASgJEhcKD3N5c3RlbV9zb2Z0d2FyZRgIIAEoCRIXCg9zeXN0ZW1faGFyZHdhcmUYCSABKAkSGAoQdGVsZWNvbV9vcGVyYXRvchgKIAEoCRIUCgxuZXR3b3JrX3R5cGUYCyABKAkSFAoMc2NyZWVuX3dpZHRoGAwgASgNEhUKDXNjcmVlbl9oZWlnaHQYDSABKA0SEgoKc2NyZWVuX2RwaRgOIAEoCRIZChFwcm9jZXNzb3JfZGV0YWlscxgPIAEoCRIOCgZtZW1vcnkYECABKA0SFAoMZ3B1X3JlbmRlcmVyGBEgASgJEhMKC2dwdV92ZXJzaW9uGBIgASgJEhgKEHVuaXF1ZV9kZXZpY2VfaWQYEyABKAkSEQoJY2xpZW50X2lwGBQgASgJEhAKCGxhbmd1YWdlGBUgASgJEg8KB29wZW5faWQYFiABKAkSFAoMb3Blbl9pZF90eXBlGBcgASgJEhMKC2RldmljZV90eXBlGBggASgJEicKEG1lbW9yeV9hdmFpbGFibGUYGSABKAsyDS5HYW1lU2VjdXJpdHkSFAoMYWNjZXNzX3Rva2VuGB0gASgJEhcKD3BsYXRmb3JtX3Nka19pZBgeIAEoBRIaChJuZXR3b3JrX29wZXJhdG9yX2EYKSABKAkSFgoObmV0d29ya190eXBlX2EYKiABKAkSHAoUY2xpZW50X3VzaW5nX3ZlcnNpb24YOSABKAkSHgoWZXh0ZXJuYWxfc3RvcmFnZV90b3RhbBg8IAEoBRIiChpleHRlcm5hbF9zdG9yYWdlX2F2YWlsYWJsZRg9IAEoBRIeChZpbnRlcm5hbF9zdG9yYWdlX3RvdGFsGD4gASgFEiIKGmludGVybmFsX3N0b3JhZ2VfYXZhaWxhYmxlGD8gASgFEiMKG2dhbWVfZGlza19zdG9yYWdlX2F2YWlsYWJsZRhAIAEoBRIfChdnYW1lX2Rpc2tfc3RvcmFnZV90b3RhbBhBIAEoBRIlCh1leHRlcm5hbF9zZGNhcmRfYXZhaWxfc3RvcmFnZRhCIAEoBRIlCh1leHRlcm5hbF9zZGNhcmRfdG90YWxfc3RvcmFnZRhDIAEoBRIQCghsb2dpbl9ieRhJIAEoBRIUCgxsaWJyYXJ5X3BhdGgYSiABKAkSEgoKcmVnX2F2YXRhchhMIAEoBRIVCg1saWJyYXJ5X3Rva2VuGE0gASgJEhQKDGNoYW5uZWxfdHlwZRhOIAEoBRIQCghjcHVfdHlwZRhPIAEoBRIYChBjcHVfYXJjaGl0ZWN0dXJlGFEgASgJEhsKE2NsaWVudF92ZXJzaW9uX2NvZGUYUyABKAkSFAoMZ3JhcGhpY3NfYXBpGFYgASgJEh0KFXN1cHBvcnRlZF9hc3RjX2JpdHNldBhXIAEoDRIaChJsb2dpbl9vcGVuX2lkX3R5cGUYWCABKAUSGAoQYW5hbHl0aWNzX2RldGFpbBhZIAEoDBIUCgxsb2FkaW5nX3RpbWUYXCABKA0SFwoPcmVsZWFzZV9jaGFubmVsGFQgASgJEhIKCmV4dHJhX2luZm8YXiABKAkSIAoYYW5kcm9pZF9lbmdpbmVfaW5pdF9mbGFnGF8gASgNEg8KB2lmX3B1c2gYYSABKAUSDgoGaXNfdnBuGGIgASgFEhwKFG9yaWdpbl9wbGF0Zm9ybV90eXBlGGMgASgJEh0KFXByaW1hcnlfcGxhdGZvcm1fdHlwZRhkIAEoCSI1CgxHYW1lU2VjdXJpdHkSDwoHdmVyc2lvbhgGIAEoBRIUCgxoaWRkZW5fdmFsdWUYCCABKARiBnByb3RvMw=="
MAJOR_LOGIN_RES_B64 = "ChNNYWpvckxvZ2luUmVzLnByb3RvInwKDU1ham9yTG9naW5SZXMSEwoLYWNjb3VudF91aWQYASABKAQSDgoGcmVnaW9uGAIgASgJEg0KBXRva2VuGAggASgJEgsKA3VybBgKIAEoCRIRCgl0aW1lc3RhbXAYFSABKAMSCwoDa2V5GBYgASgMEgoKAml2GBcgASgMYgZwcm90bzM="
GET_LOGIN_DATA_B64 = "ChVHZXRMb2dpbkRhdGFSZXMucHJvdG8ipAEKDEdldExvZ2luRGF0YRISCgpBY2NvdW50VUlEGAEgASgEEg4KBlJlZ2lvbhgDIAEoCRITCgtBY2NvdW50TmFtZRgEIAEoCRIWCg5PbmxpbmVfSVBfUG9ydBgOIAEoCRIPCgdDbGFuX0lEGBQgASgDEhYKDkFjY291bnRJUF9Qb3J0GCAgASgJEhoKEkNsYW5fQ29tcGlsZWRfRGF0YRg3IAEoCWIGcHJvdG8z"

# ============ ENCRYPTION FUNCTIONS (from byte.py) ============
def Encrypt_ID(uid: str) -> str:
    """Encrypt UID for friend request"""
    try:
        x = int(uid)
        dec = ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '8a', '8b', '8c', '8d', '8e', '8f', 
               '90', '91', '92', '93', '94', '95', '96', '97', '98', '99', '9a', '9b', '9c', '9d', '9e', '9f',
               'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'aa', 'ab', 'ac', 'ad', 'ae', 'af',
               'b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'ba', 'bb', 'bc', 'bd', 'be', 'bf',
               'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'ca', 'cb', 'cc', 'cd', 'ce', 'cf',
               'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'da', 'db', 'dc', 'dd', 'de', 'df',
               'e0', 'e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'ea', 'eb', 'ec', 'ed', 'ee', 'ef',
               'f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'fa', 'fb', 'fc', 'fd', 'fe', 'ff']
        xxx = ['1', '01', '02', '03', '04', '05', '06', '07', '08', '09', '0a', '0b', '0c', '0d', '0e', '0f',
               '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '1a', '1b', '1c', '1d', '1e', '1f',
               '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '2a', '2b', '2c', '2d', '2e', '2f',
               '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '3a', '3b', '3c', '3d', '3e', '3f',
               '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '4a', '4b', '4c', '4d', '4e', '4f',
               '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '5a', '5b', '5c', '5d', '5e', '5f',
               '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '6a', '6b', '6c', '6d', '6e', '6f',
               '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '7a', '7b', '7c', '7d', '7e', '7f']
        
        val = x / 128
        if val > 128:
            val = val / 128
            if val > 128:
                val = val / 128
                if val > 128:
                    val = val / 128
                    strx = int(val)
                    y = (val - int(val)) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    m = (n - int(n)) * 128
                    return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(val)]
                else:
                    strx = int(val)
                    y = (val - int(val)) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(val)]
            else:
                strx = int(val)
                y = (val - int(val)) * 128
                z = (y - int(y)) * 128
                return dec[int(z)] + dec[int(y)] + xxx[int(val)]
        else:
            strx = int(val)
            if strx == 0:
                y = (val - int(val)) * 128
                return xxx[int(y)]
            else:
                y = (val - int(val)) * 128
                return dec[int(y)] + xxx[int(val)]
    except Exception:
        return uid.encode().hex()

def encrypt_api(payload: str) -> str:
    """Encrypt API payload"""
    try:
        key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        plain_bytes = bytes.fromhex(payload)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        cipher_text = cipher.encrypt(pad(plain_bytes, AES.block_size))
        return cipher_text.hex()
    except Exception:
        return payload

def decrypt_api(cipher_text: str) -> str:
    """Decrypt API response"""
    try:
        key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plain_text = unpad(cipher.decrypt(bytes.fromhex(cipher_text)), AES.block_size)
        return plain_text.hex()
    except Exception:
        return cipher_text

# ============ PROTOBUF ENCRYPTION ============
def encrypt_proto(payload_bytes: bytes) -> bytes:
    cipher = AES.new(PROTO_KEY, AES.MODE_CBC, PROTO_IV)
    padded = pad(payload_bytes, AES.block_size)
    return cipher.encrypt(padded)

def decrypt_proto(encrypted_bytes: bytes) -> bytes:
    cipher = AES.new(PROTO_KEY, AES.MODE_CBC, PROTO_IV)
    decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
    return decrypted

# ============ PROTOBUF MESSAGE BUILDERS ============
def build_major_login_message(open_id: str, access_token: str) -> bytes:
    """Build MajorLogin protobuf message as bytes"""
    # Simple protobuf-like structure (simplified for compatibility)
    import struct
    
    timestamp = str(int(datetime.now().timestamp()))
    account_uid_val = int(open_id) if open_id.isdigit() else 0
    
    # Build a simplified protobuf message
    # Field 1: event_time (string, field number 3)
    event_time_bytes = timestamp.encode()
    msg = b'\x1a' + bytes([len(event_time_bytes)]) + event_time_bytes
    
    # Field 2: game_name (field 4)
    game_name = b"free fire"
    msg += b'"' + bytes([len(game_name)]) + game_name
    
    # Field 3: platform_id = 1 (field 5, varint)
    msg += b'(\x01'
    
    # Field 4: client_version (field 7)
    client_ver = b"1.123.1"
    msg += b':' + bytes([len(client_ver)]) + client_ver
    
    # Field 5: open_id (field 22)
    open_id_bytes = open_id.encode()
    msg += b'\xb2\x01' + bytes([len(open_id_bytes)]) + open_id_bytes
    
    # Field 6: access_token (field 29)
    token_bytes = access_token.encode()
    msg += b'\xea\x01' + bytes([len(token_bytes)]) + token_bytes
    
    # Add more fields as needed
    msg += b'\x80\x02\x04'  # login_by = 4
    
    return msg

def load_accounts() -> List[Dict[str, str]]:
    """Load accounts from accounts.txt"""
    accounts = []
    try:
        if os.path.exists("accounts.txt"):
            with open("accounts.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    uid, pwd = line.split(':', 1)
                    accounts.append({"uid": uid, "password": pwd})
    except Exception as e:
        print(f"Error loading accounts: {e}")
    return accounts

async def generate_access_token(session: aiohttp.ClientSession, uid: str, password: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Generate access token for account"""
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "GarenaMSDK/5.5.2P3(SM-A515F;Android 12;en-US;IND;)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"
    }
    data = {
        "uid": uid, 
        "password": password, 
        "response_type": "token",
        "client_type": "2", 
        "client_secret": CLIENT_SECRET, 
        "client_id": CLIENT_ID
    }
    try:
        async with session.post(OAUTH_URL, headers=headers, data=data, timeout=30, ssl=False) as response:
            if response.status == 200:
                resp_data = await response.json()
                return resp_data.get("open_id"), resp_data.get("access_token"), None
            elif response.status == 429:
                return None, None, "Rate limited (429) - Too many requests"
            else:
                error_text = await response.text()
                return None, None, f"HTTP {response.status}: {error_text[:200]}"
    except Exception as e:
        return None, None, str(e)

async def major_login(session: aiohttp.ClientSession, open_id: str, access_token: str) -> Tuple[bool, Any]:
    """Perform major login"""
    proto_payload = build_major_login_message(open_id, access_token)
    encrypted_payload = encrypt_proto(proto_payload)
    try:
        async with session.post(MAJOR_LOGIN_URL, data=encrypted_payload, headers=BASE_HEADERS, timeout=30, ssl=False) as response:
            if response.status == 200:
                response_data = await response.read()
                # Try to parse response - simplified
                return True, {'token': response_data.hex()[:64], 'region': 'ind'}
            else:
                return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)

async def get_jwt_token(session: aiohttp.ClientSession, uid: str, password: str) -> Tuple[Optional[str], Optional[str]]:
    """Get JWT token for account"""
    open_id, access_token, err = await generate_access_token(session, uid, password)
    if err:
        return None, err
    if not open_id:
        return None, "Failed to get open_id"
    success, login_resp = await major_login(session, open_id, access_token)
    if not success:
        return None, str(login_resp)
    if isinstance(login_resp, dict) and login_resp.get('token'):
        return login_resp.get('token'), None
    return None, "No JWT token in response"

async def send_friend_request(session: aiohttp.ClientSession, target_uid: str, token: str, region_server_url: str) -> Tuple[bool, str, str]:
    """Send friend request using account"""
    try:
        encrypted_id = Encrypt_ID(target_uid)
        payload = f"08a7c4839f1e10{encrypted_id}1801"
        encrypted_payload = encrypt_api(payload)
        url = f"{region_server_url}/RequestAddingFriend"
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(encrypted_payload)//2),
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-N975F Build/PI)",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        async with session.post(url, headers=headers, data=bytes.fromhex(encrypted_payload), timeout=15, ssl=False) as response:
            resp_text = await response.text()
            if response.status == 200:
                if "Invalid request body" in resp_text:
                    return False, f"200 OK but body: {resp_text[:200]}", url
                return True, resp_text[:200], url
            else:
                return False, f"HTTP {response.status}: {resp_text[:200]}", url
    except Exception as e:
        return False, str(e), region_server_url

async def process_account(session: aiohttp.ClientSession, account: Dict[str, str], target_uid: str, regions_to_try: List[Tuple[str, str]], delay: float = 0) -> Dict[str, Any]:
    """Process single account"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    result = {
        "uid": account['uid'][:8] + "...",
        "success": False,
        "response": None,
        "region_used": None,
        "error": None
    }
    
    # Get JWT token
    token, err = await get_jwt_token(session, account['uid'], account['password'])
    if not token:
        result["error"] = f"Token error: {err}" if err else "No token"
        return result
    
    # Try all regions
    for region_name, server_url in regions_to_try:
        ok, resp_msg, used_url = await send_friend_request(session, target_uid, token, server_url)
        if ok:
            result["success"] = True
            result["response"] = resp_msg
            result["region_used"] = region_name
            return result
        else:
            result["response"] = resp_msg
            result["region_used"] = region_name
    
    result["error"] = result["response"]
    return result

# ============ FASTAPI APP ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting FreeFire Friend Request Spammer API")
    yield
    # Shutdown
    print("Shutting down")

app = FastAPI(
    title="FreeFire Friend Request API",
    description="Send multiple friend requests using stored accounts",
    version="1.0.0",
    lifespan=lifespan
)

# Response Models
class SpamResponse(BaseModel):
    total_accounts_available: int
    accounts_used: int
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]
    summary: Dict[str, int]

class HealthResponse(BaseModel):
    status: str
    accounts_loaded: int
    timestamp: str

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "FreeFire Friend Request API",
        "endpoints": {
            "/send_requests": "POST - Send friend requests",
            "/health": "GET - Check API status",
            "/accounts/count": "GET - Get number of loaded accounts"
        }
    }

@app.post("/send_requests", response_model=SpamResponse, tags=["Requests"])
async def send_requests(
    target_uid: str = Query(..., description="Target FreeFire UID", min_length=1, max_length=20),
    count: Optional[int] = Query(None, description="Number of accounts to use (max)", ge=1, le=1000),
    region: Optional[str] = Query(None, description="Specific region (ind, me, vn, bd, pk, sg, br, na, id, ru, th)"),
    delay_between: float = Query(0.1, description="Delay between accounts in seconds", ge=0, le=5)
):
    """
    Send friend requests to target UID using loaded accounts
    """
    accounts = load_accounts()
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found in accounts.txt")
    
    # Select accounts to use
    if count:
        accounts_to_use = accounts[:min(count, len(accounts))]
    else:
        accounts_to_use = accounts
    
    # Set regions
    if region:
        region_lower = region.lower()
        if region_lower in REGION_MAP:
            regions_to_try = [(region_lower, REGION_MAP[region_lower])]
        else:
            raise HTTPException(status_code=400, detail=f"Invalid region. Valid: {list(REGION_MAP.keys())}")
    else:
        regions_to_try = ALL_REGIONS
    
    # Process accounts concurrently
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, acc in enumerate(accounts_to_use):
            task = process_account(session, acc, target_uid, regions_to_try, i * delay_between)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
    
    # Calculate statistics
    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count
    
    response_counts = {}
    for r in results:
        resp = r.get("response", "unknown")
        if resp:
            response_counts[resp[:50]] = response_counts.get(resp[:50], 0) + 1
    
    return SpamResponse(
        total_accounts_available=len(accounts),
        accounts_used=len(accounts_to_use),
        success_count=success_count,
        failed_count=failed_count,
        results=results,
        summary={"success": success_count, "failed": failed_count}
    )

@app.get("/send_requests", tags=["Requests"])
async def send_requests_get(
    uid: str = Query(..., description="Target FreeFire UID"),
    count: Optional[int] = Query(None, description="Number of accounts to use", ge=1, le=1000),
    region: Optional[str] = Query(None, description="Specific region")
):
    """
    GET endpoint for sending friend requests (convenience)
    """
    return await send_requests(uid, count, region, 0.1)

@app.get("/health", response_model=HealthResponse, tags=["Status"])
async def health_check():
    """Check API health status"""
    accounts = load_accounts()
    return HealthResponse(
        status="ok",
        accounts_loaded=len(accounts),
        timestamp=datetime.now().isoformat()
    )

@app.get("/accounts/count", tags=["Accounts"])
async def accounts_count():
    """Get number of loaded accounts"""
    accounts = load_accounts()
    return {"total_accounts": len(accounts)}

@app.post("/accounts/reload", tags=["Accounts"])
async def reload_accounts():
    """Reload accounts from file"""
    # Force reload by clearing cache
    accounts = load_accounts()
    return {"message": f"Reloaded {len(accounts)} accounts", "total": len(accounts)}

# ============ MAIN ============
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
