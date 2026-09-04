# 阿里云轻量服务器 · 保姆级部署教程

> 适用对象：已购买阿里云轻量应用服务器（Lightweight Server），想把这个平台部署到公网的人。
> 全程使用 Ubuntu 22.04 + Docker Compose，每步都有命令和“看到什么算正常”。

---

## 第 0 步：服务器选型与购买建议（还没买的看这里）

- 系统镜像选 **Ubuntu 22.04（纯净版）**，不要选“宝塔面板/WordPress/应用镜像”——
  那些会预装 Nginx/宝塔占掉 80 端口，后面还得清理；
- 配置建议 **2 核 4G 起步**（Embedding 模型、OCR、判题容器都需要内存）；
  如果已经是 2 核 2G，别急，第 3 步的脚本会自动加 4G swap，演示够用；
- 系统盘 40GB 起（判题镜像 + OCR 模型 + 数据库约 10GB）。

> ⚠️ **备案提醒（中国大陆服务器）**：用**域名**访问大陆轻量服务器，域名必须先完成
> **ICP 备案**（阿里云控制台搜“备案”，审核约 1~2 周）。急着演示：
> 用 `http://服务器IP` 直接访问（不需要备案），域名备案完成后再加上 HTTPS。

---

## 第 1 步：登录服务器

### 方式 A：阿里云网页“远程连接”（最省事）
轻量服务器控制台 → 点服务器 → “远程连接” → Workbench 网页终端，输入 root 密码进入。

### 方式 B：本机 PowerShell SSH（推荐，方便复制粘贴）
```powershell
ssh root@你的服务器IP
```
首次连接提示指纹时输入 `yes`，然后输入 root 密码。

> 看到类似 `root@xxx:~#` 的提示符就说明登录成功了。

---

## 第 2 步：放行防火墙（外网访问不了 90% 是这个原因）

阿里云轻量服务器有**两道**防火墙，都要放行：

1. **控制台防火墙**：轻量服务器控制台 → 本服务器 → 「防火墙」→「添加规则」：
   - TCP 80（HTTP）
   - TCP 443（HTTPS，配域名时用）
   - 22 一般默认已开
2. **系统内 ufw**（如果之前启用过）：
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status        # 看到 80、443 ALLOW 即可
```

验证：本机浏览器先访问 `http://服务器IP`，此时应该还打不开（服务没起），
但**不要看到“连接超时”以外的错误**——如果连“连接超时”都没有、是立刻拒绝，
说明防火墙没放行 80。

---

## 第 3 步：一键初始化服务器（Docker + Compose + swap）

先把代码上传到服务器（跳到第 4 步），上传完成后在项目根目录执行这一条命令，
它会自动：加 swap（内存 <2G 时）、装 Docker（阿里云镜像源）、装 Compose、
配 Docker Hub 加速、装 nano/curl/git/htop：

```bash
bash deploy/setup-server.sh
```

看到最后输出 `docker --version` 和 `docker compose version` 的版本号，就说明装好了。

> 国内网络拉不到 Docker 源时：脚本用的是阿里云镜像源（mirrors.aliyun.com/docker-ce），
> 一般没问题；仍失败就把报错发我。

---

## 第 4 步：把项目代码传到服务器

### 方式 A：本机打包上传（推荐，代码在本地）

在本机（Windows PowerShell，进入项目上级目录）：
```powershell
# 1) 打包（排除 node_modules、data、.git 等大目录）
tar -czf jbgs.tar.gz --exclude=node_modules --exclude=dist --exclude=frontend/node_modules `
  --exclude=.git --exclude=backend/data --exclude=backups -C D:\MyStudy\2026Summer jbgs

# 2) 上传到服务器（输入密码）
scp jbgs.tar.gz root@你的服务器IP:/root/
```

然后回到服务器 SSH 终端解压：
```bash
cd /root
tar -xzf jbgs.tar.gz
cd jbgs
```

### 方式 B：git 拉取（代码在 GitHub/Gitee）
```bash
cd /root
git clone 你的仓库地址 jbgs
cd jbgs
```

### 方式 C：阿里云网页上传
轻量服务器控制台 → 文件 → 上传文件，把压缩包传上去后在终端解压。

---

## 第 5 步：配置 .env（所有密码和密钥都在这）

```bash
cd /root/jbgs
cp .env.cloud.example .env
```

生成两个随机密钥，然后编辑：
```bash
openssl rand -hex 32     # 复制输出，稍后填到 SECRET_KEY
openssl rand -hex 16     # 复制输出，稍后填到 POSTGRES_PASSWORD
nano .env
```

在 nano 里至少改这几行（`Ctrl+O` 保存，`Ctrl+X` 退出）：

```dotenv
POSTGRES_PASSWORD=刚生成的16位随机串
SECRET_KEY=刚生成的32位随机串
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
CORS_ORIGINS=https://你的域名      # 没域名就保持注释或填 http://服务器IP
DEMO_MODE=false
```

> 域名没备案时，用 IP 访问：把 `CORS_ORIGINS` 改成 `http://你的服务器IP` 即可，
> `WEB_PORT=80` 保持默认。

---

## 第 6 步：启动（构建镜像 + 起服务）

```bash
cd /root/jbgs

# 可选：预拉判题镜像（国内网络下建议做，首次提交不用等）
bash deploy/pull-images.sh

# 构建并后台启动
docker compose up -d --build
```

看状态：
```bash
docker compose ps
```

正常应看到 3 个服务：
```
NAME            STATUS
jbgs-db         Up ... (healthy)
jbgs-backend    Up ... (healthy)
jbgs-frontend   Up
```

如果 `db` 或 `backend` 还在 `starting`，等 1~2 分钟再看一次：
```bash
sleep 60 && docker compose ps
```

看日志（有报错从这里查）：
```bash
docker compose logs -f backend
docker compose logs db
```

---

## 第 7 步：验证上线

1. 后端健康检查：
```bash
curl http://127.0.0.1:8000/api/health
```
应返回 `{"status":"ok", ...}`。

2. 本机浏览器访问：`http://服务器IP`，看到登录页就成功了。

3. 功能冒烟（建议按顺序测）：
   - 注册一个教师账号（首页 → 账号注册），注册后自动登录；
   - 新建课程 → 上传一份小 PDF（测试 OCR/RAG 链路，首次会下载模型，稍慢属正常）；
   - 建一道编程题（标准输入输出测试点）→ 学生账号提交 → 等 5~10 秒出 AC；
   - 问 AI 学科导师一个问题（测试 DeepSeek + RAG）。

---

## 第 8 步：域名 + HTTPS（备案完成后）

1. 阿里云域名解析：添加 A 记录，主机记录 `@`（或 `www`），记录值 = 服务器 IP；
2. 修改 `deploy/Caddyfile.example`，把 `your-domain.com` 换成你的域名：
```bash
cp deploy/Caddyfile.example Caddyfile
nano Caddyfile    # 改域名
```
3. 启动 Caddy（自动申请并续期 HTTPS 证书）：
```bash
docker run -d --name caddy --restart unless-stopped \
  -p 80:80 -p 443:443 \
  -v $PWD/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy-data:/data \
  caddy:2
```
4. 把 `.env` 的 `CORS_ORIGINS` 改成 `https://你的域名`，重启后端：
```bash
cd /root/jbgs
docker compose up -d
```
5. 浏览器访问 `https://你的域名` 验证。

> Caddy 拉取镜像失败就手动配加速：先执行 `bash deploy/setup-server.sh` 里的 daemon.json
> 步骤（脚本已内置），再 `docker pull caddy:2` 重试。

---

## 第 9 步：设置每日自动备份

```bash
cd /root/jbgs
crontab -e
```
粘贴这一行（每天凌晨 3 点备份）：
```
0 3 * * * cd /root/jbgs && bash deploy/backup.sh >> /var/log/jbgs-backup.log 2>&1
```
备份文件在 `/root/jbgs/backups/`，建议定期下载到本地或同步到对象存储。

---

## 第 10 步：升级更新

```bash
cd /root/jbgs
# 方式 A：git 更新（如果代码是 git 拉的）
git pull
# 方式 B：重新上传压缩包并解压覆盖
docker compose up -d --build
```
数据库结构变化会自动迁移，不会丢数据。

---

## 常见问题排查

| 现象 | 原因与解决 |
| --- | --- |
| 浏览器“连接超时” | 控制台防火墙没放行 80/443（第 2 步） |
| `docker compose up` 报 `POSTGRES_PASSWORD` 缺失 | 忘记 `cp .env.cloud.example .env` 或没填密码 |
| backend 起不来、日志报数据库连接失败 | db 还没 healthy，等 1~2 分钟；或 `docker compose logs db` 看密码是否一致 |
| 提交代码报 “Docker 执行失败” | 确认后端容器挂载了 docker.sock；`docker pull python:3.11-slim` 等镜像已拉取 |
| 上传 PDF 一直“处理中” | 首次 OCR 要下载模型，看 `docker compose logs -f backend`；内存不足可重启大内存实例或看 swap |
| AI 回答报 503 / DeepSeek 失败 | 检查 `.env` 的 `DEEPSEEK_API_KEY`；服务器出网是否正常（`curl https://api.deepseek.com`） |
| 页面白屏 / API 404 | `docker compose logs -f frontend`；确认 80 端口没被宝塔/Nginx 占用（`ss -ltnp | grep :80`） |
| 磁盘快满 | `docker system prune -f` 清无用镜像；备份文件定期下载到本地 |

---

## 其他参考

- 完整架构/环境变量/安全清单：`docs/DEPLOYMENT.md`
- 判题沙箱原理与配置：`docs/DOCKER-JUDGE.md`
- 数据库与结构化解析：`docs/PG-STRUCTURED-PARSING.md`
