import unittest
from jevscout.application.feed_refresh import next_attempt_at, historical_due_at

class FeedRefreshScheduleTests(unittest.TestCase):
    def test_success_uses_twelve_hours_and_failure_uses_day(self):
        self.assertEqual(next_attempt_at(1000, 'completed'), 1000 + 12 * 3600)
        self.assertEqual(next_attempt_at(1000, 'failed'), 1000 + 24 * 3600)
        self.assertEqual(next_attempt_at(1000, 'partial'), 1000 + 24 * 3600)

    def test_persisted_future_deadline_wins_over_old_history(self):
        self.assertEqual(historical_due_at(5000, 1000, 'completed', 60000), 60000)
        self.assertEqual(historical_due_at(5000, None, None, None), 5000)

    def test_stop_before_due_preserves_future_schedule_without_fetching(self):
        import json, tempfile, threading, time
        from pathlib import Path
        from jevscout.application.feed_refresh import FEEDS, run_worker
        from jevscout.storage.filesystem import FileRunStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'feed-refresh'; folder.mkdir()
            future = time.time() + 7200
            (folder / 'state.json').write_text(json.dumps({'version':1,'feeds':{name:{'next_attempt_at':future} for name in FEEDS},'next_global_at':0}))
            stop = threading.Event(); stop.set()
            run_worker(root, stop)
            state = json.loads((folder / 'state.json').read_text())
            self.assertEqual(state['status'], 'stopped')
            self.assertTrue(all(x['next_attempt_at'] >= future for x in state['feeds'].values()))
            self.assertEqual(FileRunStore(root).list_runs(), [])

    def test_cli_status_and_graceful_stop_without_network(self):
        import json, os, subprocess, sys, tempfile, time
        from pathlib import Path
        from jevscout.application.feed_refresh import FEEDS
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); folder = root / 'feed-refresh'; folder.mkdir()
            future = time.time() + 7200
            (folder / 'state.json').write_text(json.dumps({'version':1,'feeds':{name:{'next_attempt_at':future} for name in FEEDS},'next_global_at':0}))
            env = os.environ.copy(); env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2] / 'src')
            command = [sys.executable, '-m', 'jevscout.application.feed_refresh', '--data-dir', str(root)]
            worker = subprocess.Popen(command + ['--approve'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                for _ in range(100):
                    status = subprocess.run(command + ['--status'], env=env, capture_output=True, text=True, check=True)
                    if json.loads(status.stdout)['worker_running']: break
                    time.sleep(.05)
                else: self.fail('worker did not acquire its lock')
                result = subprocess.run(command + ['--stop'], env=env, capture_output=True, text=True, check=True)
                self.assertIn('Stop requested', result.stdout)
                worker.communicate(timeout=10)
                self.assertEqual(worker.returncode, 0)
                status = subprocess.run(command + ['--status'], env=env, capture_output=True, text=True, check=True)
                self.assertFalse(json.loads(status.stdout)['worker_running'])
            finally:
                if worker.poll() is None: worker.terminate(); worker.wait(timeout=5)
