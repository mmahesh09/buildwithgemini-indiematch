import os
from typing import Optional
import json
import urllib.request
import uuid
import datetime

# In-memory lead storage
SAVED_LEADS = []

# Global Freelance / Remote Job Market Database
GLOBAL_JOBS = [
    {
        "id": "job-101",
        "title": "Senior Full-Stack Next.js / Python Engineer",
        "client": "FinTech Scaleup",
        "country": "United States",
        "remote_scope": "Worldwide",
        "job_type": "Contract",
        "category": "Development",
        "amount": 9500,
        "hourly_rate": 75,
        "amount_display": "$9,500/mo ($75/hr)",
        "duration": "6 months+",
        "description": "Architect high-throughput financial data pipelines, streaming transaction ledgers, and responsive client dashboards.",
        "skills": ["Next.js", "Python", "FastAPI", "PostgreSQL"],
    },
    {
        "id": "job-102",
        "title": "AI Agent & Workflow Automation Developer",
        "client": "Logistics AI",
        "country": "Germany",
        "remote_scope": "Worldwide",
        "job_type": "Project",
        "category": "AI & ML",
        "amount": 6000,
        "hourly_rate": 85,
        "amount_display": "$6,000 fixed ($85/hr equivalent)",
        "duration": "4 weeks",
        "description": "Develop multi-agent workflow using Gemini ADK and A2A protocol for automated invoice and dispatch matching.",
        "skills": ["Gemini", "ADK", "Python", "Docker"],
    },
    {
        "id": "job-103",
        "title": "SaaS Product Designer & Design System Lead",
        "client": "HealthTech Labs",
        "country": "United Kingdom",
        "remote_scope": "Worldwide",
        "job_type": "Contract",
        "category": "Design",
        "amount": 7200,
        "hourly_rate": 65,
        "amount_display": "$7,200/mo ($65/hr)",
        "duration": "3 months",
        "description": "Design patient-doctor consultation workflows, responsive tokenized component libraries, and interactive prototypes.",
        "skills": ["Figma", "Design Systems", "Prototyping", "UI/UX"],
    },
    {
        "id": "job-104",
        "title": "Technical Content & SEO Growth Strategist",
        "client": "DevTools Platform",
        "country": "Canada",
        "remote_scope": "Worldwide",
        "job_type": "Retainer",
        "category": "Marketing",
        "amount": 3500,
        "hourly_rate": 50,
        "amount_display": "$3,500/mo ($50/hr)",
        "duration": "Ongoing",
        "description": "Author in-depth technical tutorials, benchmark articles, and SEO documentation for Cloud/AI developers.",
        "skills": ["Technical Writing", "Developer Relations", "SEO", "GitHub"],
    },
    {
        "id": "job-105",
        "title": "Cloud Infrastructure & Kubernetes Architect",
        "client": "E-Commerce Enterprise",
        "country": "Singapore",
        "remote_scope": "Worldwide",
        "job_type": "Project",
        "category": "Cloud & DevOps",
        "amount": 8000,
        "hourly_rate": 95,
        "amount_display": "$8,000 fixed ($95/hr equivalent)",
        "duration": "6 weeks",
        "description": "Architect GCP GKE multi-region deployment with Terraform, autoscaling, and automated canary deployments.",
        "skills": ["GCP", "Kubernetes", "Terraform", "CI/CD"],
    },
    {
        "id": "job-106",
        "title": "Mobile App Developer (Flutter / React Native)",
        "client": "EdTech Global",
        "country": "Australia",
        "remote_scope": "Worldwide",
        "job_type": "Contract",
        "category": "Development",
        "amount": 5500,
        "hourly_rate": 55,
        "amount_display": "$5,500/mo ($55/hr)",
        "duration": "4 months",
        "description": "Gamified mobile learning application with interactive quizzes, offline sync, and push notifications.",
        "skills": ["Flutter", "Dart", "Firebase", "State Management"],
    },
    {
        "id": "job-107",
        "title": "Executive AI Assistant & Lead Concierge Builder",
        "client": "Venture Studio",
        "country": "United States",
        "remote_scope": "Worldwide",
        "job_type": "Project",
        "category": "AI & ML",
        "amount": 4500,
        "hourly_rate": 90,
        "amount_display": "$4,500 fixed ($90/hr equivalent)",
        "duration": "3 weeks",
        "description": "Build an inbound lead qualification assistant and CRM synchronization using Gemini and FastAPI.",
        "skills": ["Gemini", "FastAPI", "CRM Integration", "Python"],
    },
    {
        "id": "job-108",
        "title": "Cybersecurity & Smart Contract Auditor",
        "client": "DeFi Protocol",
        "country": "Switzerland",
        "remote_scope": "Worldwide",
        "job_type": "Project",
        "category": "Security",
        "amount": 12000,
        "hourly_rate": 150,
        "amount_display": "$12,000 fixed ($150/hr equivalent)",
        "duration": "2 weeks",
        "description": "Comprehensive security assessment, fuzzing, and penetration testing on staking contracts.",
        "skills": ["Solidity", "Smart Contract Audit", "Rust", "Security Testing"],
    },
    {
        "id": "job-109",
        "title": "Principal Front-End Systems Architect",
        "client": "Design-First SaaS",
        "country": "United States",
        "remote_scope": "Worldwide",
        "job_type": "Contract",
        "category": "Development",
        "amount": 14000,
        "hourly_rate": 110,
        "amount_display": "$14,000/mo ($110/hr)",
        "duration": "6 months+",
        "description": "Build premium, fluid Apple-quality user interfaces with micro-interactions, WCAG AA accessibility, and sub-100ms INP.",
        "skills": ["React", "TypeScript", "Performance", "CSS Architecture"],
    },
    {
        "id": "job-110",
        "title": "Autonomous Marketing & Lead-Gen Agent Engineer",
        "client": "Growth Accelerator",
        "country": "United Kingdom",
        "remote_scope": "Worldwide",
        "job_type": "Retainer",
        "category": "AI & ML",
        "amount": 5000,
        "hourly_rate": 80,
        "amount_display": "$5,000/mo ($80/hr)",
        "duration": "Ongoing",
        "description": "Build and orchestrate autonomous scrapers, prospect scoring agents, and auto-generated pitch decks.",
        "skills": ["Python", "ADK", "GenAI", "APIs"],
    },
]


def search_freelance_jobs(
    country: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    min_hourly_rate: Optional[float] = None,
    job_type: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Searches worldwide freelance and remote job opportunities with custom filters.

    Args:
        country: Country of the hiring client (e.g. 'United States', 'Germany', 'United Kingdom', 'Canada', 'Singapore', 'Australia', 'Switzerland', or 'all').
        min_amount: Minimum project or monthly budget in USD (e.g. 3000, 5000, 8000, 10000).
        max_amount: Maximum project or monthly budget in USD.
        min_hourly_rate: Minimum expected hourly pay rate in USD/hr (e.g. 50, 75, 100, 120).
        job_type: Type of engagement (e.g. 'Contract', 'Project', 'Retainer', 'Full-time').
        category: Professional domain (e.g. 'Development', 'AI & ML', 'Design', 'Marketing', 'Cloud & DevOps', 'Security').

    Returns:
        List of matching job records with title, client, country, amount, hourly rate, skills, and scope.
    """
    results = []
    for job in GLOBAL_JOBS:
        if country and country.lower() not in ("all", "any"):
            if country.lower() not in job["country"].lower():
                continue
        if min_amount is not None and job["amount"] < min_amount:
            continue
        if max_amount is not None and job["amount"] > max_amount:
            continue
        if min_hourly_rate is not None and job.get("hourly_rate", 0) < min_hourly_rate:
            continue
        if job_type and job_type.lower() not in ("all", "any"):
            if job_type.lower() not in job["job_type"].lower():
                continue
        if category and category.lower() not in ("all", "any"):
            if (category.lower() not in job["category"].lower()) and (
                category.lower() not in job["title"].lower()
            ):
                continue
        results.append(job)
    return results


def fetch_live_market_jobs(
    query: Optional[str] = None,
    remote_only: bool = True,
    limit: int = 5,
) -> list[dict]:
    """Fetches real-time live job postings from the free public Arbeitnow API (from public-apis repository).

    Use this tool when users ask about live external jobs, hiring market trends, or current remote job openings in the broader market.

    Args:
        query: Optional keyword or technology skill to filter jobs by (e.g. 'Python', 'React', 'DevOps', 'Marketing').
        remote_only: When True, filters strictly to remote positions (default True).
        limit: Maximum number of job postings to return (default 5, max 10).

    Returns:
        List of matching real-world job postings containing title, company, location, remote status, tags, and application link.
    """
    api_key = os.environ.get("ARBEITNOW_API_KEY") or os.environ.get("JOB_BOARD_API_KEY")
    headers = {"User-Agent": "IndieMatch-Agent/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8")).get("data", [])
    except Exception as e:
        return [{"error": f"Failed to fetch live job market data: {str(e)}"}]

    results = []
    q = query.lower().strip() if query else ""
    max_items = min(max(1, limit), 10)

    for item in data:
        if remote_only and not item.get("remote", False):
            continue
        title = item.get("title", "")
        tags = item.get("tags", [])
        location = item.get("location", "")
        company = item.get("company_name", "")

        if q:
            matches_title = q in title.lower()
            matches_company = q in company.lower()
            matches_tags = any(q in t.lower() for t in tags)
            if not (matches_title or matches_company or matches_tags):
                continue

        results.append({
            "title": title,
            "company": company,
            "location": location,
            "remote": item.get("remote", False),
            "tags": tags,
            "url": item.get("url", ""),
        })
        if len(results) >= max_items:
            break

    return results



def calculate_project_estimate(
    estimated_hours: float,
    complexity_multiplier: float = 1.0,
    urgency_tier: str = "standard",
) -> dict:
    """Computes an estimated project price range and delivery timeline based on scope and urgency.

    Args:
        estimated_hours: Base estimated hours required for the build.
        complexity_multiplier: Multiplier for technical complexity (1.0 for standard, 1.25 for complex, 1.5 for high complexity).
        urgency_tier: Turnaround speed ('standard' with no rush, 'expedited' with 1.25x rush, or 'weekend_sprint' with 1.5x rush).

    Returns:
        Dictionary containing breakdown of estimated costs, effective hourly rate, and target turnaround.
    """
    base_rate = 100.0
    urgency_factors = {"standard": 1.0, "expedited": 1.25, "weekend_sprint": 1.5}
    urgency_mult = urgency_factors.get(urgency_tier.lower(), 1.0)

    total_cost = estimated_hours * base_rate * complexity_multiplier * urgency_mult
    low_estimate = round(total_cost * 0.9, -1)
    high_estimate = round(total_cost * 1.15, -1)
    weeks = max(1.0, round((estimated_hours * complexity_multiplier) / 25.0, 1))

    return {
        "estimated_hours": estimated_hours,
        "price_range": f"${int(low_estimate):,} - ${int(high_estimate):,}",
        "recommended_budget": f"${int(total_cost):,}",
        "estimated_turnaround_weeks": weeks,
        "notes": "Includes architecture planning, milestone delivery, QA testing, and 14 days post-delivery support.",
    }


def save_lead(
    client_name: str,
    email: str,
    project_type: str,
    budget_range: str,
    timeline: str,
    key_requirements: str,
) -> dict:
    """Saves and qualifies an inbound client lead or job match into the CRM.

    Args:
        client_name: Client or company name.
        email: Contact email address.
        project_type: Type of work needed.
        budget_range: Stated budget or compensation.
        timeline: Target deadline or duration.
        key_requirements: Scope description and core requirements.

    Returns:
        Confirmation details and generated Lead ID.
    """
    lead_id = f"LEAD-{len(SAVED_LEADS) + 101}"
    lead_record = {
        "lead_id": lead_id,
        "client_name": client_name,
        "email": email,
        "project_type": project_type,
        "budget_range": budget_range,
        "timeline": timeline,
        "key_requirements": key_requirements,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "QUALIFIED_PROSPECT",
    }
    SAVED_LEADS.append(lead_record)
    return {
        "success": True,
        "lead_id": lead_id,
        "message": f"Lead {lead_id} successfully recorded for {client_name}!",
        "record": lead_record,
    }


# Verified Global Freelancer Talent Directory
FREELANCER_PROFILES = [
    {
        "id": "free-101",
        "name": "Elena Rostova",
        "title": "Principal AI & Autonomous Agent Architect",
        "country": "Germany",
        "avatar_initials": "ER",
        "hourly_rate": 95,
        "hourly_rate_display": "$95/hr",
        "rating": 4.98,
        "completed_projects": 42,
        "category": "AI & ML",
        "badge": "Top 1% Talent",
        "bio": "Ex-DeepMind research engineer specializing in multi-agent orchestration (Gemini ADK, LangGraph), local LLMs, and RAG systems.",
        "skills": ["Gemini", "ADK", "Python", "LangGraph", "FastAPI", "Vector DBs"],
        "availability": "Available (20 hrs/week)",
    },
    {
        "id": "free-102",
        "name": "Marcus Vance",
        "title": "Senior Design Systems & Front-End Engineer",
        "country": "United States",
        "avatar_initials": "MV",
        "hourly_rate": 85,
        "hourly_rate_display": "$85/hr",
        "rating": 5.0,
        "completed_projects": 58,
        "category": "Development",
        "badge": "Verified Elite",
        "bio": "Crafts Apple-grade responsive interfaces, custom micro-interactions, WCAG AA accessibility, and scalable Next.js architectures.",
        "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "Figma", "Design Systems"],
        "availability": "Immediate",
    },
    {
        "id": "free-103",
        "name": "Amara Okafor",
        "title": "Cloud Infrastructure & Kubernetes Architect",
        "country": "United Kingdom",
        "avatar_initials": "AO",
        "hourly_rate": 110,
        "hourly_rate_display": "$110/hr",
        "rating": 4.95,
        "completed_projects": 34,
        "category": "Cloud & DevOps",
        "badge": "Certified Architect",
        "bio": "GCP Professional Cloud Architect. Specializes in Terraform IaC, zero-downtime GKE clusters, and automated CI/CD pipelines.",
        "skills": ["GCP", "Kubernetes", "Terraform", "Docker", "Security", "CI/CD"],
        "availability": "Available (30 hrs/week)",
    },
    {
        "id": "free-104",
        "name": "Liam Chen",
        "title": "Lead Product Designer & UX Researcher",
        "country": "Singapore",
        "avatar_initials": "LC",
        "hourly_rate": 75,
        "hourly_rate_display": "$75/hr",
        "rating": 4.92,
        "completed_projects": 47,
        "category": "Design",
        "badge": "Design Lead",
        "bio": "Translates complex B2B workflows into high-converting consumer-grade UI. Over 8 years designing fintech and healthcare SaaS products.",
        "skills": ["Figma", "User Research", "Prototyping", "UI/UX", "Design Tokens"],
        "availability": "Immediate",
    },
    {
        "id": "free-105",
        "name": "Sarah Lindqvist",
        "title": "Smart Contract Auditor & Web3 Security Engineer",
        "country": "Switzerland",
        "avatar_initials": "SL",
        "hourly_rate": 140,
        "hourly_rate_display": "$140/hr",
        "rating": 5.0,
        "completed_projects": 29,
        "category": "Security",
        "badge": "Security Auditor",
        "bio": "Specialized in EVM smart contract vulnerabilities, formal verification, fuzz testing, and protocol economic defense.",
        "skills": ["Solidity", "Rust", "Security Audit", "Foundry", "DeFi"],
        "availability": "Booking for next month",
    },
    {
        "id": "free-106",
        "name": "David Morales",
        "title": "Full-Stack Python & Distributed Systems Engineer",
        "country": "Canada",
        "avatar_initials": "DM",
        "hourly_rate": 70,
        "hourly_rate_display": "$70/hr",
        "rating": 4.89,
        "completed_projects": 51,
        "category": "Development",
        "badge": "Top Rated",
        "bio": "High-throughput asynchronous backends with FastAPI, PostgreSQL indexing, Redis caching, and real-time WebSockets.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Celery"],
        "availability": "Available (40 hrs/week)",
    },
    {
        "id": "free-107",
        "name": "Chloe Dupont",
        "title": "Technical Content & Developer Evangelist",
        "country": "France",
        "avatar_initials": "CD",
        "hourly_rate": 60,
        "hourly_rate_display": "$60/hr",
        "rating": 4.97,
        "completed_projects": 63,
        "category": "Marketing",
        "badge": "DevRel Specialist",
        "bio": "Creates code-level developer documentation, benchmark blogs, interactive API tutorials, and SEO growth engines.",
        "skills": ["Technical Writing", "Developer Relations", "API Documentation", "SEO", "GitHub"],
        "availability": "Immediate",
    },
    {
        "id": "free-108",
        "name": "Rohan Patel",
        "title": "Cross-Platform Mobile Engineer (Flutter & iOS)",
        "country": "Australia",
        "avatar_initials": "RP",
        "hourly_rate": 80,
        "hourly_rate_display": "$80/hr",
        "rating": 4.93,
        "completed_projects": 38,
        "category": "Development",
        "badge": "Mobile Specialist",
        "bio": "Builds high-performance 60fps mobile applications with offline SQLite sync, biometric authentication, and in-app subscriptions.",
        "skills": ["Flutter", "Dart", "Swift", "Firebase", "App Store Deployment"],
        "availability": "Available (25 hrs/week)",
    },
]


def search_freelancers(
    country: Optional[str] = None,
    max_hourly_rate: Optional[float] = None,
    min_hourly_rate: Optional[float] = None,
    category: Optional[str] = None,
    skill: Optional[str] = None,
) -> list[dict]:
    """Finds verified top-tier freelancers and specialists matching client hiring criteria.

    Args:
        country: Country where the freelancer is based (e.g. 'United States', 'Germany', 'United Kingdom', 'Canada', 'Singapore', 'Australia', 'Switzerland', 'France', or 'All').
        max_hourly_rate: Maximum acceptable hourly rate in USD/hr.
        min_hourly_rate: Minimum hourly rate baseline.
        category: Professional domain (e.g. 'Development', 'AI & ML', 'Design', 'Cloud & DevOps', 'Security', 'Marketing').
        skill: Specific tool or skill keyword (e.g. 'Gemini', 'Python', 'React', 'Kubernetes', 'Figma').

    Returns:
        List of matching verified freelancer profiles with bio, rate, ratings, and skills.
    """
    results = []
    for f in FREELANCER_PROFILES:
        if country and country.lower() not in ("all", "any"):
            if country.lower() not in f["country"].lower():
                continue
        if max_hourly_rate is not None and f["hourly_rate"] > max_hourly_rate:
            continue
        if min_hourly_rate is not None and f["hourly_rate"] < min_hourly_rate:
            continue
        if category and category.lower() not in ("all", "any"):
            if (category.lower() not in f["category"].lower()) and (
                category.lower() not in f["title"].lower()
            ):
                continue
        if skill and skill.lower() not in ("all", "any"):
            matches_skill = any(skill.lower() in s.lower() for s in f["skills"])
            if not matches_skill and skill.lower() not in f["title"].lower():
                continue
        results.append(f)
    return results

FREELANCERS = FREELANCER_PROFILES
