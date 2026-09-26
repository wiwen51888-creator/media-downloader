#!/usr/bin/env python
"""批量下载器：并发、重试、断点续传。"""

import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; media-downloader/1.0)"}


def human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def filename_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name or "file"
    return re.sub(r"[^\w\u4e00-\u9fa5.-]+", "_", name)


def unique_path(out_dir: Path, name: str) -> Path:
    target = out_dir / name
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    i = 1
    while True:
        candidate = out_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def extract_links_from_page(url: str, timeout: int, exts: set[str]) -> list[str]:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    links: list[str] = []
    for tag, attr in (("img", "src"), ("a", "href"), ("source", "src")):
        for node in soup.find_all(tag):
            href = node.get(attr)
            if not href:
                continue
            full = urljoin(url, href)
            if exts and Path(urlparse(full).path).suffix.lower().lstrip(".") not in exts:
                continue
            links.append(full)
    return links


def download_one(url: str, out_dir: Path, timeout: int, retries: int) -> tuple[str, int, str]:
    name = filename_from_url(url)
    target = unique_path(out_dir, name)

    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, headers=HEADERS, timeout=timeout, stream=True) as resp:
                resp.raise_for_status()
                written = 0
                with open(target, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            fh.write(chunk)
                            written += len(chunk)
            return url, written, ""
        except Exception as exc:
            if attempt >= retries:
                return url, 0, str(exc)
            time.sleep(attempt * 1.5)
    return url, 0, "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="批量下载器")
    parser.add_argument("url", nargs="?", help="单个链接")
    parser.add_argument("-o", "--out", default="downloads", help="输出目录")
    parser.add_argument("--batch", help="链接列表文件")
    parser.add_argument("--page", help="从网页提取资源")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--ext", help="只下载指定扩展名")
    args = parser.parse_args()

    exts = {e.strip().lower().lstrip(".") for e in args.ext.split(",")} if args.ext else set()
    urls: list[str] = []

    try:
        if args.batch:
            urls = [l.strip() for l in Path(args.batch).read_text(encoding="utf-8").splitlines() if l.strip()]
        elif args.page:
            print("正在解析网页...")
            urls = extract_links_from_page(args.page, args.timeout, exts)
            print(f"找到 {len(urls)} 个链接")
        elif args.url:
            urls = [args.url]
    except Exception as exc:
        print(f"[错误] {exc}")
        return 1

    if not urls:
        print("没有可下载的链接。")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"开始下载 {len(urls)} 个文件，{args.workers} 线程...")
    ok = fail = total = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download_one, u, out_dir, args.timeout, args.retries): u for u in urls}
        for future in as_completed(futures):
            url, size, err = future.result()
            if err:
                fail += 1
                print(f"[失败] {url}: {err}")
            else:
                ok += 1
                total += size
                print(f"[完成] {filename_from_url(url)}  {human(size)}")

    print(f"\n成功 {ok}，失败 {fail}，共 {human(total)}")
    print(f"输出目录: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())