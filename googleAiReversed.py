import html
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from cse_logger import Logger
from curl_cffi import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class GoogleAiScraper:
    def __init__(
        self,
        query: str,
        impersonate: str = "chrome131",
        timeout: int = 25,
        logger: Optional[Logger] = None,
    ):
        self.logger = logger or Logger(name="ryze")
        self.query = query.strip()
        self.impersonate = impersonate
        self.timeout = timeout

        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=1, i",
            "referer": "https://www.google.com/",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-form-factors": '"Desktop"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"19.0.0"',
            "sec-ch-ua-wow64": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        self.cookies: Dict[str, str] = {}

    def ExtractTokensFromHtml(self, html_content: str) -> Optional[Dict[str, str]]:
        soup = BeautifulSoup(html_content, "html.parser")

        stkp_el = soup.find(attrs={"data-stkp": True})
        stkp = stkp_el.get("data-stkp") if stkp_el else None

        folif_token_el = soup.find(attrs={"data-xsrf-folif-token": True})
        xsrf = folif_token_el.get("data-xsrf-folif-token") if folif_token_el else None
        srtst = folif_token_el.get("data-srtst") if folif_token_el else None
        ei = folif_token_el.get("data-ei") if folif_token_el else None

        elrc_el = soup.find(attrs={"data-elrc": True})
        elrc = elrc_el.get("data-elrc") if elrc_el else None

        if not (stkp and elrc and xsrf):
            return None

        return {
            "stkp": stkp,
            "elrc": elrc,
            "xsrf": xsrf,
            "srtst": srtst or "",
            "ei": ei or "",
        }

    def ResolveWithCurl(self) -> Optional[Dict[str, str]]:
        search_headers = dict(self.headers)
        search_headers.update({
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
        })
        search_url = f"https://www.google.com/search?q={requests.utils.quote(self.query)}&udm=50"
        try:
            resp = requests.get(
                search_url,
                headers=search_headers,
                cookies=self.cookies,
                impersonate=self.impersonate,
                timeout=self.timeout,
            )
            if resp.status_code == 200 and "enablejs" not in resp.text:
                for k, v in resp.cookies.items():
                    self.cookies[k] = v
                return self.ExtractTokensFromHtml(resp.text)
        except Exception:
            pass
        return None

    def ResolveWithBrowser(self) -> Optional[Dict[str, str]]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": True,
                    "args": ["--disable-blink-features=AutomationControlled"],
                }
                browser = None
                for channel in ["chrome", "msedge", None]:
                    try:
                        kwargs = dict(launch_kwargs)
                        if channel:
                            kwargs["channel"] = channel
                        browser = p.chromium.launch(**kwargs)
                        break
                    except Exception:
                        continue
                if not browser:
                    return None

                context = browser.new_context(user_agent=self.headers["user-agent"])
                page = context.new_page()
                search_url = f"https://www.google.com/search?q={requests.utils.quote(self.query)}&udm=50"
                page.goto(search_url, timeout=self.timeout * 1000)
                html_content = page.content()
                for c in context.cookies():
                    self.cookies[c["name"]] = c["value"]
                browser.close()
                return self.ExtractTokensFromHtml(html_content)
        except Exception:
            return None

    def FetchSessionTokens(self) -> Optional[Dict[str, str]]:
        self.logger.info(f"resolving session tokens for '{self.query}'...")
        tokens = self.ResolveWithCurl()
        if not tokens:
            tokens = self.ResolveWithBrowser()

        if not tokens:
            self.logger.warn("could not extract all session tokens from search response")
            return None

        self.logger.success("session tokens acquired successfully")
        return tokens

    def BuildUrl(self) -> Optional[str]:
        tokens = self.FetchSessionTokens()
        if not tokens:
            return None

        params = {
            "srtst": tokens["srtst"],
            "ei": tokens["ei"],
            "yv": "3",
            "cs": "1",
            "udm": "50",
            "stkp": tokens["stkp"],
            "csuir": "0",
            "elrc": tokens["elrc"],
            "q": self.query,
            "ved": "1t:244952",
            "sclient": "aim-smartcompose",
            "async": f"_fmt:adl,_xsrf:{tokens['xsrf']}",
        }
        return f"https://www.google.com/async/folif?{urlencode(params)}"

    def FetchResponse(self) -> str:
        target_url = self.BuildUrl()
        if not target_url:
            raise RuntimeError("failed to build folif url with valid session tokens")

        self.logger.info(f"sending request for query: '{self.query}' (impersonate='{self.impersonate}')...")
        response = requests.get(
            target_url,
            headers=self.headers,
            cookies=self.cookies,
            impersonate=self.impersonate,
            timeout=self.timeout,
        )
        response.raise_for_status()
        self.logger.success(f"request successful ({len(response.text):,} bytes received)")
        return response.text

    def ExtractSources(self, html_content: str) -> List[Dict[str, str]]:
        sources: List[Dict[str, str]] = []
        seen_urls = set()

        comments = re.findall(r"<!--(.*?)-->", html_content, re.DOTALL)
        for comment in comments:
            if "TgQPHd" not in comment:
                continue

            unescaped = html.unescape(comment)
            parts = unescaped.split("|||")
            if len(parts) <= 1:
                continue

            try:
                data = json.loads(parts[1])

                def walk(obj: Any):
                    if isinstance(obj, list):
                        if (
                            len(obj) >= 6
                            and isinstance(obj[0], str)
                            and isinstance(obj[5], str)
                            and obj[5].startswith("http")
                            and "favicon" not in obj[5]
                            and "gstatic.com" not in obj[5]
                            and not obj[0].startswith("http")
                        ):
                            url = obj[5]
                            title = obj[0].strip()
                            site = ""
                            if len(obj) > 4:
                                if isinstance(obj[4], list) and obj[4]:
                                    site = str(obj[4][0]).strip()
                                elif isinstance(obj[4], str):
                                    site = obj[4].strip()

                            if url not in seen_urls and title:
                                seen_urls.add(url)
                                sources.append({"title": title, "url": url, "site": site})

                        elif (
                            len(obj) >= 7
                            and isinstance(obj[0], str)
                            and obj[0].startswith("http")
                            and "favicon" not in obj[0]
                            and "gstatic.com" not in obj[0]
                            and isinstance(obj[6], str)
                            and obj[6].strip()
                        ):
                            url = obj[0]
                            title = obj[6].strip()
                            if url not in seen_urls and title:
                                seen_urls.add(url)
                                sources.append({"title": title, "url": url, "site": ""})

                        for item in obj:
                            walk(item)
                    elif isinstance(obj, dict):
                        for val in obj.values():
                            walk(val)

                walk(data)
            except Exception:
                continue

        return sources

    def ExtractAnswer(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")

        main_col = soup.find(attrs={"data-container-id": "main-col"})
        target_cids = set()
        if main_col:
            for placeholder in main_col.find_all(attrs={"data-container-id": True}):
                cid = placeholder.get("data-container-id")
                if cid:
                    target_cids.add(cid)

        containers = []
        if target_cids:
            for cid in target_cids:
                containers.extend(soup.find_all(attrs={"data-target-container-id": cid}))
        else:
            containers = soup.find_all(attrs={"data-target-container-id": True})
            if not containers and main_col:
                containers = [main_col]

        ignore_phrases = {
            "copied to clipboard",
            "failed to copy",
            "good response",
            "bad response",
            "share public link",
            "try again later",
        }

        blocks: List[str] = []

        for container in containers:
            for child in container.children:
                if not getattr(child, "name", None):
                    continue

                child_text_lower = child.get_text().lower()
                if any(phrase in child_text_lower for phrase in ignore_phrases):
                    continue
                if child.find(attrs={"role": "alert"}):
                    continue

                clone = BeautifulSoup(str(child), "html.parser")

                for tag in clone(["script", "style", "button", "svg", "img"]):
                    tag.decompose()

                for badge in clone.find_all(
                    attrs={
                        "class": lambda c: c
                        and any(cls in c for cls in ["WBgIic", "DHPVt", "notranslate"])
                    }
                ):
                    badge.decompose()

                has_list = False
                for ul in clone.find_all(["ul", "ol"]):
                    for li in ul.find_all("li"):
                        li_text = li.get_text(" ", strip=True)
                        if li_text:
                            blocks.append(f"- {li_text}")
                            has_list = True
                    ul.decompose()

                remaining = clone.get_text(" ", strip=True)
                if remaining and not has_list:
                    if not blocks or blocks[-1] != remaining:
                        blocks.append(remaining)

        return "\n\n".join(blocks)

    def Parse(self, html_content: str) -> Tuple[str, List[Dict[str, str]]]:
        answer = self.ExtractAnswer(html_content)
        sources = self.ExtractSources(html_content)
        return answer, sources

    def SaveToFile(self, filename: str, answer: str, sources: List[Dict[str, str]]) -> None:
        content_lines = [
            f"# Query: {self.query}",
            "",
            "## AI Response",
            answer if answer else "(no response text found)",
            "",
            f"## Sources ({len(sources)} found)",
        ]
        if sources:
            for idx, source in enumerate(sources, 1):
                site_label = f" [{source['site']}]" if source["site"] else ""
                content_lines.append(f"{idx}. {source['title']}{site_label}")
                content_lines.append(f"   URL: {source['url']}")
        else:
            content_lines.append("(no sources found)")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines) + "\n")
        self.logger.success(f"output saved to {filename}")

    def DisplayResults(self, answer: str, sources: List[Dict[str, str]]) -> None:
        print("\n" + "=" * 65)
        print("response:")
        print("=" * 65)
        print(answer if answer else "(no response text found)")

        print("\n" + "=" * 65)
        print(f"sources ({len(sources)} found):")
        print("=" * 65)
        if sources:
            for idx, source in enumerate(sources, 1):
                site_label = f" [{source['site']}]" if source["site"] else ""
                print(f"{idx}. {source['title']}{site_label}")
                print(f"   url: {source['url']}")
        else:
            print("(no sources found)")

    def Run(self, save_filename: Optional[str] = None) -> None:
        try:
            raw_html = self.FetchResponse()
        except Exception as exc:
            self.logger.error(f"request failed: {exc}")
            return

        answer, sources = self.Parse(raw_html)

        if save_filename:
            self.SaveToFile(save_filename + ".txt" if not save_filename.endswith(".txt") else save_filename, answer, sources)
        else:
            self.DisplayResults(answer, sources)


def main():
    logger = Logger(name="ryze")
    try:
        user_query = input(logger._format_msg(logger.MAGENTA, "input", "enter query: ")).strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not user_query:
        return

    try:
        save_input = input(logger._format_msg(logger.CYAN, "input", "save to file (or press enter to skip): ")).strip()
    except (EOFError, KeyboardInterrupt):
        save_input = ""

    scraper = GoogleAiScraper(query=user_query, logger=logger)
    scraper.Run(save_filename=save_input if save_input else None)


if __name__ == "__main__":
    main()
