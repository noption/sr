#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取上游 lazy_group.conf 快照并做完整性校验。

GitHub raw 偶发返回长度偏小的响应, 所以抓多次取最长的。
用法: python3 scripts/fetch_upstream.py [--out upstream/lazy_group.conf]
"""
import argparse, os, sys, time, urllib.request

DEFAULT_URL = "https://raw.githubusercontent.com/LOWERTOP/Shadowrocket/main/lazy_group.conf"
ANCHORS = ("[General]", "[Proxy]", "[Proxy Group]", "[Rule]", "[Host]",
           "[URL Rewrite]", "[MITM]", "FINAL,PROXY", "GEOIP,CN,DIRECT",
           "美国节点 = url-test", "苹果服务 = select")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default="upstream/lazy_group.conf")
    ap.add_argument("--retries", type=int, default=5)
    args = ap.parse_args()

    best, last = None, None
    for attempt in range(1, args.retries + 1):
        try:
            req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            missing = [a for a in ANCHORS if a not in data]
            if missing:
                raise RuntimeError(f"内容不完整, 缺少 {missing}")
            print(f"  [ok] 第{attempt}次: {len(data)} 字节")
            if best is None or len(data) > len(best):
                best = data
        except Exception as e:
            last = e
            print(f"  [!!] 第{attempt}次失败: {e}")
            time.sleep(3)

    if best is None:
        raise SystemExit(f"上游抓取全部失败: {last}")

    if os.path.exists(args.out):
        old = open(args.out, encoding="utf-8").read()
        if len(old) > len(best):
            print(f"  [!!] 新版本 {len(best)} < 本地 {len(old)}, 保留本地版本")
            return
        if old == best:
            print("  上游无变化")
            return

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(best)
    print(f"  已写入 {args.out} ({len(best)} 字节)")


if __name__ == "__main__":
    main()
