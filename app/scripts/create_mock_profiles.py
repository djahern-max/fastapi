#!/usr/bin/env python3
"""
Script to create mock female developer profiles for RYZE.ai
This script will:
1. Create 6 female developer users
2. Add detailed developer profiles
3. Include work experiences, education, certifications, and portfolio items
4. Upload profile headshots

Usage:
- Ensure your database connection is configured
- Make sure the headshot images are in the specified path
- Run the script with proper permissions to write to your database
"""

import os
import sys
import random
from datetime import datetime, timedelta
import bcrypt
import psycopg2
from psycopg2.extras import Json

# Add these imports to help with configuring paths
import sys

sys.path.append(
    "/home/dane/app/src"
)  # Add the parent directory to the path so we can access app modules
import shutil
from typing import List, Dict, Any, Optional, Tuple
import uuid

# Database connection parameters (replace with your actual credentials)
DB_PARAMS = {
    "host": "localhost",
    "database": "ryze",
    "user": "postgres",
    "password": "Guitar0123",
    "port": "5432",
}

# Path to headshot images - will need to update this to where you'll upload the images
HEADSHOTS_PATH = "/home/dane/uploads/headshots"

# Target path for profile images
TARGET_PATH = "/home/dane/app/uploads/profile_images"

# Skills list
SKILLS = [
    "Python, React, Node.js, TypeScript, Docker, FastAPI, PostgreSQL, AWS",
    "JavaScript, React, Vue.js, GraphQL, MongoDB, Express, Node.js, AWS, CI/CD",
    "Backend Development, Java, Spring Boot, Microservices, Kubernetes, Docker, AWS, JUnit",
    "Full Stack, Python, Django, React, PostgreSQL, Redis, Celery, AWS, Heroku",
    "Frontend Development, React, Next.js, TypeScript, CSS-in-JS, Tailwind, Redux, Testing Library",
    "Machine Learning, Python, PyTorch, TensorFlow, Scikit-learn, Data Analysis, Computer Vision",
]

# Female names
FIRST_NAMES = [
    "Sophia",
    "Emma",
    "Olivia",
    "Ava",
    "Isabella",
    "Mia",
    "Charlotte",
    "Amelia",
    "Harper",
    "Evelyn",
    "Abigail",
    "Emily",
    "Elizabeth",
    "Sofia",
    "Avery",
    "Ella",
    "Scarlett",
    "Grace",
    "Chloe",
    "Victoria",
    "Riley",
    "Aria",
    "Lily",
    "Aubrey",
    "Zoey",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Jones",
    "Brown",
    "Davis",
    "Miller",
    "Wilson",
    "Moore",
    "Taylor",
    "Anderson",
    "Thomas",
    "Jackson",
    "White",
    "Harris",
    "Martin",
    "Thompson",
    "Garcia",
    "Martinez",
    "Robinson",
    "Clark",
    "Rodriguez",
    "Lewis",
    "Lee",
    "Walker",
    "Hall",
    "Allen",
    "Young",
    "Hernandez",
    "King",
]

# Tech companies
COMPANIES = [
    "Google",
    "Microsoft",
    "Amazon",
    "Apple",
    "Facebook",
    "Twitter",
    "Netflix",
    "Spotify",
    "Airbnb",
    "Uber",
    "Lyft",
    "LinkedIn",
    "Dropbox",
    "Slack",
    "Square",
    "Stripe",
    "Atlassian",
    "Shopify",
    "Adobe",
    "Salesforce",
    "Zoom",
    "VMware",
    "IBM",
    "Intel",
    "Oracle",
]

# Job titles for developers
JOB_TITLES = [
    "Senior Software Engineer",
    "Lead Full Stack Developer",
    "Frontend Developer",
    "Backend Engineer",
    "Software Architect",
    "DevOps Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "iOS Developer",
    "Android Developer",
    "Product Engineer",
    "Technical Lead",
    "Engineering Manager",
    "Principal Engineer",
    "Cloud Engineer",
    "AI Research Engineer",
    "Security Engineer",
    "Blockchain Developer",
]

# Professional titles for profiles
PROFESSIONAL_TITLES = [
    "Senior Software Engineer",
    "Full Stack Developer",
    "Frontend Developer",
    "Backend Engineer",
    "Software Architect",
    "DevOps Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Mobile Developer",
    "Python Developer",
    "React Developer",
    "JavaScript Developer",
    "Java Developer",
    "Golang Developer",
    "Ruby Developer",
]

# Universities
UNIVERSITIES = [
    "MIT",
    "Stanford University",
    "Carnegie Mellon University",
    "UC Berkeley",
    "Harvard University",
    "University of Washington",
    "Georgia Tech",
    "Cornell University",
    "University of Michigan",
    "University of Illinois",
    "University of Texas at Austin",
    "Caltech",
    "Princeton University",
    "University of Wisconsin-Madison",
    "Purdue University",
    "University of California, Los Angeles",
    "University of Pennsylvania",
    "Columbia University",
    "New York University",
    "University of Maryland",
]

# Degrees
DEGREES = [
    "Bachelor of Science in Computer Science",
    "Master of Science in Computer Science",
    "Bachelor of Science in Software Engineering",
    "Master of Science in Artificial Intelligence",
    "Bachelor of Engineering in Computer Engineering",
    "Master of Computer Science",
    "Ph.D. in Computer Science",
    "Bachelor of Science in Data Science",
    "Master of Science in Machine Learning",
    "Bachelor of Science in Information Technology",
]

# Certifications
CERTIFICATIONS = [
    "AWS Certified Solutions Architect",
    "Microsoft Certified: Azure Developer Associate",
    "Google Cloud Professional Cloud Architect",
    "Certified Kubernetes Administrator (CKA)",
    "MongoDB Certified Developer Associate",
    "Oracle Certified Professional, Java SE Programmer",
    "Certified Information Systems Security Professional (CISSP)",
    "Docker Certified Associate",
    "Certified Scrum Master",
    "Certified Ethical Hacker",
    "TensorFlow Developer Certificate",
    "Confluent Certified Developer for Apache Kafka",
    "Certified Jenkins Engineer",
    "Red Hat Certified System Administrator",
    "Salesforce Certified Platform Developer",
]

# Certificate Organizations
CERT_ORGS = [
    "Amazon Web Services",
    "Microsoft",
    "Google Cloud",
    "Cloud Native Computing Foundation",
    "MongoDB, Inc.",
    "Oracle",
    "(ISC)²",
    "Docker, Inc.",
    "Scrum Alliance",
    "EC-Council",
    "TensorFlow",
    "Confluent",
    "CloudBees",
    "Red Hat",
    "Salesforce",
]

# Locations
LOCATIONS = [
    "San Francisco, CA",
    "Seattle, WA",
    "New York, NY",
    "Austin, TX",
    "Boston, MA",
    "Chicago, IL",
    "Los Angeles, CA",
    "Denver, CO",
    "Portland, OR",
    "Atlanta, GA",
    "Washington, DC",
    "Raleigh, NC",
    "San Diego, CA",
    "Boulder, CO",
    "Pittsburgh, PA",
    "Miami, FL",
    "Nashville, TN",
    "Dallas, TX",
    "Minneapolis, MN",
    "Phoenix, AZ",
]

# Bio templates
BIO_TEMPLATES = [
    "As a {title} with {years}+ years of experience, I specialize in {skills_focus}. I've led teams at {company_name}, where I was instrumental in delivering mission-critical projects that {achievement}. I'm passionate about {passion} and believe in writing clean, maintainable code that scales. I'm constantly exploring new technologies and methodologies to improve my craft.",
    "I'm a {title} with a strong background in {skills_focus} and {years} years of industry experience. At {company_name}, I architected solutions that {achievement}. I enjoy tackling complex problems and breaking them down into elegant, efficient solutions. My approach combines technical excellence with strong communication skills to deliver value-driven results.",
    "Experienced {title} with {years} years in the tech industry, focused on {skills_focus}. My work at {company_name} helped {achievement}. I'm a continuous learner who stays ahead of industry trends and best practices. I'm enthusiastic about collaboration and knowledge sharing, and I'm known for my attention to detail and ability to deliver high-quality code.",
    "I bring {years} years of experience as a {title} specializing in {skills_focus}. During my time at {company_name}, I successfully {achievement}. I'm adept at translating business requirements into technical solutions and pride myself on delivering robust, scalable systems. I thrive in collaborative environments and enjoy mentoring junior developers.",
    "Results-driven {title} with {years} years of experience building {skills_focus} applications. At {company_name}, I led initiatives that {achievement}. I'm committed to software craftsmanship and test-driven development. I excel in agile environments and have a proven track record of delivering projects on time and within scope.",
    "Creative and analytical {title} with {years} years of expertise in {skills_focus}. While working at {company_name}, I {achievement}. I combine technical proficiency with strong problem-solving abilities to create efficient, innovative solutions. I'm passionate about clean architecture and enjoy optimizing systems for performance and reliability.",
]

# Work experience responsibilities
WORK_RESPONSIBILITIES = [
    [
        "Led development of microservices architecture using {backend_tech}",
        "Implemented CI/CD pipelines with {devops_tool}, reducing deployment time by 60%",
        "Engineered scalable backend solutions handling 10M+ daily requests",
        "Mentored junior developers through code reviews and pair programming",
        "Collaborated with product and design teams to refine features",
    ],
    [
        "Built responsive, performant interfaces using {frontend_tech}",
        "Optimized application performance, achieving 30% improvement in load time",
        "Implemented complex state management using {state_tool}",
        "Created reusable component library adopted across multiple projects",
        "Conducted A/B testing to validate UX improvements",
    ],
    [
        "Designed and implemented RESTful APIs using {api_tech}",
        "Optimized database queries, reducing latency by 40%",
        "Developed automated testing suites with 90%+ coverage",
        "Integrated third-party services and payment gateways",
        "Led technical planning and sprint meetings for team of 6",
    ],
    [
        "Architected cloud infrastructure using {cloud_tech}",
        "Implemented security best practices and compliance measures",
        "Reduced infrastructure costs by 25% through optimization",
        "Created data pipelines processing 5TB+ daily",
        "Managed database migrations with zero downtime",
    ],
    [
        "Built machine learning models for {ml_application}",
        "Developed data processing pipelines using {data_tech}",
        "Improved model accuracy by 15% through feature engineering",
        "Deployed ML models to production environments",
        "Collaborated with data scientists to implement research findings",
    ],
]

# Portfolio project templates
PORTFOLIO_PROJECTS = [
    {
        "title": "E-commerce Platform",
        "description": "A complete e-commerce solution with product management, cart functionality, payment processing, and order tracking. Implemented responsive design and performance optimizations.",
        "technologies": [
            "React",
            "Node.js",
            "MongoDB",
            "Express",
            "Stripe API",
            "Redis",
        ],
        "image_url": None,
        "project_url": "https://example-ecommerce.com",
        "repository_url": "https://github.com/username/ecommerce-platform",
    },
    {
        "title": "Real-time Chat Application",
        "description": "A scalable real-time messaging platform with user authentication, message history, and live typing indicators. Supports direct messaging and group chats with media sharing.",
        "technologies": [
            "Socket.io",
            "React",
            "Redux",
            "Node.js",
            "PostgreSQL",
            "AWS S3",
        ],
        "image_url": None,
        "project_url": "https://example-chat.com",
        "repository_url": "https://github.com/username/realtime-chat",
    },
    {
        "title": "Task Management System",
        "description": "A comprehensive project management tool with task tracking, team collaboration, file sharing, and reporting features. Includes customizable workflows and integration with third-party tools.",
        "technologies": [
            "Angular",
            "TypeScript",
            "NestJS",
            "PostgreSQL",
            "Docker",
            "GraphQL",
        ],
        "image_url": None,
        "project_url": "https://example-tasks.com",
        "repository_url": "https://github.com/username/task-manager",
    },
    {
        "title": "Recommendation Engine",
        "description": "A machine learning-based recommendation system for personalized content suggestions. Uses collaborative filtering and content-based approaches with real-time processing.",
        "technologies": ["Python", "TensorFlow", "Flask", "MongoDB", "Kafka", "Docker"],
        "image_url": None,
        "project_url": "https://example-recommendations.com",
        "repository_url": "https://github.com/username/recommendation-engine",
    },
    {
        "title": "Fitness Tracking App",
        "description": "A mobile application for tracking workouts, nutrition, and health metrics. Features include progress visualization, custom workout plans, and social sharing.",
        "technologies": [
            "React Native",
            "Firebase",
            "Redux",
            "Node.js",
            "Express",
            "MongoDB",
        ],
        "image_url": None,
        "project_url": "https://example-fitness.com",
        "repository_url": "https://github.com/username/fitness-tracker",
    },
    {
        "title": "Analytics Dashboard",
        "description": "A comprehensive data visualization platform with real-time metrics, customizable reports, and interactive charts. Supports multiple data sources and export options.",
        "technologies": [
            "Vue.js",
            "D3.js",
            "Python",
            "FastAPI",
            "TimescaleDB",
            "Docker",
        ],
        "image_url": None,
        "project_url": "https://example-analytics.com",
        "repository_url": "https://github.com/username/analytics-dashboard",
    },
    {
        "title": "Content Management System",
        "description": "A headless CMS with a customizable admin interface, content modeling, and API-first approach. Supports multi-language content and role-based permissions.",
        "technologies": ["React", "GraphQL", "Node.js", "PostgreSQL", "Redis", "AWS"],
        "image_url": None,
        "project_url": "https://example-cms.com",
        "repository_url": "https://github.com/username/headless-cms",
    },
    {
        "title": "Video Streaming Platform",
        "description": "A scalable video platform with adaptive streaming, content protection, and analytics. Features include user-generated content, recommendations, and monetization options.",
        "technologies": [
            "React",
            "Node.js",
            "FFmpeg",
            "MongoDB",
            "Redis",
            "AWS MediaConvert",
        ],
        "image_url": None,
        "project_url": "https://example-streaming.com",
        "repository_url": "https://github.com/username/video-platform",
    },
]

# Domain-specific technologies for use in responsibility templates
TECHS = {
    "backend_tech": [
        "Node.js",
        "Spring Boot",
        "Django",
        "FastAPI",
        "Express",
        "Laravel",
        "Ruby on Rails",
        "ASP.NET Core",
    ],
    "frontend_tech": [
        "React",
        "Angular",
        "Vue.js",
        "Next.js",
        "Svelte",
        "Redux",
        "TypeScript",
        "Tailwind CSS",
    ],
    "devops_tool": [
        "Jenkins",
        "GitHub Actions",
        "CircleCI",
        "Travis CI",
        "GitLab CI",
        "Ansible",
        "Terraform",
        "Kubernetes",
    ],
    "state_tool": [
        "Redux",
        "MobX",
        "Vuex",
        "Context API",
        "Recoil",
        "XState",
        "NgRx",
        "Zustand",
    ],
    "api_tech": [
        "GraphQL",
        "REST",
        "gRPC",
        "Express",
        "FastAPI",
        "Spring Boot",
        "NestJS",
        "Serverless",
    ],
    "cloud_tech": [
        "AWS",
        "Google Cloud",
        "Azure",
        "Kubernetes",
        "Docker",
        "Terraform",
        "CloudFormation",
        "Pulumi",
    ],
    "ml_application": [
        "recommendation systems",
        "natural language processing",
        "computer vision",
        "predictive analytics",
        "anomaly detection",
    ],
    "data_tech": [
        "Spark",
        "Kafka",
        "Airflow",
        "Pandas",
        "Dask",
        "Luigi",
        "Beam",
        "Databricks",
    ],
}


# Helper functions
def get_random_skills() -> str:
    return random.choice(SKILLS)


def get_random_name() -> Tuple[str, str]:
    return (random.choice(FIRST_NAMES), random.choice(LAST_NAMES))


def get_random_location() -> str:
    return random.choice(LOCATIONS)


def get_random_company() -> str:
    return random.choice(COMPANIES)


def get_random_job_title() -> str:
    return random.choice(JOB_TITLES)


def get_random_professional_title() -> str:
    return random.choice(PROFESSIONAL_TITLES)


def get_random_university() -> str:
    return random.choice(UNIVERSITIES)


def get_random_degree() -> str:
    return random.choice(DEGREES)


def get_random_certification() -> Tuple[str, str]:
    index = random.randint(0, len(CERTIFICATIONS) - 1)
    return (CERTIFICATIONS[index], CERT_ORGS[index])


def generate_date(start_year: int, end_year: int) -> datetime:
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Safely avoid month end issues
    return datetime(year, month, day)


def generate_password_hash(password: str) -> str:
    """Generate a bcrypt hash for the password"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def generate_bio(years: int) -> str:
    template = random.choice(BIO_TEMPLATES)
    skills_focus = random.choice(
        [
            "frontend development",
            "backend systems",
            "full stack development",
            "cloud architecture",
            "DevOps automation",
            "machine learning",
            "mobile applications",
            "distributed systems",
            "RESTful APIs",
        ]
    )
    company = get_random_company()
    achievement = random.choice(
        [
            "improved performance by 40%",
            "reduced infrastructure costs by 30%",
            "scaled to serve millions of daily users",
            "modernized legacy systems",
            "launched multiple successful products",
            "streamlined development workflows",
            "implemented cutting-edge security measures",
            "revolutionized the user experience",
        ]
    )
    passion = random.choice(
        [
            "clean code",
            "test-driven development",
            "mentoring junior developers",
            "open source contribution",
            "learning new technologies",
            "designing scalable systems",
            "solving complex problems",
            "performance optimization",
            "creating elegant user experiences",
        ]
    )

    return template.format(
        title=get_random_professional_title(),
        years=years,
        skills_focus=skills_focus,
        company_name=company,
        achievement=achievement,
        passion=passion,
    )


def generate_responsibilities(category: str) -> List[str]:
    """Generate a list of work responsibilities"""
    resp_set = random.choice(WORK_RESPONSIBILITIES)
    return [
        r.format(**{k: random.choice(v) for k, v in TECHS.items()}) for r in resp_set
    ]


def generate_user(index: int) -> Dict[str, Any]:
    """Generate a complete user profile"""
    first_name, last_name = get_random_name()
    email = f"{first_name.lower()}.{last_name.lower()}@example.com"
    username = f"{first_name.lower()}{last_name.lower()}"

    experience_years = random.randint(3, 15)

    return {
        "username": username,
        "email": email,
        "full_name": f"{first_name} {last_name}",
        "password": generate_password_hash(
            "password123"
        ),  # Use a secure password in production
        "is_active": True,
        "user_type": "developer",
        "terms_accepted": True,
        "profile": {
            "skills": get_random_skills(),
            "experience_years": experience_years,
            "bio": generate_bio(experience_years),
            "is_public": True,
            "city": get_random_location().split(",")[0],
            "state": (
                get_random_location().split(",")[1].strip()
                if "," in get_random_location()
                else ""
            ),
            "professional_title": get_random_professional_title(),
            "total_projects": random.randint(5, 20),
            "success_rate": random.uniform(85, 98),
            "headshot_path": f"Headshot_{index+1}.png",
            "social_links": {
                "linkedin": f"https://linkedin.com/in/{username}",
                "github": f"https://github.com/{username}",
                "twitter": f"https://twitter.com/{username}",
                "website": f"https://{username}.dev",
            },
        },
        "work_experiences": generate_work_experiences(experience_years),
        "education": generate_education(),
        "certifications": generate_certifications(),
        "portfolio_items": generate_portfolio_items(),
    }


def generate_work_experiences(total_years: int) -> List[Dict[str, Any]]:
    """Generate work experience entries based on total years of experience"""
    experiences = []
    current_date = datetime.now()
    years_to_fill = total_years

    # Current job
    current_job_years = min(random.randint(1, 4), years_to_fill)
    start_date = current_date - timedelta(days=current_job_years * 365)
    experiences.append(
        {
            "company": get_random_company(),
            "position": get_random_job_title(),
            "start_date": start_date,
            "end_date": None,
            "is_current": True,
            "location": get_random_location(),
            "description": f"Working on {random.choice(['frontend', 'backend', 'full stack', 'DevOps', 'machine learning'])} development.",
            "responsibilities": generate_responsibilities(
                random.choice(list(TECHS.keys()))
            ),
        }
    )

    years_to_fill -= current_job_years
    prev_end_date = start_date

    # Previous jobs
    while years_to_fill > 0:
        job_years = min(random.randint(1, 3), years_to_fill)
        start_date = prev_end_date - timedelta(days=job_years * 365)
        experiences.append(
            {
                "company": get_random_company(),
                "position": get_random_job_title(),
                "start_date": start_date,
                "end_date": prev_end_date - timedelta(days=random.randint(1, 30)),
                "is_current": False,
                "location": get_random_location(),
                "description": f"Worked on {random.choice(['frontend', 'backend', 'full stack', 'DevOps', 'machine learning'])} development.",
                "responsibilities": generate_responsibilities(
                    random.choice(list(TECHS.keys()))
                ),
            }
        )

        years_to_fill -= job_years
        prev_end_date = start_date

    return experiences


def generate_education() -> List[Dict[str, Any]]:
    """Generate education entries"""
    educations = []

    # Bachelor's degree
    end_year = datetime.now().year - random.randint(3, 10)
    start_year = end_year - 4

    educations.append(
        {
            "degree": "Bachelor of Science in Computer Science",
            "institution": get_random_university(),
            "start_date": datetime(start_year, 8, 1),
            "end_date": datetime(end_year, 5, 15),
            "location": get_random_location(),
            "description": "Focused on software development, algorithms, and data structures.",
        }
    )

    # Master's degree (50% chance)
    if random.random() > 0.5:
        masters_end_year = end_year + 2
        masters_start_year = end_year

        educations.append(
            {
                "degree": "Master of Science in Computer Science",
                "institution": get_random_university(),
                "start_date": datetime(masters_start_year, 8, 1),
                "end_date": datetime(masters_end_year, 5, 15),
                "location": get_random_location(),
                "description": f"Specialized in {random.choice(['artificial intelligence', 'machine learning', 'distributed systems', 'human-computer interaction', 'cybersecurity', 'data science'])}.",
            }
        )

    return educations


def generate_certifications() -> List[Dict[str, Any]]:
    """Generate certification entries"""
    num_certs = random.randint(1, 4)
    certifications = []

    for _ in range(num_certs):
        cert_name, org_name = get_random_certification()
        issue_date = generate_date(datetime.now().year - 5, datetime.now().year)

        # 50% chance of expiration date
        if random.random() > 0.5:
            expiration_date = issue_date.replace(
                year=issue_date.year + random.randint(1, 3)
            )
        else:
            expiration_date = None

        certifications.append(
            {
                "name": cert_name,
                "issuing_organization": org_name,
                "issue_date": issue_date,
                "expiration_date": expiration_date,
                "credential_id": f"CERT-{uuid.uuid4().hex[:8].upper()}",
                "credential_url": f"https://example.com/verify/{uuid.uuid4().hex[:10]}",
            }
        )

    return certifications


def generate_portfolio_items() -> List[Dict[str, Any]]:
    """Generate portfolio items"""
    num_projects = random.randint(2, 4)
    projects = random.sample(PORTFOLIO_PROJECTS, num_projects)

    for project in projects:
        # Randomize completion date
        completion_year = random.randint(datetime.now().year - 3, datetime.now().year)
        completion_month = random.randint(1, 12)
        completion_day = random.randint(1, 28)
        project["completion_date"] = datetime(
            completion_year, completion_month, completion_day
        )

        # Random featured status
        project["is_featured"] = random.random() > 0.7

    return projects


def copy_profile_image(source_path: str, filename: str) -> str:
    """Copy profile image to the target directory and return the new path"""
    # Create target directory if it doesn't exist
    os.makedirs(TARGET_PATH, exist_ok=True)

    # Generate a unique filename to avoid conflicts
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    target_file = os.path.join(TARGET_PATH, unique_filename)

    # Copy the file
    try:
        if os.path.exists(os.path.join(source_path, filename)):
            shutil.copy2(os.path.join(source_path, filename), target_file)
            return target_file
        else:
            print(
                f"Warning: Source file {os.path.join(source_path, filename)} not found."
            )
            # Use a dummy path for now - we'll handle the actual file separately
            return f"/profile_images/{unique_filename}"
    except Exception as e:
        print(f"Error copying image file: {e}")
        return None


def create_database_connection():
    """Create a connection to the database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)


def insert_user(conn, user_data: Dict[str, Any]) -> int:
    """Insert a user into the database and return the user ID"""
    cursor = conn.cursor()
    try:
        # Insert user
        cursor.execute(
            """
            INSERT INTO users (
                username, email, full_name, password, is_active, user_type, 
                terms_accepted, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
            (
                user_data["username"],
                user_data["email"],
                user_data["full_name"],
                user_data["password"],
                user_data["is_active"],
                user_data["user_type"],
                user_data["terms_accepted"],
                datetime.now(),
            ),
        )

        user_id = cursor.fetchone()[0]
        return user_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting user: {e}")
        raise


def insert_developer_profile(conn, user_id: int, profile_data: Dict[str, Any]) -> int:
    """Insert a developer profile into the database and return the profile ID"""
    cursor = conn.cursor()
    try:
        # Generate unique profile image path
        profile_image_path = None
        if profile_data.get("headshot_path"):
            unique_id = uuid.uuid4().hex[:8]
            # Store a path that will be used by your frontend
            profile_image_path = f"https://nyc3.digitaloceanspaces.com/ryzevideosv3/profile_images/profile_{unique_id}_{profile_data['headshot_path']}"

        # Insert developer profile
        cursor.execute(
            """
            INSERT INTO developer_profiles (
                user_id, skills, experience_years, bio, created_at, city, state,
                social_links, is_public, profile_image_url, professional_title,
                total_projects, success_rate
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
            (
                user_id,
                profile_data["skills"],
                profile_data["experience_years"],
                profile_data["bio"],
                datetime.now(),
                profile_data["city"],
                profile_data["state"],
                Json(profile_data["social_links"]),
                profile_data["is_public"],
                profile_image_path,
                profile_data["professional_title"],
                profile_data["total_projects"],
                profile_data["success_rate"],
            ),
        )

        profile_id = cursor.fetchone()[0]
        return profile_id
    except Exception as e:
        conn.rollback()
        print(f"Error inserting developer profile: {e}")
        raise


def insert_work_experiences(conn, profile_id: int, experiences: List[Dict[str, Any]]):
    """Insert work experiences into the database"""
    cursor = conn.cursor()
    try:
        for exp in experiences:
            cursor.execute(
                """
                INSERT INTO work_experiences (
                    developer_id, company, position, start_date, end_date, is_current,
                    location, description, responsibilities
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    profile_id,
                    exp["company"],
                    exp["position"],
                    exp["start_date"],
                    exp["end_date"],
                    exp["is_current"],
                    exp["location"],
                    exp["description"],
                    Json(exp["responsibilities"]),
                ),
            )
    except Exception as e:
        conn.rollback()
        print(f"Error inserting work experiences: {e}")
        raise


def insert_education(conn, profile_id: int, educations: List[Dict[str, Any]]):
    """Insert education entries into the database"""
    cursor = conn.cursor()
    try:
        for edu in educations:
            cursor.execute(
                """
                INSERT INTO educations (
                    developer_id, degree, institution, start_date, end_date,
                    location, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    profile_id,
                    edu["degree"],
                    edu["institution"],
                    edu["start_date"],
                    edu["end_date"],
                    edu["location"],
                    edu["description"],
                ),
            )
    except Exception as e:
        conn.rollback()
        print(f"Error inserting education: {e}")
        raise


def insert_certifications(conn, profile_id: int, certifications: List[Dict[str, Any]]):
    """Insert certification entries into the database"""
    cursor = conn.cursor()
    try:
        for cert in certifications:
            cursor.execute(
                """
                INSERT INTO certifications (
                    developer_id, name, issuing_organization, issue_date,
                    expiration_date, credential_id, credential_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    profile_id,
                    cert["name"],
                    cert["issuing_organization"],
                    cert["issue_date"],
                    cert["expiration_date"],
                    cert["credential_id"],
                    cert["credential_url"],
                ),
            )
    except Exception as e:
        conn.rollback()
        print(f"Error inserting certifications: {e}")
        raise


def insert_portfolio_items(conn, profile_id: int, items: List[Dict[str, Any]]):
    """Insert portfolio items into the database"""
    cursor = conn.cursor()
    try:
        for item in items:
            cursor.execute(
                """
                INSERT INTO portfolio_items (
                    developer_id, title, description, technologies, image_url,
                    project_url, repository_url, completion_date, is_featured
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    profile_id,
                    item["title"],
                    item["description"],
                    Json(item["technologies"]),
                    item["image_url"],
                    item["project_url"],
                    item["repository_url"],
                    item["completion_date"],
                    item["is_featured"],
                ),
            )
    except Exception as e:
        conn.rollback()
        print(f"Error inserting portfolio items: {e}")
        raise


def create_mock_profile(conn, index: int):
    """Create a complete mock developer profile"""
    try:
        user_data = generate_user(index)

        # Start transaction
        conn.autocommit = False

        # Insert user
        user_id = insert_user(conn, user_data)

        # Insert developer profile
        profile_id = insert_developer_profile(conn, user_id, user_data["profile"])

        # Insert work experiences
        insert_work_experiences(conn, profile_id, user_data["work_experiences"])

        # Insert education
        insert_education(conn, profile_id, user_data["education"])

        # Insert certifications
        insert_certifications(conn, profile_id, user_data["certifications"])

        # Insert portfolio items
        insert_portfolio_items(conn, profile_id, user_data["portfolio_items"])

        # Commit transaction
        conn.commit()

        print(f"Created mock profile: {user_data['full_name']} (ID: {user_id})")
        return user_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating mock profile: {e}")
        return None


def create_mock_profiles(num_profiles=6):
    """Create multiple mock profiles"""
    conn = create_database_connection()

    try:
        created_ids = []
        for i in range(num_profiles):
            user_id = create_mock_profile(conn, i)
            if user_id:
                created_ids.append(user_id)

        print(f"Successfully created {len(created_ids)} mock profiles")
    except Exception as e:
        print(f"Error in creating mock profiles: {e}")
    finally:
        conn.close()

    return created_ids


if __name__ == "__main__":
    # Check if the headshots directory exists, but don't quit if it doesn't
    if not os.path.exists(HEADSHOTS_PATH):
        print(f"Warning: Headshots directory not found at {HEADSHOTS_PATH}")
        print(
            "The script will continue but you'll need to upload the images separately"
        )
        # Create the directory in case we need it later
        os.makedirs(HEADSHOTS_PATH, exist_ok=True)

    # Create the target directory for profile images
    os.makedirs(TARGET_PATH, exist_ok=True)

    # Count available headshots
    try:
        headshot_files = [
            f for f in os.listdir(HEADSHOTS_PATH) if f.startswith("Headshot_")
        ]
        if len(headshot_files) < 6:
            print(f"Warning: Expected 6 headshot files, found {len(headshot_files)}")
    except Exception as e:
        print(f"Warning: Couldn't check headshot files: {e}")

    # Create the mock profiles
    print("Creating 6 mock female developer profiles...")
    create_mock_profiles(6)

    print(
        "\nIMPORTANT: You'll need to upload the headshot images using SFTP or similar to:"
    )
    print(f"1. Upload headshots to: {HEADSHOTS_PATH}")
    print(
        f"2. These will be referenced in the database with paths like: profile_images/Headshot_N.png"
    )
    print(
        "3. For production use, you'll need to upload these to your DigitalOcean Spaces"
    )
    print("\nExample image paths that were created in the database:")
    print(
        "https://nyc3.digitaloceanspaces.com/ryzevideosv3/profile_images/profile_XXXXXXXX_Headshot_1.png"
    )
    print("(Replace XXXXXXXX with the actual unique IDs in the database)")
    print("\nDone!")
