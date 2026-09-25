# ================================================================

# SOURCE CREDIT

# ================================================================

# This Source Was Created and Developed By: XEROX_MODS

# Official Telegram Channel: @SEXTYMODS

# All Rights Reserved By The Original Creator.

# Do Not Remove, Edit, Replace, or Hide This Credit.

# If You Share, Modify, or Repost This Source,

# Make Sure The Original Credit Remains Untouched.

# Creator Name   : @XEROX_MODS

# Telegram       :  @SEXTYMODS

# Source Credit  :  @XEROX_MODS

# Thank You For Respecting The Original Creator.

#================================================================

import requests
import json
import threading
import time
import base64
import struct
import tempfile
import os
import sys
import importlib.util
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Flask, request, jsonify
import urllib3

try:
    from byte import Encrypt_ID, encrypt_api
except ImportError:
    def Encrypt_ID(uid: str) -> str:
        return uid.encode().hex()
    def encrypt_api(payload: str) -> str:
        return payload.encode().hex()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.json.sort_keys = False

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
PROTO_KEY = b'Yg&tc%DEuh6%Zc^8'
PROTO_IV = b'6oyZDr22E3ychjM%'

# Global storage for JWT tokens mapped by UID
JWT_TOKEN = {}

BASE_HEADERS = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': "OB55"
}

def load_accounts(region=None):
    """Loads accounts from region-specific files if specified, otherwise accounts.txt."""
    accounts = []
    filenames = []
    
    if region:
        reg_clean = region.lower().strip()
        filenames = [f"Account_{reg_clean}.txt", f"accounts_{reg_clean}.txt", f"Account{reg_clean}.txt"]
    
    # Always include fallback default file
    filenames.append("accounts.txt")
    
    target_file = None
    for fname in filenames:
        if os.path.exists(fname):
            target_file = fname
            break
            
    if not target_file:
        return []

    try:
        with open(target_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                uid, pwd = line.split(':', 1)
                accounts.append({"uid": uid.strip(), "password": pwd.strip()})
        return accounts
    except Exception:
        return []

def fetch_jwt_from_api(uid, password):
    """Fetches JWT token from your external Vercel API with better error logging."""
    api_url = f"https://ff-official-jwt-api-ob55.vercel.app/guest_to_jwt?uid={uid}&password={password}"
    try:
        response = requests.get(api_url, timeout=15)
        print(f"[{datetime.now()}] API Response for UID {uid}: Status {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                token = data.get("jwt_token") or data.get("token")
                if token:
                    return token, None
                return None, "Token key missing in JSON response"
            except json.JSONDecodeError:
                token = response.text.strip()
                if token:
                    return token, None
                return None, "Empty response from JWT API"
        else:
            return None, f"HTTP {response.status_code}: {response.text[:200]}"
    except requests.exceptions.Timeout:
        return None, "Request timed out while connecting to JWT API"
    except Exception as e:
        return None, str(e)


def update_all_tokens():
    """Background task to fetch/refresh tokens for all accounts across all regional files every 7 hours."""
    while True:
        print(f"[{datetime.now()}] Starting automatic JWT token refresh cycle...")
        
        # Gather accounts from all possible files
        all_files_to_check = ["accounts.txt"] + [f"Account_{r}.txt" for r in REGION_MAP.keys()] + [f"accounts_{r}.txt" for r in REGION_MAP.keys()]
        seen_uids = set()
        
        for fname in all_files_to_check:
            if not os.path.exists(fname):
                continue
            try:
                with open(fname, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or ':' not in line:
                            continue
                        uid, pwd = line.split(':', 1)
                        uid, pwd = uid.strip(), pwd.strip()
                        if uid in seen_uids:
                            continue
                        seen_uids.add(uid)
                        
                        token, err = fetch_jwt_from_api(uid, pwd)
                        if token:
                            JWT_TOKEN[uid] = token
                        time.sleep(1)
            except Exception:
                pass
        
        print(f"[{datetime.now()}] Token refresh cycle completed. Sleeping for 7 hours...")
        time.sleep(25200)

def format_timestamp(ts):
    if not ts:
        return "N/A"
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)

def get_player_info(target_uid, region="IND"):
    """Fetches target player details using the updated Player Info API."""
    api_url = f"https://ff-playerinfo-ob55.vercel.app/info?uid={target_uid}&region={region}"
    try:
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            player_data = response.json()
            if player_data and "basic_info" in player_data:
                p_info = player_data["basic_info"]
                prime_info = p_info.get("prime_info", {})

                return {
                    "nickname": p_info.get("nickname", "N/A"),
                    "uid": str(target_uid),
                    "region": p_info.get("region", "IND"),
                    "likes": p_info.get("liked", "N/A"),
                    "prime_level": prime_info.get("prime_level", 0),
                    "level": p_info.get("level", "N/A"),
                    "last_login": format_timestamp(p_info.get("last_login_at")),
                    "created_at": format_timestamp(p_info.get("create_at"))
                }
    except Exception:
        pass
    return None


def send_friend_request(target_uid, token, region_server_url):
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
            "ReleaseVersion": "OB55",
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(encrypted_payload)//2),
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-N975F Build/PI)",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload), timeout=15)
        resp_text = response.text[:200]
        if response.status_code == 200:
            if "Invalid request body" in resp_text:
                return False, f"200 OK but body: {resp_text}", url
            return True, resp_text, url
        else:
            return False, f"HTTP {response.status_code}: {resp_text}", url
    except Exception as e:
        return False, str(e), region_server_url

def process_account(account, target_uid, results, regions_to_try, delay=0):
    if delay > 0:
        time.sleep(delay)
    uid = account['uid']
    
    token = JWT_TOKEN.get(uid)
    if not token:
        token, err = fetch_jwt_from_api(uid, account['password'])
        if token:
            JWT_TOKEN[uid] = token
        else:
            results['failed_count'] += 1
            return

    success = False
    used_region_url = None
    for region_name, server_url in regions_to_try:
        ok, resp_msg, used_url = send_friend_request(target_uid, token, server_url)
        if ok:
            success = True
            used_region_url = used_url
            break
            
    if success:
        results['successful_count'] += 1
        results['region_urls_used'].add(used_region_url)
    else:
        results['failed_count'] += 1

def spam_friend_requests(target_uid, count=None, region=None):
    accounts = load_accounts(region)
    if not accounts:
        return {
            "error": f"No accounts found for region '{region}' or in default accounts.txt"
        }, 404

    if count is not None:
        if count <= 0:
            return {"error": "Count must be positive"}, 400
        accounts_to_use = accounts[:min(count, len(accounts))]
    else:
        accounts_to_use = accounts

    if region:
        region_lower = region.lower()
        if region_lower in REGION_MAP:
            regions_to_try = [(region_lower, REGION_MAP[region_lower])]
        else:
            return {"error": f"Invalid region: {region}"}, 400
    else:
        regions_to_try = ALL_REGIONS

    results = {
        "successful_count": 0,
        "failed_count": 0,
        "region_urls_used": set()
    }

    threads = []
    thread_delay = 0.1

    for i, acc in enumerate(accounts_to_use):
        t = threading.Thread(
            target=process_account,
            args=(
                acc,
                target_uid,
                results,
                regions_to_try,
                i * thread_delay
            )
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    player_info = get_player_info(target_uid)

    # Response starts with Status
    output_data = {
        "Status": "success"
    }

    if player_info:
        output_data["Nickname"] = player_info.get("nickname")
        output_data["Uid"] = player_info.get("uid")
        output_data["Region"] = player_info.get("region")
        output_data["Likes"] = player_info.get("likes")
        output_data["Prime level"] = player_info.get("prime_level")
    else:
        output_data["Nickname"] = "N/A"
        output_data["Uid"] = str(target_uid)
        output_data["Region"] = "N/A"
        output_data["Likes"] = "N/A"
        output_data["Prime level"] = 0

    output_data["Successful count"] = results["successful_count"]
    output_data["Failed count"] = results["failed_count"]

    output_data["Ob_version"] = "OB55"
    output_data["Client_Version"] = "1.132.1"

    # Status code at the end
    output_data["Status_Code"] = 200

    return output_data

@app.route('/spam', methods=['GET'])
def rizer():
    target_uid = request.args.get('uid')
    if not target_uid:
        return jsonify({"error": "Missing 'uid' parameter"}), 400
    count_param = request.args.get('count')
    count = int(count_param) if count_param else None
    region = request.args.get('region')
    
    result = spam_friend_requests(target_uid, count, region)
    if isinstance(result, tuple) and result[1] in [400, 404]:
        return jsonify(result[0]), result[1]
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    total_all_accounts = 0
    regional_tokens = {}
    
    for reg in REGION_MAP.keys():
        filenames = [f"Account_{reg}.txt", f"accounts_{reg}.txt", f"Account{reg}.txt"]
        file_found = None
        uids_in_reg = []
        
        for fname in filenames:
            if os.path.exists(fname):
                file_found = fname
                try:
                    with open(fname, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and ':' in line:
                                uid_part = line.split(':', 1)[0].strip()
                                uids_in_reg.append(uid_part)
                except Exception:
                    pass
                break
        
        if file_found:
            cached_count = sum(1 for uid in uids_in_reg if uid in JWT_TOKEN)
            total_all_accounts += len(uids_in_reg)
            regional_tokens[reg.upper()] = {
                "file_used": file_found,
                "total_accounts": len(uids_in_reg),
                "cached_tokens": cached_count
            }
            
    health_data = {
        "status": "ok", 
        "total_uid_password_count": total_all_accounts,
        "total_cached_tokens": len(JWT_TOKEN),
        "regional_tokens": regional_tokens
    }
            
    return jsonify(health_data)



if __name__ == "__main__":
    bg_thread = threading.Thread(target=update_all_tokens, daemon=True)
    bg_thread.system_started = True
    bg_thread.start()
    
    app.run(host="0.0.0.0", port=5000, debug=False)