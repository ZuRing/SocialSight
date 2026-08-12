#!/usr/bin/env python3
"""小红书 Playwright 采集器 - 用真实浏览器绕过反爬"""
import sys
import json
import re
import time
import os

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

def search_xiaohongshu(keyword, cookies_str="", max_results=30, headless=True):
    """用 Playwright 浏览器搜索小红书"""
    if not HAS_PLAYWRIGHT:
        return [], "未安装 Playwright"
    
    posts = []
    success = False
    error_msg = ""
    
    try:
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=headless, args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            
            # 设置 cookie
            if cookies_str:
                for item in cookies_str.split(";"):
                    item = item.strip()
                    if "=" in item:
                        k, v = item.split("=", 1)
                        # 小红书 cookie 需要 domain
                        try:
                            context.add_cookies([{
                                "name": k.strip(),
                                "value": v.strip(),
                                "domain": ".xiaohongshu.com",
                                "path": "/",
                            }])
                        except:
                            pass
            
            page = context.new_page()
            
            # 先访问首页加载 cookie
            try:
                page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
            except:
                pass
            
            # 搜索
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={__import__('urllib.parse').quote(keyword)}&source=web_search_result_notes"
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)
                
                # 等待搜索结果加载
                try:
                    page.wait_for_selector(".note-item, .feeds-page, .search-result-item", timeout=8000)
                except:
                    pass
                
                # 滚动加载更多
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.5)
                
                # 提取页面文本
                content = page.content()
                
                # 尝试从页面中提取笔记数据
                # 方法1: 从 __NEXT_DATA__ 或 __INITIAL_STATE__ 中提取
                next_data = page.evaluate("() => { try { return JSON.parse(document.getElementById('__NEXT_DATA__')?.textContent || '{}'); } catch(e) { return {}; } }")
                init_state = page.evaluate("() => { try { return window.__INITIAL_STATE__ || {}; } catch(e) { return {}; } }")
                
                # 尝试从各种数据源提取
                items = []
                
                # 从 __NEXT_DATA__ 提取
                if next_data:
                    props = next_data.get("props", {}).get("pageProps", {})
                    # 尝试不同的数据结构
                    for key in ["noteData", "searchResult", "notes", "items"]:
                        data = props.get(key, [])
                        if isinstance(data, list) and data:
                            items.extend(data)
                
                # 从 __INITIAL_STATE__ 提取
                if init_state and not items:
                    for key in ["note", "search", "feed"]:
                        section = init_state.get(key, {})
                        if isinstance(section, dict):
                            for sub_key in ["notes", "items", "results", "noteIds"]:
                                data = section.get(sub_key, [])
                                if isinstance(data, list) and data:
                                    items.extend(data)
                
                # 方法2: 从 HTML 中提取
                if not items:
                    # 提取笔记卡片
                    cards = page.query_selector_all(".note-item, .feeds-page .note-item, [class*='note']")
                    for card in cards[:max_results]:
                        try:
                            title_el = card.query_selector(".title, .note-title, [class*='title']")
                            desc_el = card.query_selector(".desc, .note-desc, [class*='desc']")
                            user_el = card.query_selector(".author, .note-author, .user, [class*='author'], [class*='user']")
                            like_el = card.query_selector(".like, .likes, [class*='like']")
                            
                            title = title_el.inner_text() if title_el else ""
                            desc = desc_el.inner_text() if desc_el else ""
                            user = user_el.inner_text() if user_el else "未知"
                            likes = like_el.inner_text() if like_el else "0"
                            
                            content_text = f"{title} {desc}".strip()
                            if content_text:
                                items.append({
                                    "title": title,
                                    "desc": desc,
                                    "user": user,
                                    "likes": likes,
                                })
                        except:
                            pass
                
                # 从页面文本中提取
                if not items:
                    text = page.evaluate("() => document.body.innerText")
                    # 查找可能的笔记标题（中文字符串，长度适中）
                    titles = re.findall(r'^[^\n]{10,80}$', text, re.MULTILINE)
                    for t in titles[:max_results]:
                        t = t.strip()
                        if len(t) >= 4 and not re.match(r'^[\d\s\W]+$', t):
                            items.append({"title": t, "desc": "", "user": "未知", "likes": "0"})
                
                # 转换为我们需要的格式
                for item in items:
                    if isinstance(item, dict):
                        title = item.get("title", "") or item.get("display_title", "") or ""
                        desc = item.get("desc", "") or item.get("description", "") or ""
                        user = item.get("user", "") or item.get("author", "") or item.get("nickname", "") or "未知"
                        if isinstance(user, dict):
                            user = user.get("nickname", "未知")
                        likes = str(item.get("likes", item.get("liked_count", item.get("interact_info", {}).get("liked_count", "0"))))
                        
                        content_text = f"{title} {desc}".strip()
                        if content_text and len(content_text) >= 3:
                            # 过滤非中文内容
                            cn_chars = len(re.findall(r'[\u4e00-\u9fff]', content_text))
                            if cn_chars >= 2:
                                from .sentiment import analyze_sentiment
                                sentiment, pos, neg = analyze_sentiment(content_text)
                                posts.append({
                                    "platform": "小红书",
                                    "user": user[:20],
                                    "content": content_text[:300],
                                    "time": "",
                                    "sentiment": sentiment,
                                    "pos_score": pos,
                                    "neg_score": neg,
                                    "likes": likes,
                                })
                
                success = len(posts) > 0
                if not success:
                    error_msg = "未能提取到任何笔记内容，页面可能需登录或验证"
                
            except Exception as e:
                error_msg = f"搜索失败: {str(e)[:100]}"
            
            browser.close()
    
    except Exception as e:
        error_msg = f"浏览器启动失败: {str(e)[:100]}"
    
    return posts[:max_results], error_msg if not success else ""


def search_xiaohongshu_simple(keyword, cookies_str="", max_results=30):
    """简化版：直接用 Playwright 浏览器打开小红书搜索页面，截图+提取文本"""
    if not HAS_PLAYWRIGHT:
        return [], "未安装 Playwright"
    
    posts = []
    error_msg = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 800},
            )
            
            # 设置 cookie
            if cookies_str:
                for item in cookies_str.split(";"):
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
            from urllib.parse import quote
            url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&type=1"
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(4)
            
            # 提取页面所有文本
            text = page.evaluate("() => document.body.innerText")
            page_title = page.title()
            
            # 检查是否被拦截
            if "登录" in page_title or "安全验证" in text[:200]:
                error_msg = "需要登录或验证码"
                browser.close()
                return [], error_msg
            
            # 提取看起来像笔记标题的内容
            lines = text.split('\n')
            potential_posts = []
            current = []
            for line in lines:
                line = line.strip()
                if not line:
                    if current:
                        potential_posts.append(' '.join(current))
                        current = []
                else:
                    current.append(line)
            if current:
                potential_posts.append(' '.join(current))
            
            # 筛选
            for pp in potential_posts:
                cn_chars = len(re.findall(r'[\u4e00-\u9fff]', pp))
                if cn_chars >= 5 and 10 <= len(pp) <= 500:
                    from .sentiment import analyze_sentiment
                    sentiment, pos, neg = analyze_sentiment(pp)
                    posts.append({
                        "platform": "小红书",
                        "user": "小红书用户",
                        "content": pp[:300],
                        "time": "",
                        "sentiment": sentiment,
                        "pos_score": pos,
                        "neg_score": neg,
                        "likes": "0",
                    })
            
            if not posts:
                error_msg = f"未能提取到内容。页面标题: {page_title[:50]}"
            
            browser.close()
    
    except Exception as e:
        error_msg = f"错误: {str(e)[:100]}"
    
    return posts[:max_results], error_msg


if __name__ == "__main__":
    # 测试
    keyword = "唯可鲜"
    print(f"搜索小红书: {keyword}")
    posts, err = search_xiaohongshu(keyword, cookies_str="", headless=True)
    if posts:
        print(f"成功获取 {len(posts)} 条笔记")
        for p in posts[:5]:
            print(f"  [{p['sentiment']}] {p['content'][:40]}")
    else:
        print(f"失败: {err}")