# 福生无量天尊
from openai import OpenAI
import feedparser
import requests
from newspaper import Article
from datetime import datetime
import time
import pytz
import os

# OpenAI API Key
# openai_client = OpenAI(api_key="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")
openai_api_key = os.getenv("OPENAI_API_KEY")
server_chan_key = os.getenv("SERVER_CHAN_KEY")
openai_client = OpenAI(api_key=openai_api_key)


# Server酱SendKey
# srz 的 SCT272699TfiTnNWUMAMHjvajyebNd6B8N
# SERVER_CHAN_KEY = "SCT272745TdQMzTMudpFDrYGFr4XOrBBgL"

# RSS源地址列表
rss_feeds = {
    "💲 华尔街见闻":{
        "华尔街见闻":"https://dedicated.wallstreetcn.com/rss.xml",      
    },
    "🇨🇳 中国经济": {
        "东方财富":"http://rss.eastmoney.com/rss_partener.xml",
        "百度股票焦点":"http://news.baidu.com/n?cmd=1&class=stock&tn=rss&sub=0",
        "中新网":"https://www.chinanews.com.cn/rss/finance.xml",
        "国家统计局-最新发布":"https://www.stats.gov.cn/sj/zxfb/rss.xml",
        "国家统计局-数据解读":"https://www.stats.gov.cn/sj/sjjd/rss.xml",
    },
      "🇺🇸 美国经济": {
        "CNN Money" :"http://rss.cnn.com/rss/money_topstories.rss",
        "MarketWatch美股": "https://www.marketwatch.com/rss/topstories",
        "ZeroHedge华尔街新闻": "https://feeds.feedburner.com/zerohedge/feed",
        "ETF Trends": "https://www.etftrends.com/feed/",
    },
    "🌍 世界经济": {
        "华尔街日报":"https://cn.wsj.com/zh-hans/rss",
        "BBC全球经济": "http://feeds.bbci.co.uk/news/business/rss.xml",
    },
}

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()


# 爬取网页正文
def fetch_article_text(url):
    try:
        print(f"📰 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]
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

# 获取RSS内容并爬取文章正文
def fetch_rss_articles(rss_feeds, max_articles=10):
    news_data = {}
    today = today_date()

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

                article_text = fetch_article_text(link)
                print(f"🔹 {source} - {title} 获取成功")

                articles.append(f"- {title}\n  {article_text}\n  [查看原文]({link})\n")
            
            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"
        
        news_data[category] = category_content
    
    return news_data

# AI生成内容摘要
def summarize(text):
    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你是一名专业的财经新闻分析师，请根据以下新闻内容，提炼出最核心的要点，提供一份1000字以内的中文清晰摘要。请确保总结精准、逻辑清晰，并突出财经领域的核心观点和关键数据，避免冗余信息。"},
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
    #每个网站获取最多5篇文章
    articles = fetch_rss_articles(rss_feeds, max_articles = 5 ) 

    final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n"
    for category, content in articles.items():
        if content.strip():
            summary = summarize(content)
            final_summary += f"## {category}\n✍️ **今日总结：** {summary}\n\n\n---\n\n{content}\n\n"
    
    send_to_wechat(title=f"📌 {today_str} 财经新闻摘要", content=final_summary)