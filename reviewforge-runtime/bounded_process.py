"""Bound compiler lifetime including descendants holding inherited output pipes."""
import os
import signal
import subprocess


def _windows_job():
    import ctypes
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',w.DWORD),
                  ('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),('active_limit',w.DWORD),
                  ('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
    class IO(ctypes.Structure):
        _fields_=[(name,ctypes.c_ulonglong) for name in ('reads','writes','other','read_bytes','write_bytes','other_bytes')]
    class Extended(ctypes.Structure):
        _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
    kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];kernel.SetInformationJobObject.restype=w.BOOL
    kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];kernel.AssignProcessToJobObject.restype=w.BOOL
    kernel.TerminateJobObject.argtypes=[w.HANDLE,w.UINT];kernel.TerminateJobObject.restype=w.BOOL
    kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
    job=kernel.CreateJobObjectW(None,None)
    if not job:raise ctypes.WinError(ctypes.get_last_error())
    info=Extended();info.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job,9,ctypes.byref(info),ctypes.sizeof(info)):
        error=ctypes.WinError(ctypes.get_last_error());kernel.CloseHandle(job);raise error
    return kernel,job


def _resume_windows_process(kernel,pid):
    """Resume the primary thread only after job assignment; no child can escape first."""
    import ctypes
    from ctypes import wintypes as w
    class ThreadEntry(ctypes.Structure):
        _fields_=[('size',w.DWORD),('usage',w.DWORD),('thread_id',w.DWORD),('owner_pid',w.DWORD),
                  ('base_priority',w.LONG),('delta_priority',w.LONG),('flags',w.DWORD)]
    kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
    kernel.Thread32First.argtypes=[w.HANDLE,ctypes.POINTER(ThreadEntry)];kernel.Thread32First.restype=w.BOOL
    kernel.Thread32Next.argtypes=[w.HANDLE,ctypes.POINTER(ThreadEntry)];kernel.Thread32Next.restype=w.BOOL
    kernel.OpenThread.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenThread.restype=w.HANDLE
    kernel.ResumeThread.argtypes=[w.HANDLE];kernel.ResumeThread.restype=w.DWORD
    snapshot=kernel.CreateToolhelp32Snapshot(0x4,0)  # TH32CS_SNAPTHREAD
    if snapshot==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry=ThreadEntry();entry.size=ctypes.sizeof(entry)
        more=kernel.Thread32First(snapshot,ctypes.byref(entry))
        while more:
            if entry.owner_pid==pid:
                thread=kernel.OpenThread(0x2,False,entry.thread_id)  # THREAD_SUSPEND_RESUME
                if not thread:raise ctypes.WinError(ctypes.get_last_error())
                try:
                    if kernel.ResumeThread(thread)==0xFFFFFFFF:raise ctypes.WinError(ctypes.get_last_error())
                    return
                finally:kernel.CloseHandle(thread)
            more=kernel.Thread32Next(snapshot,ctypes.byref(entry))
        raise OSError('Suspended compiler primary thread was not found')
    finally:kernel.CloseHandle(snapshot)


def run_process_tree(args,cwd=None,timeout=180):
    windows=os.name=='nt';kernel=None;job=None;process=None
    if windows:kernel,job=_windows_job()
    options={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW|0x4} if windows else {'start_new_session':True}  # CREATE_SUSPENDED
    try:
        process=subprocess.Popen(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace',**options)
        if windows and not kernel.AssignProcessToJobObject(job,int(process._handle)):
            # Fail closed instead of launching an unbounded compiler.
            import ctypes
            error=ctypes.WinError(ctypes.get_last_error())
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
            process.communicate(timeout=3);raise error
        if windows:_resume_windows_process(kernel,process.pid)
        try:stdout,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if windows:kernel.TerminateJobObject(job,1)
            else:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            stdout,stderr=process.communicate(timeout=3)
            raise subprocess.TimeoutExpired(args,timeout,output=stdout,stderr=stderr) from None
        return subprocess.CompletedProcess(args,process.returncode,stdout,stderr)
    finally:
        if windows and job:kernel.CloseHandle(job)
