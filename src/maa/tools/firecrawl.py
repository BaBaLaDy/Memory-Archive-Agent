import json
import os
import urllib.request
from urllib.error import HTTPError

from .base import BaseTool, ToolResult


class FirecrawlScrapeTool(BaseTool):
    """抓取网页并提取正文"""

    name = "extract_content"  # Keep the original name for compatibility with existing logic
    description = "抓取指定 URL 的网页内容并提取正文文本（使用 Firecrawl 绕过反爬虫）"
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要抓取的网页 URL"},
        },
        "required": ["url"],
    }

    def execute(self, url: str) -> ToolResult:
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            return ToolResult(success=False, error="未设置 FIRECRAWL_API_KEY 环境变量")
        
        req_url = "https://api.firecrawl.dev/v1/scrape"
        
        data = json.dumps({
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True
        }).encode()
        
        req = urllib.request.Request(
            req_url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                if result.get("success") and "data" in result:
                    data = result["data"]
                    text = data.get("markdown", "")
                    title = data.get("metadata", {}).get("title", "")
                    return ToolResult(success=True, data={"content": text, "title": title})
                else:
                    return ToolResult(success=False, error=f"抓取失败: {json.dumps(result)}")
        except HTTPError as e:
            try:
                error_msg = e.read().decode()
            except:
                error_msg = ""
            return ToolResult(success=False, error=f"网页抓取失败: {e.code} - {e.reason}. {error_msg}")
        except Exception as e:
            return ToolResult(success=False, error=f"网页抓取失败: {e}")


class FirecrawlSearchTool(BaseTool):
    """使用 Firecrawl 搜索互联网"""

    name = "web_search"
    description = "在互联网上搜索指定关键词，返回相关的网页链接和摘要内容"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "最大结果数量", "default": 5},
        },
        "required": ["query"],
    }

    def execute(self, query: str, limit: int = 5) -> ToolResult:
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            return ToolResult(success=False, error="未设置 FIRECRAWL_API_KEY 环境变量")
        
        req_url = "https://api.firecrawl.dev/v1/search"
        
        data = json.dumps({
            "query": query,
            "limit": limit,
            "lang": "zh",
            "country": "cn"
        }).encode()
        
        req = urllib.request.Request(
            req_url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                if result.get("success") and "data" in result:
                    items = []
                    for item in result["data"]:
                        items.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("description", ""),
                            "content_preview": item.get("markdown", "")[:500] if "markdown" in item else ""
                        })
                    return ToolResult(success=True, data={"results": items})
                else:
                    return ToolResult(success=False, error=f"搜索失败: {json.dumps(result)}")
        except HTTPError as e:
            try:
                error_msg = e.read().decode()
            except:
                error_msg = ""
            return ToolResult(success=False, error=f"网页搜索失败: {e.code} - {e.reason}. {error_msg}")
        except Exception as e:
            return ToolResult(success=False, error=f"网页搜索失败: {e}")
