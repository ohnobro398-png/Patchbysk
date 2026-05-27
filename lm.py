#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   APK-X ENTERPRISE LICENSE MANAGER                           ║
║   Private License System - Hardware-Locked                   ║
║   Architect: Jim (30yr EXP) | Developer: Bob                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import hashlib
import base64
import platform
import socket
import uuid
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
import sqlite3

# ==================== CONFIGURATION ====================
LICENSE_FILE = "/sdcard/APKX_Enterprise/.license"
LICENSE_DB = "/sdcard/APKX_Enterprise/Database/licenses.db"
HARDWARE_LOCK = True
TRIAL_DAYS = 7
MAX_DEVICES = 1

# ==================== DATA MODELS ====================
@dataclass
class LicenseInfo:
    license_key: str
    owner: str
    email: str
    plan: str
    issued_date: str
    expiry_date: str
    max_devices: int
    features: list
    hardware_id: str = ""
    activated: bool = False
    activation_date: str = ""

class LicenseTier:
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    
    FEATURES = {
        "free": ["basic_analysis", "single_patch"],
        "pro": ["full_analysis", "unlimited_patches", "native_support", "batch_mode", "reports"],
        "enterprise": ["full_analysis", "unlimited_patches", "native_support", "batch_mode",
                       "reports", "cloud_sync", "ai_engine", "plugin_system", "priority_support",
                       "api_access", "team_access", "audit_logs"],
    }
    
    LIMITS = {
        "free": {"max_apks": 5, "max_size_mb": 100},
        "pro": {"max_apks": 100, "max_size_mb": 500},
        "enterprise": {"max_apks": 999999, "max_size_mb": 9999},
    }

# ==================== HARDWARE ID GENERATOR ====================
class HardwareID:
    @staticmethod
    def get_device_id() -> str:
        components = []
        components.append(platform.system() or "Unknown")
        components.append(platform.release() or "Unknown")
        components.append(platform.version() or "Unknown")
        components.append(platform.machine() or "Unknown")
        
        try:
            hostname = socket.gethostname()
            components.append(hostname)
        except:
            components.append("unknown-host")
        
        try:
            mac = uuid.getnode()
            components.append(str(mac))
        except:
            components.append("unknown-mac")
        
        if os.path.exists("/system/build.prop"):
            try:
                with open("/system/build.prop", "r") as f:
                    for line in f:
                        if "ro.serialno" in line:
                            components.append(line.split("=")[1].strip())
                            break
            except:
                pass
        
        combined = "|".join(components)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    @staticmethod
    def get_device_name() -> str:
        try:
            return socket.gethostname()
        except:
            return f"Device-{HardwareID.get_device_id()[:8]}"

# ==================== LICENSE MANAGER ====================
class LicenseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.hw_id = HardwareID.get_device_id()
        self.device_name = HardwareID.get_device_name()
        self._init_db()
        self._initialized = True
    
    def _init_db(self):
        os.makedirs(os.path.dirname(LICENSE_DB), exist_ok=True)
        conn = sqlite3.connect(LICENSE_DB)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL,
                email TEXT NOT NULL,
                plan TEXT NOT NULL,
                issued_date TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                max_devices INTEGER DEFAULT 1,
                features TEXT,
                hardware_id TEXT,
                activated INTEGER DEFAULT 0,
                activation_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL,
                hardware_id TEXT NOT NULL,
                device_name TEXT,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (license_key) REFERENCES licenses(license_key)
            )
        """)
        conn.commit()
        conn.close()
    
    def generate_license(self, owner: str, email: str, plan: str,
                        days: int = 365, max_devices: int = 1) -> LicenseInfo:
        if plan not in LicenseTier.FEATURES:
            raise ValueError(f"Invalid plan: {plan}")
        
        seed = f"{owner}{email}{plan}{time.time()}{uuid.uuid4()}"
        key_hash = hashlib.sha256(seed.encode()).hexdigest()
        key_parts = [
            key_hash[0:4].upper(), key_hash[4:8].upper(),
            key_hash[8:12].upper(), key_hash[12:16].upper(),
        ]
        license_key = f"APKX-{'-'.join(key_parts)}"
        
        issued = datetime.now()
        expiry = issued + timedelta(days=days)
        
        license_info = LicenseInfo(
            license_key=license_key, owner=owner, email=email, plan=plan,
            issued_date=issued.isoformat(), expiry_date=expiry.isoformat(),
            max_devices=max_devices, features=LicenseTier.FEATURES[plan],
        )
        
        conn = sqlite3.connect(LICENSE_DB)
        conn.execute("""
            INSERT INTO licenses (license_key, owner, email, plan, issued_date,
                                expiry_date, max_devices, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (license_info.license_key, license_info.owner, license_info.email,
              license_info.plan, license_info.issued_date, license_info.expiry_date,
              license_info.max_devices, json.dumps(license_info.features)))
        conn.commit()
        conn.close()
        
        return license_info
    
    def validate_license(self, license_key: str) -> Tuple[bool, str, Optional[LicenseInfo]]:
        conn = sqlite3.connect(LICENSE_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM licenses WHERE license_key = ?",
                          (license_key,)).fetchone()
        
        if not row:
            conn.close()
            return False, "Invalid license key!", None
        
        expiry = datetime.fromisoformat(row['expiry_date'])
        if datetime.now() > expiry:
            conn.close()
            return False, f"License expired on {expiry.strftime('%Y-%m-%d')}!", None
        
        if HARDWARE_LOCK and row['hardware_id'] and row['hardware_id'] != self.hw_id:
            conn.close()
            return False, "License is locked to another device!", None
        
        if row['max_devices'] > 0:
            activation_count = conn.execute(
                "SELECT COUNT(*) FROM activations WHERE license_key = ?",
                (license_key,)).fetchone()[0]
            if activation_count >= row['max_devices'] and not row['hardware_id']:
                conn.close()
                return False, f"Maximum device limit ({row['max_devices']}) reached!", None
        
        license_info = LicenseInfo(
            license_key=row['license_key'], owner=row['owner'], email=row['email'],
            plan=row['plan'], issued_date=row['issued_date'], expiry_date=row['expiry_date'],
            max_devices=row['max_devices'],
            features=json.loads(row['features']) if row['features'] else [],
            hardware_id=row['hardware_id'] or "",
            activated=bool(row['activated']),
            activation_date=row['activation_date'] or "",
        )
        conn.close()
        return True, "License valid!", license_info
    
    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        valid, msg, info = self.validate_license(license_key)
        if not valid:
            return False, msg
        
        conn = sqlite3.connect(LICENSE_DB)
        existing = conn.execute(
            "SELECT * FROM activations WHERE license_key = ? AND hardware_id = ?",
            (license_key, self.hw_id)).fetchone()
        
        if existing:
            conn.close()
            return True, "Already activated on this device!"
        
        conn.execute(
            "UPDATE licenses SET hardware_id = ?, activated = 1, activation_date = ? WHERE license_key = ?",
            (self.hw_id, datetime.now().isoformat(), license_key))
        conn.execute(
            "INSERT INTO activations (license_key, hardware_id, device_name) VALUES (?, ?, ?)",
            (license_key, self.hw_id, self.device_name))
        conn.commit()
        conn.close()
        
        self._save_license_file(license_key)
        return True, "License activated successfully!"
    
    def _save_license_file(self, license_key: str):
        data = {
            "license_key": license_key,
            "hardware_id": self.hw_id,
            "device_name": self.device_name,
            "activated_at": datetime.now().isoformat(),
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
        with open(LICENSE_FILE, 'w') as f:
            f.write(encoded)
    
    def load_license_file(self) -> Optional[str]:
        if not os.path.exists(LICENSE_FILE):
            return None
        try:
            with open(LICENSE_FILE, 'r') as f:
                encoded = f.read()
            data = json.loads(base64.b64decode(encoded).decode())
            if data.get('hardware_id') != self.hw_id:
                return None
            return data.get('license_key')
        except:
            return None
    
    def has_feature(self, license_key: str, feature: str) -> bool:
        valid, msg, info = self.validate_license(license_key)
        if not valid:
            return False
        return feature in info.features
    
    def get_limit(self, license_key: str, limit_name: str) -> int:
        valid, msg, info = self.validate_license(license_key)
        if not valid:
            return 0
        return LicenseTier.LIMITS.get(info.plan, {}).get(limit_name, 0)
    
    def get_license_info(self, license_key: str = None) -> Optional[Dict]:
        if not license_key:
            license_key = self.load_license_file()
        if not license_key:
            return None
        
        valid, msg, info = self.validate_license(license_key)
        if not valid:
            return {'error': msg}
        
        return {
            'license_key': info.license_key,
            'owner': info.owner,
            'email': info.email,
            'plan': info.plan,
            'issued': info.issued_date,
            'expiry': info.expiry_date,
            'features': info.features,
            'limits': LicenseTier.LIMITS.get(info.plan, {}),
            'activated': info.activated,
            'device': self.device_name,
            'hardware_id': self.hw_id[:16] + '...',
        }
    
    def start_trial(self) -> Tuple[bool, str, str]:
        conn = sqlite3.connect(LICENSE_DB)
        trial = conn.execute(
            "SELECT * FROM licenses WHERE plan = 'free' AND hardware_id = ?",
            (self.hw_id,)).fetchone()
        conn.close()
        
        if trial:
            return False, "Trial already used!", ""
        
        license_info = self.generate_license(
            owner="Trial User", email="trial@apkx.dev",
            plan="free", days=TRIAL_DAYS, max_devices=1)
        self.activate_license(license_info.license_key)
        return True, f"Trial started! {TRIAL_DAYS} days remaining.", license_info.license_key

# ==================== LICENSE DECORATOR ====================
def require_license(feature: str = None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            lm = LicenseManager()
            license_key = lm.load_license_file()
            
            if not license_key:
                print("❌ No license found! Use: license_manager.start_trial()")
                return None
            
            valid, msg, info = lm.validate_license(license_key)
            if not valid:
                print(f"❌ License invalid: {msg}")
                return None
            
            if feature and feature not in info.features:
                print(f"❌ Feature '{feature}' not in your plan ({info.plan})")
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ==================== CLI ====================
def main():
    lm = LicenseManager()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║   APK-X ENTERPRISE LICENSE MANAGER                           ║
║   Private License System                                     ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    print(f"📱 Device: {lm.device_name}")
    print(f"🔑 Hardware ID: {lm.hw_id[:16]}...")
    
    existing = lm.load_license_file()
    if existing:
        info = lm.get_license_info(existing)
        if info and 'error' not in info:
            print(f"\n✅ Licensed to: {info['owner']}")
            print(f"📧 Email: {info['email']}")
            print(f"👑 Plan: {info['plan'].upper()}")
            print(f"📅 Expiry: {info['expiry'][:10]}")
            print(f"🔑 Key: {info['license_key']}")
            print(f"✨ Features: {len(info['features'])}")
        else:
            print(f"\n❌ {info.get('error', 'License invalid')}")
    else:
        print("\n⚠️  No license activated!")
    
    import argparse
    parser = argparse.ArgumentParser(description="APK-X License Manager")
    parser.add_argument("--trial", action="store_true", help="Start free trial")
    parser.add_argument("--activate", type=str, help="Activate license key")
    parser.add_argument("--generate", nargs=3, metavar=("OWNER", "EMAIL", "PLAN"),
                       help="Generate new license")
    parser.add_argument("--info", action="store_true", help="Show license info")
    parser.add_argument("--days", type=int, default=365, help="License days")
    
    args = parser.parse_args()
    
    if args.trial:
        success, msg, key = lm.start_trial()
        print(f"\n{'✅' if success else '❌'} {msg}")
        if key:
            print(f"🔑 License Key: {key}")
    
    elif args.activate:
        success, msg = lm.activate_license(args.activate)
        print(f"\n{'✅' if success else '❌'} {msg}")
    
    elif args.generate:
        owner, email, plan = args.generate
        if plan not in ["pro", "enterprise"]:
            print("❌ Plan must be 'pro' or 'enterprise'")
            return
        info = lm.generate_license(owner, email, plan, days=args.days)
        print(f"\n✅ License Generated!")
        print(f"🔑 Key: {info.license_key}")
        print(f"👤 Owner: {info.owner}")
        print(f"👑 Plan: {info.plan.upper()}")
        print(f"📅 Expiry: {info.expiry_date[:10]}")
    
    elif args.info:
        info = lm.get_license_info()
        if info:
            print(json.dumps(info, indent=2, default=str))
        else:
            print("❌ No license found!")

if __name__ == "__main__":
    main()