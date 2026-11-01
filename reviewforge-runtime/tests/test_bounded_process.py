import subprocess
import sys
import time
import unittest
from bounded_process import run_process_tree


class BoundedProcessTests(unittest.TestCase):
    def test_normal_process_output(self):
        result=run_process_tree([sys.executable,'-c','print("complete")'],timeout=5)
        self.assertEqual(result.returncode,0);self.assertIn('complete',result.stdout)

    def test_timeout_covers_child_process_inheriting_output_pipe(self):
        script='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);time.sleep(30)'
        started=time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):run_process_tree([sys.executable,'-c',script],timeout=.5)
        self.assertLess(time.monotonic()-started,8)

    @unittest.skipUnless(sys.platform=='win32','Windows native compiler-wrapper containment')
    def test_fast_native_wrapper_cannot_leave_descendants_holding_pipes(self):
        import os
        started=time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):run_process_tree([os.environ.get('COMSPEC','cmd.exe'),'/d','/c','powershell.exe','-NoProfile','-NonInteractive','-Command','Start-Sleep','-Seconds','30'],timeout=.5)
        self.assertLess(time.monotonic()-started,8)


if __name__=='__main__':unittest.main()
