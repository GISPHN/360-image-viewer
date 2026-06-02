# SHARP360 Research Share

360度の正距円筒画像1枚から、Apple SHARPを利用して近傍視点閲覧用の3D Gaussian Splattingデータを生成し、共有URLを発行するための非商用・研究教育目的の試作構成です。

既存の `360-image-viewer` 直下にある能登半島360度写真ビューワーは変更していません。本試作は `sharp360/` 配下で独立しています。

## 重要な前提

- Apple SHARPの公式実装は通常の透視投影写真を入力とするモデルです。
- 単一の360度写真から、撮影地点の周囲に写っている領域は広く再構成できます。
- 建物、家具、樹木等の背後など、元画像に写っていない面を事実として正確に復元することはできません。
- 高品質化では、方向別の重複付き透視投影、境界整理、方向間の深度尺度整合、座標変換、統合を行います。
- Apple SHARPのモデル利用条件を確認し、非商用の科学研究・学術的開発活動の範囲で使用してください。

## 復元品質プロファイル

フロントエンドでは、次の3段階を選択できます。

```text
maximum    高品質：重複付き8方向・尺度整合
balanced   標準：重複付き6方向・尺度整合
prototype  検証用：水平4方向・簡易統合
```

`prototype` は既存の動作確認用パイプラインです。`maximum` と `balanced` は、SPAG-4DのSHARP 360型パイプラインを参考に、重複付き透視投影、Voronoi境界クリッピング、DA360による方向間の尺度整合、ワールド座標への回転統合を行う高品質処理として実装します。

## 共有可能期間

フロントエンドでは、次の期間を選択できます。

```text
7日間
30日間
60日間
```

期限を保証する構成では、公開bucketを使用しません。Supabase Storageの非公開bucketに保存し、シーンごとの有効期限をバックエンドで検査します。閲覧時に期限内であれば短時間だけ有効な署名付きURLを発行し、期限切れであれば閲覧を拒否します。

Hugging Face Spacesのlocal保存は一時ディスクであるため、Space再起動後にファイルが失われます。7日間、30日間、60日間の共有を保証する場合は、Supabase Free Plan等の永続保存が必要です。

## 無料構成

```text
GitHub Pages
  └─ sharp360/ 静的フロントエンドと3DGS閲覧画面

Hugging Face Spaces Free CPU
  └─ hf-space/ FastAPIバックエンド
      ├─ 360度画像を複数方向へ変換
      ├─ Apple SHARPをCPUで逐次実行
      ├─ 高品質モードでは境界整理と尺度整合
      └─ manifest.jsonとPLYを永続保存先へ保存

Supabase Free Plan
  └─ 非公開Storage bucket
      ├─ manifest.json
      └─ PLYまたは圧縮済み3DGS
```

## 公開予定URL

GitHub Pagesが既存と同じ設定で配信されている場合、フロントエンドは次のURLで開けます。

```text
https://gisphn.github.io/360-image-viewer/sharp360/
```

## 現在の実装範囲

- [x] GitHub Pages向けアップロード画面
- [x] 復元品質の選択欄
- [x] 共有期間の選択欄
- [x] API接続先を切り替える `config.js`
- [x] 共有URLを受け取る3DGS閲覧画面
- [x] GaussianSplats3Dを利用した複数PLYの同時読み込み
- [x] FastAPIバックエンド雛形
- [x] 水平4方向の透視投影画像生成
- [x] SHARP CLIの逐次起動
- [x] local保存とSupabase保存の切替
- [ ] Hugging Face Spacesへのデプロイ
- [ ] Supabaseの非公開bucket作成と環境変数設定
- [ ] 期限日時の保存、閲覧時検査、署名付きURL発行
- [ ] 期限切れファイルの削除処理
- [ ] SPAG-4D型の高品質統合パイプライン
- [ ] 実際の360度画像を用いたCPU処理時間とメモリ消費の検証

## 設定手順

1. Supabase Free Planでプロジェクトを作成します。
2. `sharp360-scenes` という非公開Storage bucketを作成します。
3. Hugging FaceでDocker Spaceを作成し、`hf-space/` 配下のファイルを配置します。
4. Hugging Face SpaceのSecretsに、`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`SUPABASE_BUCKET`、`FRONTEND_VIEWER_URL` を登録します。
5. `config.js` の `API_BASE_URL` をHugging Face Spaceの公開URLに変更します。
6. GitHub PagesのURLを開き、個人情報や機微情報を含まないテスト画像で動作確認します。

詳細は [`hf-space/README.md`](./hf-space/README.md) を確認してください。

## 参照元

- Apple SHARP: https://github.com/apple/ml-sharp
- Apple SHARP model license: https://github.com/apple/ml-sharp/blob/main/LICENSE_MODEL
- GaussianSplats3D: https://github.com/mkkellogg/GaussianSplats3D
- SPAG-4D: https://github.com/cedarconnor/SPAG4d

## 注意

本試作はApple Inc.が提供、保証、推奨する公式サービスではありません。公開前に [`NOTICE.md`](./NOTICE.md) を確認してください。
