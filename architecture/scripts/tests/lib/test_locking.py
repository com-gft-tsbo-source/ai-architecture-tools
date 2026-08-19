import json
import logging
import tempfile
import threading
import time
import unittest
from pathlib import Path

from lib.locking import FileLock, lock_path_for


class TestLockPathFor(unittest.TestCase):
    def test_directory_target_locks_inside_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(lock_path_for(Path(tmp)), Path(tmp) / ".lock")

    def test_file_target_locks_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "objects.md"
            target.write_text("x", encoding="utf-8")
            self.assertEqual(lock_path_for(target), Path(tmp) / "objects.md.lock")


class TestNormalCycle(unittest.TestCase):
    def test_acquire_then_release_removes_lock_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = FileLock(Path(tmp))
            lock.acquire()
            self.assertTrue(lock.lock_path.exists())
            lock.release()
            self.assertFalse(lock.lock_path.exists())

    def test_context_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FileLock(Path(tmp)) as lock:
                self.assertTrue(lock.lock_path.exists())
            self.assertFalse(lock.lock_path.exists())

    def test_release_without_acquire_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            FileLock(Path(tmp)).release()  # must not raise


class TestUnrelatedTargetsNeverBlock(unittest.TestCase):
    def test_two_roots_acquire_concurrently_without_waiting(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            lock_a = FileLock(Path(tmp_a), timeout=5)
            lock_b = FileLock(Path(tmp_b), timeout=5)
            lock_a.acquire()
            started = time.monotonic()
            lock_b.acquire()  # must return immediately, not wait for lock_a
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 1.0)
            lock_a.release()
            lock_b.release()


class TestSteal(unittest.TestCase):
    def test_waiting_instance_steals_after_timeout_and_logs_previous_holder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            holder = FileLock(root)
            holder.acquire()
            previous_payload = json.loads(holder.lock_path.read_text(encoding="utf-8"))

            waiter = FileLock(root, timeout=0.05, poll_interval=0.01)
            with self.assertLogs("workctl.locking", level="WARNING") as captured:
                waiter.acquire()
            self.assertTrue(waiter._acquired)
            self.assertIn(str(previous_payload["pid"]), captured.output[0])
            self.assertIn(previous_payload["acquired"], captured.output[0])

            new_payload = json.loads(waiter.lock_path.read_text(encoding="utf-8"))
            self.assertNotEqual(new_payload["acquired"], previous_payload["acquired"])
            waiter.release()

    def test_concurrent_threads_one_waits_and_steals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = FileLock(root, timeout=5)
            first.acquire()

            second = FileLock(root, timeout=0.1, poll_interval=0.01)
            result = {}

            def run_second():
                second.acquire()
                result["acquired"] = True

            thread = threading.Thread(target=run_second)
            logging.getLogger("workctl.locking").disabled = True
            try:
                thread.start()
                thread.join(timeout=2)
            finally:
                logging.getLogger("workctl.locking").disabled = False

            self.assertTrue(result.get("acquired"))
            first.release()
            second.release()


if __name__ == "__main__":
    unittest.main()
