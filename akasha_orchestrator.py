#!/usr/bin/env python3
"""
Akashic Orchestrator
Coordinates multiple nodes working on the Akashic Record
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

class AkashicOrchestrator:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.records_dir = self.repo_path / "records"
        self.records_dir.mkdir(exist_ok=True)
    
    def create_thread(self, intent, description="", priority="normal"):
        """Create a new thread in the Akashic Record"""
        from mirror import reflect
        
        # Normalize intent
        mirrored = reflect(intent)
        normalized = mirrored["normalized"]
        
        # Create thread file
        thread_id = f"{normalized}_{int(time.time())}"
        thread_file = self.records_dir / f"{thread_id}.json"
        
        thread = {
            "id": thread_id,
            "intent": intent,
            "normalized": normalized,
            "description": description,
            "priority": priority,
            "status": "active",
            "created_at": time.time(),
            "created_by": "orchestrator",
            "progress": [],
            "locked_by": None,
            "locked_at": None
        }
        
        with open(thread_file, 'w') as f:
            json.dump(thread, f, indent=2)
        
        # Commit to git
        subprocess.run(['git', 'add', str(thread_file)], cwd=self.repo_path)
        subprocess.run(['git', 'commit', '-m', f'New thread: {intent}'], 
                      cwd=self.repo_path)
        subprocess.run(['git', 'push'], cwd=self.repo_path)
        
        print(f"✓ Created thread: {thread_id}")
        return thread_id
    
    def list_threads(self, status=None):
        """List all threads, optionally filtered by status"""
        threads = []
        
        for thread_file in self.records_dir.glob("*.json"):
            try:
                with open(thread_file) as f:
                    thread = json.load(f)
                    if status is None or thread.get("status") == status:
                        threads.append(thread)
            except Exception as e:
                print(f"Error reading {thread_file}: {e}")
        
        return sorted(threads, key=lambda t: t.get("created_at", 0), reverse=True)
    
    def show_status(self):
        """Show status of all threads and nodes"""
        print("\n" + "="*70)
        print("AKASHIC RECORD STATUS")
        print("="*70 + "\n")
        
        # Thread statistics
        all_threads = self.list_threads()
        active = [t for t in all_threads if t.get("status") == "active"]
        paused = [t for t in all_threads if t.get("status") == "paused"]
        completed = [t for t in all_threads if t.get("status") == "completed"]
        
        print(f"Threads: {len(all_threads)} total")
        print(f"  Active:    {len(active)}")
        print(f"  Paused:    {len(paused)}")
        print(f"  Completed: {len(completed)}")
        print()
        
        # Active threads detail
        if active:
            print("ACTIVE THREADS:")
            print("-" * 70)
            for thread in active[:10]:  # Show top 10
                intent = thread['intent'][:50]
                steps = len(thread.get('progress', []))
                locked = thread.get('locked_by', 'unlocked')
                age_hours = (time.time() - thread['created_at']) / 3600
                
                print(f"  [{locked:15}] {intent:50} ({steps} steps, {age_hours:.1f}h)")
            print()
        
        # Node activity
        print("NODE ACTIVITY:")
        print("-" * 70)
        nodes = {}
        for thread in all_threads:
            for progress in thread.get('progress', []):
                node = progress.get('node', 'unknown')
                nodes[node] = nodes.get(node, 0) + 1
        
        if nodes:
            for node, count in sorted(nodes.items(), key=lambda x: x[1], reverse=True):
                print(f"  {node:30} {count:6} contributions")
        else:
            print("  No node activity yet")
        print()
    
    def show_thread(self, thread_id):
        """Show detailed info about a specific thread"""
        thread_file = self.records_dir / f"{thread_id}.json"
        
        if not thread_file.exists():
            print(f"Thread not found: {thread_id}")
            return
        
        with open(thread_file) as f:
            thread = json.load(f)
        
        print("\n" + "="*70)
        print(f"THREAD: {thread['intent']}")
        print("="*70)
        print(f"ID:          {thread['id']}")
        print(f"Status:      {thread['status']}")
        print(f"Priority:    {thread.get('priority', 'normal')}")
        print(f"Created:     {datetime.fromtimestamp(thread['created_at'])}")
        print(f"Progress:    {len(thread.get('progress', []))} steps")
        
        if thread.get('locked_by'):
            print(f"Locked by:   {thread['locked_by']}")
            lock_age = (time.time() - thread.get('locked_at', 0)) / 60
            print(f"Lock age:    {lock_age:.1f} minutes")
        
        print(f"\nDescription: {thread.get('description', 'None')}")
        
        # Recent progress
        progress = thread.get('progress', [])
        if progress:
            print(f"\nRecent Progress (last 10):")
            print("-" * 70)
            for p in progress[-10:]:
                ts = datetime.fromtimestamp(p['timestamp']).strftime('%H:%M:%S')
                node = p.get('node', 'unknown')[:20]
                msg = p.get('message', '')[:40]
                print(f"  [{ts}] {node:20} {msg}")
        print()
    
    def assign_work(self):
        """Suggest work assignments for available nodes"""
        active = self.list_threads(status="active")
        paused = self.list_threads(status="paused")
        
        print("\n" + "="*70)
        print("WORK ASSIGNMENT SUGGESTIONS")
        print("="*70 + "\n")
        
        # Unlocked active threads
        unlocked_active = [t for t in active if not t.get('locked_by')]
        if unlocked_active:
            print(f"Available active threads ({len(unlocked_active)}):")
            for thread in unlocked_active[:5]:
                print(f"  • {thread['id']}")
                print(f"    Intent: {thread['intent']}")
                print(f"    Steps: {len(thread.get('progress', []))}")
                print()
        
        # Paused threads ready to resume
        if paused:
            print(f"Paused threads ready to resume ({len(paused)}):")
            for thread in paused[:5]:
                print(f"  • {thread['id']}")
                print(f"    Intent: {thread['intent']}")
                print(f"    Steps: {len(thread.get('progress', []))}")
                print()
    
    def sync_all(self):
        """Pull latest from git"""
        print("Syncing with git...")
        try:
            subprocess.run(['git', 'pull'], cwd=self.repo_path, check=True)
            print("✓ Sync complete")
        except subprocess.CalledProcessError as e:
            print(f"✗ Sync failed: {e}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Akashic Orchestrator")
        print("\nUsage:")
        print("  orchestrator.py create <intent> [description]")
        print("  orchestrator.py list [status]")
        print("  orchestrator.py status")
        print("  orchestrator.py show <thread_id>")
        print("  orchestrator.py assign")
        print("  orchestrator.py sync")
        sys.exit(1)
    
    orch = AkashicOrchestrator()
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: orchestrator.py create <intent> [description]")
            sys.exit(1)
        intent = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 else ""
        orch.create_thread(intent, description)
    
    elif command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        threads = orch.list_threads(status)
        print(f"\nThreads ({len(threads)}):")
        for t in threads:
            steps = len(t.get('progress', []))
            print(f"  [{t['status']:10}] {t['id']:50} ({steps} steps)")
    
    elif command == "status":
        orch.show_status()
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: orchestrator.py show <thread_id>")
            sys.exit(1)
        orch.show_thread(sys.argv[2])
    
    elif command == "assign":
        orch.assign_work()
    
    elif command == "sync":
        orch.sync_all()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
