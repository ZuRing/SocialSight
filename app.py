#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SocialSight - 社交平台舆情分析系统
基于真实数据的情感分析工具
"""

import os
import sys
import json
import re
import time
import hashlib
from datetime import datetime
from collections import Counter
from urllib.parse import quote, urlencode
from functools import wraps

# ===== Flask =====
from flask import Flask, render_template, request, jsonify, session, send_file

app = Flask(__name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
)
app.secret_key = "socialsight_secret_key_change_me"
app.config["REPORTS_DIR"] = os.path.join(os.path.dirname(__file__), "reports")

# =============================================
# 情感分析
# =============================================

POSITIVE_WORDS = set([
    "好喝", "不错", "喜欢", "推荐", "回购", "正宗", "新鲜", "纯正", "天然",
    "健康", "营养", "好味道", "真材实料", "良心", "好评", "满意", "太棒了",
    "值得", "很好", "完美", "实在", "靠谱", "赞", "优秀", "惊艳",
    "惊喜", "放心", "安心", "地道", "真不错", "高品质", "划算",
    "超值", "性价比", "信赖", "坚持", "支持", "国货", "回头客",
    "无限回购", "强烈推荐", "太好喝了", "无敌", "太好吃了",
    "口感好", "想喝", "买了", "已购", "再次购买", "经常买",
    "宝藏", "国货之光", "神仙饮品", "相见恨晚", "种草", "值得买",
    "真心", "好用", "果然", "终于找到", "无限回购", "囤货", "不错哦",
    "好", "棒", "赞", "美", "靓", "正", "牛", "绝", "强",
    "大爱", "最爱", "超爱", "好好喝", "超好喝", "非常好喝", "很好喝",
    "特别好", "超级好", "一级棒", "没毛病", "没问题", "物美价廉",
    "品质好", "服务好", "包装好", "物流快", "发货快", "正品",
    "第一次买", "还会再买", "还会回购", "推荐购买", "值得购买",
    "口感不错", "味道不错", "价格实惠", "真的不错", "挺好的",
])

NEGATIVE_WORDS = set([
    "难喝", "不好喝", "假的", "假货", "骗人", "虚假", "欺骗", "上当",
    "差评", "垃圾", "别买", "不值", "后悔", "太贵", "不值这个价",
    "智商税", "坑", "踩雷", "避雷", "避坑", "谨慎", "不敢", "投诉",
    "退款", "退货", "差", "烂", "恶心", "难吃", "不新鲜", "过期",
    "变质", "怀疑", "失望", "不行", "太差", "无语", "离谱", "呵呵",
    "曝光", "维权", "12315", "举报", "偷工减料", "糊弄", "敷衍",
    "虚假宣传", "标签不符", "配料表问题", "添加剂", "防腐剂", "勾兑",
    "浓缩汁", "兑水", "不是纯果汁", "不纯", "味道怪", "口感差",
    "品质差", "不敢喝了", "再也不敢", "拔草", "劝退",
    "翻车", "暴雷", "一言难尽", "什么玩意", "算了",
    "客服差", "态度差", "性价比低", "一般般", "还行吧", "凑合",
    "将就", "勉强", "不合口味", "很一般", "不如", "比不上",
    "吹过头", "过度营销", "割韭菜", "交了智商税", "上当受骗",
    "再也不买", "不会再买", "没效果", "没用", "不好", "不行",
    "太差劲", "太垃圾", "垃圾产品", "差评差评", "已退货", "申请退款",
    "质量差", "质量不好", "破损", "漏液", "过期产品", "发霉",
    "异味", "怪味", "口感不好", "喝不下去", "扔了", "倒了",
])

def analyze_sentiment(text):
    """基于关键词的情感分析（含否定词翻转）"""
    if not text:
        return "中性", 0, 0
    text_lower = text.lower()
    
    # 否定词：出现在情感词前会翻转情感
    NEGATION_WORDS = ["没", "不", "没有", "未", "别", "勿", "毫无", "不能", "不会", "不是", "没让", "不让", "不会让"]
    
    pos_count = 0
    neg_count = 0
    
    # 为每个情感词检查其前面是否有否定词
    def check_negated(idx, word_len):
        """检查情感词前 4 个字符内是否有否定词"""
        start = max(0, idx - 4)
        prefix = text_lower[start:idx]
        return any(nw in prefix for nw in NEGATION_WORDS)
    
    for w in POSITIVE_WORDS:
        idx = text_lower.find(w)
        if idx >= 0:
            if check_negated(idx, len(w)):
                neg_count += 1  # 正面词被否定 → 负面
            else:
                pos_count += 1
    
    for w in NEGATIVE_WORDS:
        idx = text_lower.find(w)
        if idx >= 0:
            if check_negated(idx, len(w)):
                pos_count += 1  # 负面词被否定 → 正面（如"没让我失望"）
            else:
                neg_count += 1
    
    if pos_count > neg_count * 1.5:
        return "正面", pos_count, neg_count
    elif neg_count > pos_count * 1.5:
        return "负面", pos_count, neg_count
    else:
        return "中性", pos_count, neg_count

def extract_keywords(texts, top_n=20):
    """提取高频关键词"""
    all_words = []
    for text in texts:
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        all_words.extend(words)
    stop_words = {"这个", "那个", "什么", "怎么", "因为", "所以", "但是", "如果",
                  "可以", "没有", "不是", "就是", "还是", "只是", "但是", "而且",
                  "或者", "虽然", "不过", "一个", "我们", "他们", "你们", "自己",
                  "知道", "觉得", "看到", "应该", "已经", "还有", "这样", "那样",
                  "之后", "之前", "就是", "而是", "还是", "还有", "等等", "等等",
                  "不会", "不能", "可能", "需要", "已经", "这么", "那么", "怎么",
                  "展开", "全文", "收起", "网页链接", "转发", "评论", "赞", "微博",
                  "分享", "图片", "链接", "查看", "回复", "举报", "编辑", "删除"}
    counter = Counter(w for w in all_words if w not in stop_words and len(w) >= 2)
    return [{"word": w, "count": c} for w, c in counter.most_common(top_n) if c > 0]


def is_relevant(text, keyword):
    """判断内容是否与搜索关键词相关"""
    if not keyword or not text:
        return True
    kw = keyword.replace(" ", "")
    if len(kw) >= 2:
        return kw in text
    return kw in text


# =============================================
# 数据采集器
# =============================================

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

class WeiboCollector:
    """微博搜索采集器"""
    
    SEARCH_URL = "https://s.weibo.com/weibo"
    
    def __init__(self, cookies_str=""):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        if cookies_str:
            for item in cookies_str.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    self.session.cookies.set(k, v, domain=".weibo.com")
    
    def search(self, keyword, pages=2):
        posts = []
        for page in range(1, pages + 1):
            try:
                r = self.session.get(self.SEARCH_URL, params={"q": keyword, "page": page}, timeout=15)
                r.encoding = "utf-8"
                cards = re.findall(r'<div class="card-wrap"[^>]*>.*?</div>\s*</div>\s*</div>', r.text, re.DOTALL)
                for card in cards[:30]:
                    post = self._parse_card(card)
                    if post and is_relevant(post["content"], keyword):
                        posts.append(post)
                time.sleep(1)
            except Exception as e:
                pass
        return posts
    
    def _parse_card(self, card):
        try:
            user_match = re.search(r'class="name"[^>]*>([^<]+)', card)
            content_match = re.search(r'<p class="txt"[^>]*>(.*?)</p>', card, re.DOTALL)
            time_match = re.search(r'<span class="time"[^>]*>([^<]+)', card)
            url_match = re.search(r'href="(https?://weibo\.com/\d+/\w+[^"]*)"', card) or re.search(r'href="(//weibo\.com/\d+/\w+[^"]*)"', card)
            
            user = user_match.group(1).strip() if user_match else "未知"
            content_raw = content_match.group(1) if content_match else ""
            content = re.sub(r'<[^>]+>', '', content_raw).strip()
            pub_time = time_match.group(1).strip() if time_match else ""
            
            if not content or len(content) < 3:
                return None
            
            sentiment, pos, neg = analyze_sentiment(content)
            post_url = ""
            if url_match:
                post_url = url_match.group(1)
                if post_url.startswith("//"):
                    post_url = "https:" + post_url
            return {
                "platform": "微博",
                "user": user,
                "content": content[:800],
                "time": pub_time,
                "url": post_url,
                "sentiment": sentiment,
                "pos_score": pos,
                "neg_score": neg,
            }
        except:
            return None


class BilibiliCollector:
    """B站搜索采集器（开放API，无需登录）"""
    
    SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/all/v2"
    
    def __init__(self, cookies_str=""):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    def search(self, keyword, pages=2):
        posts = []
        for page in range(1, pages + 1):
            try:
                params = {"keyword": keyword, "page": page}
                r = self.session.get(self.SEARCH_URL, params=params, timeout=15)
                data = r.json()
                if data.get("code") == 0:
                    for section in data.get("data", {}).get("result", []):
                        if section.get("result_type") == "video":
                            for v in section.get("data", []):
                                title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                                # 关键词过滤：只保留标题包含关键词的视频
                                if not is_relevant(title, keyword):
                                    continue
                                sentiment, pos, neg = analyze_sentiment(title)
                                posts.append({
                                    "platform": "B站",
                                    "user": v.get("author", "未知"),
                                    "content": title,
                                    "time": "",
                                    "sentiment": sentiment,
                                    "pos_score": pos,
                                    "neg_score": neg,
                                    "url": v.get("arcurl", f"https://www.bilibili.com/video/{v.get('bvid','')}"),
                                    "play": v.get("play", 0),
                                    "review": v.get("video_review", 0),
                                })
                time.sleep(0.5)
            except:
                pass
        return posts


class JDCollector:
    """京东评论采集器"""
    
    def __init__(self, cookies_str=""):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    def search_products(self, keyword):
        products = []
        try:
            url = f"https://search.jd.com/Search?keyword={quote(keyword)}&enc=utf-8"
            r = self.session.get(url, timeout=15)
            r.encoding = "utf-8"
            items = re.findall(r'data-sku="(\d+)"[\s\S]{0,200}?<em[^>]*>([\s\S]*?)</em>', r.text)
            seen = set()
            for sku_id, name_html in items[:5]:
                if sku_id not in seen:
                    seen.add(sku_id)
                    name = re.sub(r'<[^>]+>', '', name_html).strip()
                    products.append({"id": sku_id, "name": name})
            time.sleep(1)
        except:
            pass
        return products
    
    def get_comments(self, product_id, pages=2):
        comments = []
        for page in range(pages):
            try:
                url = f"https://club.jd.com/comment/productPageComments.action?productId={product_id}&score=0&sortType=5&page={page}&pageSize=10"
                r = self.session.get(url, timeout=15)
                data = r.json()
                for item in data.get("comments", []):
                    content = item.get("content", "")
                    score = item.get("score", 3)
                    sentiment, pos, neg = analyze_sentiment(content)
                    if score >= 4:
                        sentiment = "正面"
                    elif score <= 2:
                        sentiment = "负面"
                    comments.append({
                        "platform": "京东",
                        "user": item.get("nickname", "匿名"),
                        "content": content[:500],
                        "time": item.get("creationTime", ""),
                        "url": f"https://item.jd.com/{product_id}.html",
                        "sentiment": sentiment,
                        "pos_score": pos,
                        "neg_score": neg,
                        "score": score,
                    })
                time.sleep(0.5)
            except:
                pass
        return comments


class XiaohongshuCollector:
    """小红书搜索采集器 - 用 Playwright 浏览器绕过反爬"""
    
    def __init__(self, cookies_str=""):
        self.cookies_str = cookies_str
    
    def search(self, keyword, pages=2):
        """用 Playwright 浏览器搜索小红书"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return [], "未安装 Playwright，请运行: pip install playwright"
        
        # 检查 Chromium 是否可用（服务器环境无浏览器则跳过）
        try:
            sync_playwright().start()
        except Exception:
            return [], "当前环境无浏览器（在线演示环境），请本地运行或手动提供小红书数据"
        
        posts = []
        error_msg = ""
        _pw = None
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ])
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    locale="zh-CN",
                )
                
                # 设置 cookie
                if self.cookies_str:
                    for item in self.cookies_str.split(";"):
                        item = item.strip()
                        if "=" in item:
                            k, v = item.split("=", 1)
                            try:
                                context.add_cookies([{
                                    "name": k.strip(), "value": v.strip(),
                                    "domain": ".xiaohongshu.com", "path": "/",
                                }])
                            except:
                                pass
                
                page = context.new_page()
                
                # 先访问首页
                try:
                    page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                except:
                    pass
                
                # 搜索
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_search_result_notes"
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)
                
                # 检查是否被拦截
                page_title = page.title()
                body_text = page.evaluate("() => document.body.innerText")[:200]
                if "安全验证" in body_text or "登录" in page_title:
                    browser.close()
                    return [], "小红书反爬拦截（需要验证码），建议在浏览器中手动搜索后粘贴结果"
                
                # 自动滚动加载，增量收集数据
                all_notes = {}  # noteId -> data
                max_scrolls = 15
                no_new_count = 0
                for i in range(max_scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.2)
                    # 收集当前可见的卡片
                    cards_data = page.evaluate("""() => {
                        const cards = document.querySelectorAll('.note-item');
                        const results = [];
                        for (const card of cards) {
                            const noteId = card.getAttribute('data-note-id') || '';
                            if (!noteId) continue;
                            const titleEl = card.querySelector('.title, [class*="title"]');
                            const title = titleEl ? titleEl.innerText.trim() : '';
                            const authorEl = card.querySelector('.author .name, [class*="author"] .name');
                            const author = authorEl ? authorEl.innerText.trim() : '';
                            const timeEl = card.querySelector('.author .time, [class*="author"] .time');
                            const time = timeEl ? timeEl.innerText.trim() : '';
                            const aTags = card.querySelectorAll('a');
                            let noteUrl = '';
                            for (const a of aTags) {
                                const href = a.getAttribute('href') || '';
                                if (href.includes('/search_result/') && href.includes('xsec_token=')) {
                                    noteUrl = 'https://www.xiaohongshu.com' + href;
                                    break;
                                }
                            }
                            if (!noteUrl && noteId) {
                                noteUrl = 'https://www.xiaohongshu.com/explore/' + noteId;
                            }
                            results.push({noteId, title, author, time, url: noteUrl});
                        }
                        return results;
                    }""")
                    new_notes = 0
                    for nd in cards_data:
                        nid = nd.get("noteId", "")
                        if nid and nid not in all_notes:
                            all_notes[nid] = nd
                            new_notes += 1
                    if new_notes == 0:
                        no_new_count += 1
                        if no_new_count >= 3:
                            break
                    else:
                        no_new_count = 0
                
                # 提取为最终数据
                for note_id, nd in all_notes.items():
                    title = nd.get("title", "")
                    content_text = title
                    if not content_text:
                        continue
                    if not is_relevant(content_text, keyword):
                        continue
                    sentiment, pos, neg = analyze_sentiment(content_text)
                    posts.append({
                        "platform": "小红书",
                        "user": nd.get("author", "小红书用户"),
                        "content": content_text[:300],
                        "time": nd.get("time", ""),
                        "url": nd.get("url", f"https://www.xiaohongshu.com/explore/{note_id}"),
                        "sentiment": sentiment,
                        "pos_score": pos,
                        "neg_score": neg,
                        "likes": 0,
                    })
                
                browser.close()
                
                if not posts:
                    error_msg = f"未能提取到内容（页面标题: {page_title[:40]}），可能需登录"
                else:
                    error_msg = f"浏览器提取 {len(posts)} 条（如不完整建议多滚几页）" if len(posts) < 5 else ""
                
                return posts, error_msg
                
        except Exception as e:
            return [], f"浏览器自动化失败: {str(e)[:80]}"
    
    def search_api(self, keyword, pages=2):
        """后备：API 方式（可能被拦截）"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://www.xiaohongshu.com",
            "Referer": "https://www.xiaohongshu.com/",
            "Content-Type": "application/json;charset=UTF-8",
        })
        if self.cookies_str:
            for item in self.cookies_str.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    session.cookies.set(k, v, domain=".xiaohongshu.com")
        
        posts = []
        try:
            data = {"keyword": keyword, "page": "1", "page_size": "20", "sort": "general", "note_type": 0}
            r = session.post("https://edith.xiaohongshu.com/api/sns/web/v1/search/notes", json=data, timeout=15)
            result = r.json()
            if result.get("success"):
                for item in result.get("data", {}).get("items", []):
                    note = item.get("note_card", {})
                    title = note.get("display_title", "")
                    desc = note.get("desc", "")
                    content = f"{title} {desc}"
                    sentiment, pos, neg = analyze_sentiment(content)
                    posts.append({
                        "platform": "小红书",
                        "user": note.get("user", {}).get("nickname", "未知"),
                        "content": content[:500],
                        "time": "",
                        "sentiment": sentiment,
                        "pos_score": pos,
                        "neg_score": neg,
                        "likes": note.get("interact_info", {}).get("liked_count", 0),
                    })
        except:
            pass
        return posts, "API 方式"
def generate_report(all_posts, keyword, platforms_used):
    """生成暗色主题 HTML 报告，含多图表数据可视化"""
    total = len(all_posts)
    positive = sum(1 for p in all_posts if p["sentiment"] == "正面")
    negative = sum(1 for p in all_posts if p["sentiment"] == "负面")
    neutral = total - positive - negative
    
    # 按平台统计
    platform_stats = {}
    for p in all_posts:
        plat = p["platform"]
        if plat not in platform_stats:
            platform_stats[plat] = {"total": 0, "正面": 0, "负面": 0, "中性": 0}
        platform_stats[plat]["total"] += 1
        sentiment_key = p["sentiment"]
        if sentiment_key == "正面":
            platform_stats[plat]["正面"] += 1
        elif sentiment_key == "负面":
            platform_stats[plat]["负面"] += 1
        else:
            platform_stats[plat]["中性"] += 1
    
    # 关键词
    keywords = extract_keywords([p["content"] for p in all_posts])
    
    # 分类帖子（全部显示）
    pos_posts = sorted([p for p in all_posts if p["sentiment"] == "正面"], key=lambda p: len(p.get("url","")), reverse=True)
    neg_posts = sorted([p for p in all_posts if p["sentiment"] == "负面"], key=lambda p: len(p.get("url","")), reverse=True)
    neu_posts = [p for p in all_posts if p["sentiment"] == "中性"]
    
    # 计算正面率/负面率
    pos_rate = round(positive / total * 100, 1) if total else 0
    neg_rate = round(negative / total * 100, 1) if total else 0
    neu_rate = round(neutral / total * 100, 1) if total else 0
    
    # 情感倾向判断
    if pos_rate >= 60:
        sentiment_label = "正面倾向"
        sentiment_color = "#4CAF50"
    elif neg_rate >= 40:
        sentiment_label = "负面倾向"
        sentiment_color = "#F44336"
    else:
        sentiment_label = "中性偏正面" if pos_rate > neg_rate else "中性偏负面"
        sentiment_color = "#FFB300"
    
    # 数据JSON
    plat_labels = json.dumps(list(platform_stats.keys()), ensure_ascii=False)
    plat_pos = json.dumps([platform_stats[p]["正面"] for p in platform_stats], ensure_ascii=False)
    plat_neg = json.dumps([platform_stats[p]["负面"] for p in platform_stats], ensure_ascii=False)
    plat_neu = json.dumps([platform_stats[p]["中性"] for p in platform_stats], ensure_ascii=False)
    kw_labels = json.dumps([k["word"] for k in keywords[:12]], ensure_ascii=False)
    kw_counts = json.dumps([k["count"] for k in keywords[:12]], ensure_ascii=False)
    
    # 帖子渲染
    def render_post(p):
        color = {"正面": "#4CAF50", "负面": "#F44336", "中性": "#9E9E9E"}.get(p["sentiment"], "#999")
        label = {"正面": "+", "负面": "−", "中性": "="}.get(p["sentiment"], "?")
        url = p.get("url", "")
        link = f'<a href="{url}" target="_blank" class="pl">查看原文</a>' if url else ""
        return f'<div class="pc"><div class="pch"><span class="plt">{p["platform"]}</span><span class="usr">{p["user"]}</span><span class="t">{p.get("time","")}</span><span class="sg" style="background:{color}">{label} {p["sentiment"]}</span>{link}</div><div class="pct">{p["content"][:300]}</div></div>'
    
    pos_html = "".join(render_post(p) for p in pos_posts) or '<p style="color:#6b6f76;text-align:center;padding:20px;">暂无正面评价数据</p>'
    neg_html = "".join(render_post(p) for p in neg_posts) or '<p style="color:#6b6f76;text-align:center;padding:20px;">暂无负面评价数据</p>'
    neu_html = "".join(render_post(p) for p in neu_posts) or '<p style="color:#6b6f76;text-align:center;padding:20px;">暂无中性内容数据</p>'
    kw_html = "".join(f'<span class="kw">{k["word"]}<span class="kc">{k["count"]}</span></span>' for k in keywords[:25])
    
    # 滚动容器
    pos_scroll = f'<div class="scroll-box">{pos_html}</div>'
    neg_scroll = f'<div class="scroll-box">{neg_html}</div>'
    neu_scroll = f'<div class="scroll-box">{neu_html}</div>'
    
    now = datetime.now()
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>舆情分析报告 - {keyword}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{margin:0;padding:0;box-sizing:border-box;}}
body {{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#1a1d23;color:#e4e7eb;}}
.hdr {{background:#1a1d23;border-bottom:1px solid #2a2d33;padding:32px 24px;text-align:center;}}
.hdr h1 {{font-size:24px;font-weight:600;color:#f0f2f5;letter-spacing:-0.02em;}}
.hdr .sub {{font-size:13px;color:#8b8f96;margin-top:6px;}}
.hdr-s {{display:flex;justify-content:center;gap:24px;margin-top:28px;flex-wrap:wrap;}}
.hdr-s .k {{text-align:center;}}
.hdr-s .kv {{font-size:30px;font-weight:700;}}
.hdr-s .kl {{font-size:11px;color:#6b6f76;text-transform:uppercase;letter-spacing:0.04em;margin-top:2px;}}
.ctr {{max-width:1100px;margin:0 auto;padding:20px;}}
.cd {{background:#22252b;border-radius:10px;padding:24px;margin-bottom:16px;border:1px solid #2a2d33;}}
.cd h2 {{font-size:15px;font-weight:600;color:#c8cbd0;margin-bottom:16px;letter-spacing:0.02em;}}
.cr {{display:flex;gap:16px;flex-wrap:wrap;}}
.cb {{flex:1;min-width:280px;height:280px;position:relative;}}
/* 帖子卡片 */
.pc {{border:1px solid #2a2d33;border-radius:8px;padding:12px;margin-bottom:8px;background:#1a1d23;}}
.pch {{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:6px;flex-wrap:wrap;}}
.plt {{background:#2a2d33;color:#8b8f96;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;}}
.usr {{font-weight:500;color:#e4e7eb;}}
.t {{color:#6b6f76;font-size:12px;}}
.sg {{padding:2px 10px;border-radius:10px;color:#fff;font-size:11px;}}
.pl {{color:#c04a1a;font-size:12px;text-decoration:none;margin-left:auto;}}
.pl:hover {{text-decoration:underline;}}
.pct {{font-size:14px;color:#c8cbd0;line-height:1.5;}}
/* 滚动容器 */
.scroll-box {{max-height:400px;overflow-y:auto;padding-right:4px;}}
.scroll-box::-webkit-scrollbar {{width:5px;}}
.scroll-box::-webkit-scrollbar-track {{background:#1a1d23;border-radius:3px;}}
.scroll-box::-webkit-scrollbar-thumb {{background:#33363d;border-radius:3px;}}
.scroll-box::-webkit-scrollbar-thumb:hover {{background:#555;}}
/* 关键词 */
.kw {{display:inline-block;background:#1a1d23;border:1px solid #33363d;padding:5px 14px;border-radius:6px;margin:4px;font-size:13px;color:#c8cbd0;}}
.kw .kc {{color:#c04a1a;font-size:11px;margin-left:4px;}}
/* 声明 */
.alert {{background:#1f1a14;border:1px solid #c04a1a33;border-radius:6px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:#c8b090;}}
.alert strong {{color:#c04a1a;}}
/* 页脚 */
.ft {{text-align:center;padding:24px;color:#4a4d53;font-size:12px;border-top:1px solid #2a2d33;margin-top:40px;}}
@media (max-width:600px) {{.hdr-s {{gap:16px;}}.hdr-s .kv {{font-size:22px;}}.cb {{min-width:100%;}}}}
</style>
</head>
<body>
<div class="hdr">
    <h1>舆情分析报告</h1>
    <div class="sub">关键词：{keyword} ｜ 采集平台：{', '.join(platforms_used)} ｜ {now.strftime("%Y-%m-%d %H:%M")}</div>
    <div class="hdr-s">
        <div class="k"><div class="kv" style="color:#f0f2f5">{total}</div><div class="kl">总数据</div></div>
        <div class="k"><div class="kv" style="color:#4CAF50">{positive}</div><div class="kl">正面</div></div>
        <div class="k"><div class="kv" style="color:#F44336">{negative}</div><div class="kl">负面</div></div>
        <div class="k"><div class="kv" style="color:#9E9E9E">{neutral}</div><div class="kl">中性</div></div>
        <div class="k"><div class="kv" style="color:{sentiment_color}">{pos_rate}%</div><div class="kl">正面率</div></div>
    </div>
</div>
<div class="ctr">
    <div class="alert"><strong>数据真实性声明</strong> — 本报告所有数据均来自社交平台真实搜索结果，使用用户提供的登录凭证或开放 API 采集。未添加任何编造或虚构内容。</div>
    
    <div class="cd"><h2>情感分布</h2>
    <div class="cr">
        <div class="cb"><canvas id="c1"></canvas></div>
        <div class="cb"><canvas id="c2"></canvas></div>
        <div class="cb"><canvas id="c3"></canvas></div>
    </div></div>
    
    <div class="cd"><h2>热门关键词</h2>
    <div class="cr">
        <div class="cb" style="height:320px;flex:1.5;"><canvas id="c4"></canvas></div>
    </div>
    <div style="margin-top:12px;text-align:center;">{kw_html}</div></div>
    
    <div class="cd"><h2>正面评价（{positive}条）</h2>{pos_scroll}</div>
    <div class="cd"><h2>负面评价（{negative}条）</h2>{neg_scroll}</div>
    <div class="cd"><h2>中性内容（{neutral}条）</h2>{neu_scroll}</div>
</div>
<div class="ft">SocialSight 舆情分析系统 ｜ {now.strftime("%Y-%m-%d %H:%M")}</div>

<script>
const c1 = new Chart(document.getElementById('c1'), {{
    type: 'doughnut',
    data: {{labels:['正面','负面','中性'],datasets:[{{data:[{positive},{negative},{neutral}],backgroundColor:['#4CAF50','#F44336','#FFB300'],borderWidth:2,borderColor:'#22252b',hoverOffset:8}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'70%',animation:{{animateRotate:true,duration:1200,easing:'easeOutQuart'}},plugins:{{legend:{{position:'bottom',labels:{{color:'#8b8f96',font:{{size:12}},padding:14,usePointStyle:true,pointStyle:'circle'}}}},title:{{display:true,text:'{pos_rate}%',position:'top',color:'{sentiment_color}',font:{{size:24,weight:'bold'}},padding:{{bottom:2}}}}}}}}
}});

const c2 = new Chart(document.getElementById('c2'), {{
    type: 'bar',
    data: {{labels:{plat_labels},datasets:[
        {{label:'正面',data:{plat_pos},backgroundColor:'#4CAF50',borderRadius:3,maxBarThickness:26}},
        {{label:'负面',data:{plat_neg},backgroundColor:'#F44336',borderRadius:3,maxBarThickness:26}},
        {{label:'中性',data:{plat_neu},backgroundColor:'#FFB300',borderRadius:3,maxBarThickness:26}},
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:1000,easing:'easeOutQuart'}},plugins:{{legend:{{position:'bottom',labels:{{color:'#8b8f96',font:{{size:11}},usePointStyle:true,pointStyle:'circle'}}}}}},scales:{{x:{{stacked:true,grid:{{display:false}},ticks:{{color:'#8b8f96'}}}},y:{{stacked:true,grid:{{color:'#2a2d33'}},ticks:{{color:'#6b6f76'}}}}}}}}
}});

const c3 = new Chart(document.getElementById('c3'), {{
    type: 'radar',
    data: {{labels:{plat_labels},datasets:[
        {{label:'正面',data:{plat_pos},borderColor:'#4CAF50',backgroundColor:'#4CAF5033',pointBackgroundColor:'#4CAF50',pointBorderColor:'#22252b',pointRadius:4,borderWidth:2,fill:true}},
        {{label:'负面',data:{plat_neg},borderColor:'#F44336',backgroundColor:'#F4433633',pointBackgroundColor:'#F44336',pointBorderColor:'#22252b',pointRadius:4,borderWidth:2,fill:true}},
        {{label:'中性',data:{plat_neu},borderColor:'#FFB300',backgroundColor:'#FFB30033',pointBackgroundColor:'#FFB300',pointBorderColor:'#22252b',pointRadius:4,borderWidth:2,fill:true}},
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:1000,easing:'easeOutQuart'}},plugins:{{legend:{{position:'bottom',labels:{{color:'#8b8f96',font:{{size:11}},usePointStyle:true,pointStyle:'circle'}}}}}},scales:{{r:{{beginAtZero:true,ticks:{{backdropColor:'transparent',color:'#6b6f76',stepSize:1,font:{{size:10}}}},grid:{{color:'#2a2d33'}},angleLines:{{color:'#2a2d33'}},pointLabels:{{color:'#c8cbd0',font:{{size:13,weight:'600'}}}}}}}}}}
}});

const c4Ctx = document.getElementById('c4').getContext('2d');
const c4Grad = c4Ctx.createLinearGradient(0, 0, 600, 0);
c4Grad.addColorStop(0, '#c04a1a');
c4Grad.addColorStop(1, '#e5733a');
const c4 = new Chart(c4Ctx, {{
    type: 'bar',
    data: {{labels:{kw_labels},datasets:[{{label:'出现次数',data:{kw_counts},backgroundColor:c4Grad,borderRadius:4,maxBarThickness:18}}]}},
    options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:1200,easing:'easeOutQuart'}},plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#2a2d33',titleColor:'#e4e7eb',bodyColor:'#c8cbd0',borderColor:'#33363d',borderWidth:1}}}},scales:{{x:{{grid:{{color:'#2a2d33'}},ticks:{{color:'#6b6f76'}}}},y:{{grid:{{display:false}},ticks:{{color:'#c8cbd0',font:{{size:13}}}}}}}}}}
}});
</script>
</body>
</html>'''
    return html


# =============================================
# Flask 路由
# =============================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/collect", methods=["POST"])
def api_collect():
    data = request.get_json()
    keyword = data.get("keyword", "").strip()
    platforms = data.get("platforms", [])
    cookies = data.get("cookies", {})
    
    if not keyword:
        return jsonify({"error": "请输入搜索关键词"}), 400
    if not platforms:
        return jsonify({"error": "请选择至少一个平台"}), 400
    if not HAS_REQUESTS:
        return jsonify({"error": "服务器缺少 requests 库，请运行: pip install requests"}), 500
    
    all_posts = []
    platform_names = []
    warnings = []
    
    # 微博
    if "weibo" in platforms:
        platform_names.append("微博")
        wb_cookie = cookies.get("weibo", "")
        if wb_cookie:
            print(f"[微博] 搜索 '{keyword}'...")
            collector = WeiboCollector(wb_cookie)
            posts = collector.search(keyword, 2)
            print(f"  找到 {len(posts)} 条")
            all_posts.extend(posts)
        else:
            warnings.append("微博：未提供 cookie，已跳过")
    
    # B站
    if "bilibili" in platforms:
        platform_names.append("B站")
        print(f"[B站] 搜索 '{keyword}'...")
        collector = BilibiliCollector()
        posts = collector.search(keyword, 2)
        print(f"  找到 {len(posts)} 条")
        all_posts.extend(posts)
    
    # 京东
    if "jd" in platforms:
        platform_names.append("京东")
        jd_cookie = cookies.get("jd", "")
        print(f"[京东] 搜索 '{keyword}'...")
        collector = JDCollector(jd_cookie)
        products = collector.search_products(keyword)
        if products:
            for p in products[:3]:
                comments = collector.get_comments(p["id"], 2)
                print(f"  商品 '{p['name'][:20]}': {len(comments)} 条评论")
                all_posts.extend(comments)
        else:
            warnings.append("京东：未找到相关商品")
    
    # 小红书
    if "xiaohongshu" in platforms:
        platform_names.append("小红书")
        xhs_cookie = cookies.get("xiaohongshu", "")
        if xhs_cookie:
            print(f"[小红书] 搜索 '{keyword}'...")
            collector = XiaohongshuCollector(xhs_cookie)
            posts, xhs_msg = collector.search(keyword, 2)
            print(f"  找到 {len(posts)} 条 | {xhs_msg}")
            all_posts.extend(posts)
            if xhs_msg:
                warnings.append(f"小红书：{xhs_msg}")
        else:
            warnings.append("小红书：未提供 cookie，已跳过")
    
    if not all_posts:
        return jsonify({
            "total": 0,
            "posts": [],
            "warnings": warnings,
            "message": "未收集到数据" + ("。" + "；".join(warnings) if warnings else "")
        })
    
    # 生成报告
    try:
        html = generate_report(all_posts, keyword, platform_names)
    except Exception as e:
        return jsonify({"error": f"报告生成失败: {str(e)}"}), 500
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"report_{keyword}_{timestamp}.html"
    # 清理文件名
    report_name = re.sub(r'[\\/:*?"<>|]', '_', report_name)
    report_path = os.path.join(app.config["REPORTS_DIR"], report_name)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    # 统计
    positive = sum(1 for p in all_posts if p["sentiment"] == "正面")
    negative = sum(1 for p in all_posts if p["sentiment"] == "负面")
    
    return jsonify({
        "total": len(all_posts),
        "positive": positive,
        "negative": negative,
        "neutral": len(all_posts) - positive - negative,
        "report_name": report_name,
        "warnings": warnings,
        "posts": [{
            "platform": p["platform"],
            "user": p["user"],
            "content": p["content"][:150],
            "sentiment": p["sentiment"],
            "url": p.get("url", ""),
        } for p in all_posts[:5]],
    })


@app.route("/report/<name>")
def view_report(name):
    # 安全检查
    safe_name = os.path.basename(name)
    path = os.path.join(app.config["REPORTS_DIR"], safe_name)
    if os.path.exists(path):
        return send_file(path)
    return "报告不存在", 404


# 全局错误处理器：500 错误返回 JSON 而不是 HTML
@app.errorhandler(500)
def handle_500(e):
    print(f"[错误] 500: {e}")
    return jsonify({"error": "服务器内部错误，请稍后重试"}), 500


# =============================================
# 网页内直接登录（自动获取 cookie）
# =============================================

import threading
import uuid

# 登录会话存储: {session_id: {"status": "waiting"/"done"/"timeout"/"error", "cookies": "", "platform": ""}}
login_sessions_lock = threading.Lock()
login_sessions = {}

# Cookie 持久化
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
_save_lock = threading.Lock()

def _load_saved_cookies():
    """加载已保存的 cookie"""
    try:
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def _save_cookies_persist(platform, cookie_str):
    """保存 cookie 到文件（持久化）"""
    with _save_lock:
        data = _load_saved_cookies()
        data[platform] = cookie_str
        try:
            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

def _pw_browsers_path():
    """获取 Playwright 浏览器路径"""
    pw = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\pc"), "AppData", "Local", "ms-playwright")
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", pw)
    return pw

def _is_logged_in(cookies, platform):
    """判断 cookie 是否表明已登录（严格检测值有效性）"""
    def has_valid(name):
        """检查指定 cookie 是否存在且值有效"""
        for c in cookies:
            if c["name"] == name:
                val = c.get("value", "")
                return len(val) >= 10  # 真实登录 cookie 值至少10位
        return False
    
    if platform == "weibo":
        return has_valid("SUB") and has_valid("WBPSESS")
    elif platform == "xiaohongshu":
        return has_valid("web_session") and has_valid("id_token")
    return False

def _start_login_browser(session_id, platform):
    """启动浏览器让用户登录，登录后捕获 cookie"""
    try:
        _pw_browsers_path()
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # 显示浏览器窗口，供用户登录
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            page = context.new_page()
            
            # 打开登录页
            if platform == "weibo":
                page.goto("https://passport.weibo.com/sso/signin?entry=miniblog&source=web", wait_until="domcontentloaded", timeout=20000)
            elif platform == "xiaohongshu":
                page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=20000)
            else:
                with login_sessions_lock:
                    login_sessions[session_id] = {"status": "error", "cookies": "", "platform": platform}
                browser.close()
                return
            
            with login_sessions_lock:
                login_sessions[session_id] = {"status": "waiting", "cookies": "", "platform": platform}
            
            # 等待用户登录（最多10分钟）
            for _ in range(600):
                time.sleep(1)
                try:
                    # 检测登录状态：检查 cookie 是否有效
                    cookies = context.cookies()
                    cookie_names = [c["name"] for c in cookies]
                    
                    if platform == "weibo":
                        # 微博登录后有 SUB 和 WBPSESS cookie
                        sub = next((c for c in cookies if c["name"] == "SUB"), None)
                        wbpsess = next((c for c in cookies if c["name"] == "WBPSESS"), None)
                        has_sub = sub and len(sub.get("value","")) >= 10
                        has_wb = wbpsess and len(wbpsess.get("value","")) >= 10
                        is_logged_in = has_sub and has_wb
                        # 每 10 秒打印一次 cookie 状态
                        if _ % 10 == 0:
                            print(f"[登录] cookie: {cookie_names[:10]}... SUB={has_sub} WBPSESS={has_wb}")
                    elif platform == "xiaohongshu":
                        has_session = any(c["name"] == "web_session" and len(c.get("value","")) >= 10 for c in cookies)
                        has_id = any(c["name"] == "id_token" and len(c.get("value","")) >= 10 for c in cookies)
                        is_logged_in = has_session and has_id
                    else:
                        is_logged_in = False
                    
                    if is_logged_in:
                        print(f"[登录] 检测到登录成功")
                        # 等 2 秒让 cookie 稳定
                        time.sleep(2)
                        # 获取完整 cookie
                        cookies = context.cookies()
                        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                        print(f"[登录] 获取到 {len(cookies)} 个 cookie")
                        # 持久化保存
                        _save_cookies_persist(platform, cookie_str)
                        with login_sessions_lock:
                            login_sessions[session_id] = {"status": "done", "cookies": cookie_str, "platform": platform}
                        try:
                            page.goto("about:blank", wait_until="domcontentloaded", timeout=5000)
                        except:
                            pass
                        break
                except:
                    pass
            else:
                with login_sessions_lock:
                    if login_sessions.get(session_id, {}).get("status") != "done":
                        login_sessions[session_id] = {"status": "timeout", "cookies": "", "platform": platform}
            
            browser.close()
    except Exception as e:
        with login_sessions_lock:
            login_sessions[session_id] = {"status": "error", "cookies": "", "platform": platform, "msg": str(e)[:100]}

@app.route("/api/login/start", methods=["POST"])
def login_start():
    """启动登录浏览器"""
    data = request.get_json() or {}
    platform = data.get("platform", "")
    if platform not in ("weibo", "xiaohongshu"):
        return jsonify({"error": "无效的平台"}), 400
    
    session_id = uuid.uuid4().hex[:16]
    # 启动登录线程
    t = threading.Thread(target=_start_login_browser, args=(session_id, platform), daemon=True)
    t.start()
    return jsonify({"session_id": session_id, "platform": platform})

@app.route("/api/login/status")
def login_status():
    """查询登录状态"""
    session_id = request.args.get("session_id", "")
    platform = request.args.get("platform", "")
    with login_sessions_lock:
        info = login_sessions.get(session_id)
        if not info:
            return jsonify({"status": "not_found"})
        if info.get("platform") != platform:
            return jsonify({"status": "not_found"})
        return jsonify({
            "status": info["status"],
            "cookies": info.get("cookies", ""),
            "msg": info.get("msg", ""),
        })

@app.route("/api/cookies")
def get_saved_cookies():
    """获取已持久化保存的 cookie"""
    data = _load_saved_cookies()
    return jsonify(data)


@app.route("/api/checkenv")
def check_environment():
    """检查运行环境（本地 vs 服务器）"""
    import socket
    hostname = socket.gethostname()
    # 检测是否有显示器（能不能跑 Playwright 浏览器）
    has_display = bool(os.name == "nt" or os.environ.get("DISPLAY"))
    return jsonify({
        "is_local": has_display,
        "has_browser": has_display,
        "hostname": hostname,
    })


if __name__ == "__main__":
    import os
    import sys
    
    # 确定应用根目录（支持 PyInstaller 打包）
    if getattr(sys, 'frozen', False):
        APP_DIR = os.path.dirname(sys.executable)
    else:
        APP_DIR = os.path.dirname(os.path.abspath(__file__))
    
    print(f"应用目录: {APP_DIR}")
    app.config["REPORTS_DIR"] = os.path.join(APP_DIR, "reports")
    os.makedirs(app.config["REPORTS_DIR"], exist_ok=True)
    
    # 设置 Playwright 浏览器路径
    pw_path = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\pc"), "AppData", "Local", "ms-playwright")
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", pw_path)
    
    # 检查并安装 Playwright 浏览器（显示进度，下完再启动）
    chrome_path = os.path.join(pw_path, "chromium-1187", "chrome-win", "chrome.exe")
    if not os.path.exists(chrome_path):
        print("首次使用需要下载浏览器组件（约300MB，国内镜像）")
        print("下载进度如下，请耐心等待...")
        print()
        try:
            import subprocess
            env = os.environ.copy()
            env["PLAYWRIGHT_DOWNLOAD_HOST"] = "https://registry.npmmirror.com/-/binary/"
            env["PLAYWRIGHT_BROWSERS_PATH"] = pw_path
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                env=env, timeout=900
            )
            if result.returncode == 0:
                print()
                print("浏览器组件安装完成！正在启动系统...")
            else:
                print()
                print("安装失败，可手动下载或使用粘贴 cookie 方式")
        except Exception as e:
            print()
            print(f"安装失败: {e}")
            print("跳过，可手动粘贴 cookie 使用")
    
    print(f"PLAYWRIGHT_BROWSERS_PATH: {pw_path}")
    print(f"已启用网页内直接登录功能（微博/小红书）")
    print(f"SocialSight 舆情分析系统启动")
    print(f"地址: http://127.0.0.1:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)