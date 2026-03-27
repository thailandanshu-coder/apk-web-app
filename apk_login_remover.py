#!/usr/bin/env python3
"""
APK Login Page Remover
======================
Remove login from APK files automatically

Usage:
  python3 apk_login_remover.py /path/to/your.apk

Output:
  - your_app_no_login.apk (login removed)
  - Extracted folder with source code

Use ONLY on APKs you own/created!
"""

import os
import sys
import subprocess
import re
import shutil
from pathlib import Path

class APKLoginRemover:
    def __init__(self, apk_path):
        self.apk_path = os.path.abspath(apk_path)
        self.apk_name = os.path.basename(apk_path)
        self.work_dir = os.path.join(os.getcwd(), f"login_removed_{os.path.splitext(self.apk_name)[0]}")
        self.decompiled_dir = os.path.join(self.work_dir, "decompiled")
        self.output_apk = os.path.join(self.work_dir, f"{os.path.splitext(self.apk_name)[0]}_no_login.apk")
        self.keystore_path = os.path.join(self.work_dir, "test.keystore")
        
    def print_banner(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║              APK LOGIN PAGE REMOVER                          ║
║              Remove Login from Your APK                      ║
╚══════════════════════════════════════════════════════════════╝
""")
        
    def check_dependencies(self):
        """Check required tools"""
        print("[+] Checking dependencies...")
        tools = ['apktool', 'java', 'keytool', 'jarsigner']
        missing = []
        
        for tool in tools:
            result = subprocess.run(['which', tool], capture_output=True)
            if result.returncode != 0:
                missing.append(tool)
                print(f"  ✗ {tool} not found")
            else:
                print(f"  ✓ {tool} found")
                
        if missing:
            print("\n[!] Install missing tools:")
            print("  sudo apt install openjdk-11-jdk")
            print("  # Download apktool from https://ibotpeaches.github.io/Apktool/")
            return False
        return True
        
    def decompile_apk(self):
        """Decompile APK"""
        print(f"\n[+] Decompiling {self.apk_name}...")
        os.makedirs(self.work_dir, exist_ok=True)
        
        result = subprocess.run(
            ['apktool', 'd', '-f', '-o', self.decompiled_dir, self.apk_path],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f"  ✓ Decompiled to: {self.decompiled_dir}")
            return True
        else:
            print(f"  ✗ Error: {result.stderr}")
            return False
            
    def find_login_activity(self):
        """Find login activity in manifest"""
        manifest_path = os.path.join(self.decompiled_dir, 'AndroidManifest.xml')
        
        if not os.path.exists(manifest_path):
            return None
            
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        # Find package name
        package_match = re.search(r'package="([^"]+)"', content)
        package = package_match.group(1) if package_match else "unknown"
        
        # Find login-related activities
        login_keywords = ['login', 'signin', 'auth', 'splash', 'welcome']
        login_activities = []
        
        for keyword in login_keywords:
            pattern = rf'<activity[^>]*android:name="([^"]*{keyword}[^"]*)"[^>]*>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            login_activities.extend(matches)
            
        # Find main activity
        main_match = re.search(
            r'<activity[^>]*android:name="([^"]+)"[^>]*>[^<]*<intent-filter>[^<]*<action[^>]*android:name="android\.intent\.action\.MAIN"',
            content
        )
        main_activity = main_match.group(1) if main_match else None
        
        return {
            'package': package,
            'login_activities': login_activities,
            'main_activity': main_activity
        }
        
    def remove_login_from_manifest(self, manifest_info):
        """Remove login from AndroidManifest.xml"""
        print("\n[+] Modifying AndroidManifest.xml...")
        
        manifest_path = os.path.join(self.decompiled_dir, 'AndroidManifest.xml')
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        # Disable login activities
        for activity in manifest_info['login_activities']:
            pattern = rf'(<activity[^>]*android:name="{re.escape(activity)}"[^>]*)>'
            content = re.sub(pattern, r'\1 android:enabled="false">', content)
            print(f"  ✓ Disabled: {activity}")
            
        # Write back
        with open(manifest_path, 'w') as f:
            f.write(content)
            
        return len(manifest_info['login_activities']) > 0
        
    def modify_smali_code(self):
        """Modify smali code to bypass login"""
        print("\n[+] Modifying smali code...")
        
        smali_dir = os.path.join(self.decompiled_dir, 'smali')
        if not os.path.exists(smali_dir):
            return False
            
        modified = False
        
        # Find and modify login-related smali files
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if file.endswith('.smali'):
                    filepath = os.path.join(root, file)
                    
                    with open(filepath, 'r', errors='ignore') as f:
                        content = f.read()
                        
                    original = content
                    
                    # Bypass login checks
                    # Change: if-eqz vX, :cond_fail → Always pass
                    content = re.sub(
                        r'if-eqz\s+(v\d+),\s*(:cond_\w+)',
                        r'goto :cond_success  # Login bypassed',
                        content
                    )
                    
                    if content != original:
                        with open(filepath, 'w') as f:
                            f.write(content)
                        modified = True
                        print(f"  ✓ Modified: {file}")
                        
        return modified
        
    def recompile_apk(self):
        """Recompile modified APK"""
        print(f"\n[+] Recompiling APK...")
        
        result = subprocess.run(
            ['apktool', 'b', '-o', self.output_apk, self.decompiled_dir],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f"  ✓ Recompiled: {self.output_apk}")
            return True
        else:
            print(f"  ✗ Error: {result.stderr}")
            return False
            
    def create_keystore(self):
        """Create signing keystore"""
        if os.path.exists(self.keystore_path):
            return True
            
        print("\n[+] Creating keystore...")
        
        result = subprocess.run([
            'keytool', '-genkey', '-v',
            '-keystore', self.keystore_path,
            '-alias', 'test',
            '-keyalg', 'RSA', '-keysize', '2048',
            '-validity', '10000',
            '-dname', 'CN=Test, OU=Test, O=Test, L=Test, ST=Test, C=US',
            '-storepass', 'password',
            '-keypass', 'password'
        ], capture_output=True)
        
        return result.returncode == 0
        
    def sign_apk(self):
        """Sign the APK"""
        print("\n[+] Signing APK...")
        
        result = subprocess.run([
            'jarsigner', '-verbose',
            '-keystore', self.keystore_path,
            '-storepass', 'password',
            self.output_apk, 'test'
        ], capture_output=True)
        
        if result.returncode in [0, 1]:  # 1 is warning
            print(f"  ✓ APK signed")
            return True
        else:
            print(f"  ⚠ Signing warning")
            return True
            
    def verify_apk(self):
        """Verify the output APK"""
        print("\n[+] Verifying APK...")
        
        if os.path.exists(self.output_apk):
            size = os.path.getsize(self.output_apk)
            print(f"  ✓ APK created: {size / 1024 / 1024:.2f} MB")
            return True
        return False
        
    def show_result(self):
        """Show final result"""
        print("\n" + "=" * 60)
        print("✅ LOGIN REMOVED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📦 Original APK: {self.apk_path}")
        print(f"📦 Modified APK: {self.output_apk}")
        print(f"\n✨ Login has been removed!")
        print(f"\n📁 Source code: {self.decompiled_dir}")
        print("\n⚠️  Install with:")
        print(f"   adb install \"{self.output_apk}\"")
        print("=" * 60)
        
    def run(self):
        """Main process"""
        self.print_banner()
        
        if not os.path.exists(self.apk_path):
            print(f"✗ APK not found: {self.apk_path}")
            return False
            
        if not self.check_dependencies():
            return False
            
        if not self.decompile_apk():
            return False
            
        manifest_info = self.find_login_activity()
        if manifest_info:
            print(f"\n[+] Package: {manifest_info['package']}")
            print(f"[+] Login activities found: {len(manifest_info['login_activities'])}")
            for act in manifest_info['login_activities']:
                print(f"    - {act}")
                
        self.remove_login_from_manifest(manifest_info)
        self.modify_smali_code()
        
        if not self.recompile_apk():
            return False
            
        self.create_keystore()
        self.sign_apk()
        self.verify_apk()
        self.show_result()
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='APK Login Page Remover - Remove login from your APK',
        epilog="""
Example:
  python3 apk_login_remover.py myapp.apk

⚠️  Use ONLY on APKs you own/created!
        """
    )
    parser.add_argument('apk', help='Path to APK file')
    
    args = parser.parse_args()
    
    remover = APKLoginRemover(args.apk)
    if remover.run():
        print("\n✅ Done!")
    else:
        print("\n❌ Failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
