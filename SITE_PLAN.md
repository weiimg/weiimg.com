# weiimg.com 網站規劃執行企劃書

> 版本：v1.0 | 日期：2026-05-07

---

## 一、網站定位

| 項目 | 內容 |
|---|---|
| 性質 | 個人作品集 × 數位名片 |
| 主要使用情境 | 提案前傳送連結預習、提案當場展示 |
| 目標受眾 | 中南部中小企業主、行銷負責人 |
| 希望給訪客的感覺 | 有品味、有想法、值得信任 |
| 視覺語氣 | 大膽、有個性、不過度商業 |

---

## 二、網站地圖（Sitemap）

```
weiimg.com/
├── index.html              → Landing Page（單頁滾動）
├── brand/
│   ├── index.html          → 品牌形象列表
│   └── [slug]/index.html   → 個別品牌形象文章（輪播圖 + 雙欄文字）
├── shortform/
│   └── index.html          → 短影音（依產業類別篩選）
├── video/
│   └── index.html          → 影像製作（依類型篩選）
├── about/
│   └── index.html          → 關於（個人照、介紹、得獎紀錄）
└── blog/
    ├── index.html          → Blog 列表（從 Beehiiv 搬入）
    └── [slug]/index.html   → 個別 Blog 文章
```

**Nav 結構：**
- 作品 ▾（hover 自動展開：品牌形象 / 短影音 / 影像製作）
- 關於
- Blog
- 聯絡

### 頁面說明

**Landing Page（主頁）**
單頁滾動：
1. Hero — CONCEPT → CONTENT 動畫 + 從策略到執行
2. 作品牆 — 單張大圖（16:9 滿版，由使用者自行設計合成圖上傳）
3. 服務細項 + 客戶 Logo 牆
4. Contact — Email + Instagram

**品牌專案（brand/）— 文章式**
- `brand/index.html`：所有品牌專案的列表（卡片）
- 點擊卡片 → 進入該專案的獨立文章頁
- 文章頁版型：**頁面上方輪播圖** + **下方段落文字**
- 設計目標：方便日後手動新增文章

**短影音（shortform/）— 標籤篩選**
- 單頁，頂部一排產業類別標籤
- 點擊標籤動態篩選網格內容
- 產業類別：餐飲、電子工業、房產、重機、潮玩零售

**影像製作（video/）— 標籤篩選**
- 單頁，頂部一排類型標籤
- 點擊標籤動態篩選網格內容
- 類型：音樂 MV、競賽短片、實驗短片、廣告

---

## 三、技術架構

### 技術選擇
| 項目 | 選擇 | 理由 |
|---|---|---|
| 框架 | 純 HTML / CSS / JS | 無依賴、載入最快、易維護 |
| 動畫 | CSS Transitions + Intersection Observer | 不依賴 JS 動畫庫，效能好 |
| 頁面切換 | CSS opacity fade（0.3s） | 輕量，不影響載入 |
| 字型載入 | jsDelivr CDN + `font-display: swap` | 源石黑體、Sarasa TC 都託管於 jsDelivr |
| 圖片 | WebP 格式 + `loading="lazy"` | 加速載入 |
| 影片 | Cloudflare Stream（iframe lazy load） | 自適應碼率、全球 CDN |
| 部署 | GitHub Pages → Cloudflare DNS → weiimg.com | 現有架構延續 |

### 檔案結構
```
weiimg.com/
├── index.html                Landing
├── brand/
│   ├── index.html            品牌專案列表
│   ├── jiuglu/index.html     酌穀餐酒館（範例）
│   ├── meishipa/index.html   媒拾捌（範例）
│   └── [更多文章]/index.html
├── shortform/
│   └── index.html            短影音（標籤篩選）
├── video/
│   └── index.html            影像製作（標籤篩選）
├── css/
│   ├── tokens.css            設計 Token（顏色、字型、間距變數）
│   ├── base.css              Reset + 基礎排版
│   ├── layout.css            Grid 系統、Container
│   ├── components.css        Nav、Card、Carousel、Tag 篩選器
│   └── animation.css         Scroll reveal、頁面切換、CONCEPT 動畫
├── js/
│   ├── nav.js                漢堡選單、頁面淡入淡出切換
│   ├── scroll.js             IntersectionObserver scroll reveal
│   ├── hero.js               CONCEPT → CONTENT 動畫
│   └── filter.js             短影音 / 影像製作 標籤篩選
└── assets/
    ├── images/               專案封面、輪播圖（WebP）
    └── og/                   Open Graph 預覽圖
```

> 字型走 jsDelivr CDN，不需要自託管。

---

## 四、設計系統

### 4.1 色彩系統

| Token 名稱 | 色值 | 用途 |
|---|---|---|
| `--color-bg` | `#F7F6F3` | 頁面底色（暖白） |
| `--color-surface` | `#FFFFFF` | 卡片、浮層背景 |
| `--color-text-primary` | `#111111` | 主要文字 |
| `--color-text-secondary` | `#888888` | 次要文字、標籤 |
| `--color-accent` | `#2273BA` | 強調色（藍，極少使用） |
| `--color-border` | `#E5E3DE` | 分隔線、邊框 |
| `--color-overlay` | `rgba(17,17,17,0.04)` | Hover 遮罩 |

> 藍色 `#2273BA` 為唯一有彩色，出現極少，出現即有份量。整體近乎無色。

### 4.2 字型系統

| 角色 | 字型 | 備註 |
|---|---|---|
| 中文標題 | GenSeki Gothic Heavy（源石黑體） | 自托管，需取得授權或免費版本 |
| 中文內文 | Sarasa TC Regular | 自托管，開源免費 |
| 英文 / 數字 | Inter | Google Fonts CDN |

**英文排版規則：**
```css
font-family: 'Inter', sans-serif;
letter-spacing: -0.05em;
```

**字型大小階層（Desktop）：**

| 層級 | 大小 | 字重 | 字型 |
|---|---|---|---|
| Display（Hero 名字） | 120px | Heavy | GenSeki Gothic |
| H1 | 72px | Heavy | GenSeki Gothic |
| H2 | 48px | Heavy | GenSeki Gothic |
| H3 | 28px | Heavy | GenSeki Gothic |
| Body | 17px | Regular | Sarasa TC |
| Caption / Label | 13px | Regular | Sarasa TC / Inter |

> 標題與內文比例最小為 **2.8:1**，視覺對比強烈。

**字型大小階層（Mobile）：**

| 層級 | 大小 |
|---|---|
| Display | 56px |
| H1 | 40px |
| H2 | 28px |
| H3 | 20px |
| Body | 16px |
| Caption | 12px |

### 4.3 間距系統（8px 基準）

```
4px   / 0.25rem   → 極小間距
8px   / 0.5rem    → XS
16px  / 1rem      → S
24px  / 1.5rem    → M
32px  / 2rem      → L
48px  / 3rem      → XL
64px  / 4rem      → 2XL
96px  / 6rem      → 3XL
128px / 8rem      → Section 間距
```

### 4.4 Grid 系統

**Desktop（≥1280px）**
- 欄數：12 欄
- Gutter：24px
- 最大寬度：1280px
- 左右 Margin：80px

**Tablet（768px–1279px）**
- 欄數：8 欄
- Gutter：20px
- 左右 Margin：40px

**Mobile（<768px）**
- 欄數：4 欄
- Gutter：16px
- 左右 Margin：24px

---

## 五、頁面版型規格

### 5.1 Landing Page

**Nav（固定頂部）**
- 左：Logo 或名字（GenSeki Gothic）
- 右（Desktop）：品牌專案 / 短影音 / 影像製作 / 聯絡
- 右（Mobile）：漢堡選單圖示
- 背景：`rgba(247,246,243,0.9)` + `backdrop-filter: blur(12px)`
- 高度：64px
- 邊界：底部 `1px solid var(--color-border)`

**Hero Section**
- 純字體動畫，無圖片
- **總區段高度：200vh**
- 內部容器 `position: sticky; top: 0; height: 100vh`，置中排版
- **CONCEPT** 大字（Display 120px，GenSeki Gothic Heavy）

**動畫時序（依 scroll progress）：**
| 進度 | 行為 |
|---|---|
| 0% – 30% | CONCEPT 完全靜止 |
| 30% – 70% | 第4字母 C→T、第6字母 P→N 做 opacity 過渡 |
| 70% – 100% | CONTENT 定格，下方淡入小字「從策略到執行」 |
| > 100% | sticky 解除，自然滾入下一段（Services） |

- 小字：13px，letter-spacing 0.2em，置中，淡入時間 0.6s
- 計算方式：`scrollY` 相對於 Hero 容器的比例，純 JS 計算 + CSS 變數驅動 opacity

**Services Section**
- 三個服務分別佔一行，極大字級（H1 等級）
- 服務名稱本身就是連結，hover 時藍色強調
- 排版：左對齊或置中皆可，每個服務之間有大量留白
- 三行：
  - 品牌專案 → `/brand/`
  - 短影音 → `/shortform/`
  - 影像製作 → `/video/`
- 旁邊或下方可加極小英文說明（Inter，淡灰）

**Name Section（Landing Page 最底部）**
- 純名字「**林晉維**」
- Display 字級（GenSeki Gothic Heavy，120px Desktop / 56px Mobile）
- 置中
- 上下大量留白（`padding: 30vh 0`）
- 不加副標、不加任何裝飾

**Contact Section**
- 置中排版
- 大字 Email（H2 字級，可點擊）
- 次行：Instagram 連結
- 底部版權

---

### 5.2 品牌專案列表頁（brand/index.html）

**版型：**
- 頁面標題（H1）「品牌專案」
- 文章卡片網格：2 欄（Desktop）/ 1 欄（Mobile）
- 每張卡片：封面圖（4:3）/ 專案名（H3）/ 一行 tagline
- 點擊 → 進入該專案文章頁（淡入淡出）

### 5.3 品牌專案文章頁（brand/[slug]/index.html）

**版型：**
- Nav（同主站）
- 返回連結「← 品牌專案」
- 標題（H1）
- Meta：客戶名、年份、角色（淡色標籤）
- **輪播圖區域**：滿版寬，比例 16:9，左右箭頭 + 圓點導航
- **段落文字**：max-width 65ch，置中，Sarasa TC，行高 1.85
- 多段文字之間可插入單張圖（不在輪播內）
- 結尾：下一個專案連結

**輪播設定：**
- 純 CSS scroll-snap（不依賴 JS 套件）
- 鍵盤左右鍵可切換
- 觸控滑動支援
- 建議圖片數：**3–6 張**（最少 1 張，最多 8 張）
- 圖片比例：16:9 為主，可混合 4:3 / 1:1
- 若僅 1 張圖：不顯示左右箭頭 / 圓點導航

### 5.4 短影音 / 影像製作 列表頁

**版型：**
- 頁面標題（H1）
- **標籤列**（sticky，頂部）：所有類別 + 「全部」
- **作品網格**：3 欄（Desktop）/ 2 欄（Tablet）/ 1 欄（Mobile）
- 每個 item：縮圖（9:16 短影音 / 16:9 影像）/ 客戶名 / 類別標籤
- 點擊 item：開啟 lightbox 或跳到外部連結（Cloudflare Stream / IG）

**篩選機制：**
- 標籤列：**sticky** 固定於 nav 下方（`position: sticky; top: 64px`）
- 純 CSS / 輕量 JS（`data-category` + `display: none`）
- 預設：顯示「全部」
- 點擊互動：
  1. 網格淡出（opacity 0，0.2s）
  2. 切換 `data-active-category`，篩選 items
  3. 網格淡入 + 微微上移（0.3s）
- Active 標籤：底線 + 文字加粗

---

## 六、動態與互動規格

### 6.1 頁面切換（淡入淡出）
```css
/* 所有頁面初始透明 */
body { opacity: 0; transition: opacity 0.3s ease; }

/* JS 在 DOMContentLoaded 後加上 is-visible */
body.is-visible { opacity: 1; }
```
離開頁面時先 fade out，再跳轉。

### 6.2 Scroll Reveal
- 元素預設：`opacity: 0; transform: translateY(24px)`
- 進入 viewport 後：`opacity: 1; transform: translateY(0)`
- 過渡：`0.6s ease`
- 使用 `IntersectionObserver`，threshold `0.15`

### 6.3 Hover 效果
- 卡片：`transform: translateY(-4px)` + `box-shadow` 加深（0.25s）
- 連結文字：底線從左展開（`::after` pseudo-element）
- 按鈕：背景色稍深（0.2s）

### 6.4 漢堡選單（Mobile）
- 點擊後從右側滑入（`transform: translateX`）
- 背景半透明遮罩
- 選單項目逐一延遲淡入（stagger 0.05s）

---

## 七、響應式設計策略

| 斷點 | 寬度 | 說明 |
|---|---|---|
| Mobile | < 768px | 單欄，漢堡選單，字型縮小 |
| Tablet | 768px–1279px | 部分雙欄，橫向 Nav |
| Desktop | ≥ 1280px | 完整 12 欄格線，全版型 |

**Mobile 關鍵調整：**
- Hero：照片移至文字下方，或縮為圓形頭像
- Works 卡片：改為單欄
- Nav：漢堡選單，全螢幕 overlay

---

## 八、字型授權備註

| 字型 | 授權狀態 | 處理方式 |
|---|---|---|
| GenSeki Gothic（源石黑體） | 商業字型，需確認授權 | 確認是否持有授權；若無，備選 Noto Sans TC Black |
| Sarasa TC | 開源（SIL OFL） | 可自由使用，自托管 |
| Inter | 開源（SIL OFL） | Google Fonts CDN |

> ⚠️ 正式上線前請確認 GenSeki Gothic 的網路使用授權。

---

## 九、執行順序

| 階段 | 工作項目 |
|---|---|
| Phase 1 | 建立 tokens.css、base.css、layout.css |
| Phase 2 | 製作 Nav 元件 + 漢堡選單 |
| Phase 3 | Landing Page — Hero |
| Phase 4 | Landing Page — Works / Services / Contact |
| Phase 5 | 動畫系統（scroll reveal + 頁面切換） |
| Phase 6 | 三個獨立作品頁 |
| Phase 7 | 響應式調整（Mobile + Tablet） |
| Phase 8 | 圖片替換、內容填入、測試 |

---

## 十、確認事項

### 已定稿
- [x] 字型：源石黑體 Heavy（標題）/ Sarasa TC（中文內文）/ Inter（英文，letter-spacing -0.05em）
- [x] 字型載入：jsDelivr CDN
- [x] 主色：#F7F6F3 底 / #111111 文字 / #2273BA 強調（極少使用）
- [x] Hero：CONCEPT → CONTENT 滾動動畫 + 從策略到執行
- [x] Email：hi@weiimg.com
- [x] Instagram：@wei_img（https://instagram.com/wei_img）
- [x] 部署：GitHub Pages + Cloudflare DNS
- [x] 影片：Cloudflare Stream

### 待提供素材
- [ ] 個人照（如需要在某處使用）
- [ ] 各品牌專案的輪播圖
- [ ] 短影音 / 影像製作的縮圖
- [ ] Cloudflare Stream 影片 ID

### 案例分配確認

**品牌專案文章（brand/）**
- 媒拾捌（視覺識別）
- 酌穀餐酒館（餐酒館識別）
- 樂飛潮玩（品牌形象重塑）
- 草嶺石壁櫻花季（活動主視覺）
- 阿給的 Gap Year（社群圖文）

**短影音（shortform/）依產業類別**
- 餐飲：福芳臺菜
- 電子工業：詠豐電子
- 房產：住商不動產 新生盛邦
- 重機：凱旋重車台中
- 潮玩零售：樂飛潮玩

**影像製作（video/）依類型**
- 音樂 MV：在夢裡 Dreaming
- 競賽短片：雲0線、所以我們創造標籤、節日歸途、掌聲不老
- 實驗短片：躁 No-ise
- 廣告：積目交友、雲湖之願
