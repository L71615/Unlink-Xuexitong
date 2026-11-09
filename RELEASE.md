# 版本与发布规范

本文件是**每次改完代码后的固定动作清单**。只要动了项目里的东西，就按这里走一遍。

---

## 一、版本号规则

格式：`主版本.功能版本.修复版本`（`version.py:10` 的 `APP_VERSION` 是**唯一来源**，界面标题、`task/tool/version_info`、exe 属性、Release 标签全部跟着它走）。

| 位 | 含义 | 什么时候 +1 | 例子 |
|---|---|---|---|
| 第一位 `X` | 重大更新 | 架构大改、不兼容变更、整块重写 | `1.0.0` → `2.0.0` |
| 第二位 `Y` | 新功能 | 新增用户能感知的能力（如多账号切换） | `1.1.4` → `1.2.0` |
| 第三位 `Z` | Bug 修复 | 修一个错、补一处兼容，**每修一次就 +1，不跳号** | `1.1.4` → `1.1.5` → `1.1.6` |

规则细节：

1. **修 bug 只动第三位**：可以一路加到 `1.1.13` 这种，数字大不丢人，说明修得细。
2. **加功能时第三位清零**：`1.1.13` 出了新功能 → `1.2.0`。
3. **重大更新时后两位清零**：`1.2.13` 大改 → `2.0.0`。
4. 一次提交里既有修复又有功能 → 按**功能**算，进第二位。
5. 纯文档/注释改动（README、本文件）**不发版**，版本号不动。

> 当前：`1.2.0` = 主版本 1 / 功能版本 2 / 修复版本 0。
> 下一个 bug 修复是 `1.2.1`；下一个新功能是 `1.3.0`。

---

## 二、每次修改后的固定动作

按顺序做，**一步都不能省**（顺序错了会踩 `WinError 5` 或打出带 `dist\` 前缀的 zip）。

### 1. 改代码 + 跑测试

```powershell
cd D:\Xuexitong_shuake
$env:PYTHONIOENCODING='utf-8'
python -m pytest -q          # 必须全绿，当前基线 114 passed
```

### 2. 改版本号

- `version.py:10` → `APP_VERSION = "x.y.z"`
- `README.md:13` 下载名 → `CourseHelper-x.y.z-win64.zip`
- **更新日志不写进 README / 本文件**：具体改动写在 Release 的说明里（见第 7 步），README 与本文只留 Releases 链接

### 3. 打包前先关掉旧进程

```powershell
$p = Get-Process 课业助手 -ErrorAction SilentlyContinue
if ($p) { $p.CloseMainWindow() | Out-Null; Start-Sleep 3 }
if (Get-Process 课业助手 -ErrorAction SilentlyContinue) { Stop-Process -Name 课业助手 -Force }
```

**不关就会报** `PermissionError: [WinError 5] 拒绝访问 ... _internal\*.pyd`。

### 4. 重新打包

```powershell
python build_exe.py
```

校验产物（三项都要对）：

```powershell
(Get-Item 'dist\课业助手\课业助手.exe').VersionInfo.FileVersion   # 等于新版本号
Get-Content 'dist\课业助手\_internal\task\tool\version_info'       # 等于新版本号
```

### 5. 生成安装包 zip

```powershell
$zip = "D:\Xuexitong_shuake\CourseHelper-$((Get-Item 'dist\课业助手\课业助手.exe').VersionInfo.FileVersion)-win64.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    'D:\Xuexitong_shuake\dist', $zip,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false)    # 必须是 $false：$true 会多套一层 dist\
```

校验根目录必须是 `课业助手\课业助手.exe`（2197 个条目 / 约 86.3 MB）。

### 6. 提交并推送

```powershell
git add -A
git commit -m "fix|feat: 一句话说明 (x.y.z)"
$t = (gh auth token).Trim()
git -c credential.helper= push "https://x-access-token:$t@github.com/L71615/Unlink-Xuexitong.git" main
git ls-remote origin refs/heads/main    # 确认远端 head 是刚提交的 commit
```

> 本机 `http.sslBackend` 已设为 `openssl`（schannel 在此环境会 `SEC_E_NO_CREDENTIALS`）。
> 不要用 `gh auth setup-git`（写 `~/.gitconfig` 会被拒），就用上面这条带 token 的 push。

### 7. 发 Release（打标签 + 传安装包）

```powershell
# 先用 UTF-8 写 notes 文件，避免中文在 PowerShell 5.1 里被写成乱码
gh release create vx.y.z "CourseHelper-x.y.z-win64.zip" --title "vx.y.z" --notes-file .release_notes.md
Remove-Item .release_notes.md -Force
```

校验上传结果：

```powershell
gh api repos/L71615/Unlink-Xuexitong/releases/tags/vx.y.z | ConvertFrom-Json |
    Select-Object tag_name, draft, @{n='asset';e={$_.assets[0].name}},
                  @{n='MB';e={[math]::Round($_.assets[0].size/1MB,1)}},
                  @{n='state';e={$_.assets[0].state}}
```

`draft=False`、`state=uploaded`、体积与本地 zip 一致，才算发完。

---

## 三、纯文档改动怎么办

只改了 `README.md` / `RELEASE.md` / `Help.txt` 这类文字：

1. 不动版本号
2. 不重新打包、不发 Release
3. 仍然 `git add` + `commit` + `push`（保持 GitHub 上是最新的）

---

## 四、已知的坑（踩过一次就别再踩）

| 坑 | 现象 | 正确做法 |
|---|---|---|
| 边跑边打包 | `WinError 5 拒绝访问 _internal\*.pyd` | 先关进程再 `build_exe.py` |
| zip 参数 | 包内多一层 `dist\` | `CreateFromDirectory(..., $false)` |
| PowerShell 5.1 编码 | 中文变 `鎵撳紑` | 不用 `Get-Content -Raw \| Set-Content`；改中文文件用编辑工具，写 notes 用 `-Encoding utf8` |
| schannel | `SEC_E_NO_CREDENTIALS` | `git config --local http.sslBackend openssl` |
| `gh auth setup-git` | 写 `~/.gitconfig` 被拒 | 用带 token 的 push 命令 |
| `git pull --rebase` | `unable to unlink old 'task/quiz_ai.py': Invalid argument` | 用 `git merge --no-edit origin/main` |
| 打包用了旧资源 | 包内 `Help.txt` 还是老的 | `build_exe.py` 的 `stage_assets()` 会从 `task/tool/` 重新复制，确认改的是源文件 |

---

## 五、版本历史

版本历史与每个版本的具体改动**只写在 GitHub Releases**（每个 tag 的说明就是该版更新日志），本文件不再重复：

- 全部版本：https://github.com/L71615/Unlink-Xuexitong/releases
- 最新版本：https://github.com/L71615/Unlink-Xuexitong/releases/latest

发版时把更新内容写进 Release 说明即可，不要回填到这里。
