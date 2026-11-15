"""Offline archive checks: downloading over the network is never invoked."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from voc_olist.download import CSV_FILES, download_dataset


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "olist.zip"
        self.raw = self.root / "raw"

    def archive_with(self, names):
        contents = {}
        with ZipFile(self.archive, "w") as bundle:
            for name in names:
                content = f"column\ncontent for {Path(name).name}\n".encode("utf-8")
                bundle.writestr(name, content)
                contents[name] = content
        return contents

    def test_extracts_expected_four_files_and_records_verifiable_hashes(self):
        contents = self.archive_with(CSV_FILES)
        manifest = download_dataset(self.raw, archive=self.archive)
        self.assertEqual(set(manifest["files"]), set(CSV_FILES))
        self.assertEqual(manifest["archive_sha256"], hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(set(p.name for p in self.raw.iterdir()), {*CSV_FILES, "download_manifest.json"})
        for name in CSV_FILES:
            self.assertEqual((self.raw / name).read_bytes(), contents[name])
            self.assertEqual(manifest["files"][name]["sha256"], hashlib.sha256(contents[name]).hexdigest())
            self.assertEqual(manifest["files"][name]["bytes"], len(contents[name]))
        self.assertEqual(manifest, json.loads((self.raw / "download_manifest.json").read_text(encoding="utf-8")))

    def test_html_or_other_non_zip_fails_clearly(self):
        self.archive.write_text("<html>Login required</html>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "não é um ZIP válido"):
            download_dataset(self.raw, archive=self.archive)
        self.assertFalse((self.raw / CSV_FILES[0]).exists())
        self.assertFalse((self.raw / "download_manifest.json").exists())

    def test_missing_expected_csv_does_not_replace_existing_raw_files(self):
        self.raw.mkdir()
        existing = self.raw / CSV_FILES[0]
        existing.write_text("existing source", encoding="utf-8")
        self.archive_with(CSV_FILES[:-1])
        with self.assertRaisesRegex(ValueError, "obrigatório ausente"):
            download_dataset(self.raw, archive=self.archive)
        self.assertEqual(existing.read_text(encoding="utf-8"), "existing source")
        self.assertFalse((self.raw / "download_manifest.json").exists())

    def test_nested_names_work_but_destinations_are_fixed_basenames(self):
        names = [f"dataset/{name}" for name in CSV_FILES]
        contents = self.archive_with(names)
        download_dataset(self.raw, archive=self.archive)
        for name in CSV_FILES:
            self.assertEqual((self.raw / name).read_bytes(), contents[f"dataset/{name}"])
        self.assertFalse((self.raw / "dataset").exists())

    def test_traversal_and_unrelated_files_cannot_escape_raw_directory(self):
        # Even accepted CSV names are written to fixed destinations, never to
        # paths from the ZIP directory. Extra arbitrary files are ignored.
        names = [f"../../outside/{CSV_FILES[0]}", *CSV_FILES[1:], "../injected.py", "nested/ignored.txt"]
        contents = self.archive_with(names)
        download_dataset(self.raw, archive=self.archive)
        self.assertEqual((self.raw / CSV_FILES[0]).read_bytes(), contents[names[0]])
        self.assertFalse((self.root / "outside").exists())
        self.assertFalse((self.root / "injected.py").exists())
        self.assertFalse((self.raw / "nested").exists())
        self.assertEqual(set(p.name for p in self.raw.iterdir()), {*CSV_FILES, "download_manifest.json"})

    def test_duplicate_expected_basenames_are_rejected_as_ambiguous(self):
        self.archive_with([*CSV_FILES, f"nested/{CSV_FILES[0]}"])
        with self.assertRaisesRegex(ValueError, "ambíguo"):
            download_dataset(self.raw, archive=self.archive)
        self.assertFalse((self.raw / "download_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
