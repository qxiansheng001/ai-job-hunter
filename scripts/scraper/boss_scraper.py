#!/usr/bin/env python3
"""
BOSS直聘 CDP 爬虫
通过 Chrome DevTools Protocol 连接本地已登录的 Chrome 浏览器（端口 9222），
批量抓取搜索结果和 JD 详情。

用法:
  python scraper.py --keyword "大模型算法工程师" --city 101010100
  python scraper.py --keyword "NLP算法工程师" --city 101020100 --detail-count 10 --output raw_data.json

依赖: pip install websockets httpx
"""

import asyncio
import json
import re
import sys
import os
import platform
import argparse
import tempfile
from urllib.parse import quote
from datetime import datetime

from utils.protocol import emit, emit_progress, emit_fatal

try:
    import websockets
except ImportError:
    emit_fatal("DEP_WEBSOCKETS", "缺少 websockets 库，请执行: pip install websockets")

try:
    import httpx
except ImportError:
    emit_fatal("DEP_HTTPX", "缺少 httpx 库，请执行: pip install httpx")


def _chrome_path():
    """Detect Chrome executable path per platform."""
    system = platform.system()
    if system == "Windows":
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    elif system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:
        return "google-chrome"


class BossScraper:
    """通过 CDP 连接 Chrome 抓取 BOSS直聘"""

    def __init__(self, port=9222):
        self.port = port
        self.http_base = f"http://127.0.0.1:{port}"
        self.ws = None
        self._msg_id = 0
        self._pending = {}
        self.target_id = None

    # ── 连接管理 ──

    async def _http_get(self, path):
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.http_base}{path}")
            resp.raise_for_status()
            return resp.json()

    async def _http_put(self, path):
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(f"{self.http_base}{path}")
            resp.raise_for_status()
            return resp.json()

    async def connect(self):
        """连接本地 Chrome 并创建新标签页"""
        try:
            version = await self._http_get("/json/version")
            browser_ws = version.get("webSocketDebuggerUrl")
            if not browser_ws:
                return {"error": "未能获取 Chrome WebSocket URL", "step": "connect"}
        except httpx.ConnectError:
            return {
                "error": f"无法连接到 Chrome（端口 {self.port}）\n"
                         f"请先关闭所有 Chrome 窗口，然后用以下命令启动：\n"
                         f'  "{_chrome_path()}" '
                         f"--remote-debugging-port={self.port}\n"
                         f"启动后会打开一个新 Chrome 窗口，请在其中登录 BOSS直聘。",
                "step": "connect"
            }
        except Exception as e:
            return {"error": f"连接 Chrome 失败: {e}", "step": "connect"}

        try:
            page = await self._http_put("/json/new")
            ws_url = page.get("webSocketDebuggerUrl")
            self.target_id = page.get("id")
            if not ws_url:
                return {"error": "创建标签页失败", "step": "connect"}
        except Exception as e:
            return {"error": f"创建标签页失败: {e}", "step": "connect"}

        try:
            self.ws = await websockets.connect(ws_url, max_size=10_000_000)
        except Exception as e:
            return {"error": f"WebSocket 连接失败: {e}", "step": "connect"}

        return {"status": "ok"}

    async def send(self, method, params=None):
        """发送 CDP 命令并等待响应"""
        if params is None:
            params = {}
        self._msg_id += 1
        msg = json.dumps({"id": self._msg_id, "method": method, "params": params})
        await self.ws.send(msg)

        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == self._msg_id:
                if "error" in data:
                    raise Exception(data["error"]["message"])
                return data.get("result")

    async def evaluate(self, js_code):
        """在页面中执行 JS 并取返回值"""
        result = await self.send("Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": True
        })
        if result.get("exceptionDetails"):
            exc = result["exceptionDetails"]
            raise Exception(exc.get("text", "") or exc.get("exception", {}).get("description", "JS 异常"))
        return result.get("result", {}).get("value")

    async def navigate(self, url):
        """导航到 URL 并等待页面框架加载"""
        await self.send("Page.enable")
        await self.send("Page.navigate", {"url": url})
        # 等待页面开始渲染
        await asyncio.sleep(3)

    async def wait_for_cards(self, timeout=20):
        """轮询等待岗位卡片加载，返回卡片数量"""
        for i in range(int(timeout / 1.0)):
            try:
                count = await self.evaluate(
                    "document.querySelectorAll('li.job-card-box').length"
                )
                if count and int(count) > 0:
                    return int(count)
            except Exception:
                pass
            await asyncio.sleep(1.0)
        return 0

    async def close(self):
        """清理：关闭 WebSocket 和标签页"""
        if self.ws:
            await self.ws.close()
        if self.target_id:
            try:
                await self._http_put(f"/json/close/{self.target_id}")
            except Exception:
                pass

    # ── JS 提取器 ──

    LIST_EXTRACTOR = r"""(() => {
        const cards = document.querySelectorAll(
            'li.job-card-box, [class*="job-card-box"], [class*="job-card-wrap"]'
        );
        const items = [];
        const seen = new Set();

        for (const card of cards) {
            const titleEl = card.querySelector(
                'a.job-name, [class*="job-name"], [class*="job-title"] a'
            );
            const salaryEl = card.querySelector(
                '[class*="job-salary"], [class*="salary"]'
            );
            const companyEl = card.querySelector(
                'a[href*="gongsi"], [class*="company-name"], [class*="company"] a'
            );
            const areaEl = card.querySelector(
                '[class*="job-area"], [class*="area"], [class*="location"]'
            );
            const linkEl = card.querySelector(
                'a[href*="job_detail"], a.job-name'
            );
            const tagEls = card.querySelectorAll(
                'ul.tag-list li, [class*="tag-list"] li, [class*="tag"] li'
            );

            const title = titleEl ? titleEl.textContent.trim() : '';
            const salary = salaryEl ? salaryEl.textContent.trim() : '';
            const company = companyEl ? companyEl.textContent.trim() : '';
            const location = areaEl ? areaEl.textContent.trim() : '';

            let link = '';
            if (linkEl) {
                link = linkEl.getAttribute('href') || '';
                if (link && !link.startsWith('http')) {
                    link = 'https://www.zhipin.com' + link;
                }
            }

            const key = link || (title + '|' + company);
            if (seen.has(key) || !title) continue;
            seen.add(key);

            const hasObf = [...salary].some(
                c => c.codePointAt(0) >= 0xE000 && c.codePointAt(0) <= 0xF8FF
            );
            const cleanSalary = [...salary].map(c =>
                (c.codePointAt(0) >= 0xE000 && c.codePointAt(0) <= 0xF8FF)
                    ? '▯'
                    : c
            ).join('');

            const tags = Array.from(tagEls)
                .map(t => t.textContent.trim())
                .filter(Boolean);

            items.push({
                title: title,
                salary: cleanSalary,
                salary_obfuscated: hasObf,
                company: company,
                location: location,
                tags: tags,
                link: link,
            });
        }
        return items;
    })()"""

    DETAIL_EXTRACTOR = r"""(() => {
        const jdSelectors = [
            '.job-sec-text',
            '.job-detail-section',
            '.job-detail',
            '[class*="job-sec"]',
            '[class*="job-detail"]',
            '[class*="detail-content"]'
        ];

        let jdText = '';
        let jdSelector = '';
        for (const sel of jdSelectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 50) {
                jdText = el.textContent.trim();
                jdSelector = sel;
                break;
            }
        }

        if (!jdText) {
            const bodyText = document.body ? document.body.textContent : '';
            const lines = bodyText.split('\n').filter(l => {
                const t = l.trim();
                return t.length > 10
                    && !/script|style|function|var |let |const /.test(t);
            });
            jdText = lines.slice(0, 50).join('\n').substring(0, 6000);
        }

        const titleEl = document.querySelector(
            '.job-title, h1, [class*="job-title"]'
        );
        const salaryEl = document.querySelector(
            '.salary, [class*="salary"]'
        );
        const companyEl = document.querySelector(
            '[class*="company-name"], a[href*="/gongsi/"]'
        );

        const salary = salaryEl ? salaryEl.textContent.trim() : '';
        const hasObf = [...salary].some(
            c => c.codePointAt(0) >= 0xE000 && c.codePointAt(0) <= 0xF8FF
        );
        const cleanSalary = [...salary].map(c =>
            (c.codePointAt(0) >= 0xE000 && c.codePointAt(0) <= 0xF8FF)
                ? '▯'
                : c
        ).join('');

        const company = companyEl ? companyEl.textContent.trim() : '';

        let addrFromJD = '';
        const addrMatch = jdText.match(
            /(?:地址|办公地点|工作地点|公司地址)[:：]\s*([^\n。；;]{4,80})/
        );
        if (addrMatch) addrFromJD = addrMatch[1];

        const expMatch = jdText.match(
            /(\d[\d-]*年.*?经验|经验不限|应届生)/
        );
        const eduMatch = jdText.match(
            /(本科|硕士|博士|大专|学历不限)/
        );

        return {
            job_title: titleEl ? titleEl.textContent.trim() : '',
            salary: cleanSalary,
            salary_obfuscated: hasObf,
            company: company,
            address_from_jd: addrFromJD,
            experience: expMatch ? expMatch[1] : '',
            education: eduMatch ? eduMatch[1] : '',
            jd_text: jdText.substring(0, 6000),
            jd_text_length: jdText.length,
            jd_selector: jdSelector,
        };
    })()"""

    # ── 检查页面状态 ──

    async def _check_blocked(self):
        """检查是否被反爬拦截"""
        body = await self.evaluate("document.body ? document.body.textContent.substring(0, 2000) : ''")
        if re.search(r'请完成.*验证|安全验证|滑块验证|验证码|拖动.*完成', body):
            return "blocked", "被安全验证拦截 → 请在已打开的 Chrome 窗口中手动完成验证，然后重新运行"
        if re.search(r'登录|扫码登录|未登录', body) and len(body) < 1500:
            return "need_login", "未检测到登录状态 → 请在 Chrome 中登录 BOSS直聘（zhipin.com）后重试"
        if re.search(r'访问被拒绝|请求太频繁|操作太频繁', body):
            return "rate_limited", "请求太频繁 → 请稍后再试"
        return "ok", ""

    # ── 公开接口 ──

    async def scrape_list(self, keyword, city="100010000", max_items=50, max_pages=3):
        """抓取搜索结果列表，返回 (items, diagnostics)"""
        items = []
        diag = {
            "page_count": 0, "total_raw": 0,
            "blocked": False, "blocked_msg": "",
            "need_login": False, "need_login_msg": ""
        }

        for page in range(1, max_pages + 1):
            if len(items) >= max_items:
                break

            url = (f"https://www.zhipin.com/web/geek/job?"
                   f"query={quote(keyword)}&city={city}&page={page}")
            emit("scraper.list.navigate", f"正在翻页第 {page} 页...",
                 data={"page": page, "url": url})
            await self.navigate(url)
            # 首次等待稍长
            wait_for = 15 if page == 1 else 10
            card_count = await self.wait_for_cards(timeout=wait_for)

            if card_count == 0:
                status, msg = await self._check_blocked()
                if status != "ok":
                    diag[status] = True
                    diag[f"{status}_msg"] = msg
                    return items[:max_items], diag
                # 没有卡片但也没被拦截，可能是页面没加载好，滚动试试
                await self.evaluate("window.scrollBy(0, 1600)")
                await asyncio.sleep(2)
                card_count = await self.wait_for_cards(timeout=8)
                if card_count == 0:
                    continue

            # 滚到底加载更多
            await self.evaluate("window.scrollBy(0, 1800)")
            await asyncio.sleep(1.5)

            page_items = await self.evaluate(self.LIST_EXTRACTOR)
            if page_items:
                diag["page_count"] += 1
                diag["total_raw"] += len(page_items)
                items.extend(page_items)

        # 去重
        seen = set()
        deduped = []
        for it in items:
            key = it.get("link", "") or (it.get("title", "") + "|" + it.get("company", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(it)

        return deduped[:max_items], diag

    async def scrape_details(self, items, max_details=50):
        """顺序抓取详情页 JD 文本"""
        results = []
        count = 0

        for item in items:
            if count >= max_details:
                break
            link = item.get("link", "")
            if not link or "job_detail" not in link:
                continue

            try:
                await self.navigate(link)
                await asyncio.sleep(1.5)

                for _ in range(8):
                    has_jd = await self.evaluate(
                        "document.querySelector('.job-sec-text') !== null || "
                        "document.querySelector('.job-detail-section') !== null"
                    )
                    if has_jd:
                        break
                    await asyncio.sleep(0.5)

                detail = await self.evaluate(self.DETAIL_EXTRACTOR)
                detail["url"] = link
                detail["list_title"] = item.get("title", "")
                results.append(detail)
                count += 1
                emit_progress("scraper.detail.progress", count, max_details,
                              f"正在抓取详情 ({count}/{max_details}): {item.get('title')} @ {item.get('company')}")
            except Exception as e:
                emit("scraper.detail.skip", f"跳过 {item.get('title')}: {e}",
                     status="warn", warnings=[str(e)], stream=sys.stderr)
                continue

        return results


async def main():
    parser = argparse.ArgumentParser(description="BOSS直聘 CDP 爬虫")
    parser.add_argument("--keyword", required=True, help="搜索关键词")
    parser.add_argument("--city", default="100010000", help="城市编码，默认全国")
    parser.add_argument("--port", type=int, default=9222, help="Chrome CDP 端口")
    parser.add_argument("--max-items", type=int, default=50, help="最大抓取条数（不足则全取）")
    parser.add_argument("--detail-count", type=int, default=0, help="详情页抓取条数，0 表示与列表条数相同（默认全取）")
    default_output = os.path.join(tempfile.gettempdir(), "ai-job-hunter", "raw_data.json")
    parser.add_argument("--output", default=default_output, help="输出文件路径")
    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    scraper = BossScraper(port=args.port)

    # 1. 连接
    emit("init", f"正在启动 boss_scraper，关键词: {args.keyword}",
         data={"argv": sys.argv, "cwd": os.getcwd()})
    emit("scraper.connect", f"正在连接 Chrome（端口 {args.port}）...")
    result = await scraper.connect()
    if "error" in result:
        emit("fatal", result["error"], status="error",
             error={"code": "CHROME_CONNECT_FAIL", "traceback": ""})
        await scraper.close()
        sys.exit(1)

    # 2. 抓取列表
    keyword_label = args.keyword
    emit("scraper.list.start", f"正在搜索「{keyword_label}」...")

    items, diag = await scraper.scrape_list(
        args.keyword, args.city, args.max_items
    )

    output = {
        "keyword": args.keyword,
        "city": args.city,
        "scraped_at": datetime.now().isoformat(),
        "status": "success",
        "list_count": len(items),
        "list_items": items,
        "diagnostics": diag,
        "detail_count": 0,
        "detail_items": [],
    }

    if diag.get("blocked") or diag.get("need_login"):
        output["status"] = "blocked" if diag.get("blocked") else "need_login"
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        emit("scraper.blocked", diag.get("blocked_msg") or diag.get("need_login_msg"),
             status="error", data={"status": output["status"]})
        await scraper.close()
        return

    if not items:
        output["status"] = "no_results"
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        emit("done", "未找到匹配岗位", data={"count": 0})
        await scraper.close()
        return

    emit("scraper.list.done", f"列表页获取 {len(items)} 条",
         data={"count": len(items)})

    # 3. 抓取详情
    # 详情抓取数量：0 表示"与列表条数相同"
    detail_limit = args.detail_count if args.detail_count > 0 else len(items)
    if detail_limit > 0:
        emit("scraper.detail.start", f"正在抓取详情页（最多 {detail_limit} 条）...")
        details = await scraper.scrape_details(items, detail_limit)
        output["detail_count"] = len(details)
        output["detail_items"] = details
        emit("scraper.detail.done", f"详情页获取 {len(details)} 条",
             data={"count": len(details)})

    # 4. 保存
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    emit("done",
         f"完成！列表 {len(items)} 条 + 详情 {output['detail_count']} 条",
         data={"list_count": len(items), "detail_count": output["detail_count"], "output": args.output})

    await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
