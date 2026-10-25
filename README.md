# 医疗疾病数据分析系统

> **技术栈**：Spring Boot 3 + MyBatis-Plus + JWT + Spring Security | FastAPI + DeepSeek + PyTorch | Vue 3 + Element Plus + Pinia | MySQL 8

---

## 作品描述

### 一句话介绍

把"疾病知识、药品数据、真实诊疗记录"打通成一条链路：患者用日常口语说出症状就能得到可能的疾病方向与就医建议，医生开病历时能直接查到疾病与药品的对应依据，管理员统一管理数据、账号与医生资质。

### 要解决的问题

| 场景         | 现状痛点                                             | 本作品的做法                                                       |
| ------------ | ---------------------------------------------------- | ------------------------------------------------------------------ |
| 患者自查     | 搜索引擎给的是零散、同质化的健康文章，落不到具体疾病 | 口语症状 → 标准症状关键词 → 疾病库匹配，输出候选疾病、匹配度、建议检查与用药参考 |
| 医生开方     | 疾病与药品的对应关系散落在经验和说明书里，检索成本高 | 977 条疾病与 994 条药品建立 3538 条关联，开病历时按疾病带出参考用药 |
| 数据与权限   | 爬虫数据、账号、医生资质缺少统一入口                 | 管理员审核医生资质、管理用户/疾病/药品，并有统计看板               |

### 核心功能

| 角色   | 功能                                                                             |
| ------ | -------------------------------------------------------------------------------- |
| 患者   | 症状自测（多轮问诊、鉴别方向、风险提示）、查看本人病历、药品关键词搜索           |
| 医生   | 患者列表、开具病历（选患者 → 查疾病 → 加处方）、历史病历、药品查询               |
| 管理员 | 数据统计看板（ECharts）、用户管理、医生资质审核、疾病与药品数据管理               |

### 数据基础（当前数据库实测条数）

| 内容           | 规模                                  | 来源                             |
| -------------- | ------------------------------------- | -------------------------------- |
| 疾病           | 977 条                                | WHO ICD-11 爬虫采集              |
| 药品           | 994 条                                | NMPA 药品数据爬虫                |
| 疾病-药品关联  | 3538 条                               | 按适应证与名称规则构建           |
| 药品分类       | 13 类药理分类 + 剂型标准化            | 分类/剂型映射脚本                |
| 口语症状同义词 | 320 条映射                            | 手工整理，Java 与 Python 共用    |

### 技术要点

1. **症状理解走"词典 + 大模型"双通道**：320 条同义词映射把"肚子疼""嗓子不舒服"归一成标准症状，并支持"部位 + 不适"的开放组合；DeepSeek 再补全自然语言里的隐含症状。
2. **语义检索补足字面匹配的盲区**：用 bge-small-zh-v1.5 把症状向量化，Top-12 召回疾病候选，避免"咳嗽"匹配不到"以干咳为主要表现"这类表述。
3. **问诊过程可见**：Agent 拆成"症状理解 → 知识库检索 → 综合分析"三步并逐步返回前端；多轮对话通过 `history` 逐步收敛诊断。
4. **降级不空手而归**：DeepSeek 不可用时规则引擎独立出结果，页面不会空白；诊断不确定时返回"待进一步判断" + 建议检查 + 安全提醒。
5. **词典单一数据源**：Python 规则引擎直接从 Java 的 `SYMPTOM_SYNONYMS` 源码提取词典，避免前后端两套标准互相打架。

### 创新点

- 医疗结论以本地知识库为主、大模型只负责理解与组织表达，降低纯 LLM 常见的"编造病名/药品"风险。
- 规则引擎与语义检索互补：前者保证结果可解释，后者保证召回覆盖面。
- 采集、清洗、导入、问诊、病历、统计整条链路在同一系统内闭环，可直接复现。

### 作品形态

前后端分离的三端 Web 系统：Spring Boot（8088）承载业务与鉴权，FastAPI（8000）承载 AI 问诊，Vue 3 + Vite（5173）承载界面；线上通过 Nginx 反向代理部署。

### 说明与边界

本系统面向毕业设计与健康科普，输出仅供健康参考，不构成诊断结论或处方；涉及用药与治疗请以医生意见为准。

---

## 一、项目结构

```
医疗疾病系统/
├── backend/                        # Spring Boot 后端（端口 8088）
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/medical/
│       │   ├── controller/         # 8 个 REST 控制器
│       │   ├── service/            # 9 个 Service
│       │   ├── mapper/             # 9 个 MyBatis-Plus Mapper
│       │   ├── entity/             # 8 个实体类
│       │   ├── dto/                # 请求/响应 DTO
│       │   ├── config/             # Security / CORS / MyBatisPlus 配置
│       │   ├── filter/             # JWT 过滤器
│       │   ├── common/             # Result / SecurityUser / 全局异常
│       │   └── util/               # JwtUtils
│       └── resources/
│           ├── application-example.yml  # 配置模板（复制为 application.yml 后填写）
│           └── schema.sql          # 建表 SQL + 测试数据
│
├── backend_py/                     # AI 智能问诊服务（FastAPI，端口 8000）
├── frontend/                       # Vue 3 前端（端口 5173）
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── router/                 # 路由 + 守卫
│       ├── stores/                 # Pinia 状态
│       ├── api/                    # Axios 接口层
│       ├── utils/                  # request 拦截器
│       └── views/
│           ├── Login.vue / Register.vue
│           ├── layout/             # 三角色布局
│           ├── admin/              # Dashboard / 用户 / 医生审核 / 疾病 / 药品
│           ├── doctor/             # 患者列表 / 开具病历 / 历史病历 / 药品查询
│           └── patient/            # 我的病历 / 症状自测 / 药品查询
│
├── scraper_diseases.py             # WHO ICD-11 疾病爬虫
├── scraper_drugs.py                # NMPA 药品爬虫
├── generate_sample_data.py         # 生成演示数据
├── import_to_mysql.py              # CSV → MySQL 导入脚本
├── requirements.txt                # Python 依赖
└── 药品数据.xlsx
```

---

## 二、环境要求

| 环境                     | 版本要求   |
| ------------------------ | ---------- |
| JDK                      | 17         |
| Maven                    | 3.6 或以上 |
| Node.js                  | 18 或以上  |
| MySQL                    | 8.0 或以上 |
| Python（AI 问诊 / 爬虫） | 3.9 或以上 |

> 如果你已安装 Maven，但命令行提示 `mvn` 未识别，说明 Maven 的 `bin` 目录未加入系统环境变量。
>
> 例如你的 Maven 安装目录是 `D:\Maven\apache-maven-3.9.16`，则需要将以下路径添加到 `PATH`：
>
> `D:\Maven\apache-maven-3.9.16\bin`

---

## 三、启动步骤

### 第一步：初始化数据库

打开任意 MySQL 客户端（Navicat、MySQL Workbench、命令行均可），执行以下 SQL 文件：

```sql
-- 方式1：命令行
mysql -u root -p < "d:\计算机毕业设计\医疗疾病系统\backend\src\main\resources\schema.sql"

-- 方式2：在客户端中打开并执行该文件
-- 路径：backend/src/main/resources/schema.sql
```

执行完成后将创建：

- 数据库：`medical_data`
- 6 张新表：`users` / `patients` / `doctors` / `patient_doctor` / `medical_records` / `self_tests`
- 测试数据：1 管理员 + 2 医生 + 5 患者 + 8 条病历

> 如果你已有 `diseases` / `drugs` / `disease_drug_relation` 三张表（由之前的爬虫导入），会自动复用；若没有，先运行 `python generate_sample_data.py` 再运行 `python import_to_mysql.py` 生成测试数据。

---

### 第二步：生成本地配置文件（重要）

仓库出于安全考虑**不包含**真实配置，只有模板。首次克隆后先把模板复制为真实配置：

```powershell
# Spring Boot 后端
Copy-Item backend/src/main/resources/application-example.yml backend/src/main/resources/application.yml

# Python AI 服务（可选，本地私有配置）
Copy-Item backend_py/config.example.py backend_py/config_local.py
```

然后按需修改 `application.yml` 中的数据库账号密码，并设置 JWT 密钥与 DeepSeek Key：

```yaml
spring:
  datasource:
    username: root
    password: ${DB_PASSWORD:你的MySQL密码}   # 建议用环境变量 DB_PASSWORD 注入

jwt:
  secret: ${JWT_SECRET:自定义密钥，至少32字符}
```

```powershell
$env:DB_PASSWORD      = "你的MySQL密码"
$env:JWT_SECRET       = "自定义JWT密钥，至少32字符"
$env:DEEPSEEK_API_KEY = "你的DeepSeek_API_Key"
```

症状自测的规则匹配支持 DeepSeek 关键词转换。
系统会先用 DeepSeek 将自然语言症状转换为标准关键词，再结合本地疾病和药品数据匹配。未能确定具体疾病时，也会返回“待进一步判断”的参考结果、药品数据和安全建议，不会返回空结果。

> **配置文件说明**：`.gitignore` 已排除 `backend/src/main/resources/application.yml`、`backend_py/config_local.py`、`.deploy/`、`backend_py/models/`、日志与构建产物。仓库只保留 `application-example.yml` 与 `config.example.py` 两个模板；请勿把真实密码、API Key 与服务器凭据提交进仓库。

---

### 第三步：启动后端

在 `backend/` 目录下执行：

```bash
# 方式1：Maven 命令（推荐）
mvn spring-boot:run

# 方式2：先打包再运行
mvn clean package -DskipTests
java -jar target/medical-system-1.0.0.jar
```

启动成功后控制台会显示：

```
Started MedicalApplication in x.xxx seconds
Tomcat started on port 8088
```

后端接口地址：**http://localhost:8088**

---

### 第四步：启动前端

在 `frontend/` 目录下执行：

```bash
# 首次运行，先安装依赖
npm install

# 启动开发服务器
npm run dev
```

启动成功后控制台显示：

```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

前端访问地址：**http://localhost:5173**

### 第五步：启动 AI 智能问诊服务（必须单独启动）

AI 多轮问诊由独立的 Python FastAPI 服务提供，不包含在 Spring Boot 后端中。它通过 Vite 开发代理以 `/ai` 路径转发到本机 8000 端口，因此**必须同时运行 MySQL、Spring Boot、前端和 Python AI 服务**。AI 服务读取 MySQL 中的疾病、药品和关联知识库；另外使用 DeepSeek API 和本地中文语义模型提供分析能力。

#### 5.1 环境与配置

- Python 3.9 或以上版本。
- MySQL 已启动，且已按第一步初始化 `medical_data` 数据库及疾病、药品和关联表。AI 服务启动时会连接 `127.0.0.1:3306`，配置见 `backend_py/config.py`。
- 需安装 `backend_py/requirements.txt` 中的 Python 依赖。PyTorch CPU 版适合没有 NVIDIA CUDA 环境的本机开发。
- 如需 DeepSeek 在线分析，在启动 AI 服务的同一个 PowerShell 窗口设置 `DEEPSEEK_API_KEY`。Key 仅保存在当前 PowerShell 进程环境中，不要写进代码或提交到仓库。未配置 Key 时，服务可以启动，但症状理解和综合分析将使用本地规则兜底，结果可能较简单。

#### 5.2 安装并启动

另开一个 PowerShell 窗口，在项目根目录执行以下命令。该窗口需要保持打开，关闭窗口或按 `Ctrl+C` 会停止 AI 服务。

```powershell
cd "D:\计算机毕业设计\医疗疾病系统\backend_py"

# 可选：创建独立虚拟环境，避免与其他 Python 项目依赖冲突
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖。若 PyTorch 安装失败或误装了 CUDA 版，可先安装 CPU 版：
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt

# 可选：需要 DeepSeek 在线分析时设置 Key；仅对当前 PowerShell 窗口有效
$env:DEEPSEEK_API_KEY = "你的DeepSeek_API_Key"

# 启动 FastAPI 服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

如果 PowerShell 阻止虚拟环境激活，可不激活环境，直接运行 `.venv\Scripts\python.exe -m pip install -r requirements.txt` 和 `.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000`。也可使用已经配置好依赖的 Python 环境，但安装依赖和启动命令必须使用同一个 Python。

首次启动可能需要从 Hugging Face 镜像下载约 95 MB 的 `BAAI/bge-small-zh-v1.5` 模型，模型会缓存到 `backend_py\models`。模型下载期间请保持服务窗口运行。启动日志应依次显示知识库加载完成、模型加载完成和 `[embed] 索引完成：977 种疾病向量`。如果模型下载失败，服务可能仍能启动，但健康检查会显示 `embeddingModel.ready: false`，语义检索不可用。

#### 5.3 检查服务是否就绪

浏览器打开 **http://localhost:8000/ai/health**，或在另一个 PowerShell 窗口运行：

```powershell
Invoke-RestMethod http://localhost:8000/ai/health
```

检查返回值：

- `status` 为 `ok`：FastAPI 服务正在运行。
- `knowledgeBase.diseases`、`knowledgeBase.drugs` 大于 0：本地疾病、药品知识已加载。
- `embeddingModel.ready` 为 `true`：中文语义模型已加载并完成索引。
- `ruleEngine.synonyms` 大于 0：本地症状同义词规则已加载。

服务就绪后，在前端登录患者账号，进入 `/patient/self-test`，在页面顶部的“AI 智能问诊”填写症状并点击“开始 AI 问诊”。AI 推荐药名可点击查看药品详情；药品详情查询依赖 Spring Boot 8088 服务及登录状态。AI 页面中“规则引擎快速匹配”是另一项功能，调用 Spring Boot 接口，不等同于 Python AI 问诊。

#### 5.4 AI 服务接口

AI 服务的接口路径本身包含 `/ai` 前缀。Vite 开发服务器会将前端请求代理到 `http://localhost:8000`。

| 方法 | 本机地址                                | 用途                                 |
| ---- | --------------------------------------- | ------------------------------------ |
| GET  | `http://localhost:8000/ai/health`     | 查看服务、知识库、模型和规则引擎状态 |
| POST | `http://localhost:8000/ai/agent/chat` | 提交症状并进行单轮或多轮问诊         |

请求示例：

```json
{
  "symptoms": "这两天嗓子疼、咳嗽，还有点发烧",
  "history": []
}
```

多轮问诊时，`history` 是按先后顺序排列的对话数组，每项包含 `role`（`assistant` 或 `user`）和 `content`。响应包含 `steps`（症状理解、知识检索、综合分析过程）和 `result`（鉴别诊断、建议检查、风险提示、用药信息及追问）。AI 输出仅供健康参考，不可替代医生诊断或处方。

#### 5.5 常见问题排查

| 现象                                                | 检查与处理                                                                                                                                                            |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 页面提示无法连接 AI 服务 / 浏览器无法打开 8000 端口 | 确认启动命令运行在 `backend_py` 目录，AI 服务窗口没有关闭，并且日志出现 `Uvicorn running on http://0.0.0.0:8000`。检查本机 8000 端口是否被其他程序占用。          |
| 页面显示 HTTP 500 或服务启动后退出                  | 查看运行 Uvicorn 的 PowerShell 窗口完整错误。优先检查 MySQL 是否启动、`backend_py/config.py` 的数据库地址和账号是否正确、疾病/药品/关联表是否存在。                 |
| 报错缺少 `pharmacopoeia_chunks` 表                | 该表是可选药典知识。当前代码会在表不存在时跳过药典检索，不影响普通问诊；如果仍启动失败，请查看是否是其他 MySQL 表或字段报错。                                         |
| `embeddingModel.ready` 为 `false`               | 查看服务日志中的 `[embed] 加载失败`。通常是模型下载中断、网络无法访问模型镜像或 PyTorch 安装异常。修复网络/依赖后重启服务；模型下载完成后会使用本地缓存。           |
| 没有 DeepSeek 分析或结果显示规则兜底                | 在运行 AI 服务的同一个 PowerShell 窗口设置有效的 `$env:DEEPSEEK_API_KEY` 后重启服务。检查 DeepSeek Key、网络连通性和 AI 服务日志。                                  |
| AI 药品详情打不开                                   | 确认 Spring Boot 8088 服务已运行、浏览器登录状态有效，并检查药品数据及 `/api/drugs` 接口。AI 返回的药名若与本地药品库名称不完全相同，详情会显示“未找到详细信息”。 |

每次新开 PowerShell 窗口都需要重新激活虚拟环境并重新设置该窗口的 `DEEPSEEK_API_KEY`，然后启动 AI 服务。

---

## 四、访问系统

打开浏览器访问 **http://localhost:5173**，使用以下测试账号登录：

### 测试账号（密码统一为 `123456`）

| 账号             | 角色   | 登录后跳转页面                        |
| ---------------- | ------ | ------------------------------------- |
| `admin`        | 管理员 | http://localhost:5173/admin/dashboard |
| `doctor_zhang` | 医生   | http://localhost:5173/doctor/patients |
| `doctor_li`    | 医生   | http://localhost:5173/doctor/patients |
| `patient_wang` | 患者   | http://localhost:5173/patient/records |
| `patient_li`   | 患者   | http://localhost:5173/patient/records |
| `patient_zhao` | 患者   | http://localhost:5173/patient/records |
| `patient_chen` | 患者   | http://localhost:5173/patient/records |
| `patient_liu`  | 患者   | http://localhost:5173/patient/records |

### 各角色功能入口

**管理员（admin）**

- `/admin/dashboard` — 数据统计看板（ECharts 图表）
- `/admin/users` — 用户列表管理
- `/admin/doctors/verify` — 医生资质审核（通过 / 驳回）
- `/admin/diseases` — 疾病数据查看
- `/admin/drugs` — 药品数据查看

**医生（doctor_zhang / doctor_li）**

- `/doctor/patients` — 我的患者列表
- `/doctor/write-record` — 开具病历（选患者 → 搜索疾病 → 添加处方）
- `/doctor/records` — 历史病历记录
- `/doctor/drug-search` — 药品关键词搜索

**患者（patient_xxx）**

- `/patient/records` — 查看自己的病历
- `/patient/self-test` — 症状自测（输入症状 → 匹配疾病 + 推荐药品）
- `/patient/drug-search` — 药品关键词搜索

---

## 五、API 接口说明

后端 Base URL：`http://localhost:8088/api`

| 方法 | 路径                     | 说明                 | 权限             |
| ---- | ------------------------ | -------------------- | ---------------- |
| POST | `/auth/login`          | 登录，返回 JWT Token | 公开             |
| POST | `/auth/register`       | 患者注册             | 公开             |
| GET  | `/auth/me`             | 获取当前用户信息     | 已登录           |
| GET  | `/patients`            | 患者分页列表         | 管理员/医生      |
| GET  | `/patients/{id}`       | 患者详情             | 管理员/医生/本人 |
| PUT  | `/patients/{id}`       | 修改患者信息         | 本人             |
| GET  | `/doctors`             | 医生分页列表         | 管理员           |
| PUT  | `/doctors/{id}/verify` | 审核医生             | 管理员           |
| GET  | `/records`             | 病历列表（角色隔离） | 已登录           |
| POST | `/records`             | 创建病历             | 医生             |
| GET  | `/records/{id}`        | 病历详情             | 医生/患者本人    |
| GET  | `/drugs`               | 药品分页搜索         | 已登录           |
| GET  | `/drugs/{id}`          | 药品详情             | 已登录           |
| GET  | `/diseases`            | 疾病分页搜索         | 已登录           |
| GET  | `/diseases/{id}`       | 疾病详情             | 已登录           |
| GET  | `/diseases/{id}/drugs` | 疾病对应推荐药品     | 已登录           |
| POST | `/prediction`          | 症状自测匹配         | 已登录           |
| GET  | `/statistics/overview` | 统计总览             | 管理员           |

所有需要鉴权的接口，请求头需携带：

```
Authorization: Bearer <登录返回的token>
```

---

## 六、数据爬虫（可选）

如需采集真实数据替换演示数据，先安装 Python 依赖：

```bash
pip install -r requirements.txt
```

运行爬虫：

```bash
# 采集 WHO ICD-11 疾病数据 → data/diseases.csv
python scraper_diseases.py

# 采集 NMPA 药品数据 → data/drugs.csv
python scraper_drugs.py

# 将 CSV 数据导入 MySQL
python import_to_mysql.py
```

> 需要已安装 Chrome 浏览器，Selenium 4.6+ 会自动管理 ChromeDriver。

---

## 七、常见问题

**Q：后端启动报 `Unknown database 'medical_data'`**

> 先执行第一步的 schema.sql 初始化数据库。

**Q：后端报 `Access denied for user 'root'`**

> `application.yml` 中的数据库密码不正确，修改为你的 MySQL 实际密码。

**Q：前端访问报 401 / 403**

> 先确认已登录，并清除浏览器旧 Token 后重新登录：打开开发者工具执行 `localStorage.clear()`，刷新页面再登录。病历接口需要携带当前登录用户的 JWT。

**Q：症状自测仍提示 Redis 连接错误**

> 当前版本已移除 Redis 依赖，改用 JVM 本地内存缓存。请停止旧后端进程并重新执行 `mvn spring-boot:run`，确认运行的是最新代码。

**Q：`npm install` 很慢**

> 配置国内镜像：`npm config set registry https://registry.npmmirror.com`

**Q：Maven 下载依赖慢**

> 在 Maven `settings.xml` 中添加阿里云镜像：
>
> ```xml
> <mirror>
>   <id>aliyun</id>
>   <mirrorOf>central</mirrorOf>
>   <url>https://maven.aliyun.com/repository/central</url>
> </mirror>
> ```

**Q：Chrome 驱动报 `TimeoutError: wdm-lock`**

> 删除锁文件：`C:\Users\你的用户名\.wdm\.wdm-lock-chromedriver-win64`

---

*最后更新：2026年8月*
