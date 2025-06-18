#!/usr/bin/env python3
"""
ultimate_agent/storage/database/migrations/__init__.py
Database management and data persistence
"""

import os
import json
import time
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except Exception:  # pragma: no cover - optional dependency
    create_engine = None

    class Dummy:
        def __init__(self, *args, **kwargs):
            pass

    Column = Integer = String = Float = Boolean = DateTime = Text = JSON = Dummy

    def declarative_base():
        class Base:
            metadata = type('Meta', (), {'create_all': lambda *a, **k: None})
        return Base

    def sessionmaker(*args, **kwargs):
        def factory(**kw):
            class Session:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
                def add(self, *a, **k):
                    pass
                def commit(self):
                    pass
                def rollback(self):
                    pass
                def close(self):
                    pass
            return Session()
        return factory

from contextlib import contextmanager

# If SQLAlchemy is unavailable, provide dummy DatabaseManager and skip models
if create_engine is None:
    Base = object

    class DatabaseManager:
        def __init__(self, *args, **kwargs):
            self.session = None

        def init_database(self):
            pass

        @contextmanager
        def session_scope(self):
            yield None

else:
    # Database Models
    Base = declarative_base()


class TaskRecord(Base):
    """Task execution records"""
    __tablename__ = 'task_records'
    
    id = Column(String, primary_key=True)
    task_id = Column(String, unique=True)
    task_type = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)
    success = Column(Boolean)
    reward = Column(Float)
    ai_result = Column(JSON)
    blockchain_tx = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceMetric(Base):
    """System performance metrics"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    gpu_percent = Column(Float)
    network_io = Column(Float)
    task_count = Column(Integer)
    efficiency_score = Column(Float)


class EarningsRecord(Base):
    """Blockchain earnings tracking"""
    __tablename__ = 'earnings'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    amount = Column(Float)
    currency = Column(String, default='ETH')
    task_id = Column(String)
    transaction_hash = Column(String)
    block_number = Column(Integer)


class TaskExecution(Base):
    """Enhanced task execution tracking"""
    __tablename__ = 'task_executions_enhanced'
    
    id = Column(String, primary_key=True)
    task_id = Column(String)
    task_type = Column(String)
    status = Column(String)
    progress = Column(Float)
    
    assigned_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    config = Column(JSON)
    result = Column(JSON)
    error_message = Column(Text)
    
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    duration = Column(Float)


class AITrainingRecord(Base):
    """AI training session tracking"""
    __tablename__ = 'ai_training_sessions'
    
    id = Column(String, primary_key=True)
    session_id = Column(String)
    model_type = Column(String)
    training_type = Column(String)
    epochs = Column(Integer)
    final_loss = Column(Float)
    accuracy = Column(Float)
    device_used = Column(String)
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentConfiguration(Base):
    """Agent configuration history"""
    __tablename__ = 'agent_configurations'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String)
    config_value = Column(Text)
    section = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(String)


class DatabaseManager:
    """Manages database operations and data persistence"""
    
    def __init__(self, db_path: str = "ultimate_agent.db"):
        self.db_path = db_path
        self.engine = None
        self.session_factory = None
        self.stats_file = "ultimate_stats.json"
        
        self.init_database()
    
    def init_database(self):
        """Initialize database connection and create tables"""
        try:
            # Create SQLAlchemy engine
            self.engine = create_engine(f'sqlite:///{self.db_path}')
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            
            print(f"💾 Database initialized: {self.db_path}")
            
            # Run initial migrations if needed
            self._run_migrations()
            
        except Exception as e:
            print(f"⚠️ Database initialization warning: {e}")
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _run_migrations(self):
        """Run database migrations"""
        try:
            with self.get_session() as session:
                # Check if we need to run any migrations
                # This is a placeholder for actual migration logic
                pass
        except Exception as e:
            print(f"⚠️ Migration warning: {e}")
    
    def save_task_record(self, task_data: Dict[str, Any]) -> bool:
        """Save task execution record"""
        try:
            with self.get_session() as session:
                task_record = TaskRecord(
                    id=task_data.get('id', str(time.time())),
                    task_id=task_data['task_id'],
                    task_type=task_data['task_type'],
                    start_time=task_data.get('start_time'),
                    end_time=task_data.get('end_time'),
                    duration=task_data.get('duration', 0),
                    success=task_data.get('success', False),
                    reward=task_data.get('reward', 0),
                    ai_result=task_data.get('ai_result'),
                    blockchain_tx=task_data.get('blockchain_tx')
                )
                session.add(task_record)
                
            return True
        except Exception as e:
            print(f"❌ Failed to save task record: {e}")
            return False
    
    def save_ai_training_record(self, training_data: Dict[str, Any]) -> bool:
        """Save AI training session record"""
        try:
            with self.get_session() as session:
                training_record = AITrainingRecord(
                    id=training_data.get('id', str(time.time())),
                    session_id=training_data['session_id'],
                    model_type=training_data['model_type'],
                    training_type=training_data.get('training_type', 'standard'),
                    epochs=training_data.get('epochs', 0),
                    final_loss=training_data.get('final_loss', 0),
                    accuracy=training_data.get('accuracy', 0),
                    device_used=training_data.get('device_used', 'cpu'),
                    duration=training_data.get('duration', 0)
                )
                session.add(training_record)
                
            return True
        except Exception as e:
            print(f"❌ Failed to save AI training record: {e}")
            return False
    
    def save_performance_metric(self, metrics: Dict[str, Any]) -> bool:
        """Save system performance metrics"""
        try:
            with self.get_session() as session:
                metric_record = PerformanceMetric(
                    timestamp=datetime.now(),
                    cpu_percent=metrics.get('cpu_percent', 0),
                    memory_percent=metrics.get('memory_percent', 0),
                    gpu_percent=metrics.get('gpu_percent', 0),
                    network_io=metrics.get('network_io', 0),
                    task_count=metrics.get('task_count', 0),
                    efficiency_score=metrics.get('efficiency_score', 0)
                )
                session.add(metric_record)
                
            return True
        except Exception as e:
            print(f"❌ Failed to save performance metric: {e}")
            return False
    
    def save_earnings_record(self, earnings: Dict[str, Any]) -> bool:
        """Save blockchain earnings record"""
        try:
            with self.get_session() as session:
                earnings_record = EarningsRecord(
                    timestamp=datetime.now(),
                    amount=earnings['amount'],
                    currency=earnings.get('currency', 'ETH'),
                    task_id=earnings.get('task_id'),
                    transaction_hash=earnings.get('transaction_hash'),
                    block_number=earnings.get('block_number')
                )
                session.add(earnings_record)
                
            return True
        except Exception as e:
            print(f"❌ Failed to save earnings record: {e}")
            return False
    
    def get_task_records(self, limit: int = 100, task_type: str = None) -> List[Dict]:
        """Get task execution records"""
        try:
            with self.get_session() as session:
                query = session.query(TaskRecord)
                
                if task_type:
                    query = query.filter(TaskRecord.task_type == task_type)
                
                records = query.order_by(TaskRecord.created_at.desc()).limit(limit).all()
                
                return [
                    {
                        'id': record.id,
                        'task_id': record.task_id,
                        'task_type': record.task_type,
                        'start_time': record.start_time.isoformat() if record.start_time else None,
                        'end_time': record.end_time.isoformat() if record.end_time else None,
                        'duration': record.duration,
                        'success': record.success,
                        'reward': record.reward,
                        'ai_result': record.ai_result,
                        'blockchain_tx': record.blockchain_tx,
                        'created_at': record.created_at.isoformat()
                    }
                    for record in records
                ]
        except Exception as e:
            print(f"❌ Failed to get task records: {e}")
            return []
    
    def get_performance_metrics(self, hours: int = 24) -> List[Dict]:
        """Get recent performance metrics"""
        try:
            with self.get_session() as session:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                records = session.query(PerformanceMetric).filter(
                    PerformanceMetric.timestamp >= cutoff_time
                ).order_by(PerformanceMetric.timestamp.desc()).all()
                
                return [
                    {
                        'timestamp': record.timestamp.isoformat(),
                        'cpu_percent': record.cpu_percent,
                        'memory_percent': record.memory_percent,
                        'gpu_percent': record.gpu_percent,
                        'network_io': record.network_io,
                        'task_count': record.task_count,
                        'efficiency_score': record.efficiency_score
                    }
                    for record in records
                ]
        except Exception as e:
            print(f"❌ Failed to get performance metrics: {e}")
            return []
    
    def get_earnings_summary(self) -> Dict[str, Any]:
        """Get earnings summary"""
        try:
            with self.get_session() as session:
                records = session.query(EarningsRecord).all()
                
                # Group by currency
                currency_totals = {}
                total_transactions = len(records)
                
                for record in records:
                    currency = record.currency or 'ETH'
                    if currency not in currency_totals:
                        currency_totals[currency] = 0
                    currency_totals[currency] += record.amount or 0
                
                return {
                    'total_transactions': total_transactions,
                    'currency_totals': currency_totals,
                    'total_eth_equivalent': currency_totals.get('ETH', 0),
                    'last_earning': records[-1].timestamp.isoformat() if records else None
                }
        except Exception as e:
            print(f"❌ Failed to get earnings summary: {e}")
            return {}
    
    def get_ai_training_summary(self) -> Dict[str, Any]:
        """Get AI training session summary"""
        try:
            with self.get_session() as session:
                records = session.query(AITrainingRecord).all()
                
                if not records:
                    return {}
                
                # Calculate statistics
                total_sessions = len(records)
                total_epochs = sum(record.epochs or 0 for record in records)
                avg_accuracy = sum(record.accuracy or 0 for record in records) / total_sessions
                total_duration = sum(record.duration or 0 for record in records)
                
                # Group by model type
                model_types = {}
                for record in records:
                    model_type = record.model_type or 'unknown'
                    if model_type not in model_types:
                        model_types[model_type] = 0
                    model_types[model_type] += 1
                
                return {
                    'total_sessions': total_sessions,
                    'total_epochs': total_epochs,
                    'average_accuracy': avg_accuracy,
                    'total_duration_hours': total_duration / 3600,
                    'model_type_distribution': model_types,
                    'gpu_usage_percentage': len([r for r in records if r.device_used == 'gpu']) / total_sessions * 100
                }
        except Exception as e:
            print(f"❌ Failed to get AI training summary: {e}")
            return {}
    
    def load_agent_stats(self) -> Dict[str, Any]:
        """Load agent statistics from file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load stats: {e}")
        
        return {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_earnings": 0.0,
            "start_time": time.time()
        }
    
    def save_agent_stats(self, stats: Dict[str, Any]) -> bool:
        """Save agent statistics to file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Failed to save stats: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"💾 Database backed up to {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            import shutil
            
            # Close current connections
            if self.engine:
                self.engine.dispose()
            
            # Restore backup
            shutil.copy2(backup_path, self.db_path)
            
            # Reinitialize
            self.init_database()
            
            print(f"✅ Database restored from {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Database restore failed: {e}")
            return False
    
    def vacuum_database(self) -> bool:
        """Optimize database by running VACUUM"""
        try:
            # Use raw SQLite connection for VACUUM
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()
            
            print("🗂️ Database vacuumed and optimized")
            return True
        except Exception as e:
            print(f"❌ Database vacuum failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_session() as session:
                stats = {
                    'task_records': session.query(TaskRecord).count(),
                    'performance_metrics': session.query(PerformanceMetric).count(),
                    'earnings_records': session.query(EarningsRecord).count(),
                    'ai_training_records': session.query(AITrainingRecord).count(),
                    'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0,
                    'tables': ['task_records', 'performance_metrics', 'earnings', 'task_executions_enhanced', 'ai_training_sessions']
                }
                
                return stats
        except Exception as e:
            print(f"❌ Failed to get database stats: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 30) -> Dict[str, int]:
        """Clean up old records to save space"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cleanup_count = {}
            
            with self.get_session() as session:
                # Clean old performance metrics
                old_metrics = session.query(PerformanceMetric).filter(
                    PerformanceMetric.timestamp < cutoff_date
                ).count()
                
                session.query(PerformanceMetric).filter(
                    PerformanceMetric.timestamp < cutoff_date
                ).delete()
                
                cleanup_count['performance_metrics'] = old_metrics
                
                # Keep all task records and earnings (they're important)
                # Only clean up old training records if there are too many
                training_count = session.query(AITrainingRecord).count()
                if training_count > 1000:
                    old_training = session.query(AITrainingRecord).filter(
                        AITrainingRecord.created_at < cutoff_date
                    ).count()
                    
                    # Keep newest 1000 training records
                    subquery = session.query(AITrainingRecord.id).order_by(
                        AITrainingRecord.created_at.desc()
                    ).limit(1000).subquery()
                    
                    session.query(AITrainingRecord).filter(
                        ~AITrainingRecord.id.in_(subquery)
                    ).delete(synchronize_session=False)
                    
                    cleanup_count['ai_training_records'] = old_training
            
            print(f"🗑️ Cleaned up old records: {cleanup_count}")
            return cleanup_count
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        try:
            if self.engine:
                self.engine.dispose()
            print("💾 Database connection closed")
        except Exception as e:
            print(f"⚠️ Database close warning: {e}")
