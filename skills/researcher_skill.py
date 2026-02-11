import newspaper
from newspaper import Article
from skill_manager import Skill

class WebResearcher(Skill):
    name = "Web Researcher"
    description = "Scrapes and summarizes news or documentation from URLs."
    keywords = ["summarize", "research", "news", "what's happening", "article"]
    supported_intents = ["researcher_skill"]
    def run(self, parameters: dict):
        text = parameters.get("user_input", "").lower()

        # --- 1. RESEARCH A SPECIFIC URL ---
        if "http" in text:
            # Extract the URL from the text
            url = [word for word in text.split() if "http" in word][0]
            try:
                article = Article(url)
                article.download()
                article.parse()
                
                # Perform NLP (Summary & Keywords)
                article.nlp()
                
                response = f"### 📰 Summary: {article.title}\n"
                response += f"> {article.summary[:500]}...\n\n"
                response += f"**Key Points:** {', '.join(article.keywords[:5])}"
                return response
            except Exception as e:
                return f"I couldn't reach that site. The galactic firewall might be up. Error: {e}"

        # --- 2. GET NEWS BRIEFING ---
        if "news" in text or "happening" in text:
            site_url = "https://www.bbc.com/news" # Default source
            if "tech" in text: site_url = "https://techcrunch.com"
            
            paper = newspaper.build(site_url, memoize_articles=False)
            briefing = [f"Here is your briefing from {site_url}:"]
            
            # Get the top 3 headlines
            for i, article in enumerate(paper.articles[:3]):
                article.download()
                article.parse()
                briefing.append(f"{i+1}. **{article.title}**")
            
            return "\n".join(briefing) + "\n\nWould you like me to summarize any of these for you?"

        return "Please provide a URL to summarize or ask for 'the news'."