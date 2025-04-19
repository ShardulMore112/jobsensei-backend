import http.client
import urllib.parse
import json
import google.generativeai as genai
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")

def fetch_jobs_for_skill(skill: str):
    encoded_skill = urllib.parse.quote(skill)

    conn = http.client.HTTPSConnection("indeed12.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': "indeed12.p.rapidapi.com"
    }
    endpoint = f"/jobs/search?query={encoded_skill}&locality=in&start=0"
    conn.request("GET", endpoint, headers=headers)
    res = conn.getresponse()
    data = res.read()

    response = json.loads(data.decode("utf-8"))
    jobs = response.get("hits", [])

    if not jobs:
        return {"search_skill": skill, "jobs": []}

    enhanced_jobs = []
    for job in jobs:
        title = job.get("title", "N/A")
        location = job.get("location", "N/A")
        company = job.get("company_name", "Unknown")
        link = f"https://www.indeed.com{job.get('link', '')}"
        description = job.get("description", "").strip()
        job_type_original = job.get("job_type", "").strip()

        if not description or len(description) < 30:
            gen_prompt = (
                f"Write a 2-3 line job description for a position titled '{title}' "
                f"at '{company}' located in '{location}' that requires the skill '{skill}'."
            )
            try:
                gen_response = model.generate_content(gen_prompt)
                description = gen_response.text.strip()
            except:
                description = f"A {title} position at {company} in {location} requiring {skill} skills."

        details_prompt = (
            f"Based on the job title '{title}' in the field related to '{skill}', provide the following in JSON:\n"
            f"1. experience_required (in years)\n"
            f"2. skills_required (5-7 skills)\n"
            f"3. job_type (full-time or part-time)"
        )
        try:
            details_response = model.generate_content(details_prompt)
            details_text = details_response.text.strip()

            if "```json" in details_text:
                json_content = details_text.split("```json")[1].split("```")[0].strip()
            elif "```" in details_text:
                json_content = details_text.split("```")[1].strip()
            else:
                json_content = details_text

            details_data = json.loads(json_content)
            experience_required = details_data.get("experience_required", "1-3 years")
            skills_required = details_data.get("skills_required", [skill])
            if isinstance(skills_required, str):
                skills_required = [s.strip() for s in skills_required.split(",")]
            job_type = details_data.get("job_type", job_type_original or "Full-time")
        except:
            experience_required = "1-3 years"
            skills_required = [skill]
            job_type = job_type_original or "Full-time"

        enhanced_jobs.append({
            "title": title,
            "location": location,
            "company": company,
            "description": description,
            "experience_required": experience_required,
            "skills_required": skills_required,
            "job_type": job_type,
            "link": link
        })

    return {"search_skill": skill, "jobs": enhanced_jobs}
