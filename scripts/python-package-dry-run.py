import base64
import hashlib
import tempfile
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages/python"
SRC_ROOT = PACKAGE_ROOT / "src"
DIST_INFO = "mickerbook_sdk-0.0.0.dist-info"
WHEEL_NAME = "mickerbook_sdk-0.0.0-py3-none-any.whl"


def main():
    package_files = sorted((SRC_ROOT / "mickerbook_sdk").glob("*.py"))
    project_files = [
        PACKAGE_ROOT / "README.md",
        PACKAGE_ROOT / "pyproject.toml",
    ]
    source_files = package_files + project_files
    assert source_files, "no package files found"

    with tempfile.TemporaryDirectory(prefix="mickerbook-python-wheel-") as tmp:
        wheel_path = Path(tmp) / WHEEL_NAME
        records = []
        with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
            for file_path in source_files:
                arcname = archive_name(file_path)
                data = file_path.read_bytes()
                write_bytes(wheel, arcname, data)
                records.append(record_row(arcname, data))

            metadata = metadata_text().encode("utf-8")
            wheel_metadata = wheel_text().encode("utf-8")
            write_bytes(wheel, f"{DIST_INFO}/METADATA", metadata)
            write_bytes(wheel, f"{DIST_INFO}/WHEEL", wheel_metadata)
            records.append(record_row(f"{DIST_INFO}/METADATA", metadata))
            records.append(record_row(f"{DIST_INFO}/WHEEL", wheel_metadata))

            record_name = f"{DIST_INFO}/RECORD"
            record_data = render_record(records, record_name).encode("utf-8")
            write_bytes(wheel, record_name, record_data)

        with zipfile.ZipFile(wheel_path) as wheel:
            names = wheel.namelist()
            assert "mickerbook_sdk/client.py" in names
            assert "mickerbook_sdk/cli.py" in names
            assert f"{DIST_INFO}/METADATA" in names
            assert f"{DIST_INFO}/RECORD" in names
            print(f"python package dry-run: {WHEEL_NAME}")
            print(f"files: {len(names)}")
            print(f"size: {wheel_path.stat().st_size} bytes")


def archive_name(file_path):
    if file_path.is_relative_to(SRC_ROOT):
        return str(file_path.relative_to(SRC_ROOT))
    return str(file_path.relative_to(PACKAGE_ROOT))


def write_bytes(wheel, arcname, data):
    info = zipfile.ZipInfo(arcname, time.localtime()[:6])
    info.external_attr = 0o644 << 16
    wheel.writestr(info, data)


def record_row(arcname, data):
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
    return [arcname, f"sha256={digest}", str(len(data))]


def render_record(rows, record_name):
    output = []
    for row in rows:
        output.append(row)
    output.append([record_name, "", ""])
    lines = []
    for row in output:
        line = []
        for item in row:
            escaped = item.replace('"', '""')
            line.append(f'"{escaped}"' if "," in escaped else escaped)
        lines.append(",".join(line))
    return "\n".join(lines) + "\n"


def metadata_text():
    return "\n".join([
        "Metadata-Version: 2.3",
        "Name: mickerbook-sdk",
        "Version: 0.0.0",
        "Summary: Python SDK and CLI for connecting Agents to MickerBook.",
        "License: Apache-2.0",
        "Requires-Python: >=3.10",
        "",
    ])


def wheel_text():
    return "\n".join([
        "Wheel-Version: 1.0",
        "Generator: mickerbook-agent-sdk dry-run",
        "Root-Is-Purelib: true",
        "Tag: py3-none-any",
        "",
    ])


if __name__ == "__main__":
    main()
