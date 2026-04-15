# kakuyomu-rss

カクヨム作品ページ（`https://kakuyomu.jp/works/...`）から、RSS 2.0 形式のXMLを生成するPythonスクリプトです。

## できること

- 作品URLまたは作品IDを入力してRSSを生成
- 各話のタイトル、URL、公開日時をRSS `item` として出力
- `--limit` で最新N件だけ出力
- `-o` でXMLファイル保存、未指定なら標準出力

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

## オプション

- `work`  
  作品URL（`https://kakuyomu.jp/works/...`）または作品ID（数字）
- `-o, --output`  
  出力先ファイルパス（未指定時は標準出力）
- `--limit`  
  出力する最新話数（`0` で全件。デフォルト `0`）

## 仕組み

1. 作品ページHTMLを取得
2. ページ内の `__NEXT_DATA__` JSONを解析
3. `__APOLLO_STATE__` の目次データ（`tableOfContentsV2`）から話情報を抽出
4. RSS 2.0 XMLを組み立てて出力

## 注意点

- カクヨム側のページ構造が変更された場合、取得処理が動かなくなる可能性があります。
- 本スクリプトは公開ページから情報を読み取る方式です（公式作品RSSエンドポイントを直接利用する方式ではありません）。

## ファイル構成

- `kakuyomu_rss.py`: RSS生成スクリプト本体
- `README.md`: このドキュメント
