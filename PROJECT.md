# AutoPage PDF — Project Record

> 本文件是 AutoPage PDF 的開發狀態及交接紀錄。新的 AI Agent 或協作者在修改程式前，應先閱讀 `README.md`、本文件及相關原始碼。

## Status

**Maintenance**

目前穩定版本已完成 v1.3.1，重點是維持跨平台穩定性、整理發佈流程及準備下一輪功能開發。

## Source of Truth

- Canonical repository: https://github.com/wongsir1011/autopage-pdf
- Stable source branch: `main`
- Rule: `main` 只代表已測試及可部署的穩定原始碼
- Latest verified stable commit: `cff0fd0472fb4632a3c8fa3f3230782e76ba6925`
- Latest verified date: 2026-09-29
- Latest release: [v1.3.1](https://github.com/wongsir1011/autopage-pdf/releases/tag/v1.3.1), tag at `daaff5ed00102fd7cfced613091a2ef4c7735020`

## Current Version

**v1.3.1**

Version baseline:

- v1.3.0：加入本機 Tesseract OCR、可搜尋 PDF、TXT 匯出及辨識增強
- v1.3.1：修正 Windows 智慧末頁在第二頁誤停

## Production and Distribution

- Primary production site: https://autopage-pdf-seven.vercel.app/
- Secondary site: https://wongsir1011.github.io/autopage-pdf/
- Production branch: `main`
- Latest verified Vercel status on `main`: success
- GitHub Pages deployment on latest `main`: success
- Current release assets: [Windows v1.3.1 ZIP](https://github.com/wongsir1011/autopage-pdf/releases/download/v1.3.1/AutoPage_PDF_Windows_v1.3.1.zip) and [macOS v1.3.1 ZIP](https://github.com/wongsir1011/autopage-pdf/releases/download/v1.3.1/AutoPage_PDF_Mac_v1.3.1.zip)
- Repository copies: `downloads/AutoPage_PDF_Windows_v1.3.1.zip` and `downloads/AutoPage_PDF_Mac_v1.3.1.zip`

### Release note

GitHub Release [v1.3.1](https://github.com/wongsir1011/autopage-pdf/releases/tag/v1.3.1) was published with the Windows and macOS ZIP packages and their SHA-256 checksums. The release assets match the repository copies. The owner reported Windows and macOS physical-device acceptance passed on 2026-09-29. The website download buttons now point to the release assets.

### Licensing decision

On 2026-09-29, the owner decided to remove the “MIT License” claim from the website. The site footer displays the copyright notice only. The repository has no `LICENSE` file; a future license decision can be recorded separately.

## Current Stack

- Language: Python
- Desktop UI: Tkinter
- Screen automation: PyAutoGUI
- Image processing: Pillow
- PDF generation: img2pdf, ReportLab, pypdf
- OCR: Tesseract via pytesseract
- Tests: Python `unittest`
- CI: GitHub Actions on Python 3.8, 3.11 and 3.14
- Web distribution page: static HTML
- Hosting: Vercel and GitHub Pages

## Current Features

- Windows and macOS cross-platform launcher
- Interactive screenshot-region calibration
- Automatic page turning and emergency stop
- Smart final-page detection with retry protection
- Auto-crop and manual crop
- Single-page and double-page capture
- Left-to-right and right-to-left page order
- Capture preview
- Lossless image PDF output
- Offline OCR for Traditional Chinese, Simplified Chinese and English
- Searchable PDF and optional UTF-8 TXT export
- OCR environment and language-pack checks
- Persistent user settings and completion notification

## Quality Baseline

At the verified stable commit:

- GitHub Actions test workflow: passed
- Python matrix: 3.8, 3.11 and 3.14
- Vercel status: success
- GitHub Pages build and deployment: success
- Open GitHub issues at the verified baseline: 0
- Windows and macOS physical-device acceptance: owner reported passed on 2026-09-29

Any future change should preserve this baseline or explain the exception in the pull request.

## Known Project-Management Gaps

These are maintenance items, not confirmed application bugs:

1. Merged branches `docs/standardize-project-records`, `feature/v1.2.0`, `feature/v1.3.0` and `fix/windows-smart-end-page` remain in the repository.
2. `main` is not currently protected.
3. Vercel and GitHub Pages both publish the site; Vercel is treated as primary and GitHub Pages as secondary until a different decision is recorded.

## Current Work

Complete post-release maintenance and establish AutoPage as the reference workflow for future AI-assisted projects.

## Next Actions

1. Protect `main` and require successful tests before merge.
2. Remove or archive merged branches after confirming they are no longer needed.
3. Record AutoPage in the central Project Registry.
4. Open separate branches for any future feature or bug fix.

## Development Workflow

1. Read `README.md`, `PROJECT.md`, `CHANGELOG.md` and the relevant source files.
2. Create a focused branch such as `fix/...`, `feature/...` or `docs/...`.
3. Make the smallest coherent change.
4. Run compile checks and automated tests.
5. Push the branch and review the deployment preview when web files change.
6. Open a pull request that explains changes, tests, risks and remaining issues.
7. Merge only after checks pass.
8. Update `PROJECT.md`, `CHANGELOG.md` and the version when applicable.
9. Confirm Production and `main` point to the intended commit.

## Commit Convention

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `ui:` interface-only change
- `refactor:` code restructuring without intended behavior change
- `test:` test changes
- `chore:` maintenance

Examples:

- `fix: prevent false final-page detection`
- `feat: add configurable capture profiles`
- `docs: update release and deployment record`

## Handover Prompt

Use the following instruction when a new AI Agent or collaborator takes over:

> 先閱讀 Repository 內的 README.md、PROJECT.md、CHANGELOG.md 及相關 Source Code，確認目前版本、穩定 commit、已知問題和開發方向。先報告你的理解、修改範圍、測試方案和風險，未獲確認前不要直接修改 main 或 Production。

## Security and Data Rules

- Never commit API keys, passwords, tokens, personal data or `.env` files.
- Do not include captured user content or generated PDFs in the repository.
- Preserve `.gitignore` coverage for local environments, build output and temporary screenshots.
- Do not deploy directly to Production from an unreviewed branch.
- Use AutoPage only for content the user is authorized to access, back up or transform.

## Last Updated

2026-09-29
