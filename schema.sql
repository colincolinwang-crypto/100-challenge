-- ==============================================================================
-- Wang's Life Questbook (100 Challenge) - Supabase Database Schema
-- 執行方式：進入 Supabase 後台 -> 左側選單「SQL Editor」-> 貼上此腳本 -> 點擊「Run」
-- ==============================================================================

-- 1. 啟用 UUID 擴充功能（若尚未啟用）
create extension if not exists "pgcrypto";

-- 2. 建立分類配置表 (quest_categories)
-- 作用：管理 6 大挑戰（名稱、圖示、目標數量、排序權重、預設標籤）
create table if not exists quest_categories (
  id text primary key,
  title text not null,
  short_title text,
  icon text not null,
  description text,
  color text default 'gold',
  target_count int default 100,
  order_index int default 0,
  preset_tags text[] default '{}',
  created_at timestamptz default now()
);

-- 3. 建立回憶解鎖表 (quest_logs)
-- 作用：存放每一格解鎖的卡片、隨筆心得、相片網址與標籤
create table if not exists quest_logs (
  id uuid primary key default gen_random_uuid(),
  category_id text not null references quest_categories(id) on delete cascade,
  slot_number int not null check (slot_number >= 1 and slot_number <= 100),
  title text not null,
  unlocked_date date not null default current_date,
  notes text check (char_length(notes) <= 250),
  photo_url text,
  tags text[] default '{}',
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  -- 確保同一個分類下的格子編號不重複（例如 soccer 分類只有一個 #001）
  unique(category_id, slot_number)
);

-- 4. 預先填入預設的 6 大挑戰分類
insert into quest_categories (id, title, short_title, icon, description, color, target_count, order_index, preset_tags)
values
  ('soccer', '父子 100 場球', '父子球賽', '⚽', '一起流汗、互相傳球，父子間無話不談的綠茵與籃球時光。', 'emerald', 100, 1, array['足球', '籃球', '傳接球', '夜戰']),
  ('meals', '跟爸爸吃 100 次飯', '跟爸爸吃飯', '🍱', '一碗熱湯、幾句日常，最平凡卻也最珍貴的圍爐對話。', 'gold', 100, 2, array['家常菜', '巷弄老店', '早餐約會', '父親私房']),
  ('dishes', '100 道下酒菜', '百道下酒菜', '🍻', '週末夜晚的小酌微醺，親手烹調的極致下酒風味。', 'gold', 100, 3, array['下酒小點', '炙燒', '居酒屋', '慢燉', '秘製']),
  ('ai', '100 個 AI 應用', 'AI 應用專案', '💻', '探索新科技浪潮，用 AI 動手打造有溫度與解決生活問題的酷專案。', 'emerald', 100, 4, array['Agent', '自動化', '視覺生成', '工作流', '實驗室']),
  ('sketches', '100 幅速寫', '百幅速寫', '🎨', '隨手拾起畫筆，紀錄眼前光影、街景與那一刻的心境感受。', 'gold', 100, 5, array['街頭速寫', '咖啡館', '鋼筆淡彩', '旅行隨筆']),
  ('trails', '100 條步道與遠征', '步道與遠征', '⛰️', '丈量大地的腳步，走向山巔與大海的壯闊冒險（含玉山/日本爬山/單車環島）。', 'emerald', 100, 6, array['玉山', '日本爬山', '單車環島', '台灣百岳', '郊山健行', '遠征探索'])
on conflict (id) do update set
  title = excluded.title,
  icon = excluded.icon,
  description = excluded.description,
  preset_tags = excluded.preset_tags;

-- 5. 建立公開照片儲存空間 (quest-media Storage Bucket)
insert into storage.buckets (id, name, public)
values ('quest-media', 'quest-media', true)
on conflict (id) do nothing;

-- 6. 設定安全性政策 (Row Level Security, RLS)
alter table quest_categories enable row level security;
alter table quest_logs enable row level security;

-- 允許前端讀取分類
create policy "Allow public read quest_categories" 
  on quest_categories for select using (true);

-- 允許前端讀取、新增、修改與刪除卡片
create policy "Allow public read quest_logs" 
  on quest_logs for select using (true);

create policy "Allow public insert quest_logs" 
  on quest_logs for insert with check (true);

create policy "Allow public update quest_logs" 
  on quest_logs for update using (true);

create policy "Allow public delete quest_logs" 
  on quest_logs for delete using (true);

-- 允許相片上傳與讀取 (Storage Object Policies)
create policy "Allow public view quest-media" 
  on storage.objects for select using (bucket_id = 'quest-media');

create policy "Allow public upload quest-media" 
  on storage.objects for insert with check (bucket_id = 'quest-media');

create policy "Allow public update quest-media" 
  on storage.objects for update using (bucket_id = 'quest-media');

create policy "Allow public delete quest-media" 
  on storage.objects for delete using (bucket_id = 'quest-media');
