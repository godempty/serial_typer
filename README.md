# serial-typer

`serial-typer` 會把文字檔內容用指定速度「打字」到目前選定的 Windows 視窗。主要用途是把 switch/router 設定指令送到 Xshell 的 serial console，避免手動貼上時被設備吞字、輸入太快、或遇到互動式指令時來不及等待。

這個工具不是透過 SSH 或 serial API 傳送資料，而是模擬鍵盤輸入。因此它能用在 Xshell、PuTTY、SecureCRT 或其他只能接鍵盤輸入的 console 視窗。

## 功能

- 讀取文字檔並逐行輸入
- 預設以 `60 WPM` 速度打字
- 每行輸入完自動按 Enter
- 支援 `DELAY x` 控制行，讓流程暫停 `x` 秒
- 可列出目前視窗並選擇目標視窗
- 可使用倒數時間手動切到目標視窗
- 支援 dry-run，先確認檔案會被怎麼送出
- 支援 `#` 開頭註解

## 安裝

需要先安裝 `uv`。

```powershell
uv sync
```

## 快速使用

先建立一個指令檔，例如 `commands.txt`：

```text
enable
configure terminal
hostname SW1
DELAY 1
ip domain-name lab.local
crypto key generate rsa
DELAY 5
ip ssh version 2
end
write memory
```

先檢查會送出的內容：

```powershell
uv run serial-typer commands.txt --dry-run
```

選擇 Xshell 視窗後送出：

```powershell
uv run serial-typer commands.txt --choose-window
```

或不用選視窗，給自己 5 秒切到 Xshell：

```powershell
uv run serial-typer commands.txt --focus-delay 5
```

調整速度：

```powershell
uv run serial-typer commands.txt --wpm 80 --choose-window
```

## 指令檔格式

一般行會照原文字輸入，然後按 Enter。

```text
configure terminal
interface vlan 1
ip address 192.168.1.2 255.255.255.0
no shutdown
```

空白行會送出一次 Enter。

以 `#` 開頭的行預設是註解，不會送出：

```text
# This line is ignored.
show running-config
```

如果真的需要送出 `#` 開頭的內容，使用：

```powershell
uv run serial-typer commands.txt --no-comments
```

## DELAY

`DELAY x` 會暫停 `x` 秒，不會送到 console。

```text
crypto key generate rsa
DELAY 5
ip ssh version 2
```

常見需要加 `DELAY` 的地方：

- `crypto key generate rsa`
- `write memory`
- `reload`
- 第一次進入 enable/config mode
- 會要求確認、產生 key、寫入 flash、或設備明顯需要時間處理的指令

`DELAY` 可用小數：

```text
DELAY 0.5
DELAY 2
DELAY 10
```

## 建議流程

1. 先在文字檔內整理指令。
2. 對會花時間的指令後面加 `DELAY`。
3. 執行 `--dry-run` 檢查 `DELAY` 和註解有沒有被正確解析。
4. 先用一小段不危險的指令測試，例如 `show clock`、`show version`。
5. 確認 console 沒有吞字後，再送完整設定。
6. 第一次對新設備或低速 serial console 使用時，先用 `--wpm 40` 或 `--wpm 50`。

## 速度建議

預設 `60 WPM` 大約是每個字元間隔 `0.2` 秒。對多數 serial console 來說偏保守，但比較不容易吞字。

建議值：

- 穩定的本機 console：`--wpm 80`
- 一般 USB-to-serial：`--wpm 60`
- 老設備、console 反應慢、或常吞字：`--wpm 40`
- 指令很多但設備穩定：先用 `--wpm 80` 測一小段，再慢慢提高

如果設備有漏字、指令被切斷、或 prompt 還沒回來下一行就送出，請降低 `--wpm` 或增加 `DELAY`。

## 參數

```text
serial-typer FILE [options]
```

常用參數：

- `--choose-window`: 列出視窗並選擇目標視窗
- `--focus-delay N`: 開始前等待 `N` 秒，預設 `3`
- `--wpm N`: 打字速度，預設 `60`
- `--enter-delay N`: 每行 Enter 後額外等待 `N` 秒，預設 `0.05`
- `--dry-run`: 只顯示動作，不實際輸入
- `--no-comments`: 不把 `#` 開頭行當註解

## 中止

執行時可以用以下方式停止：

- 在終端機按 `Ctrl+C`
- 把滑鼠移到螢幕左上角，觸發 `pyautogui` failsafe

送設定前建議先確認 Xshell 視窗確實是目標設備。這個工具只會模擬鍵盤，所以如果焦點在錯的視窗，內容就會打到錯的地方。

## 實務注意事項

不要把需要人工判斷的互動式流程完全自動化，例如：

```text
erase startup-config
reload
```

這類流程通常會要求確認，建議拆成多個檔案執行，或在確認點前加長 `DELAY`，保留人工介入空間。

如果設備 prompt 很慢才回來，不代表打字速度太快，也可能是每行 Enter 後等待太短。這時可以先調高：

```powershell
uv run serial-typer commands.txt --enter-delay 0.3 --wpm 60
```

如果是單行內字元漏掉，通常是 `--wpm` 太高。

## 可精進方向

目前版本刻意保持簡單，避免和 terminal emulator 或設備協定綁太深。後續可以依使用情境加入：

- `WAIT_PROMPT pattern`: 等畫面出現指定 prompt 後再繼續。這需要能讀取 terminal 內容，目前鍵盤模擬做不到。
- `CONFIRM text`: 送出確認字串，例如互動式問題需要輸入 `yes`。
- `PAUSE`: 停住並等待使用者按 Enter 後繼續。
- `TYPE_ONLY`: 只打字不按 Enter，處理需要停在輸入欄位的情境。
- 每行速度控制，例如 `WPM 40` 暫時降低速度。
- 支援 include，例如把共用設定拆成 `base.txt`、`ssh.txt`、`vlan.txt`。
- 記錄執行 log，包含每一行送出的時間與 delay。
- 加入 `--window-title Xshell`，自動選第一個標題符合的視窗。

如果之後要做得更可靠，最佳方向不是一直加快鍵盤模擬，而是改走可讀寫的通道，例如直接用 serial port library 或 SSH library。鍵盤模擬的優點是最容易接上既有 Xshell 工作流程；缺點是它不知道設備是否真的已經處理完上一行。
