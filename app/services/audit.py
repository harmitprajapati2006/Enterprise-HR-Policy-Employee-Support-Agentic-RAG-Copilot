import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings


class AuditService:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.AUDIT_DB_PATH
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source_used TEXT NOT NULL,
                    kb_grade TEXT,
                    web_grade TEXT,
                    retry_count INTEGER DEFAULT 0,
                    citations_json TEXT,
                    trace_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def log_interaction(
        self,
        question: str,
        answer: str,
        source_used: str,
        kb_grade: Optional[str] = "",
        web_grade: Optional[str] = "",
        retry_count: int = 0,
        citations: Optional[List[Dict[str, Any]]] = None,
        trace: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = "default",
    ) -> int:
        """Records an agent interaction into the audit log."""
        citations_json = json.dumps(citations or [])
        trace_json = json.dumps(trace or [])
        created_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_logs (
                    session_id, question, answer, source_used, 
                    kb_grade, web_grade, retry_count, 
                    citations_json, trace_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    question,
                    answer,
                    source_used,
                    kb_grade or "",
                    web_grade or "",
                    retry_count,
                    citations_json,
                    trace_json,
                    created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_logs(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieves recent audit logs ordered by creation time descending."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, session_id, question, answer, source_used,
                       kb_grade, web_grade, retry_count, citations_json,
                       trace_json, created_at
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                item = dict(row)
                try:
                    item["citations"] = json.loads(item.get("citations_json") or "[]")
                except Exception:
                    item["citations"] = []
                try:
                    item["trace"] = json.loads(item.get("trace_json") or "[]")
                except Exception:
                    item["trace"] = []
                logs.append(item)
            return logs

    def get_stats(self) -> Dict[str, Any]:
        """Calculates operational metrics across all historical agent requests."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
            if total == 0:
                return {
                    "total_queries": 0,
                    "private_kb_count": 0,
                    "web_search_count": 0,
                    "direct_count": 0,
                    "kb_resolution_rate": "0%",
                }

            sources = conn.execute(
                "SELECT source_used, COUNT(*) as cnt FROM audit_logs GROUP BY source_used"
            ).fetchall()
            source_map = {row["source_used"]: row["cnt"] for row in sources}
            
            kb_cnt = source_map.get("private_kb", 0)
            web_cnt = source_map.get("web_search", 0)
            direct_cnt = source_map.get("direct", 0)
            kb_rate = f"{(kb_cnt / total * 100):.1f}%"

            return {
                "total_queries": total,
                "private_kb_count": kb_cnt,
                "web_search_count": web_cnt,
                "direct_count": direct_cnt,
                "kb_resolution_rate": kb_rate,
            }


audit_service = AuditService()
