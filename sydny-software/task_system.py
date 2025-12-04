"""
Task Management System for SYDNY
Handles creation, storage, and management of user tasks
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Task data file location
TASK_FILE = Path(__file__).parent / "sydny_tasks.json"

class TaskManager:
    """Manages tasks with JSON persistence"""
    
    def __init__(self):
        self.tasks = []
        self.load_tasks()
    
    def load_tasks(self):
        """Load tasks from JSON file"""
        try:
            if TASK_FILE.exists():
                with open(TASK_FILE, 'r') as f:
                    data = json.load(f)
                    self.tasks = data.get('tasks', [])
                    print(f"Loaded {len(self.tasks)} tasks from {TASK_FILE}")
            else:
                print(f"No task file found, starting fresh")
                self.tasks = []
        except Exception as e:
            print(f"Error loading tasks: {e}")
            self.tasks = []
    
    def save_tasks(self):
        """Save tasks to JSON file"""
        try:
            data = {
                'tasks': self.tasks,
                'last_updated': datetime.now().isoformat()
            }
            with open(TASK_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving tasks: {e}")
            return False
        
    def add_task(self, description, priority="normal"):
        """
        Add a new task
        Args:
            description: Task description
            priority: low, normal, or high
        Returns: Success message
        """
        try:
            # Validate inputs
            if not description or not isinstance(description, str):
                return "Invalid task description"
            
            if priority not in ["low", "normal", "high"]:
                priority = "normal"
            
            # Create task object
            task = {
                'id': len(self.tasks) + 1,
                'description': description.strip(),
                'priority': priority,
                'completed': False,
                'created': datetime.now().isoformat(),
                'completed_at': None
            }
            
            self.tasks.append(task)
            self.save_tasks()
            
            return f"Added task: {description}"
        
        except Exception as e:
            print(f"Error adding task: {e}")
            return "Error adding task"
        
    def list_tasks(self, show_completed=False):
        """
        Get list of tasks
        Args:
            show_completed: Include completed tasks
        Returns: List of task strings
        """
        try:
            if not self.tasks:
                return []
            
            # Filter tasks
            if show_completed:
                filtered = self.tasks
            else:
                filtered = [t for t in self.tasks if not t['completed']]
            
            if not filtered:
                return []
            
            # Format tasks for display
            task_list = []
            for task in filtered:
                status = "✓" if task['completed'] else "○"
                priority_marker = ""
                if task['priority'] == 'high':
                    priority_marker = "! "
                elif task['priority'] == 'low':
                    priority_marker = "- "
                
                task_str = f"{status} [{task['id']}] {priority_marker}{task['description']}"
                task_list.append(task_str)
            
            return task_list
        
        except Exception as e:
            print(f"Error listing tasks: {e}")
            return []
        
    def complete_task(self, task_id):
        """
        Mark a task as completed
        Args:
            task_id: ID of task to complete
        Returns: Success message
        """
        try:
            # Find task by ID
            task = None
            for t in self.tasks:
                if t['id'] == task_id:
                    task = t
                    break
            
            if not task:
                return f"Task {task_id} not found"
            
            if task['completed']:
                return f"Task {task_id} is already completed"
            
            # Mark as completed
            task['completed'] = True
            task['completed_at'] = datetime.now().isoformat()
            self.save_tasks()
            
            return f"Completed task: {task['description']}"
        
        except Exception as e:
            print(f"Error completing task: {e}")
            return "Error completing task"
        
    def delete_task(self, task_id):
        """
        Delete a task
        Args:
            task_id: ID of task to delete
        Returns: Success message
        """
        try:
            # Find task by ID
            task = None
            for t in self.tasks:
                if t['id'] == task_id:
                    task = t
                    break
            
            if not task:
                return f"Task {task_id} not found"
            
            description = task['description']
            self.tasks.remove(task)
            
            # Renumber remaining tasks
            for idx, t in enumerate(self.tasks, 1):
                t['id'] = idx
            
            self.save_tasks()
            
            return f"Deleted task: {description}"
        
        except Exception as e:
            print(f"Error deleting task: {e}")
            return "Error deleting task"

    def get_task_count(self, include_completed=False):
        """
        Get count of tasks
        Args:
            include_completed: Include completed tasks in count
        Returns: Number of tasks
        """
        try:
            if include_completed:
                return len(self.tasks)
            else:
                return len([t for t in self.tasks if not t['completed']])
        except Exception as e:
            print(f"Error getting task count: {e}")
            return 0

    # WE WILL GET BACK TO THIS LATER #
    # def set_priority(self, task_id, priority):
    #     """
    #     Set task priority
    #     Args:
    #         task_id: ID of task
    #         priority: low, normal, or high
    #     Returns: Success message
    #     """
    #     try:
    #         # Validate priority
    #         if priority not in ["low", "normal", "high"]:
    #             return "Priority must be low, normal, or high"
            
    #         # Find task by ID
    #         task = None
    #         for t in self.tasks:
    #             if t['id'] == task_id:
    #                 task = t
    #                 break
            
    #         if not task:
    #             return f"Task {task_id} not found"
            
    #         task['priority'] = priority
    #         self.save_tasks()
            
    #         return f"Set task {task_id} priority to {priority}"
        
    #     except Exception as e:
    #         print(f"Error setting priority: {e}")
    #         return "Error setting priority"
    
# ============================================================================
# TESTING (can be run directly)
# ============================================================================

if __name__ == '__main__':
    print("Testing Task System...\n")
    
    # Create manager
    tm = TaskManager()
    
    # Add some tasks
    print(tm.add_task("Buy groceries", "normal"))
    print(tm.add_task("Finish SYDNY project", "high"))
    print(tm.add_task("Call mom", "low"))
    
    print("\n--- All Tasks ---")
    for task in tm.list_tasks():
        print(task)
    
    print("\n--- Complete Task 2 ---")
    print(tm.complete_task(2))
    
    print("\n--- Active Tasks ---")
    for task in tm.list_tasks():
        print(task)
    
    print("\n--- All Tasks (including completed) ---")
    for task in tm.list_tasks(show_completed=True):
        print(task)
    
    print(f"\nTask count: {tm.get_task_count()} active, {tm.get_task_count(True)} total")

































































