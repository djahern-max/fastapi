# app/routers/dynamic_meta.py - Using consistent RYZE.ai branding

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
import logging

from ..database import get_db
from ..models import User, DeveloperProfile, Video, Showcase
from ..config import settings

router = APIRouter(tags=["Dynamic Meta Tags"])
logger = logging.getLogger(__name__)

BUILD_HTML_PATH = "/home/dane/app/src/ryze-ai-frontend/build/index.html"


def get_base_url():
    try:
        frontend_url = getattr(settings, "frontend_url", "https://www.ryze.ai")
        return frontend_url.rstrip("/")
    except:
        return "https://www.ryze.ai"


def get_base_html() -> str:
    try:
        if os.path.exists(BUILD_HTML_PATH):
            with open(BUILD_HTML_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info("✅ Loaded production HTML template")
            return content
        else:
            logger.error(f"❌ Build not found at: {BUILD_HTML_PATH}")
            return get_error_html()
    except Exception as e:
        logger.error(f"Error reading HTML: {str(e)}")
        return get_error_html()


def get_error_html() -> str:
    return """<!DOCTYPE html>
<html><head><title>RYZE.ai - Build Required</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>🚀 RYZE.ai</h1>
    <h2 style="color: #dc3545;">Build Missing</h2>
    <p>Run <code>npm run build</code> in the frontend directory first!</p>
    <p><a href="/#/">Continue to app</a></p>
</body></html>"""


def escape_html(text: str) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def generate_html_with_meta(meta_data: dict) -> HTMLResponse:
    base_html = get_base_html()
    if "Build Missing" in base_html:
        return HTMLResponse(content=base_html)

    meta_html = f"""
    <title>{escape_html(meta_data['title'])}</title>
    <meta name="description" content="{escape_html(meta_data['description'])}" />
    
    <!-- Open Graph -->
    <meta property="og:type" content="website" />
    <meta property="og:url" content="{meta_data['og_url']}" />
    <meta property="og:title" content="{escape_html(meta_data['og_title'])}" />
    <meta property="og:description" content="{escape_html(meta_data['og_description'])}" />
    <meta property="og:image" content="{meta_data['og_image']}" />
    <meta property="og:site_name" content="RYZE.ai" />
    
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{escape_html(meta_data['og_title'])}" />
    <meta name="twitter:description" content="{escape_html(meta_data['og_description'])}" />
    <meta name="twitter:image" content="{meta_data['og_image']}" />
    <meta name="twitter:site" content="@ryze_ai" />
    
    <!-- Redirect to React route -->
    <script>
        window.addEventListener('DOMContentLoaded', function() {{
            window.location.hash = "{meta_data['react_route']}";
        }});
    </script>"""

    if "<!-- DYNAMIC_META_TAGS -->" in base_html:
        modified_html = base_html.replace("<!-- DYNAMIC_META_TAGS -->", meta_html)
    else:
        head_end = base_html.find("</head>")
        if head_end != -1:
            modified_html = base_html[:head_end] + meta_html + base_html[head_end:]
        else:
            modified_html = base_html + meta_html

    return HTMLResponse(content=modified_html)


@router.get("/developers/{developer_id}", response_class=HTMLResponse)
async def developer_profile_meta(developer_id: int, db: Session = Depends(get_db)):
    try:
        developer_profile = (
            db.query(DeveloperProfile)
            .filter(DeveloperProfile.user_id == developer_id)
            .first()
        )

        if not developer_profile:
            return RedirectResponse(
                url=f"/#/developers/{developer_id}", status_code=302
            )

        user = developer_profile.user
        base_url = get_base_url()

        full_name = user.full_name or user.username or f"Developer #{developer_id}"
        title = developer_profile.professional_title or "Software Developer"
        bio = developer_profile.bio or ""
        skills = developer_profile.skills or ""
        experience = developer_profile.experience_years or 0

        short_bio = (bio[:120] + "...") if len(bio) > 120 else bio
        skills_preview = (skills[:80] + "...") if len(skills) > 80 else skills

        meta_data = {
            "title": f"{full_name} - {title} | RYZE.ai",
            "description": f"Check out {full_name}'s profile on RYZE.ai! {experience} years experience. {short_bio or skills_preview}",
            "og_title": f"Check Out {full_name}'s Profile on RYZE.ai! 🚀",
            "og_description": short_bio
            or f"{title} with {experience} years of experience in {skills_preview}",
            "og_image": f"{base_url}/og-image.png",  # Always use RYZE.ai brand image
            "og_url": f"{base_url}/developers/{developer_id}",
            "react_route": f"/developers/{developer_id}",
        }

        return generate_html_with_meta(meta_data)

    except Exception as e:
        logger.error(f"Error generating developer meta: {str(e)}")
        return RedirectResponse(url=f"/#/developers/{developer_id}", status_code=302)


@router.get("/videos/{video_id}", response_class=HTMLResponse)
async def video_meta(video_id: int, db: Session = Depends(get_db)):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return RedirectResponse(url=f"/#/videos/{video_id}", status_code=302)

        user = video.user
        creator_name = user.full_name or user.username or "RYZE Creator"
        base_url = get_base_url()

        video_title = video.title or f"Video by {creator_name}"
        description = video.description or ""
        short_description = (
            (description[:120] + "...") if len(description) > 120 else description
        )

        meta_data = {
            "title": f"{video_title} | RYZE.ai",
            "description": f"Watch '{video_title}' by {creator_name} on RYZE.ai. {short_description}",
            "og_title": f"🎥 Watch: {video_title}",
            "og_description": short_description or f"Amazing video by {creator_name}",
            "og_image": f"{base_url}/og-image.png",  # Always use RYZE.ai brand image
            "og_url": f"{base_url}/videos/{video_id}",
            "react_route": f"/videos/{video_id}",
        }

        return generate_html_with_meta(meta_data)

    except Exception as e:
        logger.error(f"Error generating video meta: {str(e)}")
        return RedirectResponse(url=f"/#/videos/{video_id}", status_code=302)


@router.get("/showcase/{showcase_id}", response_class=HTMLResponse)
async def showcase_meta(showcase_id: int, db: Session = Depends(get_db)):
    try:
        showcase = db.query(Showcase).filter(Showcase.id == showcase_id).first()
        if not showcase:
            return RedirectResponse(url=f"/#/showcase/{showcase_id}", status_code=302)

        developer = showcase.developer
        developer_name = developer.full_name or developer.username or "RYZE Developer"
        base_url = get_base_url()

        showcase_title = showcase.title or "Amazing Project"
        description = showcase.description or ""
        short_description = (
            (description[:120] + "...") if len(description) > 120 else description
        )

        meta_data = {
            "title": f"{showcase_title} - Project Showcase | RYZE.ai",
            "description": f"Explore '{showcase_title}' by {developer_name} on RYZE.ai. {short_description}",
            "og_title": f"✨ Check Out This Amazing Project: {showcase_title}",
            "og_description": short_description
            or f"Incredible project showcasing the skills of {developer_name}",
            "og_image": f"{base_url}/og-image.png",  # Always use RYZE.ai brand image
            "og_url": f"{base_url}/showcase/{showcase_id}",
            "react_route": f"/showcase/{showcase_id}",
        }

        return generate_html_with_meta(meta_data)

    except Exception as e:
        logger.error(f"Error generating showcase meta: {str(e)}")
        return RedirectResponse(url=f"/#/showcase/{showcase_id}", status_code=302)
