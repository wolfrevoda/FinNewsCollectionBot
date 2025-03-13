# 福生无量天尊
from openai import OpenAI
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import os

# OpenAI API Key 和 Server酱SendKey
openai_api_key = os.getenv("OPENAI_API_KEY")
server_chan_key = os.getenv("SERVER_CHAN_KEY")
openai_client = OpenAI(api_key=openai_api_key)

# RSS源地址列表
rss_feeds = {
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

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()

# 爬取网页正文 (用于 AI 分析，但不展示)
def fetch_article_text(url):
    try:
        print(f"📰 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            print(f"⚠️ 文章内容为空: {url}")
        return text
    except Exception as e:
        print(f"❌ 文章爬取失败: {url}，错误: {e}")
        return "（未能获取文章正文）"

# 添加 User-Agent 头
def fetch_feed_with_headers(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)


# 自动重试获取 RSS
def fetch_feed_with_retry(url, retries=3, delay=5):
    for i in range(retries):
        try:
            feed = fetch_feed_with_headers(url)
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                return feed
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次请求 {url} 失败: {e}")
            time.sleep(delay)
    print(f"❌ 跳过 {url}, 尝试 {retries} 次后仍失败。")
    return None

# 获取RSS内容（爬取正文但不展示）
def fetch_rss_articles(rss_feeds, max_articles=10):
    news_data = {}
    analysis_text = ""  # 用于 AI 分析的内容

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, url in sources.items():
            print(f"📡 正在获取 {source} 的 RSS 源: {url}")
            feed = fetch_feed_with_retry(url)
            if not feed:
                print(f"⚠️ 无法获取 {source} 的 RSS 数据")
                continue
            print(f"✅ {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

            articles = []
            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '无标题')
                link = entry.get('link', '') or entry.get('guid', '')
                if not link:
                    print(f"⚠️ {source} 的新闻 '{title}' 没有链接，跳过")
                    continue
                
                # 爬取正文（但不展示）
                article_text = fetch_article_text(link)
                
                # 添加到 AI 分析文本
                analysis_text += f"【{title}】\n{article_text}\n\n"

                print(f"🔹 {source} - {title} 获取成功")
                articles.append(f"- [{title}]({link})")  # 仅展示标题和链接
            
            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"
        
        news_data[category] = category_content
    
    return news_data, analysis_text  # 返回爬取的新闻标题/链接 & 用于 AI 分析的正文内容

# AI 生成内容摘要（基于爬取的正文）
def summarize(text):
    completion = openai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一名专业的财经新闻分析师，请根据以下新闻内容，提炼出最核心的财经要点，提供一份2000字以内的清晰摘要。请确保总结精准、逻辑清晰，并突出财经领域的核心趋势。"},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content.strip()

# 微信推送
# 发送微信推送
def send_to_wechat(title, content):
    requests.post(f"https://sctapi.ftqq.com/{server_chan_key}.send", data={
        "title": title,
        "desp": content
    })

# 主程序
if __name__ == "__main__":
    today_str = today_date().strftime("%Y-%m-%d")
    
    # 每个网站获取最多 5 篇文章
    articles, analysis_text = fetch_rss_articles(rss_feeds, max_articles=5) 

    # AI 生成摘要
    summary = summarize(analysis_text)

    # 生成最终消息（仅展示标题和链接）
    final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n"
    final_summary += f"✍️ **今日分析总结：**\n{summary}\n\n---\n\n"

    for category, content in articles.items():
        if content.strip():
            final_summary += f"## {category}\n{content}\n\n"
    
    send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)
