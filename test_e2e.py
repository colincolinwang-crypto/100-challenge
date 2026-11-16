import asyncio
import json
import subprocess
import time
import urllib.request
import websockets
import os
import http.server
import threading

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222
LOCAL_PORT = 8089
PROJECT_DIR = "/Users/wangjianxiang/Documents/Colin Data/Project/100-challenge"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_local_server():
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=PROJECT_DIR, **kwargs)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port

async def run_cdp_test():
    server, local_port = start_local_server()
    target_url = f"http://127.0.0.1:{local_port}/index.html"
    print(f"🚀 本地測試伺服器已就緒: {target_url}")

    user_data = "/tmp/chrome_e2e_profile_" + str(int(time.time()))
    print("🚀 啟動獨立真實 Chrome 實例 (模擬全新/無痕模式)...")
    chrome_proc = subprocess.Popen([
        CHROME_BIN,
        "--headless=new",
        "--window-size=1280,900",
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--disable-gpu",
        target_url
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        ws_url = None
        for _ in range(20):
            time.sleep(0.5)
            try:
                resp = urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=1)
                data = json.loads(resp.read().decode())
                if data and len(data) > 0 and 'webSocketDebuggerUrl' in data[0]:
                    ws_url = data[0]['webSocketDebuggerUrl']
                    break
            except Exception:
                pass

        if not ws_url:
            raise RuntimeError("無法連線至 Chrome CDP")

        print(f"🔗 已成功連線 Chrome CDP: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            msg_id = 0

            async def send_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    res = json.loads(raw)
                    if res.get("id") == msg_id:
                        return res.get("result", {})

            async def eval_js(expr):
                res = await send_cmd("Runtime.evaluate", {
                    "expression": expr,
                    "returnByValue": True,
                    "awaitPromise": True
                })
                return res.get("result", {}).get("value")

            await send_cmd("Page.enable")
            await send_cmd("Page.navigate", {"url": target_url})
            await asyncio.sleep(2)

            # ----------------------------------------------------
            # 測試 0-A: 驗證無痕/陌生人預設為「訪客模式」，後門按鈕已徹底移除
            # ----------------------------------------------------
            print("\n🛡️ [測試 0-A] 驗證全新無痕模式下的訪客模式保護...")
            is_owner = await eval_js("isOwner")
            print(f"  目前管理員身分狀態 isOwner: {is_owner} (必須為 False)")
            assert is_owner is False, "❌ 失敗: 全新開啟時預設不應具備管理員身分"

            fab_hidden = await eval_js("document.getElementById('fab-container').classList.contains('hidden')")
            print(f"  懸浮解鎖按鈕 (FAB) 是否隱藏: {fab_hidden} (必須為 True)")
            assert fab_hidden is True, "❌ 失敗: 訪客模式下不應顯示解鎖按鈕"

            has_backdoor = await eval_js("typeof loginOwnerDirect !== 'undefined'")
            print(f"  是否仍殘留 loginOwnerDirect 後門函式: {has_backdoor} (必須為 False)")
            assert has_backdoor is False, "❌ 失敗: loginOwnerDirect 後門函式未徹底移除"
            print("  ✅ 通過: 無痕訪客模式安全防護正常，無任何未授權跳過管道！")

            # ----------------------------------------------------
            # 測試 0-B: 驗證未授權 Google 帳號嘗試登入會被嚴格阻擋
            # ----------------------------------------------------
            print("\n⛔ [測試 0-B] 測試非站長 Google 帳號登入攔截...")
            await eval_js("openAuthModal()")
            await eval_js("document.getElementById('gmail-login-input').value = 'stranger@gmail.com'")
            await eval_js("document.getElementById('admin-key-input').value = '123456'")
            await eval_js("document.querySelector('#auth-logged-out-view form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))")
            await asyncio.sleep(0.5)

            is_owner_after_fake = await eval_js("isOwner")
            print(f"  非授權帳號送出後 isOwner 狀態: {is_owner_after_fake} (必須仍為 False)")
            assert is_owner_after_fake is False, "❌ 失敗: 非授權帳號被放行"

            # 測試站長帳號但輸入錯誤金鑰
            print("  測試輸入站長信箱但搭配錯誤金鑰...")
            await eval_js("document.getElementById('gmail-login-input').value = 'colincolinwang@gmail.com'")
            await eval_js("document.getElementById('admin-key-input').value = 'wrongpassword'")
            await eval_js("document.querySelector('#auth-logged-out-view form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))")
            await asyncio.sleep(0.5)

            is_owner_wrong_key = await eval_js("isOwner")
            print(f"  錯誤金鑰送出後 isOwner 狀態: {is_owner_wrong_key} (必須仍為 False)")
            assert is_owner_wrong_key is False, "❌ 失敗: 錯誤金鑰被放行"
            print("  ✅ 通過: 未授權帳號與錯誤金鑰均被 100% 嚴格阻擋！")

            # ----------------------------------------------------
            # 測試 0-C: 驗證授權之站長 Google 帳號成功登入
            # ----------------------------------------------------
            print("\n👑 [測試 0-C] 測試授權之站長 Google 帳號合法驗證登入...")
            await eval_js("document.getElementById('gmail-login-input').value = 'colincolinwang@gmail.com'")
            await eval_js("document.getElementById('admin-key-input').value = 'colin100'")
            await eval_js("document.querySelector('#auth-logged-out-view form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))")
            await asyncio.sleep(1)

            is_owner_auth = await eval_js("isOwner")
            current_user = await eval_js("currentUserEmail")
            print(f"  驗證成功後 isOwner 狀態: {is_owner_auth}, 當前身分: {current_user}")
            assert is_owner_auth is True, "❌ 失敗: 站長授權登入失敗"

            fab_shown = await eval_js("!document.getElementById('fab-container').classList.contains('hidden')")
            print(f"  管理員解鎖按鈕 (FAB) 是否顯現: {fab_shown} (必須為 True)")
            assert fab_shown is True, "❌ 失敗: 站長登入後未顯現解鎖按鈕"
            print("  ✅ 通過: 授權站長成功啟用管理員身分與完整管理功能！")

            # ----------------------------------------------------
            # 測試 1: 驗證「心得隨筆非必填」（不填心得直接解鎖）
            # ----------------------------------------------------
            print("\n📝 [測試 1] 測試「心得隨筆非必填」...")
            await eval_js("openUnlockModal('soccer', 2, '台北田徑場父子熱血夜戰')")
            notes_required = await eval_js("document.getElementById('form-notes').hasAttribute('required')")
            print(f"  心得欄位是否仍有 required 屬性: {notes_required}")
            assert notes_required is False, "❌ 失敗: form-notes 仍有 required 屬性"

            # 清空心得
            await eval_js("document.getElementById('form-notes').value = ''")
            # 模擬送出表單
            await eval_js("document.getElementById('unlock-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))")
            await asyncio.sleep(1.5)

            # 檢查 #002 是否已成功解鎖
            unlocked_2 = await eval_js("!!questData['soccer'][2]")
            notes_saved = await eval_js("questData['soccer'][2].notes")
            print(f"  #002 解鎖狀態: {unlocked_2}, 儲存心得內容: '{notes_saved}'")
            assert unlocked_2 is True, "❌ 失敗: 空心得未能成功解鎖"
            assert notes_saved == '', f"❌ 失敗: 預期空心得，但收到: {notes_saved}"
            print("  ✅ 通過: 心得隨筆未填寫時，依然能 100% 順暢解鎖！")

            # ----------------------------------------------------
            # 測試 2: 驗證「上傳照片頂多 3 張」
            # ----------------------------------------------------
            print("\n📷 [測試 2] 測試「上傳照片頂多 3 張」限制與管理...")
            await eval_js("openUnlockModal('soccer', 3, '合歡山登頂遠征')")

            img1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
            img2 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            img3 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg=="
            img4 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP4z8DwHwAFAAH/qv6q7wAAAABJRU5ErkJggg=="

            await eval_js(f'uploadedImages.push("{img1}"); renderPhotoPreviews();')
            count_1 = await eval_js("uploadedImages.length")
            print(f"  加入第 1 張照片，目前照片數: {count_1}/3")
            assert count_1 == 1, "❌ 失敗: 照片數不符"

            await eval_js(f'uploadedImages.push("{img2}"); renderPhotoPreviews();')
            count_2 = await eval_js("uploadedImages.length")
            print(f"  加入第 2 張照片，目前照片數: {count_2}/3")
            assert count_2 == 2, "❌ 失敗: 照片數不符"

            await eval_js(f'uploadedImages.push("{img3}"); renderPhotoPreviews();')
            count_3 = await eval_js("uploadedImages.length")
            print(f"  加入第 3 張照片，目前照片數: {count_3}/3")
            assert count_3 == 3, "❌ 失敗: 照片數不符"

            await eval_js(f'document.getElementById("custom-image-url-input").value = "{img4}"; applyCustomImageUrl();')
            count_4 = await eval_js("uploadedImages.length")
            print(f"  嘗試加入第 4 張照片，目前照片數: {count_4}/3 (應嚴格限制在 3)")
            assert count_4 == 3, f"❌ 失敗: 超過 3 張照片限制: {count_4}"
            print("  ✅ 通過: 照片數量被嚴格限制在最多 3 張！")

            # 測試單張移除功能
            await eval_js("removeSinglePhoto(1)")
            count_after_remove = await eval_js("uploadedImages.length")
            print(f"  移除其中 1 張照片後，目前照片數: {count_after_remove}/3")
            assert count_after_remove == 2, "❌ 失敗: 單張移除失敗"

            # 提交解鎖 #003
            await eval_js("document.getElementById('unlock-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))")
            await asyncio.sleep(1.5)

            saved_photos = await eval_js("questData['soccer'][3].photos.length")
            print(f"  #003 儲存照片數量: {saved_photos}")
            assert saved_photos == 2, "❌ 失敗: 儲存的照片陣列長度不符"
            print("  ✅ 通過: 多圖陣列成功儲存至卡片資料庫！")

            # ----------------------------------------------------
            # 測試 3: 驗證卡片詳情多圖輪播切換 (Detail Modal)
            # ----------------------------------------------------
            print("\n🖼️ [測試 3] 測試卡片詳情彈窗多圖輪播切換...")
            await eval_js("openDetailModal('soccer', 3)")
            await asyncio.sleep(0.5)

            nav_prev_visible = await eval_js("!document.getElementById('detail-prev-photo-btn').classList.contains('hidden')")
            nav_next_visible = await eval_js("!document.getElementById('detail-next-photo-btn').classList.contains('hidden')")
            counter_text = await eval_js("document.getElementById('detail-photo-counter-text').innerText")
            print(f"  詳情彈窗輪播控制: 箭頭可見={nav_prev_visible}, 照片計數='{counter_text}'")
            assert nav_prev_visible is True, "❌ 失敗: 多圖未顯示切換箭頭"
            assert counter_text == "1 / 2", f"❌ 失敗: 計數文字不符: {counter_text}"

            await eval_js("changeDetailPhoto(1)")
            counter_after_next = await eval_js("document.getElementById('detail-photo-counter-text').innerText")
            print(f"  切換下一張後計數: '{counter_after_next}'")
            assert counter_after_next == "2 / 2", "❌ 失敗: 切換照片失敗"

            notes_display = await eval_js("document.getElementById('detail-notes').innerText")
            print(f"  未填寫隨筆時的詳情顯示: '{notes_display}'")
            assert "未填寫" in notes_display or "無隨筆" in notes_display, "❌ 失敗: 未正確顯示空心得狀態"
            print("  ✅ 通過: 卡片詳情多圖輪播與空心得排版完美運作！")

            # ----------------------------------------------------
            # 測試 4: 驗證照片顯示不裁切 (object-contain) 與 尺寸顯著放大
            # ----------------------------------------------------
            print("\n🔍 [測試 4] 驗證卡片詳情「照片不裁切 (object-contain)」與「尺寸放大」...")
            
            object_fit = await eval_js("window.getComputedStyle(document.getElementById('detail-photo')).objectFit")
            print(f"  #detail-photo 的 object-fit 渲染屬性: '{object_fit}'")
            assert object_fit == "contain", f"❌ 失敗: 預期 object-fit 為 contain，但得到: {object_fit}"

            container_height = await eval_js("document.getElementById('detail-photo').parentElement.getBoundingClientRect().height")
            container_width = await eval_js("document.getElementById('detail-photo').parentElement.getBoundingClientRect().width")
            modal_width = await eval_js("document.getElementById('detail-modal').querySelector('.modal-enter').getBoundingClientRect().width")
            print(f"  圖片容器實際高度: {container_height:.1f}px (舊版本只有 256~288px)")
            print(f"  圖片容器實際寬度: {container_width:.1f}px")
            print(f"  詳情彈窗實際寬度: {modal_width:.1f}px (舊版本最大僅 512px)")

            assert container_height >= 310, f"❌ 失敗: 圖片容器高度未放大 (高度: {container_height})"
            assert modal_width >= 600, f"❌ 失敗: 彈窗寬度未放大 (寬度: {modal_width})"
            print("  ✅ 通過: 尺寸已大幅升級放大，且 object-fit: contain 完整保證 100% 比例原圖不被裁切！")

            # 截圖存證
            screenshot_res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            import base64
            img_data = base64.b64decode(screenshot_res.get("data", ""))
            with open("/Users/wangjianxiang/Documents/Colin Data/Project/100-challenge/test_verified.png", "wb") as f:
                f.write(img_data)
            print("📸 截圖已儲存至 test_verified.png！")

            print("\n=======================================================")
            print("🎉 所有測試項目（無痕訪客模式防護、Google帳號身分驗證、最多3張照片、心得非必填、照片放大不裁切）100% 驗證通過！")
            print("=======================================================")

    finally:
        chrome_proc.terminate()
        try:
            server.shutdown()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(run_cdp_test())
