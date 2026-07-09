from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
RECOGNITION_MODEL = "w600k_r50.onnx"


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, target.open("wb") as output:
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            received += len(chunk)
            if total:
                percent = received * 100 / total
                print(f"\rDownloading {percent:5.1f}%", end="")
        print()


def extract_recognition_model(zip_path: Path, output_path: Path) -> Path:
    if not zip_path.exists():
        raise FileNotFoundError(f"Model pack not found: {zip_path}")

    with zipfile.ZipFile(zip_path) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if Path(name).name.lower() == RECOGNITION_MODEL.lower()
        ]
        if not candidates:
            onnx_files = [name for name in archive.namelist() if name.lower().endswith(".onnx")]
            raise RuntimeError(
                f"Could not find {RECOGNITION_MODEL} in {zip_path}. "
                f"Available ONNX files: {onnx_files}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(candidates[0]) as source, output_path.open("wb") as target:
            shutil.copyfileobj(source, target)

    return output_path


def validate_onnx(model_path: Path) -> None:
    import onnxruntime as ort

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    input_names = [item.name for item in session.get_inputs()]
    output_names = [item.name for item in session.get_outputs()]
    print(f"Model ready: {model_path}")
    print(f"Inputs: {input_names}")
    print(f"Outputs: {output_names}")
    print(f"Providers: {session.get_providers()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install InsightFace buffalo_l recognition ONNX model.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Model pack zip URL.")
    parser.add_argument("--zip", dest="zip_path", default="", help="Use an existing local model pack zip.")
    parser.add_argument("--output", default="models/face_embedding.onnx", help="Output ONNX path.")
    parser.add_argument("--keep-zip", action="store_true", help="Keep downloaded zip file.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    if args.zip_path:
        zip_path = Path(args.zip_path)
        if not zip_path.is_absolute():
            zip_path = project_root / zip_path
    else:
        zip_path = project_root / "models" / "downloads" / "buffalo_l.zip"
        download(args.url, zip_path)

    extract_recognition_model(zip_path, output_path)
    validate_onnx(output_path)

    if not args.zip_path and not args.keep_zip:
        zip_path.unlink(missing_ok=True)

    print()
    print("Add these values to .env:")
    print("FACE_EMBEDDING_PROVIDER=onnx")
    print("FACE_ONNX_MODEL_PATH=models/face_embedding.onnx")
    print("FACE_ONNX_INPUT_SIZE=112")
    print("FACE_ONNX_EXECUTION_PROVIDERS=CPUExecutionProvider")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
