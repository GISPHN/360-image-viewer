# SHARP360 Hugging Face Spaces backend

このディレクトリは、Hugging Face Spaces の Docker Space に配置する無償CPUバックエンドです。

## 重要

- 初期値は `STORAGE_MODE=local` です。
- `local` 保存では追加サービスを使わず0円で動作します。
- Hugging Face Space がスリープまたは再起動すると、生成済み3DGSと共有URLは消失します。
- 長期間共有する場合だけ、任意で Supabase Free Plan を追加してください。
- Apple SHARP のモデルは研究目的に限定されています。商用サービスには使用しないでください。

## 1. Hugging Face Spaceを作成

Hugging Faceで新しいSpaceを作成し、SDKとして `Docker` を選択します。

例:

```text
Space name: gisphn-sharp360
Visibility: Public
SDK: Docker
Hardware: CPU basic free
```

## 2. このディレクトリをSpaceへ配置

`sharp360/hf-space/` 配下のファイルを、作成したSpaceのルートへコピーします。

```text
Dockerfile
app.py
requirements-api.txt
```

## 3. Space Variablesを設定

Hugging Face Spaceの Settings > Variables and secrets で、次のVariablesを追加します。

```text
STORAGE_MODE=local
PUBLIC_API_BASE_URL=https://YOUR-SPACE-NAME.hf.space
FRONTEND_VIEWER_URL=https://gisphn.github.io/360-image-viewer/sharp360/viewer.html
MAX_UPLOAD_MB=20
FACE_SIZE=1024
```

`YOUR-SPACE-NAME` は実際の公開URLに置き換えてください。

## 4. GitHub Pages側の設定

`sharp360/config.js` の `API_BASE_URL` を、Hugging Face Spaceの公開URLへ変更します。

```javascript
window.SHARP360_CONFIG = {
  API_BASE_URL: "https://YOUR-SPACE-NAME.hf.space",
  MAX_UPLOAD_MB: 20,
  ALLOWED_EXTENSIONS: ["jpg", "jpeg", "png"],
  VIEWER_PATH: "./viewer.html"
};
```

## 5. 動作確認

次のURLを開きます。

```text
https://gisphn.github.io/360-image-viewer/sharp360/
```

個人情報や機微情報を含まない正距円筒画像を選択してください。横幅が縦幅のおおむね2倍のJPEGまたはPNGが対象です。

## Supabase Free Planを追加する場合

Space再起動後も共有URLを維持したい場合だけ使用します。

### Supabase側

1. Supabaseプロジェクトを作成します。
2. Storageで `sharp360-scenes` という公開bucketを作成します。
3. Project URLとservice role keyを確認します。

### Hugging Face Space側

Variables:

```text
STORAGE_MODE=supabase
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_BUCKET=sharp360-scenes
PUBLIC_API_BASE_URL=https://YOUR-SPACE-NAME.hf.space
FRONTEND_VIEWER_URL=https://gisphn.github.io/360-image-viewer/sharp360/viewer.html
```

Secrets:

```text
SUPABASE_SERVICE_ROLE_KEY=YOUR-SERVICE-ROLE-KEY
```

service role keyはGitHubへ保存しないでください。

## API

```text
GET  /health
POST /api/jobs
GET  /api/jobs/{job_id}
GET  /api/scenes/{scene_id}
GET  /assets/{path}            # STORAGE_MODE=local のみ
```

## 現時点の制約

初期版は水平4方向の透視投影画像を順番にSHARPへ渡します。方向間の重複整理、尺度整合、上方・下方の復元は未実装です。まず、無料CPU環境でSHARPが完走するかを確認するための構成です。
