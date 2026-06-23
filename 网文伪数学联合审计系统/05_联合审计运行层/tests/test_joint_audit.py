import subprocess,sys,unittest
from pathlib import Path
class JointAuditTests(unittest.TestCase):
    def test_embedded_suite(self):
        root=Path(__file__).resolve().parents[1]
        p=subprocess.run([sys.executable,str(root/'联合审计器.py'),'self-test'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('负向22项',p.stdout)
if __name__=='__main__': unittest.main()
