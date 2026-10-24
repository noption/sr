#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成合并版 Shadowrocket 配置: 上游 lazy_group.conf + Apple Intelligence 增强。

用法:
  python3 scripts/merge_lazy_ai.py                    # 用 upstream/ 快照生成
  python3 scripts/merge_lazy_ai.py --upstream X --out Y

增强内容:
  * Apple Intelligence 核心域名规则插到 [Rule] 最前
  * 新增 🍎 Apple智能 分组, 默认固定 VLESS-Reality (TCP)
  * AI / 苹果服务 分组默认从 PROXY / DIRECT 改为 美国节点
  * DNS 改经代理 DoH, 国内域名保留国内 DNS
  * ipv6 = false, 防原生 IPv6 直连泄露国内 IP
  * Apple 全家桶兜底 (上游 Apple.list 里没有 apple.com 后缀, 漏网会走 GEOIP,CN 直连)
  * 规范化上游规则里策略名的大小写
"""
import argparse, hashlib, os, re

NODE_VLESS = "🇺🇸 美国-VLESS-Reality"

AI_GROUP = (
    "🍎 Apple智能 = select," + NODE_VLESS +
    ",美国节点,PROXY,policy-select-name=" + NODE_VLESS
)

APPLE_RULES = """
# ===================== Apple Intelligence 增强 (由 merge_lazy_ai.py 自动注入) =====================
# 1) 中国区 Apple 站点直连
DOMAIN-SUFFIX,apple.com.cn,DIRECT
DOMAIN-SUFFIX,icloud.com.cn,DIRECT
# 2) AI 推理核心 (PCC 私有云握手 / 模型网关 / 设备校验 / Siri)
DOMAIN-SUFFIX,pcc.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,apple-relay.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,apple-relay.cloudflare.com,🍎 Apple智能
DOMAIN-SUFFIX,apple-relay.fastly-edge.com,🍎 Apple智能
DOMAIN-SUFFIX,model-gateway.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,configuration.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,configuration.ls.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,iphone-ld.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,gdmf.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,gateway.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,probe.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,guzzoni.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,smoot.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,apple-intelligence.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,mask.apple-dns.net,🍎 Apple智能
DOMAIN-SUFFIX,ls.apple.com,🍎 Apple智能
DOMAIN-SUFFIX,apple-cloudkit.com,🍎 Apple智能
DOMAIN-SUFFIX,apple-cloudkit.net,🍎 Apple智能
DOMAIN-SUFFIX,api.apple-cloudkit.com,🍎 Apple智能
DOMAIN-KEYWORD,apple-intelligence,🍎 Apple智能
DOMAIN-KEYWORD,apple-cloudkit,🍎 Apple智能
DOMAIN-KEYWORD,guzzoni,🍎 Apple智能
# 3) ChatGPT 集成
DOMAIN-SUFFIX,chatgpt.com,🍎 Apple智能
DOMAIN-SUFFIX,chat.openai.com,🍎 Apple智能
DOMAIN-SUFFIX,openai.com,🍎 Apple智能
DOMAIN-SUFFIX,oaistatic.com,🍎 Apple智能
DOMAIN-SUFFIX,challenges.cloudflare.com,🍎 Apple智能
# 4) Apple 全家桶兜底: 统一走美国, 绝不能一半直连一半代理
#    (上游 Apple.list 里并没有 apple.com 这个后缀, 漏网会走 GEOIP,CN 直连 -> IP 不一致)
DOMAIN-SUFFIX,apple.com,🍎 Apple智能
DOMAIN-SUFFIX,icloud.com,🍎 Apple智能
DOMAIN-SUFFIX,mzstatic.com,🍎 Apple智能
DOMAIN-SUFFIX,cdn-apple.com,🍎 Apple智能
# =======================================================================================
"""

FAILED = []


def sub1(text, pattern, repl, label, flags=0):
    new, n = re.subn(pattern, repl, text, flags=flags)
    print(f"  [{'ok' if n else '!!'}] {label}" + (f"  ({n} 处)" if n else "  未命中!"))
    if not n:
        FAILED.append(label)
    return new


def normalize_policy_case(text):
    """上游规则里策略名是大写 (YOUTUBE/MAX...), 分组名却是首字母大写, 统一成和分组一致。"""
    group_names = re.findall(
        r'(?m)^([^\[\]=#\s][^=]*?)\s*=\s*(?:select|url-test|fallback|load-balance|random)\s*,', text)
    lookup = {g.lower(): g for g in group_names}
    fixed, out, in_rule = 0, [], False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if re.match(r'^\[Rule\]', stripped):
            in_rule = True
        elif re.match(r'^\[', stripped):
            in_rule = False
        if in_rule and stripped and not stripped.startswith('#'):
            m = re.match(r'^(.*,)([A-Za-z0-9+._\- ]+?)(\s*)$', line.rstrip('\n') + '\n')
            if m:
                head, pol, tail = m.group(1), m.group(2).strip(), m.group(3)
                if pol.lower() in lookup and pol != lookup[pol.lower()]:
                    line = head + lookup[pol.lower()] + tail + ('\n' if line.endswith('\n') else '')
                    fixed += 1
        out.append(line)
    return ''.join(out), fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="upstream/lazy_group.conf")
    ap.add_argument("--out", default="lazy_group_ai.conf")
    args = ap.parse_args()

    if not os.path.exists(args.upstream):
        raise SystemExit(f"缺少上游快照 {args.upstream}, 先跑 scripts/fetch_upstream.py")
    txt = open(args.upstream, encoding="utf-8").read()
    print(f"上游快照: {len(txt)} 字符, md5={hashlib.md5(txt.encode()).hexdigest()}")
    print("注入补丁:")

    # ---------- General ----------
    txt = sub1(txt, r'^dns-server\s*=.*$',
               'dns-server = https://dns.google/dns-query#proxy',
               'General/dns-server 改为经代理 DoH', re.M)
    txt = sub1(txt, r'^fallback-dns-server\s*=.*$',
               'fallback-dns-server = https://cloudflare-dns.com/dns-query#proxy',
               'General/fallback-dns-server 改为经代理 DoH', re.M)
    txt = sub1(txt, r'^(dns-server\s*=.*)$',
               r'\1\ndirect-dns-server = https://dns.alidns.com/dns-query',
               'General/direct-dns-server 新增 (国内域名仍走国内 DNS)', re.M)
    txt = sub1(txt, r'^ipv6\s*=.*$', 'ipv6 = false',
               'General/ipv6=false (防 IPv6 直连泄露国内 IP)', re.M)

    # ---------- Proxy Group ----------
    txt = sub1(txt, r'^(AI = select,.*),policy-select-name=PROXY\s*$',
               r'\1,policy-select-name=美国节点', 'Group/AI 默认改为 美国节点', re.M)
    txt = sub1(txt, r'^(苹果服务 = select,.*),policy-select-name=DIRECT\s*$',
               r'\1,policy-select-name=美国节点',
               'Group/苹果服务 默认改为 美国节点 (原来直连=Apple AI 失效的元凶)', re.M)
    txt = sub1(txt, r'(?m)^(\[Rule\]\s*)$', AI_GROUP + r'\n\n\1',
               'Group/新增 🍎 Apple智能')

    # ---------- Rule ----------
    txt = sub1(txt, r'(?m)^(\[Rule\]\s*)$', r'\1' + APPLE_RULES.replace('\\', '\\\\'),
               'Rule/插入 Apple Intelligence 规则块 (置于所有规则最前)')
    txt, fixed = normalize_policy_case(txt)
    print(f"  [{'ok' if fixed else '!!'}] Rule/规范化策略名大小写  ({fixed} 处)")

    if FAILED:
        raise SystemExit(f"有 {len(FAILED)} 个补丁未命中, 拒绝生成半成品: {FAILED}")

    banner = ("# !!! 本文件由 scripts/merge_lazy_ai.py 自动生成, 请勿手改 !!!\n"
              "# 上游: https://raw.githubusercontent.com/LOWERTOP/Shadowrocket/main/lazy_group.conf\n"
              "# 重新生成: python3 scripts/fetch_upstream.py && python3 scripts/merge_lazy_ai.py\n"
              "# 内容: 上游 lazy_group.conf + Apple Intelligence 增强\n\n")
    txt = banner + txt

    for marker in ("🍎 Apple智能", "dns.google/dns-query#proxy", "direct-dns-server",
                   "DOMAIN-SUFFIX,pcc.apple.com", "policy-select-name=美国节点"):
        if marker not in txt:
            raise SystemExit(f"出厂自检失败, 缺少 {marker}")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"已生成: {args.out}  ({len(txt)} 字符)")


if __name__ == "__main__":
    main()
