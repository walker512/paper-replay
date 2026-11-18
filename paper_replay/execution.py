"""Best-effort lifecycle cleanup for trusted scripts, not a sandbox."""
import contextlib
import os
import signal
import subprocess
import threading
import time

LOG_LIMIT=1024*1024
POLL_SECONDS=.01

class Cancelled(BaseException):
    def __init__(self,signum):self.signum=signum

@contextlib.contextmanager
def cancellation():
    # Python allows signal handlers only in its main thread.
    handlers={};state={'signal':None,'cleaning':False}
    def record(signum,frame):
        state['signal']=signum
        if not state['cleaning']:raise Cancelled(signum)
    try:
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT,signal.SIGTERM):
                handlers[sig]=signal.signal(sig,record)
        yield state
        if state['signal'] is not None:raise Cancelled(state['signal'])
    finally:
        for sig,handler in handlers.items():signal.signal(sig,handler)

def cleanup(process):
    # Always kill the original process group, even if its leader exited.
    # Descendants that deliberately create a new session can escape this.
    if os.name=='posix':
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    elif process.poll() is None:process.kill()
    process.wait(timeout=5)

def execute(command,cwd,stdout,stderr,timeout,env,state):
    process=None;reason=None;started=time.monotonic()
    try:
        state['cleaning']=True
        try:
            process=subprocess.Popen(command,cwd=cwd,stdout=stdout,stderr=stderr,
                stdin=subprocess.DEVNULL,env=env,start_new_session=(os.name=='posix'),
                **({'umask':0o077} if os.name=='posix' else {}))
        finally:state['cleaning']=False
        if state['signal'] is not None:raise Cancelled(state['signal'])
        while True:
            if max(os.fstat(stdout.fileno()).st_size,os.fstat(stderr.fileno()).st_size)>LOG_LIMIT:
                reason='output_limit';break
            if process.poll() is not None:break
            if time.monotonic()-started>=timeout:
                reason='timeout';break
            time.sleep(POLL_SECONDS)
        returncode=process.poll()
    finally:
        state['cleaning']=True
        try:
            if process is not None:cleanup(process)
            for stream in (stdout,stderr):
                if os.fstat(stream.fileno()).st_size>LOG_LIMIT:
                    reason='output_limit' if reason is None else reason
                    stream.truncate(LOG_LIMIT)
        finally:state['cleaning']=False
    if state['signal'] is not None:raise Cancelled(state['signal'])
    return returncode,reason
