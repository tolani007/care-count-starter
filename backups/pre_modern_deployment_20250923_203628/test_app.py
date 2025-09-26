#!/usr/bin/env python3
"""
Care Count App Testing Framework
Tests UI/UX changes and backend functionality
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
import subprocess
import requests
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CareCountTester:
    def __init__(self):
        self.test_results = []
        self.app_url = "http://localhost:8501"
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self, description: str = "manual_backup"):
        """Create a timestamped backup of current app state"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{description}_{timestamp}"
        
        # Backup main files
        files_to_backup = [
            "streamlit_app.py",
            ".streamlit/secrets.toml",
            "requirements.txt"
        ]
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                subprocess.run(["cp", file_path, str(backup_path / os.path.basename(file_path))])
        
        logger.info(f"Backup created: {backup_name}")
        return backup_name
    
    def restore_backup(self, backup_name: str):
        """Restore from a backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            logger.error(f"Backup {backup_name} not found")
            return False
        
        # Restore files
        files_to_restore = [
            "streamlit_app.py",
            ".streamlit/secrets.toml", 
            "requirements.txt"
        ]
        
        for file_path in files_to_restore:
            backup_file = backup_path / os.path.basename(file_path)
            if backup_file.exists():
                subprocess.run(["cp", str(backup_file), file_path])
        
        logger.info(f"Restored from backup: {backup_name}")
        return True
    
    def test_app_startup(self) -> bool:
        """Test if the app starts without errors"""
        try:
            # Check if app is already running
            response = requests.get(self.app_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ App is running and accessible")
                return True
            else:
                logger.error(f"❌ App returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ App startup test failed: {e}")
            return False
    
    def test_ui_elements(self) -> Dict[str, bool]:
        """Test key UI elements are present"""
        results = {}
        try:
            response = requests.get(self.app_url, timeout=10)
            content = response.text.lower()
            
            # Test for key UI elements
            ui_tests = {
                "title_present": "care count" in content,
                "signin_form": "sign in" in content or "email" in content,
                "camera_input": "camera" in content or "webcam" in content,
                "file_upload": "upload" in content or "file" in content,
                "visit_management": "visit" in content,
                "item_logging": "item" in content,
                "css_styling": "style" in content or "css" in content
            }
            
            for test_name, result in ui_tests.items():
                results[test_name] = result
                status = "✅" if result else "❌"
                logger.info(f"{status} {test_name}: {result}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ UI elements test failed: {e}")
            return {}
    
    def test_responsive_design(self) -> bool:
        """Test if the app has responsive design elements"""
        try:
            response = requests.get(self.app_url, timeout=10)
            content = response.text
            
            # Check for responsive design indicators
            responsive_indicators = [
                "container" in content,
                "column" in content,
                "responsive" in content,
                "mobile" in content
            ]
            
            responsive_score = sum(responsive_indicators) / len(responsive_indicators)
            is_responsive = responsive_score >= 0.5
            
            logger.info(f"📱 Responsive design score: {responsive_score:.2f} ({'✅' if is_responsive else '❌'})")
            return is_responsive
            
        except Exception as e:
            logger.error(f"❌ Responsive design test failed: {e}")
            return False
    
    def test_performance(self) -> Dict[str, float]:
        """Test app performance metrics"""
        try:
            start_time = time.time()
            response = requests.get(self.app_url, timeout=30)
            load_time = time.time() - start_time
            
            results = {
                "load_time": load_time,
                "status_code": response.status_code,
                "content_size": len(response.content)
            }
            
            logger.info(f"⚡ Load time: {load_time:.2f}s")
            logger.info(f"📊 Content size: {len(response.content)} bytes")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return {}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("🧪 Starting comprehensive app testing...")
        
        # Create backup before testing
        backup_name = self.create_backup("pre_test_backup")
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "backup_created": backup_name,
            "startup_test": self.test_app_startup(),
            "ui_elements": self.test_ui_elements(),
            "responsive_design": self.test_responsive_design(),
            "performance": self.test_performance()
        }
        
        # Calculate overall score
        ui_score = sum(test_results["ui_elements"].values()) / len(test_results["ui_elements"]) if test_results["ui_elements"] else 0
        overall_score = (
            (1 if test_results["startup_test"] else 0) +
            ui_score +
            (1 if test_results["responsive_design"] else 0)
        ) / 3
        
        test_results["overall_score"] = overall_score
        test_results["status"] = "PASS" if overall_score >= 0.8 else "FAIL"
        
        logger.info(f"🎯 Overall test score: {overall_score:.2f} ({test_results['status']})")
        
        return test_results

def main():
    """Main testing function"""
    tester = CareCountTester()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "backup":
            description = sys.argv[2] if len(sys.argv) > 2 else "manual_backup"
            tester.create_backup(description)
        elif command == "restore":
            if len(sys.argv) > 2:
                tester.restore_backup(sys.argv[2])
            else:
                print("Usage: python test_app.py restore <backup_name>")
        elif command == "test":
            results = tester.run_all_tests()
            print(f"\n📋 Test Results Summary:")
            print(f"Status: {results['status']}")
            print(f"Score: {results['overall_score']:.2f}")
            print(f"Backup: {results['backup_created']}")
        else:
            print("Available commands: backup, restore, test")
    else:
        # Run all tests by default
        results = tester.run_all_tests()
        print(f"\n📋 Test Results Summary:")
        print(f"Status: {results['status']}")
        print(f"Score: {results['overall_score']:.2f}")
        print(f"Backup: {results['backup_created']}")

if __name__ == "__main__":
    main()
