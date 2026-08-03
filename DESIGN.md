# hayate-fetch 設計ドキュメント

> クライアント側 WHATWG fetch の内部設計メモ(日本語)。
> 各節は「決定 / 理由 / 却下した代替案」の形を基本とする。
> 実装は hayate-auth v0.2(OAuth トークン交換)の要求駆動で行う(roadmap §4-6)。

## TL;DR

- **コンセプトは一文で「サーバーで受けるのと同じ Request/Response 型で、外へも fetch する」**。
  hayate 本体の `Request` / `Response` / `Headers` をクライアント方向でそのまま使う —
  1 つの型体系が受信と送信の両方を覆うのは、Fetch API モデルを表面に持つ hayate だけの芸当。
- 表面は 1 関数: `await fetch(url_or_request, *, method=..., headers=..., body=...) -> Response`。
- I/O は **`FetchBackend` protocol**(`send(Request) -> Response`)に外部化した二段構え:
  - **CPython 既定**: stdlib `urllib.request` + `asyncio.to_thread`(ゼロ依存)
  - **Workers 既定**: JS グローバル `fetch` へのパススルー(本体 workers adapter の
    FFI 変換部品を再利用。Workers では subrequest として最速・正道)
  - **CPython optional**: `hayate-fetch[httpx]` の `HttpxBackend` にアプリ所有の
    `httpx.AsyncClient` を注入(接続プール・timeout・TLS・proxy 設定を保持)

```python
from hayate_fetch import fetch

response = await fetch(
    "https://oauth2.googleapis.com/token",
    method="POST",
    headers={"content-type": "application/x-www-form-urlencoded"},
    body=encoded,
)
data = await response.json()
```

## 1. なぜ作るか

1. **hayate-auth v0.2 の OAuth トークン交換**(auth DESIGN §17-1)が最初の消費者。
   stdlib に async HTTP クライアントが無い、という Python の穴を
   「urllib + to_thread / Workers は JS fetch」で埋める場所が要る。
   auth 内に閉じず切り出す理由: mcp クライアント(mcp DESIGN §8)・otel 計測など
   将来の消費者が同じものを再発明する未来が見えているから。
2. サーバー内 fetch(service binding / サブリクエスト)と外部 API 呼び出しの
   両方が同じ表面になる。

## 2. 規範とする標準(Normative References)

| 対象 | 文書 | 対応 |
|---|---|---|
| API 形状 | WHATWG Fetch(`fetch()` / Request / Response) | 表面。**文書化されたサブセット**: ブラウザ専用フィールド(mode / credentials / cache / referrer 系)は対象外と README に明記 |
| リダイレクト | Fetch の redirect 意味論 | v0.1 は `follow`(既定)と `manual` のみ。バックエンドの挙動差は受け入れテストで固定 |
| TLS / プロキシ | 実装依存(urllib / JS fetch に委譲) | 独自実装しない |

## 3. アーキテクチャ(決定)

```
hayate_fetch.fetch(input, **init) -> Response     # 表面(WHATWG 形)
─────────────────────────────────────────────
FetchBackend protocol:  async send(Request) -> Response
─────────────────────────────────────────────
実装:  UrllibBackend(CPython 既定)| WorkersBackend(js.fetch)| HttpxBackend(optional)
```

- 既定バックエンドは実行環境で自動選択(`sys.platform == "emscripten"` → Workers)。
  auth の CryptoBackend / KDF 自動選択と同じパターン。
- **却下**: httpx への必須依存 — 既定のゼロ依存原則は維持し、必要な利用者だけが
  optional extra と protocol 注入で選択する。
- **却下**: 独自の HTTP/1.1 実装 — YAGNI + セキュリティ表面積。stdlib / プラットフォームに委譲。
- ストリーミング応答: v0.1 はバッファ(urllib の制約に合わせる)。Workers 側は
  ReadableStream ブリッジ(本体 research §5 の部品)で自然にストリームになるが、
  「両バックエンドで同じに見える」ことを優先し、v0.1 の公開契約はバッファとする。

## 4. スコープ外(YAGNI リスト)

| やらないこと | 理由 |
|---|---|
| cookie jar / セッション管理 | 消費者(auth の OAuth)はステートレスな 1 発 POST。証拠待ち |
| リトライ / バックオフ | ポリシーはアプリの領分。protocol の外で包める |
| HTTP/2, 接続プールの独自管理 | urllib / JS fetch、または optional `HttpxBackend` に注入した `AsyncClient` に委譲 |
| ブラウザ専用 Fetch フィールド | サーバーサイドに意味がない(§2) |

## 5. マイルストーン

| 版 | 内容 | 受け入れ基準 |
|---|---|---|
| v0.1 | `fetch()` + FetchBackend + urllib / Workers 両実装 | hayate-auth v0.2 の OAuth フローが CPython と workerd の両方で同一コードで通る(= auth の受け入れテストが背中を押す)。実装は auth v0.2 と同一作業列で行う |
| v0.2 | application-owned `httpx.AsyncClient` を使う optional backend | 基本 install のゼロ追加依存を維持し、pooling / redirect / error 契約を受け入れテストで固定 |
| 将来 | ストリーミング応答の公開契約化 / mcp クライアントとの合流判断 | 証拠駆動 |

### 決定済み(2026-07-23)

| 項目 | 決定 |
|---|---|
| 名前 | **hayate-fetch**(配布名)/ `hayate_fetch`(import 名) |
| リポジトリ | `hayatepy/hayate-fetch`。private 開始、v0.1 完成時に公開判断 |
| ライセンス / 最低 Python | MIT / 3.12 |
| 依存 | `hayate` のみ |
| auth §17-1 への回答 | 案 (a) を採用し、その実装置き場をこのパッケージにする(auth は hayate-fetch に依存) |
