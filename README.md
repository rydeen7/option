# US Options Volume Dashboard

米国オプション市場の日次取引高（コール・プット・コール/プット比率）を2年分取得し、Plotlyでインタラクティブに可視化するダッシュボード。

## データソース

**CBOE（Chicago Board Options Exchange）**

- URL: `https://www.cboe.com/markets/us/options/market-statistics/daily?dt=YYYY-MM-DD`
- カテゴリ: Total（株式 + ETF + 指数オプションの合計）
- 取得項目:
  - コール出来高（枚）
  - プット出来高（枚）
  - 総出来高（枚）
  - コール/プット比率
  - プット/コール比率（CBOE公式指標）

## セットアップ

```bash
# 依存パッケージはプロジェクトルートのvenvを使用
# myproject/.venv に requests / pandas / fastapi / uvicorn が含まれる

# データ取得（初回 or 更新時）
python download_data.py   # 約5〜10分、502営業日分を取得

# サーバー起動（ブラウザ自動起動）
python app.py             # http://localhost:8005
```

## ファイル構成

```
option/
├── download_data.py     # CBOEから2年分の日次データを並列取得・CSV保存
├── app.py               # FastAPI サーバー（ポート 8005）
├── templates/
│   └── index.html       # Plotly.js 可視化UI（3タブ）
├── data/                # CSVキャッシュ（.gitignore）
│   └── options_volume.csv
└── README.md
```

## 画面構成

| タブ | 内容 |
|------|------|
| 出来高 | コール/プット出来高の折れ線グラフ（日次）＋総出来高 |
| コール/プット比率 | C/P比率の折れ線グラフ＋20日移動平均＋ニュートラルライン（1.0） |
| 統計サマリー | 最新値・2年平均・最大・最小などのカード表示 |

## API エンドポイント

| エンドポイント | 内容 |
|---------------|------|
| `GET /` | ダッシュボード HTML |
| `GET /api/chart/volume` | コール・プット・総出来高の時系列データ（JSON） |
| `GET /api/chart/ratio` | C/P比率・P/C比率・20日MAの時系列データ（JSON） |
| `GET /api/stats` | サマリー統計（最新値・平均・最大最小） |

## データ取得の仕組み

`download_data.py` は以下の手順でデータを取得する。

1. 過去2年分の営業日リストを生成（`pandas.bdate_range`）
2. CBOEの日次統計ページをHTTPで取得（5並列・バッチ間1秒待機）
3. ページ内の埋め込みJSON（Next.js SSR）からオプション統計を抽出
4. 休場日・データなし日は自動スキップ
5. `data/options_volume.csv` に保存

## 注意事項

- CBOE提供データはCBOE上場オプションのみ（全米取引所合計ではない）
- 市場センチメント分析の参照指標として使用
- データは投資助言ではない
