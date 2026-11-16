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
