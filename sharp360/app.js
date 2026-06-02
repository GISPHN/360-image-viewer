(() => {
  const config = window.SHARP360_CONFIG || {};
  const submitButton = document.getElementById("submit");
  const fileInput = document.getElementById("panorama");
  const qualityProfile = document.getElementById("quality-profile");
  const retentionDays = document.getElementById("retention-days");
  const status = document.getElementById("status");
  const result = document.getElementById("result");
  const shareUrlInput = document.getElementById("share-url");
  const expiresAt = document.getElementById("expires-at");
  const copyButton = document.getElementById("copy");
  const openViewer = document.getElementById("open-viewer");

  const apiBase = (config.API_BASE_URL || "").replace(/\/$/, "");
  const allowedExtensions = new Set(config.ALLOWED_EXTENSIONS || ["jpg", "jpeg", "png"]);
  const maxUploadBytes = (config.MAX_UPLOAD_MB || 20) * 1024 * 1024;

  function setStatus(message, kind = "") {
    status.textContent = message;
    status.className = `status ${kind}`.trim();
  }

  function getExtension(filename) {
    return filename.includes(".") ? filename.split(".").pop().toLowerCase() : "";
  }

  function validateFile(file) {
    if (!file) throw new Error("360度写真を選択してください。");
    if (!allowedExtensions.has(getExtension(file.name))) {
      throw new Error("JPEGまたはPNG形式の画像を選択してください。");
    }
    if (file.size > maxUploadBytes) {
      throw new Error(`ファイル容量は${config.MAX_UPLOAD_MB || 20}MB以下にしてください。`);
    }
  }

  function buildViewerUrl(sceneId) {
    const viewer = new URL(config.VIEWER_PATH || "./viewer.html", window.location.href);
    viewer.searchParams.set("scene", sceneId);
    return viewer.toString();
  }

  function formatExpiration(isoText) {
    if (!isoText) return "";
    const date = new Date(isoText);
    if (Number.isNaN(date.getTime())) return "";
    return `共有期限: ${date.toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })}`;
  }

  async function createJob(file) {
    const formData = new FormData();
    formData.append("panorama", file);
    formData.append("quality_profile", qualityProfile.value);
    formData.append("retention_days", retentionDays.value);
    const response = await fetch(`${apiBase}/api/jobs`, { method: "POST", body: formData });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "変換ジョブを登録できませんでした。");
    return body;
  }

  async function waitForJob(jobId) {
    while (true) {
      const response = await fetch(`${apiBase}/api/jobs/${encodeURIComponent(jobId)}`);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "処理状況を取得できませんでした。");
      const progress = Number.isFinite(body.progress) ? ` ${body.progress}%` : "";
      setStatus(`${body.message || "処理中です。"}${progress}`);
      if (body.status === "completed") return body;
      if (body.status === "failed") throw new Error(body.error || "変換処理に失敗しました。");
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }

  if (!apiBase) {
    submitButton.disabled = true;
    setStatus("API接続先が未設定です。config.js の API_BASE_URL を設定してください。", "error");
  } else {
    setStatus("360度写真、復元品質、共有期間を選択してください。");
  }

  submitButton.addEventListener("click", async () => {
    result.hidden = true;
    expiresAt.textContent = "";
    try {
      validateFile(fileInput.files[0]);
      submitButton.disabled = true;
      setStatus("アップロードしています。");
      const job = await createJob(fileInput.files[0]);
      const completed = await waitForJob(job.job_id);
      const viewerUrl = completed.viewer_url || buildViewerUrl(completed.scene_id);
      shareUrlInput.value = viewerUrl;
      openViewer.href = viewerUrl;
      expiresAt.textContent = formatExpiration(completed.expires_at);
      result.hidden = false;
      setStatus("共有URLを発行しました。", "success");
    } catch (error) {
      setStatus(error.message || String(error), "error");
    } finally {
      submitButton.disabled = !apiBase;
    }
  });

  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(shareUrlInput.value);
      setStatus("共有URLをコピーしました。", "success");
    } catch {
      shareUrlInput.select();
      document.execCommand("copy");
      setStatus("共有URLをコピーしました。", "success");
    }
  });
})();
