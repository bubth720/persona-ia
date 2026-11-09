import hashlib, json, tempfile, unittest
from pathlib import Path
from persona_components.core import *

class ComponentsTest(unittest.TestCase):
 def test_manifest_and_file(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'weights';p.write_bytes(b'weights')
   m=ModelManifest('example/model','1','https://example.org/weights','test',hashlib.sha256(b'weights').hexdigest(),7,'cpu')
   self.assertTrue(verify_model(p,m));p.write_bytes(b'corrupt');self.assertFalse(verify_model(p,m))
 def test_manifest_rejects_http(self):
  m=ModelManifest('a/b','1','http://bad.org','test','0'*64,1,'cpu')
  with self.assertRaises(ValidationError):m.validate()
 def test_manifest_rejects_boolean_size(self):
  m=ModelManifest('a/b','1','https://good.org','test','0'*64,True,'cpu')
  with self.assertRaises(ValidationError):m.validate()
 def test_job_persistence_and_transitions(self):
  with tempfile.TemporaryDirectory() as d:
   s=JobStore(Path(d));j=s.create('photo');j.transition('running');j.update_progress(55);s.save(j)
   self.assertEqual(s.load(j.job_id).progress,55)
   with self.assertRaises(ValidationError):j.transition('queued')
   with self.assertRaises(ValidationError):j.update_progress(20)
 def test_atomic_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';atomic_json(p,{'a':1});atomic_json(p,{'a':2});self.assertEqual(json.loads(p.read_text())['a'],2)
 def test_thermal(self):
  p=ResourcePolicy();self.assertEqual(p.assess(ThermalReading(43,4000,90))[1],['thermal_limit'])
  self.assertTrue(p.assess(ThermalReading(30,4000,90))[0])
 def test_coverage(self):
  r=[Reference('1','front','closeup'),Reference('2','back','full_body',False)]
  result=coverage(r);self.assertIn('back',result['missing_angles']);self.assertEqual(result['approved_count'],1)
 def test_video(self):
  p=VideoPlan('asset',1024,768,24,5);self.assertEqual(p.frame_count,120)
  with self.assertRaises(ValidationError):VideoPlan('asset',1024,768,120,5).validate()
 def test_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'out';p.write_bytes(b'image')
   result=provenance_record(['ref'],p,'mock','model',{'seed':42})
   self.assertEqual(result['output_sha256'],hashlib.sha256(b'image').hexdigest())

if __name__=='__main__':unittest.main()
