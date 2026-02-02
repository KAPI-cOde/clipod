# Copilot CLI Demo Notes

## Impressive prompts
- "Add BGM timeline placement with draggable/trim-able blocks and mix export at -12dB with 3s fades."
- "Fix clipod web to run a Python server directly without dev-env.sh."
- "Implement clipod export to read BGM layout and output -16 LUFS MP3."

## Key learning moments
- Confirmed local-only workflow constraints (no fetch for BGM load).
- Reused ffmpeg filters from existing process pipeline to keep loudness consistent.
- Added explicit error handling and temporary file cleanup for export steps.

## What was built
- Web waveform editor with BGM timeline and multi-block placement.
- Local BGM mixing pipeline with default -12dB and 3s fades.
- Export command that mixes BGM (if present) and normalizes to -16 LUFS MP3.
- Workflow helper script and README updates for onboarding.

## How Copilot CLI helped
- Rapidly located existing mix/process helpers and reused them.
- Generated ffmpeg command structure and click wiring quickly.
- Kept edits small while connecting the UI, server, and export flow.

---

## 日本語まとめ（AI向けメモ）
- **Webエディタ**: BGMタイムラインを追加し、複数ブロックのドラッグ配置・右端トリムに対応。BGM波形表示と選択UI、開始/終了/音量/フェード設定を実装。
- **BGM読み込み**: `input[type=file]` + `URL.createObjectURL` でローカル読み込み。BGMファイルは `X-File-Name` を `encodeURIComponent` して送信し、サーバー側で `unquote` して保存。
- **BGM操作**: ブロック選択/削除、`d` キーでBGM/選択範囲削除の分岐、`Delete/Backspace` 対応。`d` キーに debug `console.log` を追加。
- **BGMプレビュー**: BGM単体の再生ボタンを追加（ループ再生・停止、音量スライダー連動）。
- **ミックス**: ffmpeg フィルタ生成で `[1:a]atrim=...` を含む形式に修正。`mix_bgm()` でコマンドと main/output/layout、stderr を stderr に出力するログを追加。
- **プレビューMix**: Web Audio APIでメイン音声 + BGMをリアルタイム合成する「Preview Mix」ボタンを追加。GainNodeでBGM音量をリアルタイム調整。
- **export**: `clipod export` を実装。BGMレイアウトがあればミックスし、`process.py`のFFMPEG_FILTERで -16 LUFS に正規化してMP3出力。
- **ドキュメント/スクリプト**: README更新、DEMO.mdの記録、test_workflow.sh追加。

### 注意点/現状
- 選択範囲削除は `?file=auto` のみ有効（サーバー側の `/api/delete` に依存）。
- `pytest` は環境に未インストールでテスト実行不可。
- ffmpeg mixエラーの調査用に、`FULL FFMPEG COMMAND` 等のログ出力が追加済み。
