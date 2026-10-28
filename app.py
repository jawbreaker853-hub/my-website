from __future__ import annotations
import io, os, tempfile
from pathlib import Path
from typing import Annotated

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
MAX_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 20_000_000
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}

app = FastAPI(title="ClearCut AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "app": "ClearCut AI"}

async def read_image(upload: UploadFile) -> Image.Image:
    if upload.content_type not in ALLOWED:
        raise HTTPException(415, "Unsupported file type. Use PNG, JPG, WEBP, BMP, or TIFF.")
    data = await upload.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image is too large. Maximum upload size is 12 MB.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        if image.width * image.height > MAX_PIXELS:
            raise HTTPException(413, "Image dimensions are too large. Maximum is 20 megapixels.")
        return image.convert("RGBA")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "The uploaded file could not be read as an image.")

@app.post("/api/background-remove")
async def background_remove(file: UploadFile = File(...)):
    image = await read_image(file)
    try:
        from rembg import remove, new_session
        # CPU-compatible model; weights are downloaded on first use and cached by rembg.
        session = new_session(os.getenv("CLEARCUT_REMBG_MODEL", "u2net"))
        output = remove(image, session=session, alpha_matting=False)
        buf = io.BytesIO()
        output.save(buf, format="PNG", optimize=True)
        return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as exc:
        # Do not return a pretend result if model download/inference fails.
        raise HTTPException(503, "Background processing failed. Check your internet connection for the first model download, then try again.") from exc

@app.post("/api/object-erase")
async def object_erase(file: UploadFile = File(...), mask: UploadFile = File(...), radius: int = 5):
    image = await read_image(file)
    mask_image = await read_image(mask)
    if image.size != mask_image.size:
        raise HTTPException(400, "Selection mask dimensions must match the original image.")
    try:
        original = np.array(image.convert("RGB"))
        mask_arr = np.array(mask_image.convert("RGB"))[:, :, 0]
        binary_mask = np.where(mask_arr > 32, 255, 0).astype(np.uint8)
        if cv2.countNonZero(binary_mask) == 0:
            raise HTTPException(400, "Paint over the object you want to remove first.")
        radius = max(1, min(int(radius), 15))
        # Telea inpainting is a classical CV algorithm, not generative AI.
        result = cv2.inpaint(cv2.cvtColor(original, cv2.COLOR_RGB2BGR), binary_mask, radius, cv2.INPAINT_TELEA)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        buf = io.BytesIO()
        Image.fromarray(result).save(buf, format="PNG", optimize=True)
        return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Object removal failed. Try a smaller selection or a different image.") from exc

@app.on_event("startup")
def startup_note():
    # Keep startup fast: model weights are loaded lazily when the user first runs a cutout.
    pass
