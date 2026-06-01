import * as GaussianSplats3D from "https://esm.sh/@mkkellogg/gaussian-splats-3d@0.4.7";

const message = document.getElementById("viewer-message");
const copyButton = document.getElementById("copy-viewer-url");
const config = window.SHARP360_CONFIG || {};
const apiBase = (config.API_BASE_URL || "").replace(/\/$/, "");
const sceneId = new URL(window.location.href).searchParams.get("scene");

function setMessage(text) {
  message.textContent = text;
}

function toSceneOptions(asset) {
  return {
    path: asset.url,
    splatAlphaRemovalThreshold: asset.splatAlphaRemovalThreshold ?? 5,
    rotation: asset.rotation ?? [0, 0, 0, 1],
    position: asset.position ?? [0, 0, 0],
    scale: asset.scale ?? [1, 1, 1]
  };
}

async function loadManifest() {
  if (!sceneId) throw new Error("scene パラメータがありません。");
  if (!apiBase) throw new Error("API接続先が未設定です。");
  const response = await fetch(`${apiBase}/api/scenes/${encodeURIComponent(sceneId)}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "シーン情報を取得できませんでした。");
  return body;
}

async function boot() {
  try {
    setMessage("3DGSファイルを読み込んでいます。");
    const manifest = await loadManifest();
    if (!Array.isArray(manifest.assets) || manifest.assets.length === 0) {
      throw new Error("読み込み可能な3DGSファイルがありません。");
    }

    const viewer = new GaussianSplats3D.Viewer({
      rootElement: document.getElementById("splat-viewer"),
      cameraUp: [0, -1, 0],
      initialCameraPosition: [0, 0, -1.2],
      initialCameraLookAt: [0, 0, 1.5],
      sharedMemoryForWorkers: false,
      gpuAcceleratedSort: false,
      integerBasedSort: false
    });

    await viewer.addSplatScenes(manifest.assets.map(toSceneOptions), true);
    viewer.start();
    setMessage("ドラッグで視点を回転できます。初期版は水平4方向の試作です。");
  } catch (error) {
    console.error(error);
    setMessage(error.message || String(error));
  }
}

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(window.location.href);
    setMessage("共有URLをコピーしました。");
  } catch {
    setMessage("URLをコピーできませんでした。アドレスバーからコピーしてください。");
  }
});

boot();
