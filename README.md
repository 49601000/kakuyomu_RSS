# kakuyomu-rss

カクヨム作品ページ（`https://kakuyomu.jp/works/...`）から、RSS 2.0 形式のXMLを生成するPythonスクリプトです。

## できること

- 作品URLまたは作品IDを入力してRSSを生成
- 各話のタイトル、URL、公開日時をRSS `item` として出力
- `--limit` で最新N件だけ出力
- `-o` でXMLファイル保存、未指定なら標準出力
- GitHub Actionsで2作品のRSSを独立した時刻に自動更新

## 自動更新する作品

| 作品 | 作品ID設定 | RSS出力 | 自動更新（JST） | Workflow |
| --- | --- | --- | --- | --- |
| 既存作品 | `myid.md` | `feed.xml` | 毎日 02:00 | `update-rss-daily.yml` |
| 最新AIさんの現代用語基礎知識 | `myid-modern-terms.md` | `feed-modern-terms.xml` | 毎日 09:00 | `update-modern-terms.yml` |

作品IDは、カクヨム作品URL `https://kakuyomu.jp/works/<作品ID>` の数字部分です。各設定ファイルには作品IDだけを1行で記載してください。新作の作品IDは未設定なので、公開後に `myid-modern-terms.md` へ登録します。

## 作品別に自動更新をON/OFFする

リポジトリ直下の `rss-config.json` で2作品を独立して制御します。

```json
{
  "feeds": {
    "existing": {
      "enabled": true
    },
    "modern_terms": {
      "enabled": true
    }
  }
}
```

- `feeds.existing.enabled`: 既存作品の `feed.xml`
- `feeds.modern_terms.enabled`: 新作の `feed-modern-terms.xml`
- `true`: 定期実行・手動実行のどちらでも従来どおり更新
- `false`: 取得・生成・コミットをスキップして正常終了

OFFにしても公開済みのRSSファイルは削除されず、前回生成内容へ引き続きアクセスできます。設定ファイルの欠落、JSON構文エラー、対象設定の欠落、または `enabled` がboolean以外の場合は、Workflowが理由をエラーログへ出して失敗終了します。

既存RSSは次のRaw URLから取得できます。

- `https://raw.githubusercontent.com/49601000/kakuyomu_RSS/main/feed.xml`

新作RSSは、作品ID登録後にWorkflowが一度生成すると次のURLで取得できます。

- `https://raw.githubusercontent.com/49601000/kakuyomu_RSS/main/feed-modern-terms.xml`

GitHub Pagesの公開設定は確認できていないため、上記のGitHub Raw URLを記載しています。

## GitHub Actionsから手動実行する

1. GitHubのリポジトリで **Actions** を開く
2. 実行するWorkflow（**Update RSS Daily** または **Update Modern Terms RSS**）を選ぶ
3. **Run workflow** を押す

新作Workflowは既存作品とは独立しています。新作の作品IDが空または形式不正の場合は、通知ログを出して正常終了し、RSS生成をスキップします。公開話が0件の場合も正常終了し、既存の `feed-modern-terms.xml` は変更しません。HTTPエラーやページ構造変更など、0話以外の取得失敗はエラーログを出して失敗終了するため、スキップと区別できます。

## 動作環境

- Python 3.9+
- `requests`

## インストール

```bash
pip install requests
```

### environment.yml から構築する場合（conda）

```bash
conda env create -f environment.yml
conda activate kakuyomu-rss
```

## 使い方

### 1. 標準出力にRSSを出す

```bash
python kakuyomu_rss.py "https://kakuyomu.jp/works/16818622175853938235"
```

### 2. ファイルに保存する

```bash
python kakuyomu_rss.py 16818622175853938235 -o feed.xml
```

### 3. 最新N件だけ出力する

```bash
python kakuyomu_rss.py 16818622175853938235 -o feed.xml --limit 20
```

### 4. 0話なら既存出力を保持して正常終了する

```bash
python kakuyomu_rss.py 16818622175853938235 -o feed.xml --skip-empty
```

## オプション

- `work`  
  作品URL（`https://kakuyomu.jp/works/...`）または作品ID（数字）
- `-o, --output`  
  出力先ファイルパス（未指定時は標準出力）
- `--limit`  
  出力する最新話数（`0` で全件。デフォルト `0`）
- `--skip-empty`  
  公開話が0件の場合に、出力を書き換えず正常終了

## 仕組み

1. 作品ページHTMLを取得
2. ページ内の `__NEXT_DATA__` JSONを解析
3. `__APOLLO_STATE__` の目次データ（`tableOfContentsV2`）から話情報を抽出
4. RSS 2.0 XMLを組み立てて出力

## 注意点

- カクヨム側のページ構造が変更された場合、取得処理が動かなくなる可能性があります。
- 本スクリプトは公開ページから情報を読み取る方式です（公式作品RSSエンドポイントを直接利用する方式ではありません）。
- 出力ファイルはRSS生成が完了してから書き込むため、取得失敗で既存RSSを空ファイルにしません。

## ファイル構成

- `kakuyomu_rss.py`: 2作品で共用するRSS生成スクリプト
- `rss-config.json`: 作品別のRSS更新ON/OFF設定
- `myid.md`: 既存作品の作品ID
- `myid-modern-terms.md`: 新作の作品ID（現在は未設定）
- `feed.xml`: 既存作品のRSS
- `feed-modern-terms.xml`: 新作RSS（初回生成後に作成）
- `.github/workflows/update-rss-daily.yml`: 既存作品の自動更新
- `.github/workflows/update-modern-terms.yml`: 新作の自動更新
