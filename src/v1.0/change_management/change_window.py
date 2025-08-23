"""
Change Window Manager

Manages maintenance windows and change scheduling.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ChangeWindowType(Enum):
    """Types of change windows"""
    ROUTINE = "routine"
    EXTENDED = "extended"
    EMERGENCY = "emergency"

@dataclass
class ChangeWindow:
    """Represents a change window"""
    window_id: str
    name: str
    start_time: datetime
    end_time: datetime
    window_type: ChangeWindowType
    allowed_changes: List[str]
    max_concurrent_changes: int
    active_changes: List[str] = None

class ChangeWindowManager:
    """Manages change windows and scheduling"""
    
    def __init__(self):
        self.change_windows: Dict[str, ChangeWindow] = {}
        self.scheduled_changes: Dict[str, Dict[str, Any]] = {}
    
    def schedule_change_window(
        self,
        name: str,
        start_time: datetime,
        duration_hours: int,
        window_type: ChangeWindowType,
        allowed_changes: List[str] = None,
        max_concurrent: int = 3
    ) -> ChangeWindow:
        """Schedule a new change window"""
        
        window_id = f"window_{name}_{start_time.strftime('%Y%m%d_%H%M')}"
        
        window = ChangeWindow(
            window_id=window_id,
            name=name,
            start_time=start_time,
            end_time=start_time + timedelta(hours=duration_hours),
            window_type=window_type,
            allowed_changes=allowed_changes or [],
            max_concurrent_changes=max_concurrent,
            active_changes=[]
        )
        
        self.change_windows[window_id] = window
        logger.info(f"Scheduled change window: {name} from {start_time} to {window.end_time}")
        
        return window
    
    def is_change_allowed(
        self,
        change_type: str,
        scheduled_time: datetime = None
    ) -> Dict[str, Any]:
        """Check if a change is allowed at the given time"""
        
        if scheduled_time is None:
            scheduled_time = datetime.now()
        
        # Find applicable change windows
        applicable_windows = []
        for window in self.change_windows.values():
            if (window.start_time <= scheduled_time <= window.end_time and
                (not window.allowed_changes or change_type in window.allowed_changes)):
                applicable_windows.append(window)
        
        if not applicable_windows:
            return {
                "allowed": False,
                "reason": "No applicable change window found",
                "next_window": self._find_next_window(change_type)
            }
        
        # Check capacity
        best_window = min(applicable_windows, key=lambda w: len(w.active_changes or []))
        
        if len(best_window.active_changes or []) >= best_window.max_concurrent_changes:
            return {
                "allowed": False,
                "reason": "Change window at capacity",
                "window": best_window.window_id,
                "next_window": self._find_next_window(change_type)
            }
        
        return {
            "allowed": True,
            "window": best_window.window_id,
            "window_name": best_window.name
        }
    
    def _find_next_window(self, change_type: str) -> Optional[Dict[str, Any]]:
        """Find the next available change window for a change type"""
        
        now = datetime.now()
        future_windows = [
            w for w in self.change_windows.values()
            if w.start_time > now and (not w.allowed_changes or change_type in w.allowed_changes)
        ]
        
        if future_windows:
            next_window = min(future_windows, key=lambda w: w.start_time)
            return {
                "window_id": next_window.window_id,
                "start_time": next_window.start_time.isoformat(),
                "name": next_window.name
            }
        
        return None