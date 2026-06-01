from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

APP_TITLE = "SHARP360 Research Share API"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
FACE_SIZE = int(os.getenv("FACE_SIZE", "1024"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "sharp360-scenes")
FRONTEND_VIEWER_URL = os.getenv(
    "FRONTEND_VIEWER_URL",
    "https://gisphn.github.io/360-image-viewer/sharp360/viewer.html",
)

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}
YAW_DEGREES = [0, 90, 180, 270]

app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@dataclass
class Job:
    job_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "変換待ちです。"
    error: str | None = None
    scene_id: str | None = None
    viewer_url: str | None = None


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()
PROCESS_LOCK = threading.Lock()


def update_job(job_id: str, **changes: Any) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        for key, value in changes.items():
            setattr(job, key, value)


def get_job(job_id: str) -> Job:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません。")
        return Job(**asdict(job))


def validate_environment() -> None:
    missing = [
        name
        for name, value in {
            "SUPABASE_URL": SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
            "SUPABASE_BUCKET": SUPABASE_BUCKET,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"環境変数が未設定です: {', '.join(missing)}")


def storage_headers(content_type: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "x-upsert": "true",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def upload_bytes(storage_path: str, payload: bytes, content_type: str) -> str:
    validate_environment()
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{storage_path}"
    response = requests.post(
        url,
        headers=storage_headers(content_type),
        data=payload,
        timeout=120,
    )
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"Supabaseへの保存に失敗しました: {response.status_code} {response.text}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"


def upload_file(storage_path: str, file_path: Path, content_type: str) -> str:
    return upload_bytes(storage_path, file_path.read_bytes(), content_type)


def panorama_to_perspective(
    panorama: np.ndarray,
    yaw_degrees: float,
    face_size: int = FACE_SIZE,
    horizontal_fov_degrees: float = 100.0,
) -> np.ndarray:
    """Convert an equirectangular panorama into one horizontal perspective view."""
    if panorama is None or panorama.ndim != 3:
        raise ValueError("360度画像を読み込めませんでした。")

    height, width = panorama.shape[:2]
    fov = math.radians(horizontal_fov_degrees)
    yaw = math.radians(yaw_degrees)

    axis = np.linspace(-1.0, 1.0, face_size, dtype=np.float32)
    x_plane, y_plane = np.meshgrid(axis, axis)
    focal = 1.0 / math.tan(fov / 2.0)

    # Camera coordinates: x right, y down, z forward.
    x = x_plane
    y = y_plane
    z = np.full_like(x, focal)

    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    world_x = cos_yaw * x + sin_yaw * z
    world_y = y
    world_z = -sin_yaw * x + cos_yaw * z

    longitude = np.arctan2(world_x, world_z)
    latitude = np.arctan2(world_y, np.sqrt(world_x**2 + world_z**2))

    map_x = ((longitude / (2.0 * math.pi)) + 0.5) * width
    map_y = ((latitude / math.pi) + 0.5) * height
    map_x = np.mod(map_x, width).astype(np.float32)
    map_y = np.clip(map_y, 0, height - 1).astype(np.float32)

    return cv2.remap(
        panorama,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_WRAP,
    )


def yaw_quaternion(yaw_degrees: float) -> list[float]:
    half = math.radians(yaw_degrees) / 2.0
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def run_sharp(input_dir: Path, output_dir: Path) -> None:
    command = ["sharp", "predict", "-i", str(input_dir), "-o", str(output_dir)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60 * 60)
    if completed.returncode != 0:
        raise RuntimeError(
            "SHARP推論に失敗しました。\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )


def find_ply_for_stem(output_dir: Path, stem: str) -> Path:
    exact = list(output_dir.rglob(f"{stem}.ply"))
    if exact:
        return exact[0]
    candidates = list(output_dir.rglob("*.ply"))
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError(f"{stem} に対応するPLYを特定できませんでした。")


def process_job(job_id: str, source_path: Path) -> None:
    scene_id = uuid.uuid4().hex[:16]
    work_dir = source_path.parent
    faces_dir = work_dir / "faces"
    assets: list[dict[str, Any]] = []

    try:
        with PROCESS_LOCK:
            update_job(job_id, status="processing", progress=5, message="360度画像を読み込んでいます。")
            validate_environment()
            panorama = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
            if panorama is None:
                raise RuntimeError("画像を読み込めませんでした。JPEGまたはPNG形式を確認してください。")
            if panorama.shape[1] < panorama.shape[0] * 1.8:
                raise RuntimeError("正距円筒形式の360度画像ではない可能性があります。横幅が縦幅のおおむね2倍の画像を使用してください。")

            faces_dir.mkdir(parents=True, exist_ok=True)
            for index, yaw in enumerate(YAW_DEGREES):
                face = panorama_to_perspective(panorama, yaw)
                face_path = faces_dir / f"face_{index:02d}_{yaw:03d}.jpg"
                if not cv2.imwrite(str(face_path), face, [cv2.IMWRITE_JPEG_QUALITY, 92]):
                    raise RuntimeError(f"透視投影画像を書き出せませんでした: {face_path.name}")

            update_job(job_id, progress=20, message="水平4方向の画像を生成しました。SHARP推論を開始します。")

            for index, yaw in enumerate(YAW_DEGREES):
                single_input = work_dir / f"sharp_input_{index:02d}"
                single_output = work_dir / f"sharp_output_{index:02d}"
                single_input.mkdir()
                single_output.mkdir()
                face_source = faces_dir / f"face_{index:02d}_{yaw:03d}.jpg"
                face_copy = single_input / face_source.name
                shutil.copy2(face_source, face_copy)

                update_job(
                    job_id,
                    progress=25 + index * 15,
                    message=f"SHARP推論を実行しています。{index + 1}/4方向",
                )
                run_sharp(single_input, single_output)
                ply_path = find_ply_for_stem(single_output, face_copy.stem)
                storage_path = f"{scene_id}/{ply_path.name}"
                ply_url = upload_file(storage_path, ply_path, "application/octet-stream")
                assets.append(
                    {
                        "url": ply_url,
                        "yaw_degrees": yaw,
                        "rotation": yaw_quaternion(yaw),
                        "position": [0, 0, 0],
                        "scale": [1, 1, 1],
                        "splatAlphaRemovalThreshold": 5,
                    }
                )

            update_job(job_id, progress=90, message="共有用のシーン情報を保存しています。")
            manifest = {
                "scene_id": scene_id,
                "source_type": "equirectangular-panorama",
                "pipeline": "horizontal-four-view-sharp-proof-of-concept",
                "experimental": True,
                "limitations": [
                    "境界部の重複整理は未実装です。",
                    "方向間の尺度整合処理は未実装です。",
                    "上方および下方の視野は十分に復元されません。",
                ],
                "assets": assets,
            }
            upload_bytes(
                f"{scene_id}/manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            viewer_url = f"{FRONTEND_VIEWER_URL}?scene={scene_id}"
            update_job(
                job_id,
                status="completed",
                progress=100,
                message="共有URLを発行しました。",
                scene_id=scene_id,
                viewer_url=viewer_url,
            )
    except Exception as exc:  # noqa: BLE001
        update_job(job_id, status="failed", message="変換に失敗しました。", error=str(exc))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": APP_TITLE, "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs")
async def create_job(background_tasks: BackgroundTasks, panorama: UploadFile = File(...)) -> dict[str, str]:
    suffix = Path(panorama.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="JPEGまたはPNG形式の画像を選択してください。")

    payload = await panorama.read(MAX_UPLOAD_BYTES + 1)
    if not payload:
        raise HTTPException(status_code=400, detail="空のファイルです。")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="ファイル容量が上限を超えています。")

    job_id = uuid.uuid4().hex
    work_dir = Path(tempfile.mkdtemp(prefix=f"sharp360_{job_id[:8]}_"))
    source_path = work_dir / f"panorama{suffix}"
    source_path.write_bytes(payload)

    with JOBS_LOCK:
        JOBS[job_id] = Job(job_id=job_id)
    background_tasks.add_task(process_job, job_id, source_path)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    return asdict(get_job(job_id))


@app.get("/api/scenes/{scene_id}")
def scene_manifest(scene_id: str) -> dict[str, Any]:
    if not scene_id.isalnum() or len(scene_id) > 64:
        raise HTTPException(status_code=400, detail="scene IDが不正です。")
    validate_environment()
    url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{scene_id}/manifest.json"
    response = requests.get(url, timeout=30)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="シーンが見つかりません。")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="シーン情報を取得できませんでした。")
    return response.json()
