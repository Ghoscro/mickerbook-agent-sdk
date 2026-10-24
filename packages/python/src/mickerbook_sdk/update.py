"""Managed Skill/CLI updater. No credentials, shell commands or package execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MANIFEST = "https://mickerbook.com/.well-known/mickerbook-updates.json"
FILES = {"SKILL.md", "update.py", "micker.cjs"}
STATE = ".mickerbook-update.json"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(url, limit=2 * 1024 * 1024):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "mickerbook.com" or parsed.fragment or parsed.username:
        raise ValueError("Only official HTTPS downloads are accepted")
    with build_opener(NoRedirect).open(Request(url, headers={"User-Agent": "MickerBook-Updater/1"}), timeout=20) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Download exceeds size limit")
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError("Unsupported release version")
    return tuple(map(int, value.split(".")))


def atomic(path, data):
    fd, temp = tempfile.mkstemp(prefix=".micker-update-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _managed_root(directory):
    root = Path(directory).absolute()
    # Do not collapse traversal before inspecting links: link/../dir may
    # otherwise conceal a user-controlled ancestor.
    if ".." in root.parts:
        raise ValueError("Managed directory must not contain parent traversal")
    aliases = {Path("/var"): Path("/private/var"),
               Path("/tmp"): Path("/private/tmp"),
               Path("/etc"): Path("/private/etc")}
    canonical = root
    for candidate in (root, *root.parents):
        if not candidate.is_symlink():
            continue
        target = aliases.get(candidate)
        if (sys.platform != "darwin" or candidate == root or target is None
                or candidate.lstat().st_uid != 0
                or os.readlink(candidate) not in (str(target), str(target)[1:])):
            raise ValueError("Managed directory must not be a symlink")
        # Translate only the verified OS alias, never resolve arbitrary links.
        canonical = target / root.relative_to(candidate)
    if canonical.is_symlink() or any(parent.is_symlink() for parent in canonical.parents):
        raise ValueError("Managed directory must not be a symlink")
    return canonical


def sync(directory, *, apply=False, auto=False, enable_auto=False, disable_auto=False):
    root = _managed_root(directory)
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / STATE
    if state_path.is_symlink():
        raise ValueError("State must not be a symlink")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if disable_auto:
        state["autoUpdate"] = False
        atomic(state_path, json.dumps(state).encode())
        return {"ok": True, "autoUpdate": False}
    if auto and not enable_auto and time.time() - state.get("checkedAt", 0) < 86400:
        return {"ok": True, "cached": True, "installedVersion": state.get("version"), "latestVersion": state.get("latestVersion"), "updateAvailable": state.get("latestVersion") != state.get("version"), "autoUpdate": state.get("autoUpdate", False)}
    manifest = json.loads(download(MANIFEST, 128 * 1024))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("Upgrade the updater to support this manifest schema")
    latest = manifest["skillVersion"]
    if version(latest) < version(state.get("version", "0.0.0")):
        raise ValueError("Downgrade refused")
    if enable_auto:
        state["autoUpdate"] = True
    state.update(checkedAt=time.time(), latestVersion=latest)
    result = {"ok": True, "installedVersion": state.get("version"), "latestVersion": latest, "updateAvailable": latest != state.get("version"), "autoUpdate": state.get("autoUpdate", False), "releaseNotes": manifest.get("releaseNotes"), "packages": manifest.get("packages", {})}
    should_apply = apply or ((auto or enable_auto) and state.get("autoUpdate", False))
    if should_apply and result["updateAvailable"]:
        artifacts = manifest["skillFiles"]
        if not isinstance(artifacts, dict) or set(artifacts) != FILES:
            raise ValueError("Unexpected managed file set")
        staged, originals = {}, {}
        for name, item in artifacts.items():
            target = root / name
            if target.is_symlink():
                raise ValueError("Managed files must not be symlinks")
            original = target.read_bytes() if target.exists() else None
            if original is not None and digest(original) != state.get("hashes", {}).get(name):
                # Fresh installation may already contain the identical release file.
                if digest(original) != item["sha256"]:
                    raise ValueError(f"Local changes preserved: {name}")
            expected = item["sha256"]
            if not re.fullmatch(r"[a-f0-9]{64}", expected):
                raise ValueError("Invalid SHA256")
            payload = download(item["url"])
            if digest(payload) != expected:
                raise ValueError(f"Checksum mismatch: {name}")
            staged[name], originals[name] = payload, original
        # Downloads and local modification checks finish before replacing anything.
        backup = root / ".previous"
        if backup.is_symlink():
            raise ValueError("Backup must not be a symlink")
        backup.mkdir(exist_ok=True)
        for name, data in originals.items():
            if data is not None:
                atomic(backup / name, data)
        replaced = []
        try:
            for name, data in staged.items():
                # Refuse a concurrent edit made while downloads were in flight.
                target = root / name
                current = target.read_bytes() if target.exists() else None
                if target.is_symlink() or current != originals[name]:
                    raise ValueError(f"Concurrent change preserved: {name}")
                atomic(target, data)
                replaced.append(name)
            state.update(version=latest, hashes={name:digest(data) for name,data in staged.items()})
            atomic(state_path, json.dumps(state, indent=2).encode())
        except Exception:
            for name in reversed(replaced):
                if originals[name] is None:
                    (root / name).unlink()
                else:
                    atomic(root / name, originals[name])
            raise
        result.update(installedVersion=latest, updateAvailable=False, updated=True)
    else:
        atomic(state_path, json.dumps(state, indent=2).encode())
    return result


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check or update a managed MickerBook Skill/CLI folder")
    parser.add_argument("--dir", default=str(Path.home() / ".mickerbook" / "skill"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--auto", action="store_true", help="Check at most daily; apply only when auto-update is enabled")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enable-auto", action="store_true")
    mode.add_argument("--disable-auto", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(sync(args.dir, apply=args.apply, auto=args.auto, enable_auto=args.enable_auto, disable_auto=args.disable_auto), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
