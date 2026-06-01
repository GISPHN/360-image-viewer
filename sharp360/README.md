# SHARP360 Research Share

360度の正距円筒画像1枚から、Apple SHARPを利用して近傍視点閲覧用の3D Gaussian Splattingデータを生成し、共有URLを発行するための非商用・研究教育目的の試作構成です。

既存の `360-image-viewer` 直下にある能登半島360度写真ビューワーは変更していません。本試作は `sharp360/` 配下で独立しています。

## 重要な前提

- Apple SHARPの公式実装は通常の透視投影写真を入力とするモデルです。
- 本試作では、360度画像を水平4方向の透視投影画像へ変換し、各画像にSHARPを逐次適用します。
- 生成した複数のPLYをWeb閲覧時に同時読み込みします。
- 初期版は動作確認用です。境界部の重複整理、深度の整合、上方・下方画像の統合は今後の改善項目です。
- Apple SHARPのモデル利用条件を確認し、非商用の科学研究・学術的開発活動の範囲で使用してください。

## 無料構成

```text
GitHub Pages
  └─ sharp360/ 静的フロントエンドと3DGS閲覧画面

Hugging Face Spaces Free CPU
  └─ hf-space/ FastAPIバックエンド
      ├─ 360度画像を水平4方向へ変換
      ├─ Apple SHARPをCPUで逐次実行
      └─ PLYとmanifest.jsonをSupabaseへ保存

Supabase Free Plan
  └─ 公開Storage bucket
      ├─ manifest.json
      └─ 方向別PLY
```

## 公開予定URL

GitHub Pagesが既存と同じ設定で配信されている場合、フロントエンドは次のURLで開けます。

```text
https://gisphn.github.io/360-image-viewer/sharp360/
```

## 現在の実装範囲

- [x] GitHub Pages向けアップロード画面
- [x] API接続先を切り替える `config.js`
- [x] 共有URLを受け取る3DGS閲覧画面
- [x] GaussianSplats3Dを利用した複数PLYの同時読み込み
- [x] FastAPIバックエンド雛形
- [x] 水平4方向の透視投影画像生成
- [x] SHARP CLIの逐次起動
- [x] Supabase Storageへの保存処理
- [ ] Hugging Face Spacesへのデプロイ
- [ ] Supabase bucketの作成と環境変数設定
- [ ] 実際の360度画像を用いたCPU処理時間とメモリ消費の検証
- [ ] PLY境界部の重複整理と尺度整合の改善
- [ ] 生成物の自動削除

## 設定手順

1. Supabase Free Planでプロジェクトを作成します。
2. `sharp360-scenes` という公開Storage bucketを作成します。
3. Hugging FaceでDocker Spaceを作成し、`hf-space/` 配下のファイルを配置します。
4. Hugging Face SpaceのSecretsに、`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`SUPABASE_BUCKET`、`FRONTEND_VIEWER_URL` を登録します。
5. `config.js` の `API_BASE_URL` をHugging Face Spaceの公開URLに変更します。
6. GitHub PagesのURLを開き、個人情報や機微情報を含まないテスト画像で動作確認します。

詳細は [`hf-space/README.md`](./hf-space/README.md) を確認してください。

## 参照元

- Apple SHARP: https://github.com/apple/ml-sharp
- Apple SHARP model license: https://github.com/apple/ml-sharp/blob/main/LICENSE_MODEL
- GaussianSplats3D: https://github.com/mkkellogg/GaussianSplats3D

## 注意

本試作はApple Inc.が提供、保証、推奨する公式サービスではありません。公開前に [`NOTICE.md`](./NOTICE.md) を確認してください。
