"""
Audit Logger for compliance audit trail
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AuditEntry:
    """Audit trail entry"""
    entry_id: str
    timestamp: datetime
    actor: str
    action: str
    resource: str
    details: Dict[str, Any]

class AuditLogger:
    """Audit logger for compliance trails"""
    
    def __init__(self):
        self.audit_trail: List[AuditEntry] = []
    
    def log_action(
        self,
        actor: str,
        action: str, 
        resource: str,
        details: Dict[str, Any]
    ):
        """Log an auditable action"""
        entry = AuditEntry(
            entry_id=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            actor=actor,
            action=action,
            resource=resource,
            details=details
        )
        
        self.audit_trail.append(entry)
        logger.info(f"Audit: {actor} performed {action} on {resource}")
    
    def get_audit_trail(self, resource: str = None) -> List[AuditEntry]:
        """Get audit trail entries"""
        if resource:
            return [e for e in self.audit_trail if e.resource == resource]
        return self.audit_trail