#!/usr/bin/env python3
"""
The Librarian - Query and Search Interface for the Akashic Records
"""

import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

class Librarian:
    """
    The Librarian knows all that has been recorded.
    Query the Akashic Records in any way imaginable.
    """
    
    def __init__(self, repo_path: Path = Path(".")):
        self.repo_path = repo_path
        self.records_dir = repo_path / "records"
        self.cache = {}
        self.cache_time = 0
        self.cache_ttl = 60  # seconds
    
    def _load_all_threads(self, force_refresh: bool = False) -> List[Dict]:
        """Load all threads with caching"""
        if not force_refresh and time.time() - self.cache_time < self.cache_ttl:
            return self.cache.get("threads", [])
        
        threads = []
        if self.records_dir.exists():
            for thread_file in self.records_dir.glob("*.json"):
                if "_conversation" in thread_file.name:
                    continue
                try:
                    with open(thread_file) as f:
                        thread = json.load(f)
                        thread["_file"] = str(thread_file)
                        threads.append(thread)
                except Exception as e:
                    print(f"Error loading {thread_file}: {e}")
        
        self.cache["threads"] = threads
        self.cache_time = time.time()
        return threads
    
    def search(self, query: str, field: Optional[str] = None) -> List[Dict]:
        """
        Search threads by text query
        Searches in intent, description, and progress by default
        """
        threads = self._load_all_threads()
        query_lower = query.lower()
        results = []
        
        for thread in threads:
            if field:
                # Search specific field
                if field in thread and query_lower in str(thread[field]).lower():
                    results.append(thread)
            else:
                # Search all text fields
                searchable = [
                    thread.get("intent", ""),
                    thread.get("description", ""),
                    str(thread.get("progress", []))
                ]
                if any(query_lower in text.lower() for text in searchable):
                    results.append(thread)
        
        return results
    
    def find_by_status(self, status: str) -> List[Dict]:
        """Find all threads with given status"""
        threads = self._load_all_threads()
        return [t for t in threads if t.get("status") == status]
    
    def find_by_node(self, node_id: str) -> List[Dict]:
        """Find all threads a node has worked on"""
        threads = self._load_all_threads()
        results = []
        
        for thread in threads:
            for progress in thread.get("progress", []):
                if progress.get("node") == node_id:
                    results.append(thread)
                    break
        
        return results
    
    def find_by_time_range(self, start: float, end: float) -> List[Dict]:
        """Find threads created or active in time range"""
        threads = self._load_all_threads()
        results = []
        
        for thread in threads:
            created = thread.get("created_at", 0)
            if start <= created <= end:
                results.append(thread)
                continue
            
            # Check if any progress in time range
            for progress in thread.get("progress", []):
                if start <= progress.get("timestamp", 0) <= end:
                    results.append(thread)
                    break
        
        return results
    
    def find_related(self, thread_id: str, limit: int = 5) -> List[Dict]:
        """
        Find threads related to given thread
        Based on keyword overlap in intent/description
        """
        threads = self._load_all_threads()
        target = next((t for t in threads if t["id"] == thread_id), None)
        
        if not target:
            return []
        
        # Extract keywords from target
        target_text = f"{target.get('intent', '')} {target.get('description', '')}"
        target_keywords = set(re.findall(r'\w+', target_text.lower()))
        target_keywords = {w for w in target_keywords if len(w) > 3}
        
        # Score other threads by keyword overlap
        scored = []
        for thread in threads:
            if thread["id"] == thread_id:
                continue
            
            thread_text = f"{thread.get('intent', '')} {thread.get('description', '')}"
            thread_keywords = set(re.findall(r'\w+', thread_text.lower()))
            thread_keywords = {w for w in thread_keywords if len(w) > 3}
            
            overlap = len(target_keywords & thread_keywords)
            if overlap > 0:
                scored.append((overlap, thread))
        
        scored.sort(reverse=True)
        return [t for _, t in scored[:limit]]
    
    def get_statistics(self) -> Dict:
        """Get overall statistics about the Akashic Records"""
        threads = self._load_all_threads()
        
        stats = {
            "total_threads": len(threads),
            "by_status": defaultdict(int),
            "by_priority": defaultdict(int),
            "total_progress": 0,
            "active_nodes": set(),
            "total_contributions": 0,
            "oldest_thread": None,
            "newest_thread": None,
            "most_active_thread": None
        }
        
        oldest_time = float('inf')
        newest_time = 0
        max_progress = 0
        
        for thread in threads:
            stats["by_status"][thread.get("status", "unknown")] += 1
            stats["by_priority"][thread.get("priority", "normal")] += 1
            
            progress_count = len(thread.get("progress", []))
            stats["total_progress"] += progress_count
            
            if progress_count > max_progress:
                max_progress = progress_count
                stats["most_active_thread"] = thread
            
            created = thread.get("created_at", 0)
            if created < oldest_time:
                oldest_time = created
                stats["oldest_thread"] = thread
            if created > newest_time:
                newest_time = created
                stats["newest_thread"] = thread
            
            for progress in thread.get("progress", []):
                node = progress.get("node")
                if node:
                    stats["active_nodes"].add(node)
                    stats["total_contributions"] += 1
        
        stats["active_nodes"] = list(stats["active_nodes"])
        stats["by_status"] = dict(stats["by_status"])
        stats["by_priority"] = dict(stats["by_priority"])
        
        return stats
    
    def get_timeline(self, thread_id: str) -> List[Dict]:
        """Get complete timeline of a thread"""
        threads = self._load_all_threads()
        thread = next((t for t in threads if t["id"] == thread_id), None)
        
        if not thread:
            return []
        
        timeline = [{
            "event": "created",
            "timestamp": thread.get("created_at"),
            "details": f"Thread created: {thread.get('intent')}"
        }]
        
        for progress in thread.get("progress", []):
            timeline.append({
                "event": "progress",
                "timestamp": progress.get("timestamp"),
                "node": progress.get("node"),
                "step": progress.get("step"),
                "message": progress.get("message", "")[:100]
            })
        
        return sorted(timeline, key=lambda x: x.get("timestamp", 0))
    
    def get_knowledge_graph(self) -> Dict:
        """
        Build a knowledge graph of all threads
        Shows how concepts connect across threads
        """
        threads = self._load_all_threads()
        
        # Extract keywords from all threads
        keyword_threads = defaultdict(list)
        
        for thread in threads:
            text = f"{thread.get('intent', '')} {thread.get('description', '')}"
            keywords = set(re.findall(r'\w+', text.lower()))
            keywords = {w for w in keywords if len(w) > 4}
            
            for keyword in keywords:
                keyword_threads[keyword].append(thread["id"])
        
        # Find keywords that connect multiple threads
        connectors = {k: v for k, v in keyword_threads.items() if len(v) > 1}
        
        # Build graph
        graph = {
            "nodes": [{"id": t["id"], "intent": t.get("intent")} for t in threads],
            "edges": [],
            "keywords": connectors
        }
        
        # Create edges based on shared keywords
        for keyword, thread_ids in connectors.items():
            for i, tid1 in enumerate(thread_ids):
                for tid2 in thread_ids[i+1:]:
                    graph["edges"].append({
                        "source": tid1,
                        "target": tid2,
                        "keyword": keyword
                    })
        
        return graph
    
    def recommend_next(self, thread_id: str) -> List[Dict]:
        """
        Recommend what to work on next after completing a thread
        """
        related = self.find_related(thread_id, limit=10)
        
        # Prioritize active threads
        active = [t for t in related if t.get("status") == "active"]
        paused = [t for t in related if t.get("status") == "paused"]
        
        recommendations = []
        
        for thread in active[:3]:
            recommendations.append({
                "thread": thread,
                "reason": "Related active thread",
                "priority": "high"
            })
        
        for thread in paused[:3]:
            recommendations.append({
                "thread": thread,
                "reason": "Related paused thread ready to resume",
                "priority": "medium"
            })
        
        return recommendations
    
    def export_thread(self, thread_id: str, format: str = "markdown") -> str:
        """Export thread in readable format"""
        threads = self._load_all_threads()
        thread = next((t for t in threads if t["id"] == thread_id), None)
        
        if not thread:
            return "Thread not found"
        
        if format == "markdown":
            output = f"# {thread.get('intent')}\n\n"
            output += f"**ID:** {thread['id']}\n"
            output += f"**Status:** {thread.get('status')}\n"
            output += f"**Created:** {datetime.fromtimestamp(thread.get('created_at', 0))}\n"
            output += f"**Priority:** {thread.get('priority', 'normal')}\n\n"
            
            if thread.get('description'):
                output += f"## Description\n\n{thread['description']}\n\n"
            
            output += f"## Progress\n\n"
            output += f"Total steps: {len(thread.get('progress', []))}\n\n"
            
            for i, progress in enumerate(thread.get('progress', []), 1):
                ts = datetime.fromtimestamp(progress.get('timestamp', 0))
                node = progress.get('node', 'unknown')
                msg = progress.get('message', '')
                
                output += f"### Step {i} - {ts.strftime('%Y-%m-%d %H:%M')}\n"
                output += f"**Node:** {node}\n\n"
                output += f"{msg}\n\n"
            
            return output
        
        elif format == "json":
            return json.dumps(thread, indent=2)
        
        return "Unknown format"
    
    def query(self, query_str: str) -> List[Dict]:
        """
        Natural language query interface
        Examples:
          - "quantum" -> search for quantum
          - "status:active" -> filter by status
          - "node:droid_123" -> threads by node
          - "recent" -> threads from last 24h
        """
        query_str = query_str.strip().lower()
        
        # Check for special queries
        if query_str.startswith("status:"):
            status = query_str.split(":")[1]
            return self.find_by_status(status)
        
        if query_str.startswith("node:"):
            node_id = query_str.split(":")[1]
            return self.find_by_node(node_id)
        
        if query_str == "recent":
            start = time.time() - (24 * 3600)
            return self.find_by_time_range(start, time.time())
        
        if query_str == "stats":
            stats = self.get_statistics()
            return [{"type": "statistics", "data": stats}]
        
        # Default: text search
        return self.search(query_str)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("The Librarian - Akashic Records Query Interface")
        print("\nUsage:")
        print("  librarian.py search <query>")
        print("  librarian.py find <status|node|recent>")
        print("  librarian.py related <thread_id>")
        print("  librarian.py timeline <thread_id>")
        print("  librarian.py stats")
        print("  librarian.py export <thread_id> [format]")
        print("  librarian.py graph")
        sys.exit(1)
    
    lib = Librarian()
    command = sys.argv[1]
    
    if command == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = lib.search(query)
        print(f"\nFound {len(results)} threads:")
        for t in results:
            print(f"  • {t['id']}: {t.get('intent')}")
    
    elif command == "find":
        if len(sys.argv) < 3:
            print("Usage: librarian.py find <status|node:id|recent>")
            sys.exit(1)
        
        results = lib.query(sys.argv[2])
        print(f"\nFound {len(results)} threads:")
        for t in results:
            if t.get("type") == "statistics":
                stats = t["data"]
                print("\nStatistics:")
                print(f"  Total threads: {stats['total_threads']}")
                print(f"  By status: {stats['by_status']}")
                print(f"  Active nodes: {len(stats['active_nodes'])}")
            else:
                print(f"  • {t['id']}: {t.get('intent')}")
    
    elif command == "related":
        if len(sys.argv) < 3:
            print("Usage: librarian.py related <thread_id>")
            sys.exit(1)
        
        thread_id = sys.argv[2]
        related = lib.find_related(thread_id)
        print(f"\nThreads related to {thread_id}:")
        for t in related:
            print(f"  • {t['id']}: {t.get('intent')}")
    
    elif command == "timeline":
        if len(sys.argv) < 3:
            print("Usage: librarian.py timeline <thread_id>")
            sys.exit(1)
        
        thread_id = sys.argv[2]
        timeline = lib.get_timeline(thread_id)
        print(f"\nTimeline for {thread_id}:")
        for event in timeline:
            ts = datetime.fromtimestamp(event.get('timestamp', 0))
            print(f"  [{ts}] {event.get('event')}: {event.get('details', '')}")
    
    elif command == "stats":
        stats = lib.get_statistics()
        print("\nAkashic Records Statistics:")
        print(f"  Total threads: {stats['total_threads']}")
        print(f"  By status: {json.dumps(stats['by_status'], indent=4)}")
        print(f"  Total progress steps: {stats['total_progress']}")
        print(f"  Active nodes: {len(stats['active_nodes'])}")
        print(f"  Total contributions: {stats['total_contributions']}")
        
        if stats['oldest_thread']:
            print(f"\n  Oldest: {stats['oldest_thread'].get('intent')}")
        if stats['newest_thread']:
            print(f"  Newest: {stats['newest_thread'].get('intent')}")
        if stats['most_active_thread']:
            steps = len(stats['most_active_thread'].get('progress', []))
            print(f"  Most active: {stats['most_active_thread'].get('intent')} ({steps} steps)")
    
    elif command == "export":
        if len(sys.argv) < 3:
            print("Usage: librarian.py export <thread_id> [markdown|json]")
            sys.exit(1)
        
        thread_id = sys.argv[2]
        format = sys.argv[3] if len(sys.argv) > 3 else "markdown"
        output = lib.export_thread(thread_id, format)
        print(output)
    
    elif command == "graph":
        graph = lib.get_knowledge_graph()
        print(f"\nKnowledge Graph:")
        print(f"  Nodes: {len(graph['nodes'])}")
        print(f"  Edges: {len(graph['edges'])}")
        print(f"  Connecting keywords: {len(graph['keywords'])}")
        print(f"\n  Top keywords:")
        sorted_kw = sorted(graph['keywords'].items(), 
                          key=lambda x: len(x[1]), reverse=True)
        for kw, threads in sorted_kw[:10]:
            print(f"    {kw}: {len(threads)} threads")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
