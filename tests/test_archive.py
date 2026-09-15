import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import VaultSandbox


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.sandbox = VaultSandbox().__enter__()
        from lib import archive
        self.ar = archive

    def tearDown(self):
        self.sandbox.__exit__(None, None, None)

    def test_ensure_creates_skeleton(self):
        path = self.ar.ensure_archive()
        self.assertTrue(path.exists())
        self.assertIn("# 보관함", path.read_text())

    def test_append_creates_group_header(self):
        from lib.models import TaskBlock
        path = self.ar.ensure_archive()
        block = TaskBlock(top_text="보관 대상 #보관", has_archive_marker=True)
        self.ar.append_archived(path, date(2030, 6, 15), block)
        content = path.read_text()
        self.assertIn("## 2030-06", content)
        self.assertIn("- [ ] 보관 대상 #보관 (보관: 06-15)", content)

    def test_append_second_item_same_month(self):
        from lib.models import TaskBlock
        path = self.ar.ensure_archive()
        self.ar.append_archived(path, date(2030, 6, 10),
                                TaskBlock(top_text="A", has_archive_marker=True))
        self.ar.append_archived(path, date(2030, 6, 20),
                                TaskBlock(top_text="B", has_archive_marker=True))
        content = path.read_text()
        self.assertEqual(content.count("## 2030-06"), 1)
        self.assertLess(content.index("A"), content.index("B"))

    def test_append_new_month_group(self):
        from lib.models import TaskBlock
        path = self.ar.ensure_archive()
        self.ar.append_archived(path, date(2030, 6, 10),
                                TaskBlock(top_text="Jun A", has_archive_marker=True))
        self.ar.append_archived(path, date(2030, 7, 5),
                                TaskBlock(top_text="Jul A", has_archive_marker=True))
        content = path.read_text()
        self.assertIn("## 2030-06", content)
        self.assertIn("## 2030-07", content)
        self.assertLess(content.index("Jun A"), content.index("## 2030-07"))

    def test_append_preserves_children(self):
        from lib.models import TaskBlock
        path = self.ar.ensure_archive()
        block = TaskBlock(
            top_text="보관",
            has_archive_marker=True,
            children=["    - 메모", "    - [x] 서브"],
        )
        self.ar.append_archived(path, date(2030, 6, 15), block)
        content = path.read_text()
        self.assertIn("    - 메모", content)
        self.assertIn("    - [x] 서브", content)


if __name__ == "__main__":
    unittest.main()
