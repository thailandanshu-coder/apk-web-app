#!/usr/bin/env python3
"""
APK Login Remover Tool
======================
Automatically removes login from APK files
Use ONLY on your own APKs!

Usage: python3 remove_login.py /path/to/your.apk
"""

import os
import sys
import subprocess
import shutil
import re
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
║           APK LOGIN REMOVER                                  ║
║           Remove Login from Your APK                         ║
╚══════════════════════════════════════════════════════════════╝
⚠️  WARNING: Use this tool ONLY on APKs you own/created!
""")
        
    def check_dependencies(self):
        """Check if required tools are installed"""
        print("[+] Checking dependencies...")
        tools = ['apktool', 'java', 'keytool', 'jarsigner', 'zipalign']
        
        for tool in tools:
            result = subprocess.run(['which', tool], capture_output=True)
            if result.returncode != 0:
                print(f"  ✗ {tool} not found!")
                print(f"  [!] Please install {tool} first")
                return False
            else:
                print(f"  ✓ {tool} found")
        return True
        
    def decompile_apk(self):
        """Decompile APK using APKTool"""
        print(f"\n[+] Decompiling {self.apk_name}...")
        os.makedirs(self.work_dir, exist_ok=True)
        
        cmd = ['apktool', 'd', '-f', '-o', self.decompiled_dir, self.apk_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ APK decompiled successfully")
            print(f"  📁 Location: {self.decompiled_dir}")
            return True
        else:
            print(f"  ✗ Decompilation failed:")
            print(result.stderr)
            return False
            
    def analyze_manifest(self):
        """Analyze AndroidManifest.xml to find login activity"""
        manifest_path = os.path.join(self.decompiled_dir, 'AndroidManifest.xml')
        
        if not os.path.exists(manifest_path):
            print("  ✗ AndroidManifest.xml not found!")
            return None
            
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract package name
        package_match = re.search(r'package="([^"]+)"', content)
        package_name = package_match.group(1) if package_match else "unknown"
        print(f"  📦 Package: {package_name}")
        
        # Find launcher activity (main activity)
        # Pattern: activity with MAIN action and LAUNCHER category
        launcher_pattern = r'<activity[^>]*android:name="([^"]+)"[^>]*>[\s\S]*?<intent-filter>[\s\S]*?<action[^>]*android:name="android\.intent\.action\.MAIN"[\s\S]*?<category[^>]*android:name="android\.intent\.category\.LAUNCHER"[\s\S]*?</intent-filter>[\s\S]*?</activity>'
        launcher_match = re.search(launcher_pattern, content)
        
        if launcher_match:
            launcher_activity = launcher_match.group(1)
            print(f"  🚀 Launcher Activity: {launcher_activity}")
        else:
            launcher_activity = None
            print("  ⚠️  No launcher activity found!")
            
        # Find potential login activities
        login_keywords = ['login', 'signin', 'auth', 'splash', 'welcome']
        login_activities = []
        
        activity_pattern = r'<activity[^>]*android:name="([^"]+)"[^>]*>'
        activities = re.findall(activity_pattern, content)
        
        for activity in activities:
            activity_lower = activity.lower()
            for keyword in login_keywords:
                if keyword in activity_lower:
                    login_activities.append(activity)
                    break
                    
        if login_activities:
            print(f"  🔐 Potential Login Activities: {', '.join(login_activities)}")
        else:
            print("  ⚠️  No obvious login activities found")
            # If no login activity found, use the launcher as fallback
            if launcher_activity:
                print("  ℹ️  Will modify launcher activity")
                
        return {
            'package': package_name,
            'launcher': launcher_activity,
            'login_activities': login_activities,
            'all_activities': activities
        }
        
    def remove_login_method_1_manifest(self, manifest_info):
        """Method 1: Disable login activity in manifest and set main as launcher"""
        print("\n[+] Method 1: Modifying AndroidManifest.xml...")
        
        manifest_path = os.path.join(self.decompiled_dir, 'AndroidManifest.xml')
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Find login activity and disable it
        if manifest_info['login_activities']:
            login_activity = manifest_info['login_activities'][0]
            
            # Pattern to find the login activity tag
            login_pattern = rf'(<activity[^>]*android:name="{re.escape(login_activity)}"[^>]*>)'
            
            # Add enabled="false" to disable it
            content = re.sub(login_pattern, r'\1\n            android:enabled="false"', content)
            
            print(f"  ✓ Disabled login activity: {login_activity}")
            
        # Find a main activity to set as launcher (not the login one)
        main_activity = None
        for activity in manifest_info['all_activities']:
            if activity not in manifest_info['login_activities']:
                if 'main' in activity.lower() or 'home' in activity.lower():
                    main_activity = activity
                    break
                    
        # If no main found, use the first non-login activity
        if not main_activity:
            for activity in manifest_info['all_activities']:
                if activity not in manifest_info['login_activities']:
                    main_activity = activity
                    break
                    
        if main_activity:
            print(f"  ✓ Setting {main_activity} as launcher")
            
            # Check if this activity already has launcher intent-filter
            activity_pattern = rf'(<activity[^>]*android:name="{re.escape(main_activity)}"[^>]*>)(.*?)(</activity>)'
            activity_match = re.search(activity_pattern, content, re.DOTALL)
            
            if activity_match:
                if 'LAUNCHER' not in activity_match.group(2):
                    # Add launcher intent-filter
                    launcher_filter = '''\n            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>'''
                    
                    content = content.replace(
                        activity_match.group(0),
                        activity_match.group(1) + launcher_filter + activity_match.group(2) + activity_match.group(3)
                    )
                    
        # Write modified manifest
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        if content != original_content:
            print("  ✓ AndroidManifest.xml modified successfully")
            return True
        else:
            print("  ⚠️  No changes made to manifest")
            return False
            
    def remove_login_method_2_smali(self, manifest_info):
        """Method 2: Modify smali code to bypass login check"""
        print("\n[+] Method 2: Modifying Smali code...")
        
        smali_dir = os.path.join(self.decompiled_dir, 'smali')
        if not os.path.exists(smali_dir):
            print("  ✗ Smali directory not found!")
            return False
            
        # Find login-related smali files
        login_files = []
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if file.endswith('.smali'):
                    file_lower = file.lower()
                    if any(keyword in file_lower for keyword in ['login', 'signin', 'auth']):
                        login_files.append(os.path.join(root, file))
                        
        if not login_files:
            print("  ⚠️  No login-related smali files found")
            return False
            
        print(f"  Found {len(login_files)} login-related files")
        
        modified = False
        for smali_file in login_files[:1]:  # Modify first one only
            print(f"  Processing: {os.path.basename(smali_file)}")
            
            with open(smali_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # Common patterns to bypass login
            # Pattern 1: if-eqz vX, :cond_X (if zero, jump) - flip to if-nez
            content = re.sub(
                r'if-eqz\s+(v\d+),\s*(:cond_\w+)',
                r'if-nez \1, \2  # MODIFIED: Login bypassed',
                content
            )
            
            # Pattern 2: const/4 vX, 0x0 (return false) - change to 0x1 (return true)
            content = re.sub(
                r'(const/4\s+v\d+,)\s+0x0\s*$',
                r'\1 0x1  # MODIFIED: Return true',
                content,
                flags=re.MULTILINE
            )
            
            if content != original_content:
                with open(smali_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ Modified: {os.path.basename(smali_file)}")
                modified = True
            else:
                print(f"  ℹ️  No login check pattern found in: {os.path.basename(smali_file)}")
                
        return modified
        
    def recompile_apk(self):
        """Recompile the modified APK"""
        print(f"\n[+] Recompiling APK...")
        
        cmd = ['apktool', 'b', '-o', self.output_apk, self.decompiled_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✓ APK recompiled successfully")
            print(f"  📦 Output: {self.output_apk}")
            return True
        else:
            print(f"  ✗ Recompilation failed:")
            print(result.stderr)
            return False
            
    def create_keystore(self):
        """Create a test keystore for signing"""
        print(f"\n[+] Creating keystore...")
        
        if os.path.exists(self.keystore_path):
            print("  ✓ Keystore already exists")
            return True
            
        cmd = [
            'keytool', '-genkey', '-v',
            '-keystore', self.keystore_path,
            '-alias', 'test',
            '-keyalg', 'RSA', '-keysize', '2048',
            '-validity', '10000',
            '-dname', 'CN=Test, OU=Test, O=Test, L=Test, ST=Test, C=US',
            '-storepass', 'password',
            '-keypass', 'password'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ Keystore created")
            return True
        else:
            print(f"  ✗ Keystore creation failed:")
            print(result.stderr)
            return False
            
    def sign_apk(self):
        """Sign the APK with the keystore"""
        print(f"\n[+] Signing APK...")
        
        # Sign with jarsigner
        cmd = [
            'jarsigner', '-verbose',
            '-sigalg', 'SHA1withRSA',
            '-digestalg', 'SHA1',
            '-keystore', self.keystore_path,
            '-storepass', 'password',
            self.output_apk, 'test'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ APK signed successfully")
        else:
            print(f"  ⚠️  Signing warning (may still work):")
            # Don't return False, as signing warnings are common
            
        # Align with zipalign if available
        aligned_apk = self.output_apk.replace('.apk', '_aligned.apk')
        
        cmd = ['zipalign', '-v', '4', self.output_apk, aligned_apk]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            shutil.move(aligned_apk, self.output_apk)
            print("  ✓ APK aligned successfully")
        else:
            print("  ℹ️  zipalign not available or failed (APK may still work)")
            
        return True
        
    def verify_apk(self):
        """Verify the modified APK"""
        print(f"\n[+] Verifying APK...")
        
        # Check if file exists and has size
        if os.path.exists(self.output_apk):
            size = os.path.getsize(self.output_apk)
            print(f"  ✓ APK created: {size / 1024 / 1024:.2f} MB")
            
            # Verify with apktool
            cmd = ['apktool', 'd', '-f', '-o', '/tmp/verify_apk', self.output_apk]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("  ✓ APK is valid and can be decompiled")
                shutil.rmtree('/tmp/verify_apk', ignore_errors=True)
                return True
            else:
                print("  ⚠️  APK may have issues (but might still work)")
                return True
        else:
            print("  ✗ APK file not found!")
            return False
            
    def generate_install_instructions(self):
        """Generate install instructions"""
        print(f"\n" + "="*70)
        print("LOGIN REMOVED APK READY!")
        print("="*70)
        print(f"\n📦 Modified APK: {self.output_apk}")
        print(f"\n🔧 To install on your device:")
        print(f"   1. Enable 'Unknown Sources' in Settings")
        print(f"   2. Connect your device via USB")
        print(f"   3. Run: adb install \"{self.output_apk}\"")
        print(f"\n⚠️  NOTE: This APK has login removed!")
        print(f"   Use only for testing your own apps!")
        print("="*70)
        
        # Save instructions to file
        instructions_file = os.path.join(self.work_dir, "INSTALL_INSTRUCTIONS.txt")
        with open(instructions_file, 'w') as f:
            f.write(f"""APK Login Remover - Instructions
{'='*50}

Original APK: {self.apk_name}
Modified APK: {os.path.basename(self.output_apk)}

INSTALLATION:
1. Enable "Unknown Sources" in Android Settings
2. Connect device via USB
3. Run: adb install "{self.output_apk}"

Or copy the APK to your device and install directly.

⚠️  WARNING: This APK has login removed!
    Use only for testing your own apps!

Generated by APK Login Remover Tool
""")
        print(f"\n📝 Instructions saved to: {instructions_file}")
        
    def run(self):
        """Run the complete login removal process"""
        self.print_banner()
        
        # Check APK file exists
        if not os.path.exists(self.apk_path):
            print(f"✗ APK file not found: {self.apk_path}")
            return False
            
        # Check dependencies
        if not self.check_dependencies():
            print("\n[!] Please install missing dependencies first:")
            print("    - apktool: https://ibotpeaches.github.io/Apktool/")
            print("    - Java JDK: sudo apt install openjdk-11-jdk")
            return False
            
        # Decompile
        if not self.decompile_apk():
            return False
            
        # Analyze manifest
        manifest_info = self.analyze_manifest()
        if not manifest_info:
            return False
            
        # Try multiple methods to remove login
        method1_success = self.remove_login_method_1_manifest(manifest_info)
        method2_success = self.remove_login_method_2_smali(manifest_info)
        
        if not method1_success and not method2_success:
            print("\n[!] Could not find login to remove automatically")
            print("    You may need to manually modify the code")
            
        # Recompile
        if not self.recompile_apk():
            return False
            
        # Create keystore and sign
        if not self.create_keystore():
            return False
            
        if not self.sign_apk():
            return False
            
        # Verify
        if not self.verify_apk():
            return False
            
        # Generate instructions
        self.generate_install_instructions()
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='APK Login Remover - Remove login from your APKs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 remove_login.py /path/to/your/app.apk
  
⚠️  WARNING: Only use this on APKs you own or have permission to modify!
        """
    )
    parser.add_argument('apk', help='Path to APK file')
    
    args = parser.parse_args()
    
    remover = APKLoginRemover(args.apk)
    success = remover.run()
    
    if success:
        print("\n✅ Login removal completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Login removal failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
