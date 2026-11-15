from enum import Enum
class Role(str, Enum):
    admin = 'admin'
    analyst = 'analyst'
    viewer = 'viewer'
class JobStatus(str, Enum):
    queued = 'queued'
    running = 'running'
    completed = 'completed'
    failed = 'failed'
class ReconStatus(str, Enum):
    pending = 'pending'
    mismatch = 'mismatch'
    confirmed = 'confirmed'
    revoked = 'revoked'
