from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Enum as SQLAlchemyEnum,
    TIMESTAMP,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Float,
    JSON,
    text,
    CheckConstraint,
    ARRAY,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
import enum
from datetime import datetime
from .database import Base
from sqlalchemy import Table
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB


# ------------------ Mixin ------------------
class TimestampMixin:
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


# ------------------ Enums ------------------
class UserType(str, enum.Enum):
    client = "client"
    developer = "developer"


class RequestStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ConversationStatus(str, enum.Enum):
    active = "active"
    negotiating = "negotiating"
    agreed = "agreed"
    completed = "completed"


class VideoType(str, enum.Enum):
    project_overview = "project_overview"
    solution_demo = "solution_demo"
    progress_update = "progress_update"
    pitch_contest = "pitch_contest"
    tutorials = "tutorials"


class ProductType(str, enum.Enum):
    BROWSER_EXTENSION = "browser_extension"
    WEB_APP = "web_app"
    API_SERVICE = "api_service"
    AUTOMATION_SCRIPT = "automation_script"


class PricingModel(str, enum.Enum):
    ONE_TIME = "one_time"
    SUBSCRIPTION_MONTHLY = "subscription_monthly"
    SUBSCRIPTION_YEARLY = "subscription_yearly"
    USAGE_BASED = "usage_based"


# ------------------ User Model ------------------
class User(Base):
    __tablename__ = "users"
    __table_args__ = {
        "extend_existing": True
    }  # Add this to prevent duplicate table errors

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password = Column(String, nullable=False)  # Hashed password
    is_active = Column(Boolean, default=True)
    user_type = Column(SQLAlchemyEnum(UserType), nullable=True)
    terms_accepted = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Add this line to store JWT token (Optional, based on your auth method)
    token = Column(String, nullable=True)  # Stores JWT token if needed

    # OAuth Users (if using external authentication)
    google_id = Column(String, unique=True, nullable=True)
    github_id = Column(String, unique=True, nullable=True)
    linkedin_id = Column(String, unique=True, nullable=True)
    needs_role_selection = Column(Boolean, default=False)
    stripe_customer_id = Column(String, nullable=True)
    needs_role_selection = Column(Boolean, default=True)

    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    requests = relationship(
        "Request", back_populates="user", cascade="all, delete-orphan"
    )
    projects = relationship(
        "Project", back_populates="user", cascade="all, delete-orphan"
    )
    shared_requests = relationship(
        "RequestShare",
        foreign_keys="[RequestShare.shared_with_user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    request_comments = relationship(
        "RequestComment", back_populates="user", cascade="all, delete-orphan"
    )
    developer_profile = relationship(
        "DeveloperProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    client_profile = relationship(
        "ClientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    subscription = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    showcases = relationship(
        "Showcase",
        back_populates="developer",
        foreign_keys="[Showcase.developer_id]",
        lazy="select",
    )
    showcase_ratings_given = relationship(
        "ShowcaseRating",
        back_populates="rater",
        foreign_keys="[ShowcaseRating.rater_id]",
    )

    donations = relationship(
        "Donation", back_populates="user", cascade="all, delete-orphan"
    )

    oauth_connections = relationship("OAuthConnection", back_populates="user")

    playlists = relationship(
        "VideoPlaylist",
        back_populates="creator",
        cascade="all, delete-orphan",
        foreign_keys="[VideoPlaylist.creator_id]",
    )


# ------------------ OAuth ------------------
class UserToken(Base):
    __tablename__ = "user_tokens"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider = Column(String, nullable=False)  # e.g., 'google', 'github', 'linkedin'
    access_token = Column(Text, nullable=False)  # OAuth access token
    refresh_token = Column(Text, nullable=True)  # Optional refresh token
    expires_at = Column(DateTime, nullable=True)  # Expiration timestamp

    user = relationship("User", backref="tokens")


class OAuthConnection(Base):
    __tablename__ = "oauth_connections"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String)  # "google", "github", "linkedin"
    provider_user_id = Column(String)  # ID from the provider
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="oauth_connections")


# ------------------ Video Model ------------------
showcase_videos = Table(
    "showcase_videos",
    Base.metadata,
    Column("showcase_id", Integer, ForeignKey("showcases.id", ondelete="CASCADE")),
    Column("video_id", Integer, ForeignKey("videos.id", ondelete="CASCADE")),
    UniqueConstraint("showcase_id", "video_id", name="unique_showcase_video"),
    extend_existing=True,  # Add this to prevent duplicate table errors
)


class VideoRating(Base):
    __tablename__ = "video_ratings"
    __table_args__ = (
        CheckConstraint("stars >= 1 AND stars <= 5", name="check_video_stars_range"),
        UniqueConstraint("video_id", "rater_id", name="unique_video_rating"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    rater_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stars = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="ratings")
    rater = relationship("User")


class ShowcaseRating(Base):
    __tablename__ = "showcase_ratings"
    __table_args__ = (
        CheckConstraint("stars >= 1 AND stars <= 5", name="check_stars_range"),
        UniqueConstraint("showcase_id", "rater_id", name="unique_showcase_rating"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    showcase_id = Column(
        Integer,
        ForeignKey("showcases.id", ondelete="CASCADE"),
        nullable=False,
    )
    rater_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stars = Column(Integer, nullable=False)  # Changed from rating to stars
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    showcase = relationship("Showcase", back_populates="ratings")
    rater = relationship("User")


# New model in app/models.py
class VideoPlaylist(Base):
    __tablename__ = "video_playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_public = Column(Boolean, default=True)
    share_token = Column(String, unique=True, nullable=True)  # Add this line

    # Relationships
    creator = relationship("User", back_populates="playlists")
    videos = relationship("PlaylistVideo", back_populates="playlist")


# Join table for playlist-video many-to-many relationship
class PlaylistVideo(Base):
    __tablename__ = "playlist_videos"

    playlist_id = Column(
        Integer, ForeignKey("video_playlists.id", ondelete="CASCADE"), primary_key=True
    )
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    order = Column(Integer, default=0)  # For ordering videos in playlist
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    playlist = relationship("VideoPlaylist", back_populates="videos")
    video = relationship("Video", back_populates="playlists")


# Update the existing Video model
class Video(Base):
    __tablename__ = "videos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    request_id = Column(
        Integer, ForeignKey("requests.id", ondelete="SET NULL"), nullable=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_type = Column(
        SQLAlchemyEnum(VideoType), nullable=False, default=VideoType.solution_demo
    )
    share_token = Column(String, unique=True, nullable=True, index=True)
    project_url = Column(String, nullable=True)
    is_public = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="videos")
    project = relationship("Project", back_populates="videos")
    request = relationship("Request", back_populates="videos")
    votes = relationship("Vote", back_populates="video", cascade="all, delete-orphan")
    showcases = relationship(
        "Showcase", secondary=showcase_videos, back_populates="videos"
    )
    ratings = relationship(
        "VideoRating", back_populates="video", cascade="all, delete-orphan"
    )
    playlists = relationship("PlaylistVideo", back_populates="video")


# ------------------ Developer Showcase Models ------------------
class Showcase(Base):
    __tablename__ = "showcases"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String)
    readme_url = Column(String)
    project_url = Column(String)
    repository_url = Column(String)
    demo_url = Column(String)
    developer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    developer_profile_id = Column(Integer, ForeignKey("developer_profiles.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    average_rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    share_token = Column(String, unique=True, nullable=True)

    developer = relationship(
        "User",
        back_populates="showcases",
        foreign_keys=[developer_id],
        lazy="select",
    )
    developer_profile = relationship(
        "DeveloperProfile", backref="showcases", lazy="joined"
    )
    videos = relationship(
        "Video", secondary="showcase_videos", back_populates="showcases", lazy="select"
    )
    ratings = relationship(
        "ShowcaseRating",
        back_populates="showcase",
        cascade="all, delete-orphan",
        lazy="select",
    )

    content_links = relationship(
        "ShowcaseContentLink",
        back_populates="showcase",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @hybrid_property
    def linked_content(self):
        content = []
        for link in self.content_links:
            if link.content_type == "video":
                video = link.video
                if video:
                    content.append(
                        {
                            "id": link.id,
                            "type": "video",
                            "content_id": video.id,
                            "title": video.title,
                            "thumbnail_url": video.thumbnail_path,
                        }
                    )
            elif link.content_type == "profile":
                profile = link.profile
                if profile:
                    content.append(
                        {
                            "id": link.id,
                            "type": "profile",
                            "content_id": link.content_id,
                            "developer_name": profile.user.username,
                            "profile_image_url": profile.profile_image_url,
                        }
                    )
        return content


class ShowcaseContentLink(Base):
    __tablename__ = "showcase_content_links"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    showcase_id = Column(
        Integer, ForeignKey("showcases.id", ondelete="CASCADE"), nullable=False
    )
    content_type = Column(String, nullable=False)  # 'video' or 'profile'
    content_id = Column(Integer, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Add relationships
    showcase = relationship("Showcase", back_populates="content_links")
    video = relationship(
        "Video",
        primaryjoin="and_(ShowcaseContentLink.content_type=='video', "
        "ShowcaseContentLink.content_id==Video.id)",
        foreign_keys=[content_id],
        viewonly=True,
    )
    profile = relationship(
        "DeveloperProfile",
        primaryjoin="and_(ShowcaseContentLink.content_type=='profile', "
        "ShowcaseContentLink.content_id==DeveloperProfile.user_id)",
        foreign_keys=[content_id],
        viewonly=True,
    )


# ------------------ Profile Models ------------------
class DeveloperProfile(Base):
    __tablename__ = "developer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Basic fields (existing)
    skills = Column(String)
    experience_years = Column(Integer)
    bio = Column(Text)
    is_public = Column(Boolean, default=False)
    profile_image_url = Column(String)
    rating = Column(Float)
    total_projects = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    # Extended fields (new)
    professional_title = Column(String, default="Software Developer")

    # Location fields
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

    # Contact fields
    phone = Column(String)
    contact_email = Column(String)

    # JSON fields for complex data
    social_links = Column(
        JSONB
    )  # Store as JSON: {"linkedin": "url", "github": "url", etc.}
    work_experiences = Column(JSONB)  # Store as JSON array
    educations = Column(JSONB)  # Store as JSON array
    certifications = Column(JSONB)  # Store as JSON array
    portfolio_items = Column(JSONB)  # Store as JSON array

    # Relationships (existing)
    user = relationship("User", back_populates="developer_profile")
    ratings = relationship(
        "DeveloperRating", back_populates="developer", cascade="all, delete-orphan"
    )


class ClientProfile(Base):
    __tablename__ = "client_profiles"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    website = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="client_profile")


# ------------------ Project Model ------------------
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Project metadata
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="projects")
    requests = relationship("Request", back_populates="project")
    videos = relationship("Video", back_populates="project")


# ------------------ Request and RequestShare Models ------------------
class Request(Base, TimestampMixin):
    __tablename__ = "requests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(
        SQLAlchemyEnum(RequestStatus), default=RequestStatus.open, nullable=False
    )

    # Optional project grouping
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    added_to_project_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Visibility and sharing
    is_public = Column(Boolean, default=False)
    # Removed: contains_sensitive_data = Column(Boolean, default=False)

    # Business details
    estimated_budget = Column(Float, nullable=True)
    agreed_amount = Column(Float, nullable=True)

    # New fields for idea/collaboration feature
    is_idea = Column(Boolean, default=False)
    seeks_collaboration = Column(Boolean, default=False)
    collaboration_details = Column(Text, nullable=True)

    # Added metadata columns
    request_metadata = Column(JSONB, nullable=True)
    external_metadata = Column(JSONB, nullable=True)

    # Relationships
    user = relationship("User", back_populates="requests")
    project = relationship("Project", back_populates="requests")
    shared_with = relationship(
        "RequestShare", back_populates="request", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="request", cascade="all, delete-orphan"
    )
    comments = relationship(
        "RequestComment", back_populates="request", cascade="all, delete-orphan"
    )
    videos = relationship("Video", back_populates="request")


class RequestShare(Base):
    __tablename__ = "request_shares"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "shared_with_user_id", name="unique_request_share"
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(
        Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    shared_with_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    can_edit = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    viewed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    request = relationship("Request", back_populates="shared_with")
    user = relationship("User", foreign_keys=[shared_with_user_id])


# ------------------ Comment Models ------------------
class RequestComment(Base):
    __tablename__ = "request_comments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    request_id = Column(
        Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id = Column(
        Integer, ForeignKey("request_comments.id", ondelete="CASCADE"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    request = relationship("Request", back_populates="comments")
    user = relationship("User", back_populates="request_comments")
    replies = relationship(
        "RequestComment", backref=backref("parent", remote_side=[id])
    )
    votes = relationship(
        "RequestCommentVote", back_populates="comment", cascade="all, delete"
    )


class RequestCommentVote(Base):
    __tablename__ = "request_comment_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="unique_request_comment_vote"),
        {"extend_existing": True},
    )

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    comment_id = Column(
        Integer, ForeignKey("request_comments.id", ondelete="CASCADE"), primary_key=True
    )
    vote_type = Column(Integer, nullable=False)  # 1 for upvote, -1 for downvote
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    comment = relationship("RequestComment", back_populates="votes")


# ------------------ Conversation Models ------------------
class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(
        Integer,
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    starter_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(
        SQLAlchemyEnum(ConversationStatus),
        nullable=False,
        default=ConversationStatus.active,
    )
    is_external = Column(Boolean, default=False)  # Flag for external conversations
    external_source = Column(String, nullable=True)  # "analytics-hub", etc.
    external_reference_id = Column(String, nullable=True)  # ID from external system
    external_metadata = Column(JSONB, nullable=True)  # Metadata from external system

    # Relationships
    request = relationship("Request", back_populates="conversations")
    starter = relationship("User", foreign_keys=[starter_user_id])
    recipient = relationship("User", foreign_keys=[recipient_user_id])
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    content_links = relationship(
        "ConversationContentLink",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content = Column(Text, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    external_source = Column(String, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")
    content_links = relationship(
        "ConversationContentLink",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ConversationContentLink(Base):
    __tablename__ = "conversation_content_links"
    __table_args__ = (
        UniqueConstraint(
            "message_id", "content_type", "content_id", name="unique_content_link"
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    message_id = Column(
        Integer,
        ForeignKey("conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_type = Column(String, nullable=False)  # 'video' or 'profile'
    content_id = Column(Integer, nullable=False)  # video_id or user_id
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="content_links")
    message = relationship("ConversationMessage", back_populates="content_links")


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # Optional name for anonymous users
    email = Column(String, nullable=True)  # Optional email for anonymous users
    rating = Column(Integer)
    comment = Column(String)
    location = Column(String)  # Where in the app the feedback was given
    target_id = Column(String, nullable=True)  # ID of the specific item being rated
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ------------------ Subscription Model ------------------
class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    stripe_subscription_id = Column(String, unique=True, nullable=False)
    stripe_customer_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False)  # active, canceled, past_due
    current_period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Add to User model
    user = relationship("User", back_populates="subscription")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = {"extend_existing": True}

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    video = relationship("Video", back_populates="votes")


# ------------------ Donations ------------------
class Donation(Base):
    __tablename__ = "donations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_positive_amount"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # Make nullable
    amount = Column(Integer, nullable=False)
    stripe_session_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="donations")


# ------------------ Developer Rating System ------------------
class DeveloperRating(Base):
    __tablename__ = "developer_ratings"
    __table_args__ = (
        # Ensure a user can only rate a developer once
        UniqueConstraint(
            "developer_id", "user_id", name="unique_developer_user_rating"
        ),
        # Ensure rating is between 1 and 5
        CheckConstraint("stars >= 1 AND stars <= 5", name="stars_range_check"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, nullable=False)
    developer_id = Column(
        Integer,
        ForeignKey("developer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stars = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    developer = relationship("DeveloperProfile", back_populates="ratings")
    user = relationship("User")  # Change this from "client" to "user"


# ------------------ Snagged Ticket Model ------------------
class SnaggedRequest(Base):
    __tablename__ = "snagged_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(
        Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    developer_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    snagged_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    is_active = Column(Boolean, default=True)  # For soft delete/hide functionality

    # Relationships
    request = relationship("Request", backref="snagged_by")
    developer = relationship("User", backref="snagged_requests")


# ------------------ Collaboration Session Models ------------------


class CollaborationSession(Base):
    __tablename__ = "collaboration_sessions"

    id = Column(Integer, primary_key=True, index=True)
    external_ticket_id = Column(Integer, nullable=False)
    source_system = Column(String(50), nullable=False)
    status = Column(String(20), default="open", nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    access_token = Column(String(255), unique=True)
    session_metadata = Column(JSONB, nullable=True)

    # Relationships
    participants = relationship(
        "CollaborationParticipant",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    messages = relationship(
        "CollaborationMessage", back_populates="session", cascade="all, delete-orphan"
    )


class CollaborationParticipant(Base):
    __tablename__ = "collaboration_participants"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("collaboration_sessions.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False)
    user_name = Column(String(255), nullable=False)
    user_type = Column(String(50), nullable=False)
    external_user_id = Column(String(255), nullable=True)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)
    notification_settings = Column(JSONB, nullable=True)

    # Relationships
    session = relationship("CollaborationSession", back_populates="participants")
    user = relationship("User", backref="collaboration_participants")
    messages = relationship("CollaborationMessage", back_populates="participant")


class CollaborationMessage(Base):
    __tablename__ = "collaboration_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("collaboration_sessions.id"))
    participant_id = Column(
        Integer, ForeignKey("collaboration_participants.id"), nullable=True
    )
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")
    created_at = Column(DateTime(timezone=True), default=func.now())
    message_metadata = Column(JSONB, nullable=True)
    is_system = Column(Boolean, default=False)

    # Relationships
    session = relationship("CollaborationSession", back_populates="messages")
    participant = relationship("CollaborationParticipant", back_populates="messages")
    attachments = relationship(
        "CollaborationAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class CollaborationAttachment(Base):
    __tablename__ = "collaboration_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("collaboration_messages.id"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    message = relationship("CollaborationMessage", back_populates="attachments")
