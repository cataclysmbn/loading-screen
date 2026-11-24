# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=11"]
# ///
"""Check loading screens, draw a collage of them, or turn a submission issue into a pull request.

loading_screen.py check <path>...
loading_screen.py collage <out.webp>
loading_screen.py submit   (in GitHub Actions, on an issues event)
"""

import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import warnings
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont, ImageOps

LIMIT = 128 * 1024
MAX_DOWNLOAD = 10 * 1024 * 1024
EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
FORMATS = {"PNG", "JPEG", "WEBP", "GIF", "BMP"}
LOADING_DIR = re.compile(r"^data/(json|mods/[^/]+)/loading/[^/]+$")
ATTACHMENT = re.compile(r"https://github\.com/user-attachments/assets/[0-9a-fA-F-]+")
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"

Image.MAX_IMAGE_PIXELS = 40_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)


class Rejected(Exception):
    pass


def git(*args: str, data: bytes | None = None) -> str:
    return subprocess.run(["git", *args], input=data, capture_output=True, check=True).stdout.decode()


def open_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:
        raise Rejected(f"not a readable image: {e}") from e
    if img.format not in FORMATS:
        raise Rejected(f"unsupported image format {img.format}")
    return img


def check(path: Path) -> list[str]:
    name = path.as_posix()
    errors = []
    if not LOADING_DIR.match(name):
        errors.append("must be in data/json/loading/ or data/mods/<mod>/loading/")
    if path.suffix.lower() not in EXTENSIONS:
        errors.append(f"extension must be one of {' '.join(sorted(EXTENSIONS))}")
    author, sep, title = path.stem.partition("_")
    if not (author and sep and title):
        errors.append("name must be <author>_<title>.<ext>")
    if path.stat().st_size > LIMIT:
        errors.append(f"{path.stat().st_size} B is over the {LIMIT} B limit")
    try:
        if not git("cat-file", "-p", f"HEAD:{name}").startswith("version https://git-lfs"):
            errors.append("not stored with Git LFS")
    except subprocess.CalledProcessError:
        errors.append("not committed")
    try:
        open_image(path.read_bytes())
    except Rejected as e:
        errors.append(str(e))
    return [f"{name}: {e}" for e in errors]


def encode(img: Image.Image, **options) -> bytes:
    out = io.BytesIO()
    img.save(out, "WEBP", method=6, **options)
    return out.getvalue()


def convert(img: Image.Image, pixel_art: bool) -> tuple[bytes, Image.Image, str]:
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA" if img.has_transparency_data else "RGB")
    if pixel_art:
        for k in range(1, 9):
            small = img.resize((img.width // k, img.height // k), Image.Resampling.NEAREST) if k > 1 else img
            if len(data := encode(small, lossless=True)) <= LIMIT:
                return data, small, "lossless" if k == 1 else f"lossless, 1/{k} scale"
        raise Rejected("pixel art does not fit in 128 KiB even at 1/8 scale")
    while True:
        for quality in range(90, 65, -5):
            if len(data := encode(img, quality=quality)) <= LIMIT:
                return data, img, f"quality {quality}"
        if max(img.size) <= 640:
            raise Rejected("image does not fit in 128 KiB even at 640 px")
        scale = min(1920, max(img.size) * 4 // 5) / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)


def form_fields(body: str) -> dict[str, str]:
    parts = re.split(r"^### (.+)$", body, flags=re.MULTILINE)
    return {k.strip(): v.strip() for k, v in zip(parts[1::2], parts[2::2])}


def clean_name(text: str, label: str) -> str:
    text = " ".join(re.sub(r"[^\w .,'()&+!-]|_", " ", text).split())[:60].strip(" .-")
    if not text or text == "_No response_":
        raise Rejected(f"{label} is empty")
    return text


def download(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "loading-screen-bot"})) as r:
        data = r.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise Rejected("image is larger than 10 MiB")
    return data


def prepare(issue: dict) -> tuple[Path, bytes, str, str]:
    fields = form_fields(issue.get("body") or "")
    checklist = fields.get("Checklist", "")
    if "- [ ]" in checklist or checklist.count("- [X]") < 4:
        raise Rejected("check every checklist box")
    author = clean_name(fields.get("Artist", ""), "Artist")
    title = clean_name(fields.get("Title", ""), "Title")
    target = fields.get("Target", "")
    folder = Path("data/json/loading" if target == "core" else f"data/mods/{target}/loading")
    if not re.fullmatch(r"\w+", target) or not folder.is_dir():
        raise Rejected(f"unknown target {target!r}")
    urls = set(ATTACHMENT.findall(fields.get("Image", "")))
    if len(urls) != 1:
        raise Rejected("upload exactly one image in the Image field")
    original = download(urls.pop())
    source = open_image(original)
    data, img, mode = convert(source, fields.get("Kind") == "Pixel art")
    path = folder / f"{author}_{title}.webp"
    if path.exists():
        raise Rejected(f"{path} already exists")
    table = "\n".join(
        [
            "|          | Format | Size | Bytes |",
            "| -------- | ------ | ---- | ----: |",
            f"| Original | {source.format} | {source.width}x{source.height} | {len(original)} |",
            f"| Output   | WebP, {mode} | {img.width}x{img.height} | {len(data)} |",
        ]
    )
    return path, data, f'feat: add "{title}" by {author}', table


def collage(out: Path, columns: int = 4, tile: tuple[int, int] = (384, 216)) -> None:
    paths = sorted(p for p in Path("data").rglob("*") if p.suffix.lower() in EXTENSIONS)
    rows = -(-len(paths) // columns)
    sheet = Image.new("RGB", (tile[0] * columns, tile[1] * rows))
    font = ImageFont.load_default(16)
    for i, path in enumerate(paths):
        thumb = ImageOps.fit(open_image(path.read_bytes()).convert("RGB"), tile, Image.Resampling.LANCZOS)
        author, _, title = path.stem.partition("_")
        ImageDraw.Draw(thumb).text(
            (8, tile[1] - 8), f"{title} by {author}", "white", font, "ld", stroke_width=2, stroke_fill="black"
        )
        sheet.paste(thumb, (i % columns * tile[0], i // columns * tile[1]))
    sheet.save(out, "WEBP", quality=70, method=6)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, check=True, text=True).stdout.strip()


def submit() -> None:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    issue, repo = event["issue"], event["repository"]["full_name"]
    number, user = issue["number"], issue["user"]
    run_url = f"{os.environ['GITHUB_SERVER_URL']}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"

    def comment(text: str) -> None:
        gh("issue", "comment", str(number), "--repo", repo, "--body", text)

    try:
        path, data, subject, table = prepare(issue)
        branch = f"submission/{number}"
        git("switch", "-C", branch)
        path.write_bytes(data)
        git("add", "--", path.as_posix())
        coauthor = f"{user['login']} <{user['id']}+{user['login']}@users.noreply.github.com>"
        message = f"{subject}\n\nArtist permission checklist: #{number}\n\nCo-authored-by: {coauthor}\n"
        bot = ["-c", "user.name=github-actions[bot]", "-c", f"user.email={BOT_EMAIL}"]
        git(*bot, "commit", "-F", "-", data=message.encode())
        if errors := check(path):
            raise Rejected("\n".join(errors))
        git("push", "--force", "origin", branch)
        sha = git("rev-parse", "HEAD").strip()
        preview = f"https://media.githubusercontent.com/media/{repo}/{sha}/{quote(path.as_posix())}"
        body = f"Closes #{number}\n\n`{path}`\n\n![preview]({preview})\n\n{table}\n"
        if pr := gh("pr", "list", "--repo", repo, "--head", branch, "--json", "url", "--jq", ".[].url"):
            gh("pr", "edit", pr, "--repo", repo, "--title", subject, "--body", body)
            reply = f"Updated {pr}."
        else:
            pr = gh("pr", "create", "--repo", repo, "--head", branch, "--title", subject, "--body", body)
            reply = f"Opened {pr} for review."
        comment(reply)
    except Rejected as e:
        comment(f"Could not prepare image:\n\n{e}\n\nEdit this issue to try again.")
        sys.exit(1)
    except Exception:
        comment(f"Bot failed: {run_url}")
        raise


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["check", *paths] if paths:
            errors = [e for p in paths for e in check(Path(p))]
            print("\n".join(errors) or f"{len(paths)} file(s) OK")
            sys.exit(1 if errors else 0)
        case ["collage", out]:
            collage(Path(out))
        case ["submit"]:
            submit()
        case _:
            sys.exit(__doc__)
