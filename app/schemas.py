from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
import enum
import re
from datetime import datetime
from pydantic.types import conint


# ------------------ Enums ------------------
class UserType(str, Enum):
    client = "client"
    developer = "developer"


class UserRoleSelect(BaseModel):
    user_type: UserType


class RequestStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ConversationStatus(str, Enum):
    active = "active"
    negotiating = "negotiating"
    agreed = "agreed"
    completed = "completed"


class VideoType(str, Enum):
    project_overview = "project_overview"
    solution_demo = "solution_demo"
    progress_update = "progress_update"
    pitch_contest = "pitch_contest"
    tutorials = "tutorials"


class RequestPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RequestVisibility(str, Enum):
    private = "private"
    shared = "shared"
    public = "public"


class ProductType(str, Enum):
    BROWSER_EXTENSION = "browser_extension"
    WEB_APP = "web_app"
    API_SERVICE = "api_service"
    AUTOMATION_SCRIPT = "automation_script"


class PricingModel(str, Enum):
    ONE_TIME = "one_time"
    SUBSCRIPTION_MONTHLY = "subscription_monthly"
    SUBSCRIPTION_YEARLY = "subscription_yearly"
    USAGE_BASED = "usage_based"


# ------------------ User Schemas ------------------
class UserBase(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserBasicInfo(UserBase):
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class UserBasic(BaseModel):
    id: int
    username: str

    class Config:
        from_orm = True


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    user_type: UserType
    terms_accepted: bool

    @field_validator("user_type", mode="before")
    def user_type_to_lower(cls, v):
        return v.lower() if isinstance(v, str) else v

    @field_validator("terms_accepted")
    def terms_must_be_accepted(cls, v):
        if not v:
            raise ValueError("Terms must be accepted")
        return v

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(UserBasicInfo):
    email: str
    is_active: bool
    user_type: UserType
    created_at: datetime
    needs_role_selection: Optional[bool] = False
    google_id: Optional[str] = None
    github_id: Optional[str] = None
    linkedin_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OAuthUserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    google_id: Optional[str] = None
    github_id: Optional[str] = None
    linkedin_id: Optional[str] = None
    user_type: UserType = UserType.client  # Default to client

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    id: int
    username: str
    is_active: bool
    user_type: UserType

    model_config = ConfigDict(from_attributes=True)


# Used for simple user references in other schemas
class UserBasic(UserBase):
    pass


from pydantic import BaseModel


class RoleSelection(BaseModel):
    email: str
    user_type: str

    class Config:
        orm_mode = True
        schema_extra = {"example": {"email": "user@example.com", "user_type": "client"}}


class OAuthCallbackRequest(BaseModel):
    code: str

    class Config:
        orm_mode = True
        schema_extra = {"example": {"code": "4/P7q7W91a-oMsCeLvIaQm6bTrgtp7"}}


class UserTypeUpdate(BaseModel):
    user_type: str

    class Config:
        orm_mode = True
        schema_extra = {"example": {"user_type": "client"}}  # or "developer"


# In schemas.py
class UserRoleSelect(BaseModel):
    user_type: UserType

    model_config = ConfigDict(from_attributes=True)


# ------------------ Developer Rating ------------------


# Add these schemas for handling developer ratings
class DeveloperRatingBase(BaseModel):
    stars: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class DeveloperRatingCreate(BaseModel):
    stars: int = Field(ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: Optional[str] = Field(
        None, max_length=1000, description="Optional comment about the developer"
    )


class DeveloperRatingUpdate(BaseModel):
    stars: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class DeveloperRatingOut(BaseModel):
    id: int
    developer_id: int
    user_id: int
    stars: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeveloperRatingStats(BaseModel):
    average_rating: float = 0.0
    total_ratings: int = 0
    rating_distribution: Dict[int, int] = {}


class RatingResponse(BaseModel):
    success: bool
    average_rating: float
    total_ratings: int
    message: str


# ------------------ Profile Schemas ------------------
# First define the nested models
class SocialLink(BaseModel):
    platform: str
    url: str


class Achievement(BaseModel):
    title: str
    date: datetime
    description: Optional[str] = None
    url: Optional[str] = None


# First, add the nested models for complex data structures
class SocialLinks(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkExperience(BaseModel):
    company: str
    position: str
    start_date: str  # or datetime if you prefer
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class Education(BaseModel):
    degree: str
    institution: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Certification(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioItem(BaseModel):
    title: str
    description: Optional[str] = None
    technologies: List[str] = []
    project_url: Optional[str] = None
    repository_url: Optional[str] = None
    completion_date: Optional[str] = None
    is_featured: bool = False

    model_config = ConfigDict(from_attributes=True)


# Updated Developer Profile Schemas
class DeveloperProfileCreate(BaseModel):
    # Basic information
    skills: str
    experience_years: int = Field(ge=0)
    bio: Optional[str] = None
    is_public: bool = False

    # Extended fields
    professional_title: Optional[str] = "Software Developer"

    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Contact
    phone: Optional[str] = None
    contact_email: Optional[str] = None

    # Social links
    social_links: Optional[Dict[str, str]] = {}

    # Experience and education (stored as JSON)
    work_experiences: Optional[List[Dict]] = []
    educations: Optional[List[Dict]] = []
    certifications: Optional[List[Dict]] = []
    portfolio_items: Optional[List[Dict]] = []


class ClientProfileCreate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None


class DeveloperProfileUpdate(BaseModel):
    # Basic fields
    skills: Optional[str] = None
    experience_years: Optional[int] = Field(None, ge=0)
    bio: Optional[str] = None
    is_public: Optional[bool] = None
    profile_image_url: Optional[str] = None
    total_projects: Optional[int] = Field(None, ge=0)

    # Extended fields
    professional_title: Optional[str] = None

    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Contact
    phone: Optional[str] = None
    contact_email: Optional[str] = None

    # Social links
    social_links: Optional[Dict[str, str]] = None

    # Experience and education
    work_experiences: Optional[List[Dict]] = None
    educations: Optional[List[Dict]] = None
    certifications: Optional[List[Dict]] = None
    portfolio_items: Optional[List[Dict]] = None


class DeveloperProfilePublic(BaseModel):
    id: int
    user_id: int
    user: UserBasic  # Add this line to include user information
    skills: str
    experience_years: int
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    total_projects: int
    success_rate: float
    created_at: datetime

    # Extended fields (these might be missing in your current schema)
    professional_title: Optional[str] = "Software Developer"
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[str] = None
    social_links: Optional[Dict[str, str]] = {}
    work_experiences: Optional[List[Dict]] = []
    educations: Optional[List[Dict]] = []
    certifications: Optional[List[Dict]] = []
    portfolio_items: Optional[List[Dict]] = []

    model_config = ConfigDict(from_attributes=True)


class ClientProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None


class DeveloperProfileOut(BaseModel):
    # Existing fields
    id: int
    user_id: int
    skills: str
    experience_years: int
    bio: Optional[str] = None
    is_public: bool
    profile_image_url: Optional[str] = None
    rating: Optional[float] = None
    total_projects: int
    success_rate: float
    created_at: datetime

    # Extended fields
    professional_title: Optional[str] = "Software Developer"

    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    # Contact
    phone: Optional[str] = None
    contact_email: Optional[str] = None

    # Social links
    social_links: Optional[Dict[str, str]] = {}

    # Experience and education
    work_experiences: Optional[List[Dict]] = []
    educations: Optional[List[Dict]] = []
    certifications: Optional[List[Dict]] = []
    portfolio_items: Optional[List[Dict]] = []

    # Rating fields
    ratings: Optional[List[DeveloperRatingOut]] = None
    average_rating: Optional[float] = Field(None, ge=0, le=5)

    model_config = ConfigDict(from_attributes=True)


class ClientProfileOut(BaseModel):
    id: int
    user_id: int
    company_name: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    website: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileCheckResponse(BaseModel):
    has_profile: bool
    profile_type: Optional[str] = None
    profile_id: Optional[int] = None


# ------------------ Token Schemas ------------------
class TokenData(BaseModel):
    id: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    provider: Optional[str] = None  # 'google', 'github', 'linkedin'

    model_config = ConfigDict(from_attributes=True)


# ------------------ Video Schemas ------------------


# Base schema with common fields
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    file_path: str
    thumbnail_path: Optional[str] = None
    project_id: Optional[int] = None
    request_id: Optional[int] = None
    video_type: VideoType = VideoType.solution_demo
    likes: int = 0
    liked_by_user: bool = False
    # Add these fields
    average_rating: float = 0.0
    total_ratings: int = 0

    model_config = ConfigDict(from_attributes=True)


# Schema for creating videos
class VideoCreate(VideoBase):
    user_id: int


# Schema for updating videos
class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_path: Optional[str] = None
    project_id: Optional[int] = None
    request_id: Optional[int] = None
    video_type: Optional[VideoType] = None

    model_config = ConfigDict(from_attributes=True)


# Complete video information for responses
class VideoOut(VideoBase):
    id: int
    user_id: int
    upload_date: datetime
    updated_at: Optional[datetime] = None


# Schema for returning lists of videos
class VideoResponse(BaseModel):
    user_videos: List[VideoOut]
    other_videos: List[VideoOut]

    model_config = ConfigDict(from_attributes=True)


# Schema for video with metadata from cloud storage
class SpacesVideoInfo(BaseModel):
    filename: str
    size: int
    last_modified: datetime
    url: str
    thumbnail_path: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    video_type: VideoType = VideoType.solution_demo
    project_id: Optional[int] = None
    request_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# Schema for video vote operations
class VideoVote(BaseModel):
    video_id: int
    dir: int  # 1 for like, 0 for unlike

    model_config = ConfigDict(from_attributes=True)


# Schema for video search/filter parameters
class VideoFilter(BaseModel):
    search: Optional[str] = None
    video_type: Optional[VideoType] = None
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    request_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class VideoRatingResponse(BaseModel):
    success: bool
    average_rating: float
    total_ratings: int
    message: str

    model_config = ConfigDict(from_attributes=True)


class VideoRatingBase(BaseModel):
    stars: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class VideoRatingCreate(VideoRatingBase):
    pass


class VideoRating(VideoRatingBase):
    id: int
    video_id: int
    rater_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoRatingStats(BaseModel):
    average_rating: float = Field(default=0.0)
    total_ratings: int = Field(default=0)

    model_config = ConfigDict(from_attributes=True)


class VideoRatingResponse(BaseModel):
    success: bool
    average_rating: float
    total_ratings: int
    message: str


class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    creator_id: int
    created_at: datetime
    video_count: Optional[int] = 0  # Make sure this field exists

    class Config:
        orm_mode = True  # Use this for Pydantic v1
        # For Pydantic v2, use: model_config = ConfigDict(from_attributes=True)


class VideoInPlaylist(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    thumbnail_path: Optional[str] = None
    file_path: str
    order: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class CreatorInfo(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class PlaylistDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    creator_id: int
    created_at: datetime
    videos: List[VideoInPlaylist] = []
    creator: Optional[CreatorInfo] = None

    model_config = ConfigDict(from_attributes=True)


class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

    model_config = ConfigDict(from_attributes=True)


class PlaylistCreate(PlaylistBase):
    pass


# Add this for video updates
class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    video_type: Optional[VideoType] = None
    project_id: Optional[int] = None
    request_id: Optional[int] = None

    class Config:
        orm_mode = True


# Add this for playlist updates
class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------ Project Schemas ------------------
class ProjectBase(BaseModel):
    """Simplified project schema - just basic grouping info"""

    name: str
    description: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(ProjectBase):
    is_active: Optional[bool] = None


class ProjectStats(BaseModel):
    total: int
    open: int
    completed: int
    total_budget: float
    agreed_amount: float


class ConversationStats(BaseModel):
    total: int
    active: int
    negotiating: int
    agreed: int


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]  # Make this optional if it can be null
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]  # Make this optional if it's nullable in the DB

    model_config = {"from_attributes": True}


class ProjectWithRequests(ProjectOut):
    requests: List["RequestOut"] = []

    model_config = ConfigDict(from_attributes=True)


# ------------------ Request Schemas ------------------
class RequestBase(BaseModel):
    title: str
    content: str
    estimated_budget: Optional[float] = None
    is_public: bool = False
    # Remove this line:
    # contains_sensitive_data: bool = False
    is_idea: bool = False
    seeks_collaboration: bool = False
    collaboration_details: Optional[str] = None


class RequestShareInfo(BaseModel):
    user_id: int
    username: str
    can_edit: bool

    model_config = ConfigDict(from_attributes=True)


class SimpleRequestOut(BaseModel):
    id: int
    title: str
    content: str
    project_id: Optional[int]
    user_id: int
    owner_username: str
    is_public: bool
    status: str
    estimated_budget: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    # Remove this line:
    # contains_sensitive_data: bool
    shared_with: List[RequestShareInfo] = Field(alias="shared_with_info")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RequestOut(BaseModel):
    id: int
    title: str
    content: str
    estimated_budget: Optional[float] = None
    is_public: bool
    # Remove this line:
    # contains_sensitive_data: bool
    is_idea: bool
    seeks_collaboration: bool
    collaboration_details: Optional[str] = None
    user_id: int
    status: RequestStatus
    project_id: Optional[int] = None
    added_to_project_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_username: str
    shared_with_info: List[dict] = []
    # Keep these fields:
    request_metadata: Optional[Dict[str, Any]] = None
    external_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("owner_username", mode="before")
    @classmethod
    def get_owner_username(cls, v, values):
        if hasattr(v, "username"):
            return v.username
        return v


class RequestCreate(RequestBase):
    project_id: Optional[int] = None
    developer_id: Optional[int] = None
    video_id: Optional[int] = None


class RequestUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    project_id: Optional[int] = None
    estimated_budget: Optional[float] = None
    is_public: Optional[bool] = None
    # Remove this line:
    # contains_sensitive_data: Optional[bool] = None
    status: Optional[RequestStatus] = None
    is_idea: Optional[bool] = None
    seeks_collaboration: Optional[bool] = None

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }


class RequestInProject(BaseModel):
    """Schema for adding/removing a request to/from a project"""

    project_id: Optional[int] = None


class RequestShare(BaseModel):
    shared_with_user_id: int
    can_edit: bool

    model_config = ConfigDict(from_attributes=True)


class SharedUserInfo(BaseModel):
    user: UserBasic
    can_edit: bool

    model_config = ConfigDict(from_attributes=True)


class RequestShareResponse(BaseModel):
    id: int
    request_id: int
    shared_with_user_id: int
    can_edit: bool
    created_at: datetime
    viewed_at: Optional[datetime] = None
    is_new: bool = True  # Computed field

    model_config = ConfigDict(from_attributes=True)


class SharedRequestOut(BaseModel):
    id: int
    title: str
    content: str
    project_id: Optional[int]
    user_id: int
    owner_username: str
    is_public: bool
    status: str
    estimated_budget: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]
    # Remove this line:
    # contains_sensitive_data: bool
    shared_with_info: List[dict] = []
    is_new: bool
    share_id: int
    share_date: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestShareWithUsername(BaseModel):
    id: int
    request_id: int
    shared_with_user_id: int
    can_edit: bool
    created_at: datetime
    username: str

    model_config = ConfigDict(from_attributes=True)


class PublicRequestOut(BaseModel):
    id: int
    title: str
    content: str
    user_id: int
    owner_username: str
    status: str
    estimated_budget: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RequestProjectAction(BaseModel):
    """Track project grouping actions"""

    action: str  # "added_to_project" or "removed_from_project"
    project_id: Optional[int]
    timestamp: datetime


# ------------------ Response Schemas for Request-Centric Operations ------------------
class RequestActionResponse(BaseModel):
    """Generic response for request actions"""

    success: bool
    message: str
    request_id: int
    action: str  # e.g., "added_to_project", "removed_from_project", "status_updated"


class RequestWithDetails(RequestOut):
    """Extended request information including related data"""

    conversations: List["ConversationOut"] = []
    comments: List["RequestCommentResponse"] = []  # Changed from CommentOut
    project: Optional[ProjectBase] = (
        None  # Basic project info if request is in a project
    )

    model_config = ConfigDict(from_attributes=True)


# ------------------ Dashboard Schemas ------------------
class DashboardStats(BaseModel):
    """New schema for dashboard statistics"""

    total_requests: int
    open_requests: int
    in_progress_requests: int
    completed_requests: int
    total_projects: int
    active_projects: int


class RequestDashboard(BaseModel):
    """New schema for request-centric dashboard view"""

    recent_requests: List[RequestOut]
    active_conversations: List["ConversationOut"]
    shared_with_me: List["SharedRequestOut"]
    public_requests: List[RequestOut]

    model_config = ConfigDict(from_attributes=True)


# ------------------ Comment Schemas ------------------
class RequestCommentBase(BaseModel):
    content: str


class RequestCommentCreate(RequestCommentBase):
    request_id: int
    parent_id: Optional[int] = None


class RequestCommentVoteCreate(BaseModel):
    vote_type: int = Field(..., ge=-1, le=1)


class RequestCommentResponse(RequestCommentBase):
    id: int
    request_id: int
    user_id: int
    parent_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    user: UserBasic
    vote_count: int = 0
    user_vote: Optional[int] = None
    replies: List["RequestCommentResponse"] = []  # Using string literal

    model_config = ConfigDict(from_attributes=True)


# ------------------ Conversation Schemas ------------------
class ConversationCreate(BaseModel):
    request_id: int
    initial_message: Optional[str] = None
    video_ids: Optional[List[int]] = []
    include_profile: Optional[bool] = False
    is_external_support: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    id: int
    request_id: int
    starter_user_id: int
    recipient_user_id: int
    status: ConversationStatus
    agreed_amount: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationMessageCreate(BaseModel):
    content: str
    video_ids: Optional[List[int]] = []
    include_profile: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class ConversationContentLink(BaseModel):
    id: int
    type: str  # 'video' or 'profile'
    content_id: int
    title: Optional[str] = None  # For videos
    url: Optional[str] = None  # For profile/video URLs

    model_config = ConfigDict(from_attributes=True)


class ConversationMessageOut(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    content: str
    created_at: datetime
    linked_content: List[ConversationContentLink] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationWithMessages(BaseModel):
    id: int
    request_id: int
    starter_user_id: int
    recipient_user_id: int
    starter_username: str
    recipient_username: str
    status: ConversationStatus
    agreed_amount: Optional[int] = None
    created_at: datetime
    messages: List[ConversationMessageOut]
    request_title: str

    model_config = ConfigDict(from_attributes=True)


# Update forward references
RequestOut.model_rebuild()
RequestCommentResponse.model_rebuild()
ProjectWithRequests.model_rebuild()


class ConversationUpdate(BaseModel):
    status: str


class ConversationFromVideo(BaseModel):
    video_id: int
    title: str
    content: str
    user_id: int


# ------------------ Feedback Section ------------------


# In schemas.py
class FeedbackCreate(BaseModel):
    rating: int
    comment: str
    location: str
    target_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None

    @field_validator("rating")
    def rating_must_be_valid(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("email")
    def validate_email(cls, v):
        if v is not None and not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Invalid email format")
        return v


class FeedbackResponse(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    rating: int
    comment: str
    location: str
    target_id: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Subscription Section ------------------


class SubscriptionBase(BaseModel):
    stripe_subscription_id: str
    stripe_customer_id: str
    status: str
    current_period_end: datetime


class SubscriptionCreate(SubscriptionBase):
    user_id: int


class SubscriptionOut(SubscriptionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class Vote(BaseModel):
    video_id: int
    dir: int = Field(..., description="1 to like, 0 to unlike")

    @field_validator("dir")
    def validate_direction(cls, v):
        if v not in [0, 1]:
            raise ValueError("Direction must be 0 or 1")
        return v

    model_config = ConfigDict(from_attributes=True)


# ------------------ Snagged Ticket ------------------


class SnaggedRequestOut(BaseModel):
    id: int
    request_id: int
    developer_id: int
    snagged_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SnaggedRequestWithDetails(BaseModel):
    id: int
    request_id: int
    developer_id: int
    snagged_at: datetime
    is_active: bool
    request: dict = {
        "id": int,
        "title": str,
        "content": str,
        "status": str,
        "estimated_budget": Optional[float],
        "owner_username": str,
    }

    model_config = ConfigDict(from_attributes=True)


class SnaggedRequestCreate(BaseModel):
    request_id: int
    message: str
    profile_link: bool = False
    video_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)


# Base class for ratings
class ShowcaseRatingBase(BaseModel):
    stars: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# Used for creating ratings
class ShowcaseRatingCreate(ShowcaseRatingBase):
    pass


# Full rating model with all fields
class ShowcaseRating(ShowcaseRatingBase):
    id: int
    showcase_id: int
    rater_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Statistics response model
class ShowcaseRatingStats(BaseModel):
    average_rating: float = Field(default=0.0)
    total_ratings: int = Field(default=0)

    model_config = ConfigDict(from_attributes=True)


class ShowcaseRatingResponse(BaseModel):
    success: bool
    average_rating: float
    total_ratings: int
    message: str

    model_config = ConfigDict(from_attributes=True)


# Base class for showcases
class ProjectShowcaseBase(BaseModel):
    title: str
    description: str
    project_url: Optional[str] = None
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None  # Add this to match your model
    selected_video_ids: Optional[List[int]] = []  # Add this for video selection

    @field_validator("project_url", "repository_url", "demo_url")
    def validate_urls(cls, v):
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


# Used for creating showcases
class ProjectShowcaseCreate(BaseModel):
    title: str
    description: str
    project_url: Optional[str] = None
    repository_url: Optional[str] = None
    selected_video_ids: Optional[List[int]] = []

    @field_validator("project_url", "repository_url")
    def validate_urls(cls, v):
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class DeveloperMetricsResponse(BaseModel):
    profile_rating: float
    video_rating: float
    showcase_rating: float
    composite_score: float
    total_videos: int
    total_showcases: int
    total_likes: int
    total_projects: int
    success_rate: float

    model_config = ConfigDict(from_attributes=True)


class TableOfContentsItem(BaseModel):
    level: int
    text: str
    id: str


class ReadmeMetadata(BaseModel):
    word_count: int
    heading_count: int
    has_code_blocks: bool


class ReadmeContent(BaseModel):
    content: str
    format: str
    toc: Optional[List[TableOfContentsItem]] = None
    metadata: Optional[ReadmeMetadata] = None


class ProjectShowcaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_url: Optional[str] = None
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None

    @field_validator("project_url", "repository_url", "demo_url")
    def validate_urls(cls, v):
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ShowcaseContentLink(BaseModel):
    id: int
    type: str  # 'video' or 'profile'
    content_id: int
    title: Optional[str] = None  # For videos
    thumbnail_url: Optional[str] = None  # For videos
    profile_image_url: Optional[str] = None  # For profiles
    developer_name: Optional[str] = None  # For profiles

    model_config = ConfigDict(from_attributes=True)


# Update the ProjectShowcase schema
class ProjectShowcase(ProjectShowcaseBase):
    id: int
    developer_id: int
    created_at: datetime
    updated_at: datetime
    image_url: Optional[str] = None
    readme_url: Optional[str] = None
    demo_url: Optional[str] = None
    average_rating: Optional[float] = 0.0
    total_ratings: Optional[int] = 0
    share_token: Optional[str] = None
    linked_content: List[ShowcaseContentLink] = []  # Add this field
    videos: Optional[List[VideoOut]] = []
    developer: Optional[UserBasic] = None
    developer_profile: Optional[DeveloperProfilePublic] = None

    model_config = ConfigDict(from_attributes=True)


class DonationCreate(BaseModel):
    amount: int
    currency: str = "usd"
    is_anonymous: bool = False

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    model_config = ConfigDict(from_attributes=True)


class DonationOut(BaseModel):
    id: int
    user_id: int
    amount: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------ Support - External ------------------


class ConversationMessage(BaseModel):
    """Schema for a single message in the conversation history"""

    role: str = Field(..., description="The role of the sender (user, system, support)")
    content: str = Field(..., description="The message content")
    timestamp: Optional[str] = Field(None, description="When the message was sent")


class ExternalSupportTicketBase(BaseModel):
    """Base schema for external support tickets"""

    email: EmailStr
    issue: str
    source: str = "analytics-hub"
    website_id: Optional[str] = None
    platform: Optional[str] = None
    analytics_hub_id: Optional[str] = None  # Add this field
    conversation_history: Optional[List[ConversationMessage]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "issue": "I can't access my analytics dashboard",
                "source": "analytics-hub",
                "website_id": "site-123",
                "platform": "web",
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "I need help with my analytics dashboard",
                        "timestamp": "2025-04-03T12:34:56Z",
                    },
                    {
                        "role": "system",
                        "content": "Would you like to speak with a support agent?",
                        "timestamp": "2025-04-03T12:35:10Z",
                    },
                    {
                        "role": "user",
                        "content": "Yes please",
                        "timestamp": "2025-04-03T12:35:30Z",
                    },
                ],
            }
        }


class ExternalSupportTicketCreate(ExternalSupportTicketBase):
    """Schema for creating external support tickets"""

    pass


class ExternalSupportTicketResponse(BaseModel):
    """Schema for responding with external support ticket data"""

    status: str
    message: str
    ticket_id: int


# External message schemas
class ExternalMessageCreate(BaseModel):
    content: str
    sender_platform: str = "analytics-hub"
    sender_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "content": "This is a message from Analytics Hub",
                "sender_platform": "analytics-hub",
                "sender_id": "user@example.com",
                "metadata": {"is_resolution": False},
            }
        }


# For the Analytics Hub endpoint
class TicketMessageCreate(BaseModel):
    content: str
    sender_type: str = "support"  # support or customer
    message_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "content": "This is a response from ireallycode support",
                "sender_type": "support",
                "message_id": "123",
            }
        }


# Pydantic models for collaboration API
class ParticipantBase(BaseModel):
    email: str
    user_name: str
    user_type: str
    external_user_id: Optional[str] = None
    notification_settings: Optional[dict] = None


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantResponse(ParticipantBase):
    id: int
    session_id: int
    last_viewed_at: Optional[datetime] = None
    is_current_user: bool = False

    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    content: str
    message_type: str = "text"
    metadata: Optional[dict] = None


class MessageCreate(MessageBase):
    attachments: Optional[List[dict]] = []


class MessageResponse(MessageBase):
    id: int
    session_id: int
    participant_id: int
    created_at: datetime
    is_system: bool = False
    attachments: Optional[List[dict]] = None

    class Config:
        orm_mode = True


class AttachmentResponse(BaseModel):
    id: int
    message_id: int
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime

    class Config:
        orm_mode = True


class SessionStatus(BaseModel):
    status: str

    @field_validator("status")
    def validate_status(cls, v):
        valid_statuses = ["open", "in_progress", "resolved"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class SessionCreate(BaseModel):
    external_ticket_id: int
    source_system: str
    metadata: Optional[dict] = None


class AccessRequest(BaseModel):
    email: str
    user_name: Optional[str] = None
    user_type: str
    duration_days: Optional[int] = 30


class SessionResponse(BaseModel):
    id: int
    external_ticket_id: int
    source_system: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    metadata: Optional[dict]
    participants: List[ParticipantResponse]

    class Config:
        orm_mode = True
