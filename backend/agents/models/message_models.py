"""
Message Models for DJAgent IM System

Defines the data structures for different message types in the chat interface:
- text: Plain text messages
- form_card: Structured form data for user input
- summary_card: Summary/conclusion cards
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """Enumeration of message types in the IM system"""
    TEXT = "text"
    FORM_CARD = "form_card"
    SUMMARY_CARD = "summary_card"
    IMAGE = "image"
    FILE = "file"


class MessageSender(str, Enum):
    """Enumeration of who sent the message"""
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


@dataclass
class TextMessage:
    """Plain text message"""
    type: str = MessageType.TEXT
    content: str = ""
    sender: str = MessageSender.AGENT
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "content": self.content,
            "sender": self.sender,
            "timestamp": self.timestamp or datetime.now().isoformat()
        }


@dataclass
class FormCardMessage:
    """Form card message - contains JSON schema for form rendering"""
    type: str = MessageType.FORM_CARD
    schema: Dict[str, Any] = field(default_factory=dict)
    sender: str = MessageSender.AGENT
    timestamp: Optional[str] = None
    task_id: Optional[str] = None
    form_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "schema": self.schema,
            "sender": self.sender,
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "task_id": self.task_id,
            "form_id": self.form_id
        }

    def validate(self) -> bool:
        """Validate form schema structure"""
        required_fields = {"id", "title", "state", "sections"}
        return all(field in self.schema for field in required_fields)


@dataclass
class SummaryCardMessage:
    """Summary card message - displays task summary or conclusion"""
    type: str = MessageType.SUMMARY_CARD
    title: str = ""
    summary: str = ""
    status: str = "pending"  # pending, completed, failed
    data: Dict[str, Any] = field(default_factory=dict)
    sender: str = MessageSender.AGENT
    timestamp: Optional[str] = None
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "data": self.data,
            "sender": self.sender,
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "task_id": self.task_id
        }


@dataclass
class ChatMessage:
    """Universal chat message structure"""
    type: str = MessageType.TEXT
    sender: str = MessageSender.AGENT
    timestamp: Optional[str] = None

    # Text message fields
    content: Optional[str] = None

    # Form card fields
    schema: Optional[Dict[str, Any]] = None
    form_id: Optional[str] = None
    task_id: Optional[str] = None

    # Summary card fields
    title: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    # Additional fields
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set default timestamp if not provided"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @classmethod
    def from_text(
        cls,
        content: str,
        sender: str = MessageSender.AGENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ChatMessage':
        """Create a text message"""
        return cls(
            type=MessageType.TEXT,
            content=content,
            sender=sender,
            metadata=metadata or {}
        )

    @classmethod
    def from_form_card(
        cls,
        schema: Dict[str, Any],
        form_id: str,
        task_id: Optional[str] = None,
        sender: str = MessageSender.AGENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ChatMessage':
        """Create a form card message"""
        return cls(
            type=MessageType.FORM_CARD,
            schema=schema,
            form_id=form_id,
            task_id=task_id,
            sender=sender,
            metadata=metadata or {}
        )

    @classmethod
    def from_summary_card(
        cls,
        title: str,
        summary: str,
        status: str = "completed",
        data: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        sender: str = MessageSender.AGENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ChatMessage':
        """Create a summary card message"""
        return cls(
            type=MessageType.SUMMARY_CARD,
            title=title,
            summary=summary,
            status=status,
            data=data or {},
            task_id=task_id,
            sender=sender,
            metadata=metadata or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {
            "type": self.type,
            "sender": self.sender,
            "timestamp": self.timestamp
        }

        # Add type-specific fields if they have values
        if self.content is not None:
            result["content"] = self.content

        if self.schema is not None:
            result["schema"] = self.schema

        if self.form_id is not None:
            result["form_id"] = self.form_id

        if self.task_id is not None:
            result["task_id"] = self.task_id

        if self.title is not None:
            result["title"] = self.title

        if self.summary is not None:
            result["summary"] = self.summary

        if self.status is not None:
            result["status"] = self.status

        if self.data:
            result["data"] = self.data

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ChatMessage':
        """Create ChatMessage from dictionary"""
        message_type = data.get("type", MessageType.TEXT)
        sender = data.get("sender", MessageSender.AGENT)
        timestamp = data.get("timestamp")

        # Create ChatMessage with appropriate fields
        message = ChatMessage(
            type=message_type,
            sender=sender,
            timestamp=timestamp,
            content=data.get("content"),
            schema=data.get("schema"),
            form_id=data.get("form_id"),
            task_id=data.get("task_id"),
            title=data.get("title"),
            summary=data.get("summary"),
            status=data.get("status"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {})
        )

        return message

    def validate(self) -> bool:
        """Validate message structure based on type"""
        if self.type == MessageType.TEXT:
            return bool(self.content)
        elif self.type == MessageType.FORM_CARD:
            return bool(self.schema and self.form_id)
        elif self.type == MessageType.SUMMARY_CARD:
            return bool(self.title and self.summary)
        return True


# Feedback data structure for storing form submissions
@dataclass
class FormSubmission:
    """Represents a form submission by a user"""
    form_id: str
    task_id: str
    user_id: str
    form_data: Dict[str, Any]
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: bool = False
    modification_count: int = 0
    modification_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "form_id": self.form_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "form_data": self.form_data,
            "submitted_at": self.submitted_at,
            "modified": self.modified,
            "modification_count": self.modification_count,
            "modification_history": self.modification_history
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FormSubmission':
        """Create FormSubmission from dictionary"""
        return FormSubmission(
            form_id=data.get("form_id", ""),
            task_id=data.get("task_id", ""),
            user_id=data.get("user_id", ""),
            form_data=data.get("form_data", {}),
            submitted_at=data.get("submitted_at", datetime.now().isoformat()),
            modified=data.get("modified", False),
            modification_count=data.get("modification_count", 0),
            modification_history=data.get("modification_history", [])
        )

    def record_modification(self, modified_data: Dict[str, Any]):
        """Record a form modification"""
        self.modified = True
        self.modification_count += 1
        self.modification_history.append({
            "modification_number": self.modification_count,
            "modified_at": datetime.now().isoformat(),
            "data": modified_data
        })
        self.form_data = modified_data  # Update current form data


# Example usage documentation
"""
# Creating different message types:

# 1. Text message
text_msg = ChatMessage.from_text(
    content="请填写这份质量缺陷报告",
    sender=MessageSender.AGENT
)

# 2. Form card message
form_schema = {
    "id": "form_quality_defect_001",
    "title": "质量缺陷核查",
    "state": "editable",
    "sections": [...]
}
form_msg = ChatMessage.from_form_card(
    schema=form_schema,
    form_id="form_quality_defect_001",
    task_id="TASK_001"
)

# 3. Summary card message
summary_msg = ChatMessage.from_summary_card(
    title="核查完成",
    summary="缺陷已记录，整改措施已批准",
    status="completed",
    task_id="TASK_001"
)

# Converting to/from dictionary
msg_dict = text_msg.to_dict()
msg_from_dict = ChatMessage.from_dict(msg_dict)

# Validating message
if text_msg.validate():
    print("Message is valid")
"""
