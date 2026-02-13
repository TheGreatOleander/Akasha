#!/usr/bin/env python3
"""
Akashic Node Worker
Runs on old Android devices via Termux
Each node works on threads from the Akashic Record
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

class AkashicNode:
    def __init__(self, node_id=None, repo_path=".", checkpoint_interval=10):
        self.node_id = node_id or self._generate_node_id()
        self.repo_path = Path(repo_path)
        self.checkpoint_interval = checkpoint_interval
        self.current_thread = None
        self.message_count = 0
        
    def _generate_node_id(self):
        """Generate unique node ID from device info"""
        try:
            # Try to get Android device ID
            result = subprocess.run(['getprop', 'ro.serialno'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return f"droid_{result.stdout.strip()}"
        except:
            pass
        # Fallback to hostname
        import socket
        return f"node_{socket.gethostname()}"
    
    def git_pull(self):
        """Pull latest from remote"""
        try:
            subprocess.run(['git', 'pull'], cwd=self.repo_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Git pull failed: {e}")
            return False
    
    def git_commit_push(self, message):
        """Commit and push changes"""
        try:
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', message], 
                         cwd=self.repo_path, check=True)
            subprocess.run(['git', 'push'], cwd=self.repo_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Git commit/push failed: {e}")
            return False
    
    def get_available_thread(self):
        """Find a thread that needs work"""
        threads_dir = self.repo_path / "records"
        if not threads_dir.exists():
            return None
        
        # Look for threads marked as 'active' or 'paused'
        for thread_file in threads_dir.rglob("*.json"):
            try:
                with open(thread_file) as f:
                    thread = json.load(f)
                if thread.get("status") in ["active", "paused"]:
                    # Check if another node is working on it
                    if not thread.get("locked_by") or \
                       time.time() - thread.get("locked_at", 0) > 3600:
                        return thread_file, thread
            except Exception as e:
                print(f"Error reading {thread_file}: {e}")
        
        return None
    
    def lock_thread(self, thread_file, thread):
        """Lock thread for this node"""
        thread["locked_by"] = self.node_id
        thread["locked_at"] = time.time()
        thread["status"] = "active"
        
        with open(thread_file, 'w') as f:
            json.dump(thread, f, indent=2)
        
        self.git_commit_push(f"[{self.node_id}] Locked thread: {thread['intent']}")
    
    def unlock_thread(self, thread_file, thread):
        """Unlock thread"""
        thread["locked_by"] = None
        thread["locked_at"] = None
        thread["status"] = "paused"
        
        with open(thread_file, 'w') as f:
            json.dump(thread, f, indent=2)
        
        self.git_commit_push(f"[{self.node_id}] Released thread: {thread['intent']}")
    
    def add_progress(self, thread_file, thread, message):
        """Add progress to thread"""
        if "progress" not in thread:
            thread["progress"] = []
        
        thread["progress"].append({
            "node": self.node_id,
            "timestamp": time.time(),
            "message": message,
            "step": len(thread["progress"])
        })
        
        self.message_count += 1
        
        with open(thread_file, 'w') as f:
            json.dump(thread, f, indent=2)
        
        # Checkpoint every N messages
        if self.message_count % self.checkpoint_interval == 0:
            self.checkpoint(thread_file, thread)
    
    def checkpoint(self, thread_file, thread):
        """Save checkpoint to git"""
        step = len(thread.get("progress", []))
        self.git_commit_push(
            f"[{self.node_id}] Checkpoint: {thread['intent']} - step {step}"
        )
        print(f"✓ Checkpoint saved at step {step}")
    
    def work_session(self, duration_minutes=30):
        """Run a work session"""
        print(f"Node {self.node_id} starting work session ({duration_minutes}m)")
        
        # Pull latest
        print("Pulling latest from git...")
        self.git_pull()
        
        # Get a thread
        result = self.get_available_thread()
        if not result:
            print("No available threads. Idling.")
            return
        
        thread_file, thread = result
        print(f"Working on: {thread['intent']}")
        
        # Lock it
        self.lock_thread(thread_file, thread)
        
        try:
            # Work loop
            start_time = time.time()
            self.message_count = 0
            
            print("\n" + "="*60)
            print(f"THREAD: {thread['intent']}")
            print(f"PROGRESS: {len(thread.get('progress', []))} steps completed")
            print("="*60 + "\n")
            
            print("Ready for conversation. Type your messages.")
            print("Commands: !done (finish), !pause (save & exit), !status\n")
            
            while time.time() - start_time < duration_minutes * 60:
                # In real version, this would interact with AI API
                # For now, manual input simulation
                user_input = input(f"[{self.node_id}]> ")
                
                if user_input == "!done":
                    thread["status"] = "completed"
                    print("Thread marked as completed!")
                    break
                elif user_input == "!pause":
                    print("Pausing work...")
                    break
                elif user_input == "!status":
                    print(f"Steps: {len(thread.get('progress', []))}")
                    print(f"Messages this session: {self.message_count}")
                    print(f"Time remaining: {duration_minutes - (time.time()-start_time)/60:.1f}m")
                    continue
                
                # Add progress
                self.add_progress(thread_file, thread, user_input)
                print(f"  → Recorded (total: {len(thread['progress'])} steps)")
        
        finally:
            # Always unlock when done
            self.unlock_thread(thread_file, thread)
            print(f"\nSession complete. {self.message_count} messages recorded.")
    
    def monitor_mode(self, check_interval=60):
        """Monitor and sync mode - just keeps repo updated"""
        print(f"Node {self.node_id} in monitor mode")
        while True:
            print("Syncing with git...")
            self.git_pull()
            time.sleep(check_interval)


def main():
    if len(sys.argv) < 2:
        print("Akashic Node Worker")
        print("\nUsage:")
        print("  node.py work [duration_minutes]  - Work on a thread")
        print("  node.py monitor                  - Monitor/sync mode")
        print("  node.py status                   - Show node info")
        sys.exit(1)
    
    node = AkashicNode()
    
    command = sys.argv[1]
    
    if command == "work":
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        node.work_session(duration)
    
    elif command == "monitor":
        node.monitor_mode()
    
    elif command == "status":
        print(f"Node ID: {node.node_id}")
        print(f"Repo: {node.repo_path}")
        print(f"Checkpoint interval: {node.checkpoint_interval} messages")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
