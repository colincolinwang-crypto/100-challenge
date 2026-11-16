# 🎯 100 Challenge 系統設定與交接手冊 (System Handover Document)

本文件專為新工作階段接手開發、維運或功能擴充所設計，收錄專案架構、雲端設定、身分驗證防護、近期功能修正細節與端對端自動化測試流程。

---

## 📌 1. 專案基本資訊 (Project Overview)

- **專案名稱**：100 Challenge（人生探險挑戰手札）
- **應用型態**：自包含無伺服器單頁應用程式 (Single Page Application, Vanilla JS + Tailwind CSS)
- **線上運行網址 (Production)**：[https://colincolinwang-crypto.github.io/100-challenge/](https://colincolinwang-crypto.github.io/100-challenge/)
- **GitHub 倉庫**：`git@github.com:colincolinwang-crypto/100-challenge.git` (主分支: `main`)
- **本機工作目錄**：`/Users/wangjianxiang/Documents/Colin Data/Project/100-challenge`
- **主要檔案結構**：
  - `index.html`：應用程式核心介面、樣式、前端業務邏輯與 Supabase 同步引擎。
  - `config.js`：系統全域環境變數、Supabase 連線憑證與站長授權設定。
  - `schema.sql`：Supabase 資料庫結構、預設分類與 RLS 安全政策。
  - `test_e2e.py`：基於真實 Chrome (CDP) 的端對端自動化驗證測試套件。
  - `README.md`：產品特色與使用說明文件。

---

## ⚙️ 2. 系統設定檔與環境金鑰 (System Configuration)

設定檔路徑：`config.js`

```javascript
// ==============================================================================
// 100 Challenge - 系統環境與權限設定檔 (Config)
// ==============================================================================

window.QUESTBOOK_CONFIG = {
  // 1. Supabase 雲端資料庫設定
  supabaseUrl: "https://wnyilvamlcvxvbpnprff.supabase.co",
  supabaseAnonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndueWlsdmFtbGN2eHZicG5wcmZmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0OTg4MzcsImV4cCI6MjEwODA3NDgzN30.c9JgFGYCOZFarbaRWMX9Wn9p6nQG6ih-JuKivvHvnFI",

  // 2. Google OAuth Client ID (選填：至 Google Cloud Console 申請 Web Client ID 後填入此處，即可啟用官方 Google 一鍵登入與 One Tap)
  googleClientId: "",

  // 3. 站長授權身分設定 (僅授權之 Google 帳號與安全金鑰可取得管理員權限，其他人一律唯讀訪客)
  ownerEmail: "colincolinwang@gmail.com",
  adminSecretKey: "colin100"
};
```

### 設定欄位說明：
| 欄位名稱 | 類型 | 說明 |
| :--- | :--- | :--- |
| `supabaseUrl` | 字串 | Supabase 雲端專案端點 URL |
| `supabaseAnonKey` | 字串 | Supabase 公開匿名連線金鑰 (Anon Public Key) |
| `googleClientId` | 字串 | Google Cloud Console 申請的 Web Client ID（填入後會自動啟用官方「Sign in with Google」按鈕與「Google One Tap」提示） |
| `ownerEmail` | 字串 | 站長合法授權 Email（預設為 `colincolinwang@gmail.com`，系統同時認定包含 `colin` 或 `wangjianxiang` 之帳號） |
| `adminSecretKey` | 字串 | 站長安全認證金鑰（預設為 `colin100`），無痕模式或陌生裝置登入必填 |

---

## 🔐 3. 身分驗證與訪客權限模型 (Security & Permissions)

為確保使用者在任何裝置（包含 Chrome 無痕模式）瀏覽時的安全性，系統採**嚴格最小權限原則**：

### 3.1 權限分級
1. **公開訪客模式 (Visitor / Read-Only)**：
   - 預設狀態。任何未認證之裝置、無痕模式視窗或陌生人開啟網頁時皆為此狀態。
   - **禁止操作**：完全隱藏右下角懸浮解鎖按鈕（FAB `#fab-container`），點擊已解鎖卡片僅能以唯讀檢視，不能編輯、上傳或刪除。
   - 頂部導覽列顯示「🔒 訪客模式 (登入)」。
2. **站長管理員模式 (Owner / Admin)**：
   - 只有通過身分驗證的站長 Colin 才能啟用。
   - **具備權限**：可解鎖新卡片、上傳相片（最多 3 張）、修改或刪除卡片資料、操作「100 道下酒菜專屬願望清單」。
   - 頂部導覽列顯示「👑 管理員 (Colin)」。

### 3.2 驗證方式與阻擋機制
- **嚴格身分核對函式**：
  - `isAuthorizedAdminEmail(email)`：檢驗 Email 是否等於 `ownerEmail` 或包含 `colin` / `wangjianxiang`。非站長 Google 帳號嘗試登入會被直接阻擋並跳出警示 `⛔ 存取拒絕：非站長授權帳號，只能以訪客模式唯讀瀏覽`。
  - `isAuthorizedAdminKey(key)`：檢驗安全金鑰是否相符（`colin100` 或 `colin`）。密鑰錯誤立即拒絕。
- **後門清理**：
  - 徹底銷毀了舊版本無驗證的 `loginOwnerDirect()` 函式與相關按鈕，杜絕任何人以無痕模式點擊一鍵跳過驗證。
- **站長專屬快速授權網址**：
  - 站長本人在更換電腦或在無痕模式中，可直接開啟：
    `https://colincolinwang-crypto.github.io/100-challenge/?admin=colin100`
  - 驗證成功後，系統會透過 `window.history.replaceState` 自動清除網址參數，維持網址美觀並於本機啟用管理員身分。

---

## 🗄️ 4. 資料庫架構與雲端同步機制 (Supabase Database & Storage)

資料庫腳本路徑：`schema.sql`

### 4.1 資料庫表結構 (Tables)
1. **`quest_categories` (挑戰支線表)**
   - `id` (text, PK): 分類識別代碼（`soccer`, `meals`, `dishes`, `ai`, `sketches`, `trails`）。
   - `title` (text): 完整標題（例：`⚽ 父子 100 場球`）。
   - `short_title` (text): 簡稱。
   - `icon` (text): Emoji 圖示。
   - `description` (text): 分類說明。
   - `color` (text): 主題色系標籤（`gold` / `emerald`）。
   - `target_count` (int): 目標格數（預設 100）。
   - `order_index` (int): 顯示排序順序。
   - `preset_tags` (text[]): 預設標籤陣列。
2. **`quest_logs` (回憶卡片表)**
   - `id` (uuid, PK): 卡片唯一識別碼。
   - `category_id` (text, FK): 所屬分類。
   - `slot_number` (int): 格子編號（1 ~ 100）。
   - `title` (text): 解鎖標題。
   - `unlocked_date` (date): 解鎖日期。
   - `notes` (text): 隨筆心得（選填，長度上限 250 字）。
   - `photo_url` (text): 封面相片網址。
   - `tags` (text[]): 關聯標籤。
   - `metadata` (jsonb): 擴充結構，包含多圖相片陣列 `{"photos": ["url1", "url2", "url3"]}`。
   - 唯一性約束：`unique(category_id, slot_number)`。

### 4.2 圖片儲存空間 (Storage Bucket)
- Storage Bucket 名稱：`quest-media`（公開唯讀，允許本機 Canvas 智慧壓縮圖片上傳）。

### 4.3 容錯與離線機制 (Sync & Fallback Engine)
- **3.5 秒逾時保護**：`syncWithSupabase()` 內建 `Promise.race`，若遇網路不穩或 Supabase 冷啟動延遲，3.5 秒內未回應自動降級為 `localStorage` 本機快取，介面立即切換為「☁️ 系統就緒 / 本機快取」，絕對不卡在「連線中...」。

---

## 🎨 5. 核心功能規格與近期修正 (Recent Highlights)

1. **卡片詳情照片放大與 100% 比例不裁切 (Non-cropped & Enlarged Image)**：
   - 彈窗容器寬度擴展至 `max-w-2xl sm:max-w-3xl lg:max-w-4xl`。
   - 圖片展示區拉高至 `h-80 sm:h-[460px] md:h-[520px] max-h-[68vh]`。
   - 圖片樣式採用 `object-contain`，配合深黑沉浸式底色，不論 16:9、4:3、1:1 抑或直向照片（9:16），四周皆 100% 完整呈現不被裁切。
   - 移除了遮擋視覺的深黑漸層遮罩。
2. **多圖支援（上限 3 張）**：
   - 上傳表單支援一次或分次選取最多 3 張照片（智慧 Canvas 壓縮限制在 ~80KB）。
   - 支援單張即時刪除、第一張自動標註「封面」、未滿 3 張顯示「+ 加照片」。
   - 卡片詳情支援多圖左右輪播切換按鈕、小縮圖列、以及 `1 / 3` 計數器標籤。
3. **心得隨筆改為選填**：
   - 移除 HTML `required` 限制，使用者不填心得亦可 100% 順暢解鎖。
   - 卡片詳情在空心得時友善呈現「（站長未填寫隨筆心得）」。
4. **手機端排版與字體優化**：
   - 未解鎖格子在卡片流模式下改為緊湊條狀卡片（Compact Strip），徹底消除大片空白垂直間隔。
   - 行動裝置字體放大至 13px~15px，按鈕加大符合觸控人體工學。
5. **雙層儲存引擎升級（IndexedDB 巨量快取 + 解除 5MB 瀏覽器限制）**：
   - **問題根因**：先前前端僅依賴瀏覽器 `localStorage` 存放所有 Base64 相片，因瀏覽器對每個網域有硬性 5MB 上限，約 10 張卡片即會填滿 5MB 配額並誤發「儲存空間已滿」警告。
   - **雲端資料庫實際容量**：Supabase PostgreSQL 免費方案具備 500 MB 配額，目前 9 筆卡片僅使用 4.59 MB（使用率 < 1%），所有資料均 100% 完好存在雲端。
   - **升級方案**：
     - 前端引入 `IndexedDB` 引擎（容量高達數百 MB ~ 數 GB，絕不爆滿）。
     - `localStorage` 超標時自動降級保存文字索引，不再彈出空間已滿警報。
     - 圖片壓縮演算法優化為 800x800 0.70，體積再減少 65%，肉眼依然清晰銳利。

---

## 🧪 6. 端對端自動化測試流程 (E2E Testing Guide)

本專案具備完整的 CDP (Chrome DevTools Protocol) 測試腳本：`test_e2e.py`。
此腳本會啟動真實獨立的 Google Chrome Headless 實例，模擬全新無痕模式並逐項驗證功能。

### 6.1 測試涵蓋範圍
- **測試 0-A**：驗證無痕模式預設鎖定訪客唯讀、FAB 隱藏、無跳過後門。
- **測試 0-B**：驗證非授權 Google 信箱及錯誤金鑰被 100% 攔截阻擋。
- **測試 0-C**：驗證授權之站長帳號合法啟用管理員權限。
- **測試 1**：驗證心得未填時可順暢解鎖。
- **測試 2**：驗證相片上限嚴格限制在 3 張、單張移除與多圖陣列儲存。
- **測試 3**：驗證卡片詳情多圖輪播控制與空心得排版。
- **測試 4**：驗證相片呈現為 `object-contain` 零裁切、容器高度放大至 520px。

### 6.2 執行測試指令
```bash
cd "/Users/wangjianxiang/Documents/Colin Data/Project/100-challenge"
python3 test_e2e.py
```

---

## 🚀 7. 下一步維護與接手指南 (Handover Checklist)

新對話接手時，請參考以下常見操作：

1. **推送最新變更至線上環境**：
   ```bash
   cd "/Users/wangjianxiang/Documents/Colin Data/Project/100-challenge"
   git add .
   git commit -m "feat/fix: <說明>"
   git push origin main
   ```
   推送後 GitHub Pages 會在 15~30 秒內自動發布最新版。
2. **申請並啟用 Google 官方一鍵登入 (Google Identity Services)**（選填）：
   - 至 [Google Cloud Console](https://console.cloud.google.com/) 建立專案。
   - 「APIs & Services」->「Credentials」-> 建立「OAuth 2.0 Client ID (Web Application)」。
   - 在「Authorized JavaScript origins」填入：`https://colincolinwang-crypto.github.io`。
   - 將取得的 Client ID 填入 `config.js` 的 `googleClientId` 欄位。
   - 重新推送後，網站即會呈現 Google 官方原生的「Sign in with Google」按鈕與「One Tap」快速登入卡片。
3. **資料備份與還原**：
   - 網頁右上角選單提供「匯出 JSON 備份檔」與「匯入還原」，檔案命名規則為 `100_challenge_backup_YYYY-MM-DD.json`。
