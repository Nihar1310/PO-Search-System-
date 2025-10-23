#!/usr/bin/env python3
import argparse
import io
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.cloud import storage

# ----------------------------
# Config & Constants
# ----------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_GDOC  = "application/vnd.google-apps.document"
MIME_GSHEET= "application/vnd.google-apps.spreadsheet"
MIME_GSLIDE= "application/vnd.google-apps.presentation"
MIME_GDRAW = "application/vnd.google-apps.drawing"

# Export mappings for Google-native files -> PDF
GSUITE_EXPORTS = {
    MIME_GDOC:  ("application/pdf", ".pdf"),
    MIME_GSHEET:("application/pdf", ".pdf"),
    MIME_GSLIDE:("application/pdf", ".pdf"),
    MIME_GDRAW: ("application/pdf", ".pdf"),
}

# ----------------------------
# Helpers
# ----------------------------

def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def safe_join(*parts: str) -> str:
    cleaned = []
    for p in parts:
        p = p.replace("\\", "/").strip("/")
        if p:
            cleaned.append(p)
    return "/".join(cleaned) + ("/" if cleaned and parts[-1].endswith("/") else "")

def ensure_creds(creds_path: str, token_path: str) -> Credentials:
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"client secret file not found: {creds_path}\n"
            "Download OAuth client (Desktop App) JSON from Google Cloud Console and point --creds to it."
        )
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
            print(f"🔐 Saved token to {token_path}")
    return creds

def drive_client(creds: Credentials):
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def storage_client():
    return storage.Client()

def list_children(service, folder_id: str) -> List[Dict]:
    """List direct children of a Drive folder (no recursion)."""
    files: List[Dict] = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed=false"
    while True:
        resp = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            pageSize=1000,
            pageToken=page_token,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files

def download_binary(service, file_id: str, name: str) -> Tuple[bytes, str]:
    """Download a binary/non-GSuite file; returns (bytes, mime)."""
    req = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"   ↳ downloading {name}: {int(status.progress() * 100)}%", end="\r")
    data = buf.getvalue()
    # fetch mime from metadata (lighter than another call; optional)
    meta = service.files().get(fileId=file_id, fields="mimeType", supportsAllDrives=True).execute()
    return data, meta.get("mimeType", "application/octet-stream")

def export_gsuite(service, file_id: str, name: str, export_mime: str) -> bytes:
    """Export GSuite file (Docs/Sheets/Slides/Drawings) to given mime (PDF)."""
    data = service.files().export(fileId=file_id, mimeType=export_mime).execute()
    # export returns bytes as raw response
    return data

def upload_gcs(client, bucket_name: str, dest_path: str, data: bytes, content_type: Optional[str] = None):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_file(io.BytesIO(data), rewind=True, content_type=content_type)
    size = human_size(len(data))
    print(f"   ✅ uploaded {dest_path} ({size})")

def is_allowed_type(name: str, allowed_exts: Optional[List[str]]) -> bool:
    if not allowed_exts:
        return True
    low = name.lower()
    return any(low.endswith(f".{ext.lower().lstrip('.')}") for ext in allowed_exts)

def sanitize_component(s: str) -> str:
    # basic cleanup for object names
    bad = '<>:"\\|?*\n\r\t'
    for ch in bad:
        s = s.replace(ch, "_")
    return s.strip()

def walk_and_transfer(
    service,
    gcs,
    drive_folder_id: str,
    bucket: str,
    prefix: str,
    convert_gsuite: bool,
    allowed_exts: Optional[List[str]],
    root_path_stack: List[str],
    counters: Dict[str, int]
):
    children = list_children(service, drive_folder_id)
    for f in children:
        name = sanitize_component(f["name"])
        mime = f["mimeType"]
        fid  = f["id"]
        if mime == MIME_FOLDER:
            # Recurse into subfolder
            print(f"📁 {safe_join(*(root_path_stack + [name]))} (folder)")
            walk_and_transfer(
                service, gcs, fid, bucket, prefix, convert_gsuite, allowed_exts,
                root_path_stack + [name], counters
            )
            continue

        dest_rel = safe_join(*root_path_stack, name)
        dest_gcs = safe_join(prefix, dest_rel)

        try:
            if mime in GSUITE_EXPORTS:
                if not convert_gsuite:
                    print(f"   ⚠️  skipping Google file (enable --convert-gsuite to export): {dest_rel}")
                    counters["skipped"] += 1
                    continue
                export_mime, ext = GSUITE_EXPORTS[mime]
                # Force .pdf extension
                base, _sep, _ext = name.partition(".")
                export_name = base if base else name
                export_name += ext
                dest_rel_pdf = safe_join(*root_path_stack, export_name)
                dest_gcs_pdf = safe_join(prefix, dest_rel_pdf)

                print(f"📝 exporting Google file → PDF: {name} → {export_name}")
                data = export_gsuite(service, fid, name, export_mime)
                if allowed_exts and "pdf" not in [e.lower().lstrip(".") for e in allowed_exts]:
                    print(f"   ⚠️  skipping (allowed types do not include pdf): {export_name}")
                    counters["skipped"] += 1
                    continue
                upload_gcs(gcs, bucket, dest_gcs_pdf, data, content_type=export_mime)
                counters["uploaded"] += 1
                continue

            # Binary files (pdf, images, etc.)
            if not is_allowed_type(name, allowed_exts):
                print(f"   ⚠️  skipping (not in allowed types): {dest_rel}")
                counters["skipped"] += 1
                continue

            print(f"⬇️  downloading: {dest_rel}")
            data, real_mime = download_binary(service, fid, name)
            upload_gcs(gcs, bucket, dest_gcs, data, content_type=real_mime)
            counters["uploaded"] += 1

        except HttpError as e:
            print(f"   ❌ HTTP error for {name}: {e}")
            counters["errors"] += 1
        except Exception as e:
            print(f"   ❌ error for {name}: {e}")
            counters["errors"] += 1


# ----------------------------
# Main
# ----------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Copy an entire Google Drive folder (recursively) to a GCS bucket, with optional GSuite→PDF export."
    )
    p.add_argument("--folder-id", required=True, help="Google Drive Folder ID (the long ID after /folders/ in the Drive URL)")
    p.add_argument("--bucket", required=True, help="Destination GCS bucket name (no gs:// prefix).")
    p.add_argument("--prefix", default="po-training/", help="GCS prefix (folder path) to upload under, e.g. 'po-training/'.")
    p.add_argument("--creds", default="client_secret.json", help="Path to OAuth client JSON (Desktop App).")
    p.add_argument("--token", default="token.json", help="Path to save/load OAuth user token JSON.")
    p.add_argument("--convert-gsuite", action="store_true", help="Export Google Docs/Sheets/Slides/Drawings to PDF before upload.")
    p.add_argument("--only-types", default="", help="Comma-separated list of file extensions to include (e.g. 'pdf,jpg,png'). Empty = all.")
    return p.parse_args()

def main():
    args = parse_args()

    # Normalize allowed extensions
    allowed_exts = [s.strip().lower().lstrip(".") for s in args.only_types.split(",") if s.strip()] or None

    # Sanity: creds exist
    if not os.path.exists(args.creds):
        print(f"❌ client secret not found at: {args.creds}")
        sys.exit(1)

    # Auth
    creds = ensure_creds(args.creds, args.token)
    drv = drive_client(creds)
    gcs = storage_client()

    # Summary counters
    counters = {"uploaded": 0, "skipped": 0, "errors": 0}

    print("============================================")
    print(" Drive → GCS transfer (recursive)")
    print(f"  Source Drive Folder ID : {args.folder_id}")
    print(f"  Destination GCS Bucket : {args.bucket}")
    print(f"  GCS Prefix             : {args.prefix}")
    print(f"  Convert Google files   : {'YES' if args.convert_gsuite else 'no'}")
    print(f"  Allowed extensions     : {', '.join(allowed_exts) if allowed_exts else '(all)'}")
    print("============================================")

    try:
        # Kick off recursive walk
        walk_and_transfer(
            service=drv,
            gcs=gcs,
            drive_folder_id=args.folder_id,
            bucket=args.bucket,
            prefix=args.prefix,
            convert_gsuite=args.convert_gsuite,
            allowed_exts=allowed_exts,
            root_path_stack=[],
            counters=counters
        )
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user.")
    finally:
        print("============================================")
        print(f" ✅ Uploaded: {counters['uploaded']}")
        print(f" ⚠️  Skipped : {counters['skipped']}")
        print(f" ❌ Errors  : {counters['errors']}")
        print(" Done.")

if __name__ == "__main__":
    main()
