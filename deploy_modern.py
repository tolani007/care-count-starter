#!/usr/bin/env python3
"""
Care Count Modern UI Deployment Script
Safe deployment with testing, backup, and rollback capabilities
"""

import os
import sys
import time
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CareCountDeployer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.deployment_log = []
        
    def log_deployment_step(self, step: str, status: str, details: str = ""):
        """Log deployment steps for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        self.deployment_log.append(log_entry)
        logger.info(f"{step}: {status} - {details}")
    
    def create_backup(self, description: str = "pre_deployment") -> str:
        """Create comprehensive backup of current state"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{description}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        # Files to backup
        files_to_backup = [
            "streamlit_app.py",
            "streamlit_app_modern.py",
            ".streamlit/secrets.toml",
            "requirements.txt",
            "ui_improvements.py",
            "test_app.py"
        ]
        
        try:
            for file_path in files_to_backup:
                if os.path.exists(file_path):
                    shutil.copy2(file_path, backup_path / os.path.basename(file_path))
            
            # Save deployment metadata
            metadata = {
                "backup_name": backup_name,
                "timestamp": timestamp,
                "description": description,
                "files_backed_up": [f for f in files_to_backup if os.path.exists(f)],
                "git_status": self.get_git_status()
            }
            
            with open(backup_path / "backup_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.log_deployment_step("backup_creation", "SUCCESS", f"Created backup: {backup_name}")
            return backup_name
            
        except Exception as e:
            self.log_deployment_step("backup_creation", "FAILED", str(e))
            raise
    
    def get_git_status(self) -> dict:
        """Get current git status"""
        try:
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True, cwd=self.project_root)
            return {
                "modified_files": result.stdout.strip().split('\n') if result.stdout.strip() else [],
                "return_code": result.returncode
            }
        except Exception:
            return {"error": "Git not available"}
    
    def run_tests(self) -> bool:
        """Run comprehensive tests before deployment"""
        try:
            self.log_deployment_step("testing", "STARTED", "Running pre-deployment tests")
            
            # Test 1: Check if modern app can be imported
            try:
                import streamlit_app_modern
                self.log_deployment_step("import_test", "SUCCESS", "Modern app imports successfully")
            except Exception as e:
                self.log_deployment_step("import_test", "FAILED", str(e))
                return False
            
            # Test 2: Check if UI improvements can be imported
            try:
                from ui_improvements import ModernUIComponents
                self.log_deployment_step("ui_import_test", "SUCCESS", "UI improvements import successfully")
            except Exception as e:
                self.log_deployment_step("ui_import_test", "FAILED", str(e))
                return False
            
            # Test 3: Run the test framework
            try:
                result = subprocess.run([sys.executable, "test_app.py", "test"], 
                                      capture_output=True, text=True, cwd=self.project_root)
                if result.returncode == 0:
                    self.log_deployment_step("app_tests", "SUCCESS", "All app tests passed")
                else:
                    self.log_deployment_step("app_tests", "FAILED", result.stderr)
                    return False
            except Exception as e:
                self.log_deployment_step("app_tests", "FAILED", str(e))
                return False
            
            self.log_deployment_step("testing", "SUCCESS", "All tests passed")
            return True
            
        except Exception as e:
            self.log_deployment_step("testing", "FAILED", str(e))
            return False
    
    def deploy_modern_ui(self) -> bool:
        """Deploy the modern UI version"""
        try:
            self.log_deployment_step("deployment", "STARTED", "Deploying modern UI")
            
            # Stop current Streamlit process
            try:
                subprocess.run(["pkill", "-f", "streamlit run"], check=False)
                time.sleep(2)
                self.log_deployment_step("stop_app", "SUCCESS", "Stopped current app")
            except Exception as e:
                self.log_deployment_step("stop_app", "WARNING", f"Could not stop app: {e}")
            
            # Backup current app
            current_backup = self.create_backup("pre_modern_deployment")
            
            # Replace current app with modern version
            shutil.copy2("streamlit_app_modern.py", "streamlit_app.py")
            self.log_deployment_step("file_replacement", "SUCCESS", "Replaced app with modern version")
            
            # Start new app
            try:
                # Start in background
                process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(5)  # Give it time to start
                
                # Check if it's running
                if process.poll() is None:
                    self.log_deployment_step("app_start", "SUCCESS", "Modern app started successfully")
                    return True
                else:
                    stdout, stderr = process.communicate()
                    self.log_deployment_step("app_start", "FAILED", f"App failed to start: {stderr.decode()}")
                    return False
                    
            except Exception as e:
                self.log_deployment_step("app_start", "FAILED", str(e))
                return False
                
        except Exception as e:
            self.log_deployment_step("deployment", "FAILED", str(e))
            return False
    
    def rollback(self, backup_name: str) -> bool:
        """Rollback to a previous version"""
        try:
            self.log_deployment_step("rollback", "STARTED", f"Rolling back to {backup_name}")
            
            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                self.log_deployment_step("rollback", "FAILED", f"Backup {backup_name} not found")
                return False
            
            # Stop current app
            try:
                subprocess.run(["pkill", "-f", "streamlit run"], check=False)
                time.sleep(2)
            except Exception:
                pass
            
            # Restore files
            files_to_restore = [
                "streamlit_app.py",
                ".streamlit/secrets.toml",
                "requirements.txt"
            ]
            
            for file_path in files_to_restore:
                backup_file = backup_path / os.path.basename(file_path)
                if backup_file.exists():
                    shutil.copy2(backup_file, file_path)
            
            # Restart app
            try:
                subprocess.Popen([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(3)
                self.log_deployment_step("rollback", "SUCCESS", f"Rolled back to {backup_name}")
                return True
            except Exception as e:
                self.log_deployment_step("rollback", "FAILED", f"Failed to restart after rollback: {e}")
                return False
                
        except Exception as e:
            self.log_deployment_step("rollback", "FAILED", str(e))
            return False
    
    def list_backups(self) -> list:
        """List available backups"""
        backups = []
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backup_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                        backups.append(metadata)
                    except Exception:
                        backups.append({
                            "backup_name": backup_dir.name,
                            "timestamp": "unknown",
                            "description": "unknown"
                        })
        return sorted(backups, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def save_deployment_log(self):
        """Save deployment log for audit trail"""
        log_file = self.backup_dir / f"deployment_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, "w") as f:
            json.dump(self.deployment_log, f, indent=2)
        logger.info(f"Deployment log saved to {log_file}")

def main():
    """Main deployment function"""
    deployer = CareCountDeployer()
    
    if len(sys.argv) < 2:
        print("""
Care Count Modern UI Deployment Script

Usage:
  python deploy_modern.py deploy     - Deploy modern UI with testing
  python deploy_modern.py rollback   - Rollback to previous version
  python deploy_modern.py list       - List available backups
  python deploy_modern.py test       - Run tests only
  python deploy_modern.py backup     - Create backup only

Examples:
  python deploy_modern.py deploy
  python deploy_modern.py rollback backup_20241223_143022
  python deploy_modern.py list
        """)
        return
    
    command = sys.argv[1]
    
    try:
        if command == "deploy":
            print("🚀 Starting modern UI deployment...")
            
            # Run tests first
            if not deployer.run_tests():
                print("❌ Tests failed. Deployment aborted.")
                return
            
            # Deploy
            if deployer.deploy_modern_ui():
                print("✅ Modern UI deployed successfully!")
                print("🌐 App should be running at http://localhost:8501")
            else:
                print("❌ Deployment failed. Check logs for details.")
            
        elif command == "rollback":
            if len(sys.argv) < 3:
                print("❌ Please specify backup name to rollback to")
                print("Available backups:")
                for backup in deployer.list_backups():
                    print(f"  - {backup['backup_name']}")
                return
            
            backup_name = sys.argv[2]
            if deployer.rollback(backup_name):
                print(f"✅ Successfully rolled back to {backup_name}")
            else:
                print(f"❌ Rollback to {backup_name} failed")
        
        elif command == "list":
            backups = deployer.list_backups()
            if backups:
                print("📋 Available backups:")
                for backup in backups:
                    print(f"  - {backup['backup_name']} ({backup.get('description', 'unknown')})")
            else:
                print("📋 No backups found")
        
        elif command == "test":
            if deployer.run_tests():
                print("✅ All tests passed!")
            else:
                print("❌ Tests failed!")
        
        elif command == "backup":
            backup_name = deployer.create_backup("manual_backup")
            print(f"✅ Backup created: {backup_name}")
        
        else:
            print(f"❌ Unknown command: {command}")
            return
        
        # Save deployment log
        deployer.save_deployment_log()
        
    except KeyboardInterrupt:
        print("\n⚠️ Deployment interrupted by user")
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        logger.error(f"Deployment error: {e}")

if __name__ == "__main__":
    main()
