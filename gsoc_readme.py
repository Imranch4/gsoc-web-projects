#!/usr/bin/env python3
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import os
from typing import List, Dict, Set, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://summerofcode.withgoogle.com"
API_BASE = "https://summerofcode.withgoogle.com/api"

class GSoCReadmeUpdater:
    def __init__(self):
        self.technology_keywords = {
            # Web Frontend
            'React': ['react', 'reactjs', 'react.js'],
            'Vue.js': ['vue', 'vuejs', 'vue.js'],
            'Angular': ['angular', 'angularjs'],
            'JavaScript': ['javascript', 'js', 'ecmascript'],
            'TypeScript': ['typescript', 'ts'],
            'HTML': ['html', 'html5'],
            'CSS': ['css', 'css3'],
            'Sass/SCSS': ['sass', 'scss'],
            'Less': ['less'],
            'Stylus': ['stylus'],
            'Bootstrap': ['bootstrap'],
            'Tailwind CSS': ['tailwind', 'tailwindcss'],
            'jQuery': ['jquery'],
            'D3.js': ['d3.js', 'd3'],
            'Three.js': ['three.js', 'threejs'],
            
            # Web Backend
            'Node.js': ['node', 'nodejs', 'node.js'],
            'Express.js': ['express', 'expressjs'],
            'Django': ['django'],
            'Flask': ['flask'],
            'Spring Boot': ['spring boot', 'springboot'],
            'Laravel': ['laravel'],
            'Ruby on Rails': ['rails', 'ruby on rails', 'ror'],
            'FastAPI': ['fastapi'],
            'ASP.NET': ['asp.net', 'aspnet'],
            'Phoenix': ['phoenix'],
            
            # Programming Languages
            'Python': ['python'],
            'Java': ['java'],
            'C++': ['c++', 'cpp'],
            'C': ['c'],
            'Go': ['go', 'golang'],
            'Rust': ['rust'],
            'Kotlin': ['kotlin'],
            'Swift': ['swift'],
            'PHP': ['php'],
            'Ruby': ['ruby'],
            'C#': ['c#', 'csharp'],
            
            # Mobile
            'React Native': ['react native'],
            'Flutter': ['flutter'],
            'Android': ['android'],
            'iOS': ['ios'],
            
            # Databases
            'MySQL': ['mysql'],
            'PostgreSQL': ['postgresql', 'postgres'],
            'MongoDB': ['mongodb', 'mongo'],
            'Redis': ['redis'],
            'SQLite': ['sqlite'],
            'Cassandra': ['cassandra'],
            'Elasticsearch': ['elasticsearch'],
            
            # DevOps & Cloud
            'Docker': ['docker'],
            'Kubernetes': ['kubernetes', 'k8s'],
            'AWS': ['aws', 'amazon web services'],
            'Azure': ['azure'],
            'GCP': ['gcp', 'google cloud'],
            
            # Tools & Frameworks
            'Webpack': ['webpack'],
            'Babel': ['babel'],
            'Jest': ['jest'],
            'Mocha': ['mocha'],
            'GraphQL': ['graphql'],
            'REST API': ['rest', 'restful', 'rest api'],
            'WebSocket': ['websocket', 'websockets'],
            'WebRTC': ['webrtc'],
        }
        
        # Web-specific technologies for filtering
        self.web_tech_keywords = [
            'react', 'vue', 'angular', 'javascript', 'typescript', 'html', 'css',
            'sass', 'scss', 'less', 'stylus', 'bootstrap', 'tailwind', 'jquery',
            'd3.js', 'three.js', 'node.js', 'express', 'django', 'flask',
            'spring boot', 'laravel', 'ruby on rails', 'fastapi', 'asp.net',
            'phoenix', 'react native', 'webpack', 'babel', 'jest', 'mocha', 
            'graphql', 'rest api', 'websocket', 'webrtc'
        ]
        
        self.cached_data = self.load_cached_data()
    
    def load_cached_data(self) -> Dict:
        """Load cached organization data to avoid re-scraping."""
        cache_file = "gsoc_cache.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_cached_data(self):
        """Save cached organization data."""
        cache_file = "gsoc_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cached_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_cache_key(self, org_slug: str, year: int) -> str:
        """Generate cache key for organization."""
        return f"{year}_{org_slug}"
    
    def get_available_years(self) -> List[int]:
        """Check which GSoC years have data available."""
        current_year = datetime.now().year
        available_years = []
        
        for year in range(current_year, current_year - 5, -1):
            url = f"{API_BASE}/program/{year}/organizations/"
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    available_years.append(year)
                    logger.info(f"✓ GSoC {year} data is available")
                else:
                    logger.info(f"✗ GSoC {year} data not available (Status: {response.status_code})")
            except Exception as e:
                logger.info(f"✗ GSoC {year} data not available: {e}")
        
        return available_years
    
    def get_organizations(self, year: int) -> List[Dict]:
        """Get all organizations for a specific year."""
        url = f"{API_BASE}/program/{year}/organizations/"
        try:
            logger.info(f"Fetching organizations for GSoC {year}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            organizations = response.json()
            logger.info(f"Found {len(organizations)} organizations for GSoC {year}")
            return organizations
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch organizations for {year}: {e}")
            return []
    
    def extract_technologies_from_text(self, text: str) -> List[str]:
        """Extract technologies from text using comprehensive keyword matching."""
        if not text:
            return []
        
        text_lower = text.lower()
        found_technologies = set()
        
        for tech_name, aliases in self.technology_keywords.items():
            for alias in aliases:
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, text_lower):
                    found_technologies.add(tech_name)
                    break
        
        return list(found_technologies)
    
    def scrape_organization_page(self, org_slug: str, year: int) -> Dict:
        """Scrape the organization page to get technologies and detailed info."""
        cache_key = self.get_cache_key(org_slug, year)
        
        if cache_key in self.cached_data:
            cached_entry = self.cached_data[cache_key]
            if 'timestamp' in cached_entry:
                cache_time = datetime.fromisoformat(cached_entry['timestamp'])
                if datetime.now() - cache_time < timedelta(days=7):
                    logger.info(f"Using cached data for {org_slug}")
                    return cached_entry['data']
        
        url = f"{BASE_URL}/programs/{year}/organizations/{org_slug}"
        try:
            logger.info(f"Scraping organization page: {org_slug}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            technologies = set()
            description = ""
            project_ideas = ""
            
            page_text = soup.get_text()
            
            text_technologies = self.extract_technologies_from_text(page_text)
            technologies.update(text_technologies)
            
            project_selectors = [
                '[class*="project"]',
                '[class*="idea"]',
                '[class*="proposal"]',
                '.project-ideas',
                '.ideas-list',
                '.proposals'
            ]
            
            for selector in project_selectors:
                elements = soup.select(selector)
                for element in elements:
                    project_text = element.get_text()
                    project_ideas += " " + project_text
                    project_techs = self.extract_technologies_from_text(project_text)
                    technologies.update(project_techs)
            
            if project_ideas:
                project_techs = self.extract_technologies_from_text(project_ideas)
                technologies.update(project_techs)
            
            tech_sections = soup.find_all(['div', 'section'], 
                                        string=re.compile(r'technolog|stack|skill', re.IGNORECASE))
            
            for section in tech_sections:
                section_text = section.get_text()
                section_techs = self.extract_technologies_from_text(section_text)
                technologies.update(section_techs)
            
            tech_selectors = [
                '[class*="tech"]',
                '[class*="tag"]',
                '[class*="skill"]',
                '[class*="label"]',
                '[class*="badge"]',
                '.tag', '.label', '.badge', '.skill', '.technology'
            ]
            
            for selector in tech_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) < 50:
                        element_techs = self.extract_technologies_from_text(text)
                        technologies.update(element_techs)
            
            desc_selectors = [
                'p',
                '.description',
                '.org-description', 
                '.organization-description',
                '[class*="description"]',
                'div > p',
                'section > p'
            ]
            
            for selector in desc_selectors:
                desc_elements = soup.select(selector)
                for desc_element in desc_elements:
                    desc_text = desc_element.get_text(strip=True)
                    if len(desc_text) > 100 and len(desc_text) < 1000:
                        description = desc_text
                        break
                if description:
                    break
            
            if not description:
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50 and len(text) < 500:
                        description = text
                        break
            
            result = {
                'technologies': sorted(list(technologies)),
                'description': description,
                'url': url,
                'project_ideas_text': project_ideas[:1000]
            }
            
            self.cached_data[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'data': result
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to scrape {org_slug}: {e}")
            result = {'technologies': [], 'description': '', 'url': url, 'project_ideas_text': ''}
            
            self.cached_data[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'data': result
            }
            
            return result
    
    def contains_web_technologies(self, technologies: List[str]) -> bool:
        """Check if technologies list contains web development technologies."""
        if not technologies:
            return False
        
        tech_lower = [tech.lower() for tech in technologies]
        return any(any(web_tech in tech_lower_tech for web_tech in self.web_tech_keywords) 
                  for tech_lower_tech in tech_lower)
    
    def analyze_organization_web_projects(self, org_data: Dict, year: int) -> Tuple[bool, Dict]:
        """Analyze if organization has web development projects."""
        org_name = org_data.get('name', 'Unknown Organization')
        org_slug = org_data.get('slug', '')
        
        scraped_data = self.scrape_organization_page(org_slug, year)
        org_description = org_data.get('description', '') + ' ' + scraped_data.get('description', '')
        org_technologies = scraped_data.get('technologies', [])
        
        desc_technologies = self.extract_technologies_from_text(org_description)
        project_technologies = self.extract_technologies_from_text(scraped_data.get('project_ideas_text', ''))
        
        all_technologies = list(set(org_technologies + desc_technologies + project_technologies))
        
        has_web_tech = self.contains_web_technologies(all_technologies)
        
        return has_web_tech, {**scraped_data, 'technologies': all_technologies}
    
    def extract_web_technologies(self, technologies: List[str]) -> str:
        """Extract and format web technologies from technology list."""
        web_technologies = []
        for tech in technologies:
            if any(web_tech in tech.lower() for web_tech in self.web_tech_keywords):
                web_technologies.append(tech)
        
        return ', '.join(sorted(web_technologies)) if web_technologies else 'Web technologies'
    
    def generate_readme_content(self, web_organizations_by_year: Dict[int, List[Dict]]) -> str:
        """Generate the README content with multiple years."""
        current_year = datetime.now().year
        next_year = current_year + 1
        
        available_years = sorted(web_organizations_by_year.keys(), reverse=True)
        latest_year = available_years[0] if available_years else current_year - 1
        
        readme_content = f'''<div style="text-align:center"><img src="https://user-images.githubusercontent.com/53327173/127941396-fd0de7de-1a04-4e99-a346-815b293637c8.png"/></div>

<br>

<p align="center">List of Open Source organizations participating in <b>Google Summer of Code</b> having <b>Web Development</b> projects<br>based on technologies like <b>React</b>, <b>Vue.js</b>, <b>Angular</b>, <b>JavaScript</b>, <b>TypeScript</b>, <b>Node.js</b>, and more! 📝</p>

<br>
  
**NOTE:** This list helps you find & compare web development projects across different GSoC years.

<br>

## 📊 Current Status

'''
        
        for year in sorted(available_years, reverse=True):
            org_count = len(web_organizations_by_year[year])
            readme_content += f"- **GSoC {year}**: {org_count} organizations with web projects\n"
        
        readme_content += f"\n> 🔄 **Auto-updates weekly** | 📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for year in sorted(available_years, reverse=True):
            orgs = web_organizations_by_year[year]
            if not orgs:
                continue
                
            readme_content += f"## 🚀 GSoC {year} - Web Development Organizations\n\n"
            readme_content += f"**Total: {len(orgs)} organizations**\n\n"
            readme_content += "| No. | Organization | Web Technologies |\n"
            readme_content += "|-----|--------------|------------------|\n"
            
            for i, org in enumerate(orgs, 1):
                org_name = org['name']
                anchor = f"{year}-" + org_name.lower().replace(' ', '-').replace('.', '').replace(',', '').replace('&', '')
                technologies = org['technologies']
                readme_content += f"| {i}. | [{org_name}](#{anchor}) | {technologies} |\n"
            
            readme_content += "\n<br>\n\n"
        
        for year in sorted(available_years, reverse=True):
            orgs = web_organizations_by_year[year]
            if not orgs:
                continue
                
            readme_content += f"## 📋 GSoC {year} - Organization Details\n\n"
            
            for i, org in enumerate(orgs, 1):
                org_name = org['name']
                org_url = org['url']
                technologies = org['technologies']
                description = org['description']
                anchor = f"{year}-" + org_name.lower().replace(' ', '-').replace('.', '').replace(',', '').replace('&', '')
                
                readme_content += f"### {i}. {org_name} {{#{anchor}}}\n\n"
                if description:
                    readme_content += f"{description}\n\n"
                readme_content += f"- **Technologies**: {technologies}\n"
                readme_content += f"- **GSoC URL**: [View on GSoC]({org_url})\n"
                if org.get('website_url'):
                    readme_content += f"- **Website**: [Visit Website]({org['website_url']})\n"
                readme_content += "\n<br>\n\n"
        
        readme_content += f'''---
## 📈 Statistics

| Year | Organizations with Web Projects |
|------|----------------------------------|
'''
        for year in sorted(available_years, reverse=True):
            org_count = len(web_organizations_by_year[year])
            readme_content += f"| GSoC {year} | {org_count} |\n"
        
        readme_content += f'''

## 🔧 Technical Details

- **Last Updated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Data Source**: Google Summer of Code Official API
- **Web Technologies Detected**: {', '.join(sorted(set(self.web_tech_keywords)))}
- **Update Frequency**: Weekly automatic checks
- **Cache**: Enabled (1 week duration)

## 🔄 Automatic Updates

This repository automatically:
1. Checks for new GSoC data every Monday
2. Updates the README with the latest organizations
3. Maintains historical data for multiple years
4. Caches results to be respectful to GSoC servers

When GSoC {next_year} organizations are announced, this list will update automatically!

<div align="center">

Made with ❤️ by Imranch4 for the GSoC Community

**⭐ Star this repo if you find it helpful! ⭐**

</div>
'''
        return readme_content
    
    def update_readme(self):
        """Main function to update the README with data from all available years."""
        logger.info("Starting GSoC README update...")
        
        available_years = self.get_available_years()
        
        if not available_years:
            logger.error("No GSoC data available for any year!")
            return False
        
        web_organizations_by_year = {}
        
        for year in available_years:
            logger.info(f"Processing GSoC {year}...")
            
            organizations = self.get_organizations(year)
            if not organizations:
                logger.warning(f"No organizations found for GSoC {year}")
                continue
            
            web_organizations = []
            for i, org in enumerate(organizations, 1):
                org_name = org.get('name', 'Unknown')
                logger.info(f"Analyzing {i}/{len(organizations)}: {org_name} (GSoC {year})")
                
                has_web_projects, scraped_data = self.analyze_organization_web_projects(org, year)
                if has_web_projects:
                    technologies = self.extract_web_technologies(scraped_data['technologies'])
                    web_org_data = {
                        'name': org_name,
                        'url': scraped_data.get('url', f"{BASE_URL}/programs/{year}/organizations/{org.get('slug', '')}"),
                        'description': scraped_data.get('description', org.get('description', '')),
                        'technologies': technologies,
                        'website_url': org.get('website_url', ''),
                        'slug': org.get('slug', '')
                    }
                    web_organizations.append(web_org_data)
                    logger.info(f"✓ {org_name} has web projects: {technologies}")
                
                time.sleep(0.5)
            
            web_organizations_by_year[year] = web_organizations
            logger.info(f"Found {len(web_organizations)} web organizations for GSoC {year}")
            
            with open(f"gsoc_{year}_web_organizations.json", "w", encoding="utf-8") as f:
                json.dump(web_organizations, f, indent=2, ensure_ascii=False)
        
        readme_content = self.generate_readme_content(web_organizations_by_year)
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        self.save_cached_data()
        
        total_orgs = sum(len(orgs) for orgs in web_organizations_by_year.values())
        logger.info(f"✓ README updated! Found {total_orgs} web organizations across {len(web_organizations_by_year)} years")
        
        return total_orgs

def main():
    print("GSoC Web Development Organizations Updater")
    print("=============================================")
    print("This script automatically finds GSoC organizations with web development projects.")
    print("It will check all available GSoC years and maintain historical data.\n")
    
    updater = GSoCReadmeUpdater()
    count = updater.update_readme()
    
    if count:
        current_year = datetime.now().year
        print(f"\n✓ Success! Updated {count} organizations across multiple years")
        print(f"✓ Check README.md for the complete list")
        print(f"✓ The list will auto-update weekly and when new GSoC data becomes available")
    else:
        print("\n❌ Failed to update README.md")

if __name__ == "__main__":
    main()