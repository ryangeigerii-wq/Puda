"""
Integration Hooks Manager

Provides hooks for external system integration.
"""

import json
import requests
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import logging
import threading
import queue


class HookEvent(Enum):
    """Hook event types."""
    DOCUMENT_ARCHIVED = "document.archived"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_RETRIEVED = "document.retrieved"
    BATCH_COMPLETED = "batch.completed"
    QC_APPROVED = "qc.approved"
    QC_REJECTED = "qc.rejected"
    VERSION_CREATED = "version.created"
    VERSION_ROLLED_BACK = "version.rolled_back"


@dataclass
class HookPayload:
    """Hook event payload."""
    event: HookEvent
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event': self.event.value,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }


@dataclass
class HookResult:
    """Result of hook execution."""
    success: bool
    hook_name: str
    event: HookEvent
    execution_time: float
    error: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


class IntegrationHook:
    """Base class for integration hooks."""
    
    def __init__(self, name: str):
        """
        Initialize hook.
        
        Args:
            name: Hook name
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def should_process(self, event: HookEvent, payload: HookPayload) -> bool:
        """
        Check if hook should process this event.
        
        Args:
            event: Event type
            payload: Event payload
            
        Returns:
            True if hook should process
        """
        return True
    
    def process(self, payload: HookPayload) -> HookResult:
        """
        Process hook event.
        
        Args:
            payload: Event payload
            
        Returns:
            HookResult
        """
        raise NotImplementedError


class WebhookHook(IntegrationHook):
    """HTTP webhook integration."""
    
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        retry_count: int = 3
    ):
        """
        Initialize webhook hook.
        
        Args:
            name: Hook name
            url: Webhook URL
            method: HTTP method
            headers: HTTP headers
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        super().__init__(name)
        self.url = url
        self.method = method.upper()
        self.headers = headers or {'Content-Type': 'application/json'}
        self.timeout = timeout
        self.retry_count = retry_count
    
    def process(self, payload: HookPayload) -> HookResult:
        """Send webhook HTTP request."""
        start_time = datetime.now()
        
        try:
            # Prepare request
            data = json.dumps(payload.to_dict())
            
            # Retry logic
            last_error = None
            for attempt in range(self.retry_count):
                try:
                    if self.method == 'POST':
                        response = requests.post(
                            self.url,
                            data=data,
                            headers=self.headers,
                            timeout=self.timeout
                        )
                    elif self.method == 'PUT':
                        response = requests.put(
                            self.url,
                            data=data,
                            headers=self.headers,
                            timeout=self.timeout
                        )
                    else:
                        raise ValueError(f"Unsupported HTTP method: {self.method}")
                    
                    response.raise_for_status()
                    
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    return HookResult(
                        success=True,
                        hook_name=self.name,
                        event=payload.event,
                        execution_time=execution_time,
                        response={
                            'status_code': response.status_code,
                            'body': response.text[:500]  # Truncate for logging
                        }
                    )
                except requests.RequestException as e:
                    last_error = str(e)
                    if attempt < self.retry_count - 1:
                        self.logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")
                        continue
                    break
            
            # All retries failed
            execution_time = (datetime.now() - start_time).total_seconds()
            return HookResult(
                success=False,
                hook_name=self.name,
                event=payload.event,
                execution_time=execution_time,
                error=f"Failed after {self.retry_count} attempts: {last_error}"
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return HookResult(
                success=False,
                hook_name=self.name,
                event=payload.event,
                execution_time=execution_time,
                error=str(e)
            )


class CallbackHook(IntegrationHook):
    """Python callback function hook."""
    
    def __init__(
        self,
        name: str,
        callback: Callable[[HookPayload], Any],
        events: Optional[List[HookEvent]] = None
    ):
        """
        Initialize callback hook.
        
        Args:
            name: Hook name
            callback: Callback function
            events: List of events to handle (None = all events)
        """
        super().__init__(name)
        self.callback = callback
        self.events = events
    
    def should_process(self, event: HookEvent, payload: HookPayload) -> bool:
        """Check if hook should process this event."""
        if self.events is None:
            return True
        return event in self.events
    
    def process(self, payload: HookPayload) -> HookResult:
        """Execute callback function."""
        start_time = datetime.now()
        
        try:
            result = self.callback(payload)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return HookResult(
                success=True,
                hook_name=self.name,
                event=payload.event,
                execution_time=execution_time,
                response={'result': str(result)}
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return HookResult(
                success=False,
                hook_name=self.name,
                event=payload.event,
                execution_time=execution_time,
                error=str(e)
            )


class FileLogHook(IntegrationHook):
    """File-based logging hook."""
    
    def __init__(
        self,
        name: str,
        log_file: Path,
        format: str = "json"
    ):
        """
        Initialize file log hook.
        
        Args:
            name: Hook name
            log_file: Log file path
            format: Log format (json or text)
        """
        super().__init__(name)
        self.log_file = Path(log_file)
        self.format = format
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def process(self, payload: HookPayload) -> HookResult:
        """Write event to log file."""
        start_time = datetime.now()
        
        try:
            with open(self.log_file, 'a') as f:
                if self.format == 'json':
                    f.write(json.dumps(payload.to_dict()) + '\n')
                else:
                    f.write(f"[{payload.timestamp.isoformat()}] {payload.event.value}: {json.dumps(payload.data)}\n")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return HookResult(
                success=True,
                hook_name=self.name,
                event=payload.event,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return HookResult(
                success=False,
                hook_name=self.name,
                event=payload.event,
                execution_time=execution_time,
                error=str(e)
            )


class IntegrationHookManager:
    """
    Manages integration hooks for external systems.
    
    Features:
    - Multiple hook types (webhook, callback, file)
    - Asynchronous execution
    - Event filtering
    - Error handling and retries
    - Hook statistics
    """
    
    def __init__(
        self,
        async_execution: bool = True,
        max_queue_size: int = 1000
    ):
        """
        Initialize hook manager.
        
        Args:
            async_execution: Execute hooks asynchronously
            max_queue_size: Maximum queue size for async execution
        """
        self.hooks: Dict[str, IntegrationHook] = {}
        self.async_execution = async_execution
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'events_fired': 0,
            'hooks_executed': 0,
            'hooks_failed': 0,
            'total_execution_time': 0.0
        }
        
        # Async queue
        if async_execution:
            self.event_queue = queue.Queue(maxsize=max_queue_size)
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
    
    def register_hook(self, hook: IntegrationHook):
        """
        Register a new hook.
        
        Args:
            hook: Integration hook instance
        """
        self.hooks[hook.name] = hook
        self.logger.info(f"Registered hook: {hook.name}")
    
    def unregister_hook(self, name: str) -> bool:
        """
        Unregister a hook.
        
        Args:
            name: Hook name
            
        Returns:
            True if hook was removed
        """
        if name in self.hooks:
            del self.hooks[name]
            self.logger.info(f"Unregistered hook: {name}")
            return True
        return False
    
    def fire_event(
        self,
        event: HookEvent,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None
    ) -> List[HookResult]:
        """
        Fire an event to all registered hooks.
        
        Args:
            event: Event type
            data: Event data
            metadata: Optional metadata
            
        Returns:
            List of HookResult (empty if async)
        """
        payload = HookPayload(
            event=event,
            timestamp=datetime.now(),
            data=data,
            metadata=metadata
        )
        
        self.stats['events_fired'] += 1
        
        if self.async_execution:
            self.event_queue.put(payload)
            return []
        else:
            return self._execute_hooks(payload)
    
    def _execute_hooks(self, payload: HookPayload) -> List[HookResult]:
        """Execute all hooks for an event."""
        results = []
        
        for hook in self.hooks.values():
            if not hook.should_process(payload.event, payload):
                continue
            
            try:
                result = hook.process(payload)
                results.append(result)
                
                self.stats['hooks_executed'] += 1
                self.stats['total_execution_time'] += result.execution_time
                
                if not result.success:
                    self.stats['hooks_failed'] += 1
                    self.logger.error(f"Hook {hook.name} failed: {result.error}")
                else:
                    self.logger.debug(f"Hook {hook.name} executed in {result.execution_time:.3f}s")
            except Exception as e:
                self.logger.error(f"Exception in hook {hook.name}: {e}")
                self.stats['hooks_failed'] += 1
                results.append(HookResult(
                    success=False,
                    hook_name=hook.name,
                    event=payload.event,
                    execution_time=0.0,
                    error=str(e)
                ))
        
        return results
    
    def _process_queue(self):
        """Worker thread for async hook execution."""
        while True:
            try:
                payload = self.event_queue.get()
                self._execute_hooks(payload)
                self.event_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing event queue: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hook execution statistics."""
        avg_execution_time = 0.0
        if self.stats['hooks_executed'] > 0:
            avg_execution_time = self.stats['total_execution_time'] / self.stats['hooks_executed']
        
        return {
            **self.stats,
            'avg_execution_time': avg_execution_time,
            'registered_hooks': len(self.hooks),
            'async_queue_size': self.event_queue.qsize() if self.async_execution else 0,
            'success_rate': (
                (self.stats['hooks_executed'] - self.stats['hooks_failed']) / 
                max(self.stats['hooks_executed'], 1) * 100
            )
        }
    
    def clear_statistics(self):
        """Reset statistics."""
        self.stats = {
            'events_fired': 0,
            'hooks_executed': 0,
            'hooks_failed': 0,
            'total_execution_time': 0.0
        }
    
    def list_hooks(self) -> List[Dict[str, str]]:
        """List all registered hooks."""
        return [
            {
                'name': hook.name,
                'type': hook.__class__.__name__
            }
            for hook in self.hooks.values()
        ]
