import requests
import time
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus
from skill_manager import Skill
import re

# Conditional import for DuckDuckGo
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    print("⚠️ [OSINT]: duckduckgo-search not installed. Install with: pip install duckduckgo-search")
    DDGS_AVAILABLE = False

@dataclass
class SearchResult:
    name: str
    source: str
    url: str
    description: str
    confidence: float
    timestamp: str

class OSINTSkill(Skill):
    name = "OSINT Investigator"
    description = "Open Source Intelligence gathering and investigation"

    keywords = [
    "find", "search for", "look up", "who is",
    "investigate", "background check", "osint",
    "profile", "dossier", "social media",
    "research", "information", "person search",
    "company search"
    ]

    supported_intents = ["osint_investigator"]

    def __init__(self):
        self.max_results = 10
        self.history_path = "core/osint_history.json"
        self.history = self._load_history()
        
        # Common data sources
        self.data_sources = {
            "social_media": {
                "linkedin": "https://www.linkedin.com/search/results/all/?keywords={}",
                "twitter": "https://twitter.com/search?q={}&src=typed_query",
                "facebook": "https://www.facebook.com/public/{}",
                "instagram": "https://www.instagram.com/{}/",
                "github": "https://github.com/search?q={}&type=users",
                "reddit": "https://www.reddit.com/search/?q={}"
            },
            "public_records": {
                "google": "https://www.google.com/search?q={}",
                "wikipedia": "https://en.wikipedia.org/wiki/{}",
                "crunchbase": "https://www.crunchbase.com/textsearch?q={}",
                "angel_list": "https://angel.co/search?q={}",
                "indeed": "https://www.indeed.com/resumes?q={}"
            },
            "email_phone": {
                "haveibeenpwned": "https://haveibeenpwned.com/account/{}",
                "truecaller": "https://www.truecaller.com/search/{}",
                "whitepages": "https://www.whitepages.com/name/{}"
            }
        }
        
        # Search patterns
        self.search_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
            "username": r'@[\w\d_]+',
            "domain": r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)\b'
        }
        
        print("✅ [OSINT]: Investigator initialized")

    def _load_history(self):
        """Load search history"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_history(self, query: str, results: List[SearchResult]):
        """Save search to history"""
        try:
            search_entry = {
                "query": query,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "result_count": len(results),
                "sources": list(set(r.source for r in results))
            }
            self.history.append(search_entry)
            
            # Keep only last 50 searches
            if len(self.history) > 50:
                self.history = self.history[-50:]
            
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            with open(self.history_path, "w") as f:
                json.dump(self.history, f, indent=2)
        except:
            pass

    def _identify_query_type(self, query: str) -> Dict[str, str]:
        """Identify what type of information is being searched"""
        query_lower = query.lower()
        
        # Check for email
        email_match = re.search(self.search_patterns["email"], query)
        if email_match:
            return {"type": "email", "value": email_match.group()}
        
        # Check for phone
        phone_match = re.search(self.search_patterns["phone"], query)
        if phone_match:
            return {"type": "phone", "value": phone_match.group()}
        
        # Check for username
        username_match = re.search(self.search_patterns["username"], query)
        if username_match:
            return {"type": "username", "value": username_match.group()}
        
        # Check for domain/website
        domain_match = re.search(self.search_patterns["domain"], query_lower)
        if domain_match:
            return {"type": "domain", "value": domain_match.group(1)}
        
        # Check for person name
        name_words = query.split()
        if len(name_words) >= 2 and any(word.istitle() for word in name_words):
            return {"type": "person", "value": query}
        
        # Check for company
        company_indicators = ["inc", "llc", "corp", "ltd", "company", "tech", "software", "lab"]
        if any(indicator in query_lower for indicator in company_indicators):
            return {"type": "company", "value": query}
        
        # Default to general search
        return {"type": "general", "value": query}

    def _search_duckduckgo(self, query: str, query_type: str) -> List[SearchResult]:
        """Search using DuckDuckGo"""
        if not DDGS_AVAILABLE:
            return []
        
        try:
            results = []
            search_queries = []
            
            # Build search queries based on type
            if query_type == "person":
                search_queries = [
                    query,
                    f"{query} linkedin",
                    f"{query} twitter",
                    f"{query} github"
                ]
            elif query_type == "company":
                search_queries = [
                    query,
                    f"{query} crunchbase",
                    f"{query} reviews",
                    f"{query} company"
                ]
            elif query_type == "email":
                search_queries = [
                    query,
                    f'"{query}"',
                    f"email {query}",
                    f"{query} breach"
                ]
            else:
                search_queries = [query]
            
            with DDGS() as ddgs:
                for search_query in search_queries[:3]:  # Limit to 3 queries
                    for r in ddgs.text(search_query, max_results=5):
                        source = self._extract_source(r.get('href', ''))
                        results.append(SearchResult(
                            name=query,
                            source=source,
                            url=r.get('href', ''),
                            description=r.get('body', 'No description available'),
                            confidence=0.7 if query_type == "person" else 0.6,
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                        ))
                    
                    # Add small delay between queries
                    time.sleep(0.5)
            
            return results
            
        except Exception as e:
            print(f"⚠️ [OSINT]: DuckDuckGo search failed: {e}")
            return []

    def _extract_source(self, url: str) -> str:
        """Extract source name from URL"""
        url_lower = url.lower()
        
        source_map = {
            'linkedin.com': 'LinkedIn',
            'twitter.com': 'Twitter/X',
            'x.com': 'Twitter/X',
            'facebook.com': 'Facebook',
            'instagram.com': 'Instagram',
            'github.com': 'GitHub',
            'wikipedia.org': 'Wikipedia',
            'crunchbase.com': 'Crunchbase',
            'angel.co': 'AngelList',
            'indeed.com': 'Indeed',
            'reddit.com': 'Reddit',
            'youtube.com': 'YouTube',
            'medium.com': 'Medium',
            'stackoverflow.com': 'Stack Overflow',
            'producthunt.com': 'Product Hunt'
        }
        
        for domain, name in source_map.items():
            if domain in url_lower:
                return name
        
        # Check for news sites
        news_domains = ['cnn.com', 'bbc.com', 'reuters.com', 'bloomberg.com', 'wsj.com', 'nytimes.com']
        for domain in news_domains:
            if domain in url_lower:
                return 'News'
        
        return 'Web'

    def _generate_direct_links(self, query: str, query_type: str) -> List[SearchResult]:
        """Generate direct search links for various platforms"""
        results = []
        
        # Social media links
        for platform, url_template in self.data_sources["social_media"].items():
            encoded_query = quote_plus(query)
            url = url_template.format(encoded_query)
            
            results.append(SearchResult(
                name=query,
                source=platform.title(),
                url=url,
                description=f"Direct search link for {query} on {platform}",
                confidence=0.5,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        return results

    def _format_results(self, query: str, query_info: Dict, results: List[SearchResult]) -> str:
        """Format OSINT results"""
        query_type = query_info["type"]
        query_value = query_info["value"]
        
        output = []
        
        # Header
        output.append(f"🔍 **OSINT Investigation Report**")
        output.append("=" * 60)
        output.append(f"**Target:** {query_value}")
        output.append(f"**Type:** {query_type.title()}")
        output.append(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        
        if not results:
            output.append("❌ No public information found.")
            output.append("")
            output.append("💡 **Suggestions:**")
            output.append("• Try different search terms")
            output.append("• Include location or additional identifiers")
            output.append("• Check privacy settings on social media")
            return "\n".join(output)
        
        # Group results by source type
        social_results = [r for r in results if r.source in ['LinkedIn', 'Twitter/X', 'Facebook', 'Instagram', 'GitHub']]
        web_results = [r for r in results if r.source in ['Wikipedia', 'Crunchbase', 'News', 'Web']]
        direct_links = [r for r in results if r.confidence <= 0.5]
        
        # Social Media Findings
        if social_results:
            output.append("📱 **Social Media Profiles:**")
            for result in social_results[:5]:  # Top 5 social results
                confidence_icon = "🟢" if result.confidence > 0.6 else "🟡"
                output.append(f"• **{result.source}** {confidence_icon}")
                output.append(f"  {result.url}")
                if len(result.description) > 100:
                    output.append(f"  *{result.description[:100]}...*")
                output.append("")
        
        # Web/News Findings
        if web_results:
            output.append("🌐 **Web/News References:**")
            for result in web_results[:5]:  # Top 5 web results
                output.append(f"• **{result.source}**")
                output.append(f"  {result.url}")
                if len(result.description) > 100:
                    output.append(f"  *{result.description[:100]}...*")
                output.append("")
        
        # Direct Search Links
        if direct_links and (not social_results and not web_results):
            output.append("🔗 **Search Directly On:**")
            platforms = list(set(r.source for r in direct_links))
            for platform in platforms[:6]:  # Top 6 platforms
                platform_results = [r for r in direct_links if r.source == platform]
                if platform_results:
                    output.append(f"• **{platform}**: {platform_results[0].url}")
            output.append("")
        
        # Statistics
        output.append("📊 **Summary:**")
        output.append(f"• Total sources checked: {len(results)}")
        output.append(f"• Social media profiles found: {len(social_results)}")
        output.append(f"• Web references found: {len(web_results)}")
        output.append("")
        
        # Recommendations based on query type
        output.append("💡 **Next Steps:**")
        if query_type == "person":
            output.append("• Check public records in their location")
            output.append("• Look for professional publications or patents")
            output.append("• Search for associated companies or projects")
        elif query_type == "company":
            output.append("• Check SEC filings for public companies")
            output.append("• Look for news articles about funding or acquisitions")
            output.append("• Search for employee reviews on Glassdoor")
        elif query_type == "email":
            output.append("• Check Have I Been Pwned for breaches")
            output.append("• Search for associated usernames")
            output.append("• Look for domain registration information")
        else:
            output.append("• Try more specific search terms")
            output.append("• Include dates or locations if relevant")
            output.append("• Check multiple search engines")
        
        output.append("")
        output.append("⚠️ **Disclaimer:** This is public information only.")
        output.append("   Respect privacy and follow legal guidelines.")
        
        return "\n".join(output)

    def run(self, parameters: Dict[str, Any]) -> str:
        user_input = parameters.get("user_input", "").strip()
        
        print(f"🔍 [OSINT]: Processing: '{user_input}'")
        
        if not user_input:
            return "I need something to search for. Try: 'find John Smith' or 'search for Tesla Inc'"
        
        # Clean the query
        triggers = ["find ", "search for ", "look up ", "who is ", "investigate ", 
                   "background check on ", "osint on ", "research ", "information about "]
        
        query = user_input.lower()
        for trigger in triggers:
            if query.startswith(trigger):
                query = user_input[len(trigger):].strip()
                break
        
        if not query or len(query) < 2:
            return "Please provide a proper search term (at least 2 characters)."
        
        # Identify query type
        query_info = self._identify_query_type(query)
        print(f"🔍 [OSINT]: Query type: {query_info['type']}, Value: {query_info['value']}")
        
        # Perform searches
        all_results = []
        
        # Use DuckDuckGo if available
        if DDGS_AVAILABLE:
            ddg_results = self._search_duckduckgo(query_info["value"], query_info["type"])
            all_results.extend(ddg_results)
        
        # Generate direct links as fallback
        direct_results = self._generate_direct_links(query_info["value"], query_info["type"])
        all_results.extend(direct_results)
        
        # Remove duplicates (by URL)
        unique_results = []
        seen_urls = set()
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        # Save to history
        self._save_history(query, unique_results)
        
        # Format and return results
        return self._format_results(query, query_info, unique_results)

# Test function
def test_osint():
    """Test the OSINT skill"""
    skill = OSINTSkill()
    
    test_queries = [
        "find Elon Musk",
        "search for Tesla company",
        "who is Satoshi Nakamoto",
        "investigate Microsoft",
        "help",
    ]
    
    print("\n🔍 Testing OSINT Investigator:")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n🔘 Query: {query}")
        result = skill.run({"user_input": query})
        print(f"📊 Result:\n{result}")
        time.sleep(2)

if __name__ == "__main__":
    test_osint()