# ClearCut AI

A local-first image editing web app with three tools:

- **Background Remover** — real foreground/background segmentation using the open-source `rembg` U²-Net model; exports transparent PNG.
- **Object Eraser** — pointer/touch brush mask, undo/redo, clear mask, and OpenCV Telea inpainting. This is classical computer vision, not generative AI.
- **Object Extractor** — subject isolation using the same segmentation model as the background remover; exports a transparent PNG.

The UI is built with HTML, CSS, and vanilla JavaScript. The backend uses FastAPI and runs on Windows without requiring a dedicated GPU. CPU processing can be slow for large images.

## Requirements

- Windows 10/11, 64-bit
- Python 3.11 or 3.12 recommended (some ML dependencies may not yet support every newest Python version)
- Internet access for the first segmentation run so `rembg` can download its model weights
- About 2–4 GB of free RAM recommended; more helps with large images

## Install on Windows

1. Extract the ZIP to a simple path, for example `C:\ClearCut`.
2. Open **Command Prompt** or **PowerShell** in that folder.
3. Create a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`, or run `.venv\Scripts\python.exe -m pip ...` without activating.
4. Upgrade pip and install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Optional environment configuration: copy `.env.example` to `.env` and set `CLEARCUT_REMBG_MODEL=u2net`. The app currently reads the environment variable directly; it does not auto-load `.env`. To use `.env`, set the variable in PowerShell before starting:

   ```powershell
   $env:CLEARCUT_REMBG_MODEL = "u2net"
   ```
6. Start the server:

   ```powershell
   python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```
7. Open **http://127.0.0.1:8000** in your browser. Keep the terminal open while using ClearCut. Stop the server with `Ctrl+C`.

### First model run

The server starts without loading the segmentation model. The first Background Remover or Object Extractor request downloads the model weights if they are not cached, so it can take a while and needs internet access. Subsequent requests should use the cached model. If model download fails, the app returns an error rather than a fake result. The default `u2net` model is CPU-compatible; it does not require a CUDA GPU.

## Test the tools

1. **Background Remover:** upload a photo with a clear foreground subject, click **Remove background**, inspect the transparent result, then download the PNG.
2. **Object Eraser:** upload a photo, choose **Object eraser**, paint over a small unwanted object, test Undo/Redo and Clear mask, click **Erase object**, then download the PNG. Inpainting may produce visible artifacts for large selections or complex textures.
3. **Object Extractor:** upload a photo, choose **Extractor**, click **Extract subject**, inspect the transparent PNG, then download it.
4. **Upload validation:** try a text file renamed `.jpg`, an unsupported format, a file larger than 12 MB, or an image above 20 megapixels. The frontend and backend both validate relevant constraints.
5. **Failure handling:** temporarily disconnect the internet before the first segmentation request to verify that a processing error is shown; reconnect and retry.
6. **Health endpoint:** visit `http://127.0.0.1:8000/health`; it should return JSON with status `ok`.

## Privacy and security

Images are uploaded to the local FastAPI server at `127.0.0.1`. The app does not intentionally persist uploads or outputs to disk, and it does not call an external image API. The open-source segmentation model is downloaded from its model source on first use. Do not expose this prototype publicly as-is: add authentication or abuse controls, request/concurrency limits, HTTPS, stricter content inspection, and deployment-specific privacy/legal review before hosting it for other users.

## Known limitations

- Background removal and extraction depend on `rembg` and model weights. Model startup/inference can be memory-heavy and slower on older CPUs.
- Object erasing uses OpenCV's Telea inpainting, not generative AI. It is best for small objects; large objects, faces, text, repeating patterns, and detailed backgrounds may not reconstruct convincingly.
- The before/after comparison is available for segmentation results. Object-erasing results appear in the result panel; the brush mask is editable, but its canvas is not a full layered photo editor.
- No login, cloud storage, payment system, or third-party API is included.
- The footer contact address is a local-demo placeholder and must be replaced or removed before public deployment.

## Project layout

```text
clearcut/
  app.py
  requirements.txt
  .env.example
  .gitignore
  README.md
  static/
    index.html
    css/style.css
    js/main.js
```

## API endpoints

- `GET /` — app UI
- `GET /health` — health check
- `POST /api/background-remove` — multipart image upload, returns transparent PNG
- `POST /api/object-erase` — multipart `file`, `mask`, optional `radius`, returns inpainted PNG

The extractor uses the background-removal endpoint because the model output is the extracted foreground with an alpha channel.
