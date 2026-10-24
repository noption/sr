# Shadowrocket 配置 · Apple Intelligence 增强

自建代理的分流配置。核心目标：**让 Apple Intelligence（Apple 智能）在受限地区稳定可用**。

- `lazy_group_ai.conf` — **主配置**。上游 [LOWERTOP/Shadowrocket](https://github.com/LOWERTOP/Shadowrocket) 的 `lazy_group.conf`（24 个分组 / 72 条规则，含 YouTube、Netflix、AI、苹果服务等全套分流）+ Apple 智能增强。
- `apple-intel.conf` — **精简版**。只做 Apple 智能分流，不含其他服务分组。适合只想要 AI 功能、不想动其他分流的人。

两个文件都能直接喂给 Shadowrocket 的「配置 → + → 粘贴配置链接」。

---

## 为什么需要这套东西

Apple Intelligence 的推理跑在私有云（Private Cloud Compute），苹果会在服务端看你的出口 IP 判断是否在支持地区。要跑通必须满足：

1. **所有 `apple.com` / `icloud.com` 流量统一走同一个美国 IP**
   一半直连、一半代理会导致账号校验与 PCC 握手 IP 不一致 → 失败。
   上游的 `Apple.list` 规则集里**并没有 `apple.com` 这个后缀**，漏网的会掉到 `GEOIP,CN,DIRECT`，
   所以本仓库额外加了兜底规则。
2. **DNS 不泄露到国内**
   上游默认用国内 DoH（`doh.pub`）且 `fallback=system`，这里改成经代理的 DoH，
   同时用 `direct-dns-server` 让国内域名仍然走国内 DNS，不影响国内服务速度。
3. **IPv6 关掉**
   上游 `ipv6 = true`，手机原生 IPv6 直连会漏出国内 IP，这里改成 `false`。
4. **AI 流量走 TCP 而不是 UDP/QUIC**
   Apple 社区实测 TCP+TLS 比 UDP/QUIC 稳定，所以新增的 `🍎 Apple智能` 组
   默认固定选 `🇺🇸 美国-VLESS-Reality`（TCP），而不是 Hysteria2。

### 相对上游改了什么

| 位置 | 改动 |
|---|---|
| `General/dns-server` | `https://dns.google/dns-query#proxy`（经代理） |
| `General/fallback-dns-server` | `https://cloudflare-dns.com/dns-query#proxy` |
| `General/direct-dns-server` | 新增 `https://dns.alidns.com/dns-query`（国内域名仍走国内 DNS） |
| `General/ipv6` | `true` → `false` |
| `Proxy Group/AI` | 默认 `PROXY` → `美国节点` |
| `Proxy Group/苹果服务` | 默认 `DIRECT` → `美国节点`（**Apple 智能失效的直接原因**） |
| `Proxy Group/🍎 Apple智能` | 新增，默认 `🇺🇸 美国-VLESS-Reality` |
| `Rule` | 最前面插入 Apple Intelligence 核心域名 + Apple 全家桶兜底 |
| `Rule` | 规范化策略名大小写（上游 `YOUTUBE` vs 分组 `YouTube`，共 14 处） |

---

## 使用步骤

### 1. 订阅节点

节点订阅**不放在这个仓库**（里面有 UUID 和密码，公开仓库会泄露）。
订阅地址从你自己服务器获取，形如：

```
http://<你的服务器>/sub/<你的token>
```

订阅里的节点名必须带**地区前缀**，否则 `lazy_group_ai.conf` 里的「美国节点」分组
（靠 `policy-regex-filter` 按节点名筛选）会是空的：

```
🇺🇸 美国-VLESS-Reality      ← TCP/TLS，更稳，Apple 智能默认用这个
🇺🇸 美国-Hysteria2          ← UDP/QUIC，更快，日常上网用
```

> 节点名前缀要和配置里的一致，否则分组会空。
> 参考链接格式：
> `vless://<uuid>@<host>:<port>?encryption=none&security=reality&type=tcp&sni=<sni>&fp=chrome&pbk=<publicKey>&sid=<shortId>&flow=xtls-rprx-vision#🇺🇸 美国-VLESS-Reality`

### 2. 导入小火箭

1. 首页 `+` → 类型选 **Subscribe** → 粘贴订阅地址 → 添加
2. 顶部「**配置**」→ `+` → 粘贴本仓库的 raw 地址 → 下载 → 点右侧 `✓` 使用配置
3. 首页「**全局路由**」→ 必须选「**配置**」（不是「代理」）
4. 确认分组：`🍎 Apple智能` → 选中 `🇺🇸 美国-VLESS-Reality`

raw 地址格式：

```
https://raw.githubusercontent.com/<账号>/<仓库>/main/lazy_group_ai.conf
https://raw.githubusercontent.com/<账号>/<仓库>/main/apple-intel.conf
```

### 3. iPhone 设置

```
设置 → 通用 → 语言与地区 → 地区 = United States
设置 → Apple 智能与 Siri → Siri 语言 = English (United States)
                          → Siri 声音 = American
```

然后接上 Wi-Fi + 充电 + **锁屏静置 10~15 分钟**，让约 7GB 的模型下载完成，
最后回到 设置 → Apple 智能与 Siri → 打开「Apple 智能」开关。

---

## 怎么更新

上游 `lazy_group.conf` 更新后，仓库会自动同步：

- **GitHub Actions** — `.github/workflows/update.yml` 每天跑一次，
  拉上游 → 重新合并 → 有变化就自动提交。也可以在 Actions 页面手动点一下触发。
- **本地手动跑**（改过脚本或想立刻生效）：

```bash
python3 scripts/fetch_upstream.py    # 拉上游快照到 upstream/lazy_group.conf
python3 scripts/merge_lazy_ai.py     # 重新生成 lazy_group_ai.conf
```

脚本有两道保险：上游内容不完整（段落缺失）会重试并取最长的版本；
任何一条补丁没命中就**拒绝生成半成品**，直接报错退出。

---

## 文件说明

```
lazy_group_ai.conf          主配置 (自动生成, 别手改)
apple-intel.conf            精简版 (手工维护)
upstream/lazy_group.conf    上游快照 (自动更新, 用于 diff 和复现)
scripts/fetch_upstream.py   拉上游 + 完整性校验
scripts/merge_lazy_ai.py    合并 + 生成 + 出厂自检
.github/workflows/          自动同步工作流
```

---

## 免责声明

本仓库只含**分流规则**，不含任何节点凭据。请不要把订阅链接、UUID、密码提交进公开仓库。
规则仅供个人学习研究使用。
