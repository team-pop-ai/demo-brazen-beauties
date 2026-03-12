import os
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import anthropic

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load mock data with error handling
def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

# Load all mock data
students = load_json("data/students.json", [])
courses = load_json("data/courses.json", [])
social_campaigns = load_json("data/social_campaigns.json", [])
leads = load_json("data/leads.json", [])

# Initialize Claude client
anthropic_client = None
if os.environ.get("ANTHROPIC_API_KEY"):
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Calculate metrics
    total_students = len(students)
    active_courses = len([c for c in courses if c["status"] == "active"])
    total_leads = len(leads)
    course_revenue = sum(s.get("total_spent", 0) for s in students)
    
    # Recent activity
    recent_students = sorted(students, key=lambda x: x["enrolled_date"], reverse=True)[:5]
    recent_leads = sorted(leads, key=lambda x: x["captured_date"], reverse=True)[:5]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_students": total_students,
        "active_courses": active_courses,
        "total_leads": total_leads,
        "course_revenue": course_revenue,
        "recent_students": recent_students,
        "recent_leads": recent_leads,
        "social_campaigns": social_campaigns[:3],  # Show top 3 campaigns
        "voice_agent_active": True
    })

@app.get("/courses", response_class=HTMLResponse)
async def courses_page(request: Request):
    return templates.TemplateResponse("courses.html", {
        "request": request,
        "courses": courses
    })

@app.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_detail(request: Request, course_id: str):
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        return HTMLResponse("Course not found", status_code=404)
    
    # Get students enrolled in this course
    course_students = [s for s in students if course_id in s.get("enrolled_courses", [])]
    
    return templates.TemplateResponse("course_detail.html", {
        "request": request,
        "course": course,
        "course_students": course_students,
        "total_enrolled": len(course_students)
    })

@app.post("/generate_course_content")
async def generate_course_content(course_topic: str = Form(...)):
    if not anthropic_client:
        return {"error": "AI service not available"}
    
    try:
        system_prompt = """You are helping create gemology course content for Brazen Beauties, taught by Nakeesha, a certified gemologist with 25 years experience.

Create a detailed course outline with:
1. Course introduction (2-3 paragraphs)
2. 5-6 lesson titles with 2-sentence descriptions each
3. Learning objectives (4-5 bullet points)
4. Course completion certificate details

Make it professional but accessible. Emphasize practical, hands-on knowledge that jewelry enthusiasts and professionals would pay $197-497 to learn."""

        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Create detailed course content for: {course_topic}"}]
        )
        
        return {"course_content": message.content[0].text}
    except Exception as e:
        return {"error": f"AI generation failed: {str(e)}"}

@app.get("/campaigns", response_class=HTMLResponse)
async def campaigns_page(request: Request):
    return templates.TemplateResponse("campaigns.html", {
        "request": request,
        "campaigns": social_campaigns
    })

@app.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
async def campaign_detail(request: Request, campaign_id: str):
    campaign = next((c for c in social_campaigns if c["id"] == campaign_id), None)
    if not campaign:
        return HTMLResponse("Campaign not found", status_code=404)
    
    # Get leads from this campaign
    campaign_leads = [l for l in leads if l.get("source_campaign") == campaign_id]
    
    return templates.TemplateResponse("campaign_detail.html", {
        "request": request,
        "campaign": campaign,
        "campaign_leads": campaign_leads,
        "total_leads": len(campaign_leads)
    })

@app.post("/create_campaign")
async def create_campaign(
    event_name: str = Form(...),
    event_date: str = Form(...),
    target_location: str = Form(...),
    target_interests: str = Form(...)
):
    if not anthropic_client:
        return {"error": "AI service not available"}
    
    try:
        system_prompt = """You are creating a targeted social media campaign for Brazen Beauties jewelry pop-up events.

Generate a campaign strategy including:
1. Target audience demographics and interests
2. 3-4 compelling ad copy variations (Facebook/Instagram style)
3. Recommended budget allocation
4. Expected reach and engagement metrics
5. Post-event follow-up sequence (3-4 touchpoints)

Focus on luxury jewelry enthusiasts, permanent jewelry trends, and gemstone education. Make it feel premium but approachable."""

        campaign_request = f"""
Event: {event_name}
Date: {event_date}
Location: {target_location}
Target Interests: {target_interests}
"""

        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Create a social media campaign strategy for this jewelry event:\n{campaign_request}"}]
        )
        
        return {"campaign_strategy": message.content[0].text}
    except Exception as e:
        return {"error": f"AI generation failed: {str(e)}"}

@app.get("/leads", response_class=HTMLResponse)
async def leads_page(request: Request):
    # Group leads by status
    new_leads = [l for l in leads if l["status"] == "new"]
    contacted = [l for l in leads if l["status"] == "contacted"]
    qualified = [l for l in leads if l["status"] == "qualified"]
    
    return templates.TemplateResponse("leads.html", {
        "request": request,
        "new_leads": new_leads,
        "contacted": contacted,
        "qualified": qualified,
        "total_leads": len(leads)
    })

@app.post("/generate_followup")
async def generate_followup(lead_id: str = Form(...), lead_context: str = Form(...)):
    if not anthropic_client:
        return {"error": "AI service not available"}
    
    try:
        system_prompt = """You are writing personalized follow-up messages for Brazen Beauties jewelry leads.

Write as Nakeesha, a certified gemologist with 25 years experience who creates luxury jewelry and offers permanent jewelry services.

Create a warm, personal follow-up that:
1. References their specific interests (from the context provided)
2. Offers relevant gemology education or jewelry insights
3. Invites them to upcoming events or consultations
4. Maintains premium positioning without being pushy

Keep it conversational but professional. Include a clear next step."""

        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Write a personalized follow-up message for this lead:\n{lead_context}"}]
        )
        
        return {"followup_message": message.content[0].text}
    except Exception as e:
        return {"error": f"AI generation failed: {str(e)}"}

@app.get("/voice-agent", response_class=HTMLResponse)
async def voice_agent_page(request: Request):
    return templates.TemplateResponse("voice_agent.html", {
        "request": request
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)