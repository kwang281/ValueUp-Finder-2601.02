import requests
from bs4 import BeautifulSoup
import urllib.parse

def fetch_naver_news(code):
    """
    (Deprecated) 네이버 금융에서 해당 종목의 최신 뉴스를 가져옵니다.
    """
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={code}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        news_list = []
        titles = soup.select('td.title a')
        
        for link in titles:
            title = link.text.strip()
            if title:
                news_list.append(title)
                if len(news_list) >= 5:
                    break
        return news_list

    except Exception as e:
        print(f"Error scraping Naver news for {code}: {e}")
        return ["뉴스 정보를 가져오는데 실패했습니다."]

def fetch_naver_news_search(query):
    """
    네이버 뉴스 검색을 통해 관련 기사를 가져옵니다.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        # Sort by date (sort=1) to get latest
        url = f"https://search.naver.com/search.naver?where=news&query={encoded_query}&sm=tab_opt&sort=1&photo=0&field=0&pd=0&ds=&de=&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so%3Add%2Cp%3Aall&is_sug_officeid=0"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.naver.com"
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Naver Search Result Class for News Title
        # Usually 'news_tit' class
        news_items = soup.select(".news_tit")
        
        results = []
        for item in news_items[:5]:
            title = item.get("title") # title attribute often contains full text
            if not title:
                title = item.text
            link = item.get("href")
            results.append({"title": title, "link": link})
            
        return results
        
    except Exception as e:
        print(f"Error searching Naver news for {query}: {e}")
        return []
