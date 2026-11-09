"""PERSONA IA portable components M4-M6. Pure Python 3.10+, no network or GPU."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import hashlib, json, os, re, tempfile, time, uuid
from urllib.parse import urlparse

class ValidationError(ValueError): pass

@dataclass(frozen=True)
class ModelManifest:
    model_id: str
    version: str
    url: str
    license: str
    sha256: str
    size_bytes: int
    runtime: str
    architecture: str = 'arm64-v8a'
    def validate(self) -> None:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{1,127}', self.model_id) or '..' in self.model_id: raise ValidationError('invalid model_id')
        if not all(isinstance(x,str) and x.strip() for x in (self.version,self.license,self.runtime)): raise ValidationError('missing model metadata')
        p=urlparse(self.url)
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.fragment: raise ValidationError('HTTPS URL required')
        if not re.fullmatch('[0-9a-fA-F]{64}',self.sha256): raise ValidationError('invalid SHA256')
        if type(self.size_bytes) is not int or self.size_bytes<=0: raise ValidationError('invalid size')
        if self.architecture!='arm64-v8a': raise ValidationError('unsupported architecture')

def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()

def verify_model(path:Path, manifest:ModelManifest) -> bool:
    manifest.validate()
    p=Path(path)
    return p.is_file() and p.stat().st_size==manifest.size_bytes and sha256_file(p).lower()==manifest.sha256.lower()

def atomic_json(path:Path, data:dict) -> None:
    """Crash-safe replacement of metadata file; no user-media deletion."""
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=str(path.parent),prefix='.persona-',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,sort_keys=True,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

@dataclass(frozen=True)
class ThermalReading:
    battery_c: float
    available_ram_mb: int
    battery_percent: int
    charging: bool=False

@dataclass(frozen=True)
class ResourcePolicy:
    max_battery_c: float=42.0
    min_ram_mb: int=1024
    min_battery_percent: int=20
    def assess(self, reading:ThermalReading) -> tuple[bool,list[str]]:
        reasons=[]
        if reading.battery_c>=self.max_battery_c: reasons.append('thermal_limit')
        if reading.available_ram_mb<self.min_ram_mb: reasons.append('memory_limit')
        if reading.battery_percent<self.min_battery_percent and not reading.charging: reasons.append('battery_limit')
        return not reasons,reasons

STATES={'queued','running','paused','completed','failed','cancelled'}
TRANSITIONS={'queued':{'running','cancelled'},'running':{'paused','completed','failed','cancelled'},'paused':{'running','cancelled'},'failed':{'queued'},'completed':set(),'cancelled':set()}

@dataclass
class Job:
    job_id:str
    kind:str
    state:str='queued'
    progress:int=0
    result_path:Optional[str]=None
    error:Optional[str]=None
    def transition(self, state:str) -> None:
        if state not in TRANSITIONS[self.state]: raise ValidationError(f'invalid transition {self.state}->{state}')
        self.state=state
    def update_progress(self, progress:int) -> None:
        if self.state!='running' or type(progress) is not int or not self.progress<=progress<=100: raise ValidationError('invalid progress')
        self.progress=progress

class JobStore:
    """Local JSON state, no scheduler or background processing implied."""
    def __init__(self,root:Path): self.root=Path(root)
    def create(self,kind:str) -> Job:
        if kind not in {'photo','video','download','reference_analysis'}: raise ValidationError('unknown job kind')
        job=Job(str(uuid.uuid4()),kind);self.save(job);return job
    def save(self,job:Job) -> None:
        if job.state not in STATES or not re.fullmatch('[0-9a-f-]{36}',job.job_id): raise ValidationError('invalid job')
        atomic_json(self.root/(job.job_id+'.json'),asdict(job))
    def load(self,job_id:str) -> Job:
        if not re.fullmatch('[0-9a-f-]{36}',job_id): raise ValidationError('invalid id')
        data=json.loads((self.root/(job_id+'.json')).read_text(encoding='utf-8'))
        job=Job(**data)
        if job.state not in STATES: raise ValidationError('invalid stored state')
        return job

ANGLES={'front','left_profile','right_profile','back','three_quarter_left','three_quarter_right'}
DISTANCES={'closeup','medium','full_body'}
@dataclass(frozen=True)
class Reference:
    asset_id:str
    angle:str
    distance:str
    approved:bool=True

def coverage(references:list[Reference]) -> dict:
    """Metadata-based completeness; does NOT recognize faces or infer identity."""
    valid=[r for r in references if r.approved and r.angle in ANGLES and r.distance in DISTANCES]
    present_angles={r.angle for r in valid}; present_distances={r.distance for r in valid}
    return {'approved_count':len(valid),'missing_angles':sorted(ANGLES-present_angles), 'missing_distances':sorted(DISTANCES-present_distances), 'complete':present_angles==ANGLES and present_distances==DISTANCES}

@dataclass(frozen=True)
class VideoPlan:
    source_asset_id:str
    width:int
    height:int
    fps:int
    duration_seconds:float
    def validate(self) -> None:
        if not self.source_asset_id or any(type(x) is not int for x in (self.width,self.height,self.fps)): raise ValidationError('invalid video metadata')
        if not 1<=self.fps<=60 or not 1<=self.width<=4096 or not 1<=self.height<=4096: raise ValidationError('video bounds exceeded')
        if not 0<self.duration_seconds<=30: raise ValidationError('duration out of bounds')
        if self.width*self.height*self.fps*self.duration_seconds>4096*2160*30*10: raise ValidationError('frame budget exceeded')
    @property
    def frame_count(self)->int:
        self.validate();return round(self.fps*self.duration_seconds)

def provenance_record(input_ids:list[str],output_path:Path,engine:str,model_id:str,parameters:dict)->dict:
    """Local audit metadata, not cryptographic authenticity certification."""
    if not engine or not model_id or not Path(output_path).is_file(): raise ValidationError('missing output or engine')
    return {'schema':'persona.provenance.v1','input_asset_ids':list(input_ids),'output_sha256':sha256_file(output_path),'engine':engine,'model_id':model_id,'parameters':parameters,'timestamp_utc':int(time.time())}
