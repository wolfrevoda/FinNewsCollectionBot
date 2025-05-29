# 福生无量天尊
from openai import OpenAI
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import os
import argparse

class ArticleFetcher:
    """Class for fetching articles from RSS feeds"""
    
    RSS_FEEDS = {
        "💲 华尔街见闻":{
            "华尔街见闻":"https://dedicated.wallstreetcn.com/rss.xml",      
        },
        "💻 36氪":{
            "36氪":"https://36kr.com/feed",   
        },
        "🇨🇳 中国经济": {
            "香港經濟日報":"https://www.hket.com/rss/china",
            "东方财富":"http://rss.eastmoney.com/rss_partener.xml",
            "百度股票焦点":"http://news.baidu.com/n?cmd=1&class=stock&tn=rss&sub=0",
            "中新网":"https://www.chinanews.com.cn/rss/finance.xml",
            "国家统计局-最新发布":"https://www.stats.gov.cn/sj/zxfb/rss.xml",
        },
        "🇺🇸 美国经济": {
            "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
            "华尔街日报 - 市场":"https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
            "MarketWatch美股": "https://www.marketwatch.com/rss/topstories",
            "ZeroHedge华尔街新闻": "https://feeds.feedburner.com/zerohedge/feed",
            "ETF Trends": "https://www.etftrends.com/feed/",
        },
        "🌍 世界经济": {
            "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
            "BBC全球经济": "http://feeds.bbci.co.uk/news/business/rss.xml",
        },
    }

    @staticmethod
    def today_date():
        """Get current Beijing date"""
        return datetime.now(pytz.timezone("Asia/Shanghai")).date()

    @staticmethod
    def fetch_article_text(url):
        """Fetch article content from URL"""
        try:
            print(f"📰 正在爬取文章内容: {url}")
            article = Article(url)
            article.download()
            article.parse()
            text = article.text[:1500]  # Limit length to prevent API input overflow
            if not text:
                print(f"⚠️ 文章内容为空: {url}")
            return text
        except Exception as e:
            print(f"❌ 文章爬取失败: {url}，错误: {e}")
            return "（未能获取文章正文）"

    @staticmethod
    def fetch_feed_with_headers(url):
        """Fetch RSS feed with headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        return feedparser.parse(url, request_headers=headers)

    @staticmethod
    def fetch_feed_with_retry(url, retries=3, delay=5):
        """Fetch RSS feed with retry mechanism"""
        for i in range(retries):
            try:
                feed = ArticleFetcher.fetch_feed_with_headers(url)
                if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                    return feed
            except Exception as e:
                print(f"⚠️ 第 {i+1} 次请求 {url} 失败: {e}")
                time.sleep(delay)
        print(f"❌ 跳过 {url}, 尝试 {retries} 次后仍失败。")
        return None

    def fetch_rss_articles(self, max_articles=10):
        """Fetch articles from all RSS feeds"""
        news_data = {}
        analysis_text = ""  # Text for AI analysis

        for category, sources in self.RSS_FEEDS.items():
            category_content = ""
            for source, url in sources.items():
                print(f"📡 正在获取 {source} 的 RSS 源: {url}")
                feed = self.fetch_feed_with_retry(url)
                if not feed:
                    print(f"⚠️ 无法获取 {source} 的 RSS 数据")
                    continue
                print(f"✅ {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

                articles = []
                for entry in feed.entries[:5]:
                    title = entry.get('title', '无标题')
                    link = entry.get('link', '') or entry.get('guid', '')
                    if not link:
                        print(f"⚠️ {source} 的新闻 '{title}' 没有链接，跳过")
                        continue

                    article_text = self.fetch_article_text(link)
                    analysis_text += f"【{title}】\n{article_text}\n\n"

                    print(f"🔹 {source} - {title} 获取成功")
                    articles.append(f"- [{title}]({link})")

                if articles:
                    category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"

            news_data[category] = category_content

        return news_data, analysis_text


class ArticleSummarizer:
    """Class for summarizing articles using DeepSeek API"""
    
    def __init__(self, api_key):
        """Initialize with API key"""
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def summarize(self, text):
        """Generate summary using DeepSeek API"""
        completion = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位经验丰富、逻辑严谨的财经新闻分析师，服务对象为券商分析师、基金经理、金融研究员、宏观策略师等专业人士。请基于以下财经新闻原文内容，完成高质量的内容理解与结构化总结，形成一份专业、精准、清晰的财经要点摘要，用于支持机构投资者的日常研判工作。【输出要求】1.全文控制在 2000 字以内，内容精炼、逻辑清晰；2.从宏观政策、金融市场、行业动态、公司事件、风险提示等角度进行分类总结；3.每一部分要突出数据支持、趋势研判、可能的市场影响；4.明确指出新闻背后的核心变量或政策意图，并提出投资视角下的参考意义；5.语气专业、严谨、无情绪化表达，适配专业机构投研阅读习惯；6.禁止套话，不重复新闻原文，可用条列式增强结构性；7.如涉及数据和预测，请标注来源或指出主张机构（如高盛、花旗等）；8.若原文较多内容无关财经市场，可酌情略去，只保留关键影响要素。"},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content.strip()


class ResultPublisher:
    """Class for publishing results to WeChat"""
    
    def __init__(self, server_chan_keys):
        """Initialize with Server酱 keys"""
        self.server_chan_keys = server_chan_keys.split(",") if isinstance(server_chan_keys, str) else server_chan_keys

    def send_to_wechat(self, title, content):
        """Send message to WeChat via Server酱"""
        for key in self.server_chan_keys:
            url = f"https://sctapi.ftqq.com/{key}.send"
            data = {"title": title, "desp": content}
            response = requests.post(url, data=data, timeout=10)
            if response.ok:
                print(f"✅ 推送成功: {key}")
            else:
                print(f"❌ 推送失败: {key}, 响应：{response.text}")

    def generate_summary(self, news_data, summary, today_str):
        """Generate formatted summary message"""
        final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\n{summary}\n\n---\n\n"
        for category, content in news_data.items():
            if content.strip():
                final_summary += f"## {category}\n{content}\n\n"
        return final_summary


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Finance News Collection Bot')
    parser.add_argument('--openai_key', required=True, help='OpenAI API key')
    parser.add_argument('--server_chan_keys', required=True, help='Server酱 SendKeys, comma separated')
    args = parser.parse_args()

    # Initialize components
    fetcher = ArticleFetcher()
    summarizer = ArticleSummarizer(args.openai_key)
    publisher = ResultPublisher(args.server_chan_keys)

    # Get current date
    today_str = fetcher.today_date().strftime("%Y-%m-%d")
    
    # Fetch articles
    articles_data, analysis_text = fetcher.fetch_rss_articles(max_articles=5)
    
    # Generate summary
    summary = summarizer.summarize(analysis_text)

    # Publish results
    final_summary = publisher.generate_summary(articles_data, summary, today_str)
    publisher.send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)
