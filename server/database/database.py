import sqlite3
import os
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Production-ready SQLite database manager with proper connection handling"""
    
    def __init__(self, db_path: str = "thesis_ai.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('student', 'supervisor', 'admin')),
                    disabled BOOLEAN DEFAULT FALSE,
                    supervisor_id TEXT,
                    assigned_students TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supervisor_id) REFERENCES users (username)
                )
            ''')
            
            # Theses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS theses (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed_by_ai', 'reviewed_by_supervisor', 'approved')),
                    ai_feedback_id TEXT,
                    supervisor_feedback_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES users (id),
                    FOREIGN KEY (ai_feedback_id) REFERENCES feedback (id),
                    FOREIGN KEY (supervisor_feedback_id) REFERENCES feedback (id)
                )
            ''')
            
            # Feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    thesis_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_ai_feedback BOOLEAN NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thesis_id) REFERENCES theses (id),
                    FOREIGN KEY (reviewer_id) REFERENCES users (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_theses_student_id ON theses(student_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_theses_status ON theses(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_thesis_id ON feedback(thesis_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_reviewer_id ON feedback(reviewer_id)')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def dict_from_row(self, row) -> Dict[str, Any]:
        """Convert sqlite3.Row to dict"""
        if row is None:
            return None
        return dict(row)
    
    def list_from_json(self, json_str: str) -> List[str]:
        """Convert JSON string to list"""
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return []
    
    def json_from_list(self, lst: List[str]) -> str:
        """Convert list to JSON string"""
        return json.dumps(lst) if lst else '[]'

class UserRepository:
    """Repository for user operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        # Generate ID if not provided
        if 'id' not in user_data:
            user_data['id'] = str(uuid.uuid4())
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, username, email, full_name, hashed_password, role, supervisor_id, assigned_students)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data['full_name'],
                user_data['hashed_password'],
                user_data['role'],
                user_data.get('supervisor_id'),
                self.db.json_from_list(user_data.get('assigned_students', []))
            ))
            conn.commit()
            return self.get_user_by_username(user_data['username'])
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row:
                user_dict = self.db.dict_from_row(row)
                user_dict['assigned_students'] = self.db.list_from_json(user_dict['assigned_students'])
                return user_dict
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                user_dict = self.db.dict_from_row(row)
                user_dict['assigned_students'] = self.db.list_from_json(user_dict['assigned_students'])
                return user_dict
            return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            rows = cursor.fetchall()
            users = []
            for row in rows:
                user_dict = self.db.dict_from_row(row)
                user_dict['assigned_students'] = self.db.list_from_json(user_dict['assigned_students'])
                users.append(user_dict)
            return users
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get users by role"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE role = ? ORDER BY full_name', (role,))
            rows = cursor.fetchall()
            users = []
            for row in rows:
                user_dict = self.db.dict_from_row(row)
                user_dict['assigned_students'] = self.db.list_from_json(user_dict['assigned_students'])
                users.append(user_dict)
            return users
    
    def update_user(self, username: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key == 'assigned_students':
                    set_clauses.append(f"{key} = ?")
                    values.append(self.db.json_from_list(value))
                elif key in ['username', 'email', 'full_name', 'hashed_password', 'role', 'supervisor_id', 'disabled']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return self.get_user_by_username(username)
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(username)
            
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE username = ?"
            cursor.execute(query, values)
            conn.commit()
            
            return self.get_user_by_username(username)
    
    def assign_supervisor(self, student_username: str, supervisor_username: str) -> bool:
        """Assign supervisor to student"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current supervisor
            cursor.execute('SELECT supervisor_id FROM users WHERE username = ?', (student_username,))
            current_supervisor = cursor.fetchone()
            
            # Remove student from previous supervisor's assigned_students
            if current_supervisor and current_supervisor['supervisor_id']:
                cursor.execute('SELECT assigned_students FROM users WHERE username = ?', (current_supervisor['supervisor_id'],))
                prev_supervisor = cursor.fetchone()
                if prev_supervisor:
                    assigned_students = self.db.list_from_json(prev_supervisor['assigned_students'])
                    if student_username in assigned_students:
                        assigned_students.remove(student_username)
                        cursor.execute('UPDATE users SET assigned_students = ? WHERE username = ?', 
                                     (self.db.json_from_list(assigned_students), current_supervisor['supervisor_id']))
            
            # Update student's supervisor
            cursor.execute('UPDATE users SET supervisor_id = ? WHERE username = ?', (supervisor_username, student_username))
            
            # Add student to new supervisor's assigned_students
            cursor.execute('SELECT assigned_students FROM users WHERE username = ?', (supervisor_username,))
            supervisor = cursor.fetchone()
            if supervisor:
                assigned_students = self.db.list_from_json(supervisor['assigned_students'])
                if student_username not in assigned_students:
                    assigned_students.append(student_username)
                    cursor.execute('UPDATE users SET assigned_students = ? WHERE username = ?', 
                                 (self.db.json_from_list(assigned_students), supervisor_username))
            
            conn.commit()
            return True
    
    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new user (alias for create_user)"""
        return self.create_user(user_data)
    
    def add_assigned_student(self, supervisor_id: str, student_username: str) -> bool:
        """Add a student to supervisor's assigned students"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT assigned_students FROM users WHERE id = ?', (supervisor_id,))
            supervisor = cursor.fetchone()
            if supervisor:
                assigned_students = self.db.list_from_json(supervisor['assigned_students'])
                if student_username not in assigned_students:
                    assigned_students.append(student_username)
                    cursor.execute('UPDATE users SET assigned_students = ? WHERE id = ?', 
                                 (self.db.json_from_list(assigned_students), supervisor_id))
                    conn.commit()
                    return True
            return False
    
    def remove_assigned_student(self, supervisor_id: str, student_username: str) -> bool:
        """Remove a student from supervisor's assigned students"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT assigned_students FROM users WHERE id = ?', (supervisor_id,))
            supervisor = cursor.fetchone()
            if supervisor:
                assigned_students = self.db.list_from_json(supervisor['assigned_students'])
                if student_username in assigned_students:
                    assigned_students.remove(student_username)
                    cursor.execute('UPDATE users SET assigned_students = ? WHERE id = ?', 
                                 (self.db.json_from_list(assigned_students), supervisor_id))
                    conn.commit()
                    return True
            return False
    
    def update_student_supervisor(self, student_id: str, supervisor_username: str) -> bool:
        """Update student's supervisor"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET supervisor_id = ? WHERE id = ?', (supervisor_username, student_id))
            conn.commit()
            return True
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            if row:
                user_dict = self.db.dict_from_row(row)
                user_dict['assigned_students'] = self.db.list_from_json(user_dict['assigned_students'])
                return user_dict
            return None
    
    def get_assigned_students(self, supervisor_id: str) -> List[Dict[str, Any]]:
        """Get students assigned to a supervisor"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE supervisor_id = ? AND role = "student" ORDER BY full_name', (supervisor_id,))
            rows = cursor.fetchall()
            students = []
            for row in rows:
                user_dict = self.db.dict_from_row(row)
                user_dict['assigned_students'] = self.db.list_from_json(user_dict['assigned_students'])
                students.append(user_dict)
            return students
    
    def update_user_supervisor(self, student_id: str, supervisor_id: str) -> bool:
        """Update user's supervisor"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET supervisor_id = ? WHERE id = ?', (supervisor_id, student_id))
            conn.commit()
            return True
    
    def delete_user(self, username: str) -> bool:
        """Delete a user by username"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            return cursor.rowcount > 0
    
    def update_user(self, username: str, update_data: dict) -> bool:
        """Update user details"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                if value is not None:  # Only update non-None values
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False  # Nothing to update
            
            values.append(username)
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE username = ?"
            
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

class ThesisRepository:
    """Repository for thesis operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_thesis(self, thesis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new thesis"""
        # Generate ID if not provided
        if 'id' not in thesis_data:
            thesis_data['id'] = str(uuid.uuid4())
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO theses (id, student_id, filename, filepath, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                thesis_data['id'],
                thesis_data['student_id'],
                thesis_data['filename'],
                thesis_data['filepath'],
                thesis_data.get('status', 'pending')
            ))
            conn.commit()
            return self.get_thesis_by_id(thesis_data['id'])
    
    def get_thesis_by_id(self, thesis_id: str) -> Optional[Dict[str, Any]]:
        """Get thesis by ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM theses WHERE id = ?', (thesis_id,))
            row = cursor.fetchone()
            return self.db.dict_from_row(row) if row else None
    
    def get_theses_by_student_id(self, student_id: str) -> List[Dict[str, Any]]:
        """Get theses by student ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM theses WHERE student_id = ? ORDER BY upload_date DESC', (student_id,))
            rows = cursor.fetchall()
            return [self.db.dict_from_row(row) for row in rows]
    
    def get_theses_by_supervisor(self, supervisor_username: str) -> List[Dict[str, Any]]:
        """Get theses assigned to a supervisor"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.* FROM theses t
                JOIN users u ON t.student_id = u.id
                WHERE u.supervisor_id = ?
                ORDER BY t.upload_date DESC
            ''', (supervisor_username,))
            rows = cursor.fetchall()
            return [self.db.dict_from_row(row) for row in rows]
    
    def get_all_theses(self) -> List[Dict[str, Any]]:
        """Get all theses"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM theses ORDER BY upload_date DESC')
            rows = cursor.fetchall()
            return [self.db.dict_from_row(row) for row in rows]
    
    def update_thesis(self, thesis_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update thesis"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['status', 'ai_feedback_id', 'supervisor_feedback_id']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return self.get_thesis_by_id(thesis_id)
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(thesis_id)
            
            query = f"UPDATE theses SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            
            return self.get_thesis_by_id(thesis_id)
    
    def add_thesis(self, thesis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new thesis (alias for create_thesis)"""
        return self.create_thesis(thesis_data)
    
    def update_thesis_status(self, thesis_id: str, status: str, feedback_id: str = None) -> bool:
        """Update thesis status with optional feedback ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if feedback_id:
                if status == "reviewed_by_ai":
                    cursor.execute('UPDATE theses SET status = ?, ai_feedback_id = ? WHERE id = ?', 
                                 (status, feedback_id, thesis_id))
                elif status == "reviewed_by_supervisor":
                    cursor.execute('UPDATE theses SET status = ?, supervisor_feedback_id = ? WHERE id = ?', 
                                 (status, feedback_id, thesis_id))
                else:
                    cursor.execute('UPDATE theses SET status = ? WHERE id = ?', (status, thesis_id))
            else:
                cursor.execute('UPDATE theses SET status = ? WHERE id = ?', (status, thesis_id))
            conn.commit()
            return True
    
    def get_theses_by_student(self, student_id: str) -> List[Dict[str, Any]]:
        """Get theses by student ID (alias for get_theses_by_student_id)"""
        return self.get_theses_by_student_id(student_id)
    
    def get_theses_by_supervisor(self, supervisor_id: str) -> List[Dict[str, Any]]:
        """Get theses assigned to a supervisor by supervisor ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.* FROM theses t
                JOIN users u ON t.student_id = u.id
                WHERE u.supervisor_id = ?
                ORDER BY t.upload_date DESC
            ''', (supervisor_id,))
            rows = cursor.fetchall()
            return [self.db.dict_from_row(row) for row in rows]
    
    def update_thesis_ai_feedback(self, thesis_id: str, feedback_id: str) -> bool:
        """Update thesis AI feedback ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE theses SET ai_feedback_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (feedback_id, thesis_id))
            conn.commit()
            return True
    
    def update_thesis_supervisor_feedback(self, thesis_id: str, feedback_id: str) -> bool:
        """Update thesis supervisor feedback ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE theses SET supervisor_feedback_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (feedback_id, thesis_id))
            conn.commit()
            return True

class FeedbackRepository:
    """Repository for feedback operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new feedback"""
        # Generate ID if not provided
        if 'id' not in feedback_data:
            feedback_data['id'] = str(uuid.uuid4())
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (id, thesis_id, reviewer_id, content, is_ai_feedback)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                feedback_data['id'],
                feedback_data['thesis_id'],
                feedback_data['reviewer_id'],
                feedback_data['content'],
                feedback_data['is_ai_feedback']
            ))
            conn.commit()
            return self.get_feedback_by_id(feedback_data['id'])
    
    def get_feedback_by_id(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        """Get feedback by ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM feedback WHERE id = ?', (feedback_id,))
            row = cursor.fetchone()
            return self.db.dict_from_row(row) if row else None
    
    def get_feedback_by_thesis_id(self, thesis_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a thesis"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM feedback WHERE thesis_id = ? ORDER BY created_at DESC', (thesis_id,))
            rows = cursor.fetchall()
            return [self.db.dict_from_row(row) for row in rows]
    
    def get_ai_feedback_by_thesis_id(self, thesis_id: str) -> Optional[Dict[str, Any]]:
        """Get AI feedback for a thesis"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM feedback WHERE thesis_id = ? AND is_ai_feedback = TRUE ORDER BY created_at DESC LIMIT 1', (thesis_id,))
            row = cursor.fetchone()
            return self.db.dict_from_row(row) if row else None
    
    def get_supervisor_feedback_by_thesis_id(self, thesis_id: str) -> Optional[Dict[str, Any]]:
        """Get supervisor feedback for a thesis"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM feedback WHERE thesis_id = ? AND is_ai_feedback = FALSE ORDER BY created_at DESC LIMIT 1', (thesis_id,))
            row = cursor.fetchone()
            return self.db.dict_from_row(row) if row else None
    
    def add_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new feedback (alias for create_feedback)"""
        return self.create_feedback(feedback_data)
    
    def get_feedback_by_reviewer(self, reviewer_id: str) -> List[Dict[str, Any]]:
        """Get feedback by reviewer ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM feedback WHERE reviewer_id = ? ORDER BY created_at DESC', (reviewer_id,))
            rows = cursor.fetchall()
            return [self.db.dict_from_row(row) for row in rows]
    
    def get_feedback_by_thesis_and_reviewer(self, thesis_id: str, reviewer_type: str) -> Optional[Dict[str, Any]]:
        """Get feedback by thesis ID and reviewer type (ai or supervisor)"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if reviewer_type == "ai":
                cursor.execute('SELECT * FROM feedback WHERE thesis_id = ? AND is_ai_feedback = TRUE ORDER BY created_at DESC LIMIT 1', (thesis_id,))
            elif reviewer_type == "supervisor":
                cursor.execute('SELECT * FROM feedback WHERE thesis_id = ? AND is_ai_feedback = FALSE ORDER BY created_at DESC LIMIT 1', (thesis_id,))
            else:
                return None
            row = cursor.fetchone()
            return self.db.dict_from_row(row) if row else None

# Global database instance
db_manager = DatabaseManager()
user_repo = UserRepository(db_manager)
thesis_repo = ThesisRepository(db_manager)
feedback_repo = FeedbackRepository(db_manager) 