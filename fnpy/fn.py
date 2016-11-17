#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#######################################################
# @Autor:        Isaac.Zeng ~~~ zenggf@ufish.io
# @Setup Time:   Saturday, 30 November 2013.
# @Updated Time: 2014-01-15 15:17:07
# @Description:
#######################################################


from __future__ import print_function
import threading, time
from multiprocessing import Process, Pipe
from contextlib import contextmanager
import hashlib

try:
    # python 2
    import Queue
except:
    # python 3
    import queue as Queue

####################### Concurrence ###################
class future(threading.Thread):

    def __init__(self, fn, *args, **kwargs):
        threading.Thread.__init__(self)
        self.fn = lambda: fn(*args, **kwargs)
        self.val = None
        self.start()

    def run(self):
        self.val = self.fn()

    def deref(self, timeout_ms=None, timeout_val=None):
        self.join(timeout_ms and (timeout_ms / 1000.0))
        if self.is_alive():
            return timeout_val
        return self.val

    def __call__(self):
        return self.deref()


def deref(f, timeout_ms=None, timeout_val=None):
    return f.deref(timeout_ms, timeout_val)
#deref = future.deref


#def pmap(f, *seqs):
#    return map(deref, map(lambda args: future(f, *args), zip(*seqs)))

def pcall(fs):
    return map(deref, [future(f) for f in fs])

def inject_to(o):
    def inject(fn):
        setattr(o, fn.__name__, fn)
        #o.__setattr__(fn.func_name, fn)
    return inject

def set_interval(fn, start, interval=None):
    if not interval:
        interval = start
        start = 0

    def job():
        time.sleep(start)
        while not job.canceled:
            fn()
            time.sleep(job.interval)

    job.canceled = False
    job.interval = interval
    t = threading.Thread(target=job)

    @inject_to(t)
    def change_interval(interval):
        job.interval = interval

    @inject_to(t)
    def cancel():
        job.canceled = True
    t.start()

    return t

### p_map is not thread safe
def pmap(f, *seqs, **kwargs):
    argvs = list(zip(*seqs))
    argvs_len = len(argvs)
    q = Queue.Queue(min(argvs_len, kwargs.get('pool_size', 32)))
    #argvs = seqs
    def worker():
        for argv in argvs:
            q.put(future(f, *argv))
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()
    class ResultSet(object):
        def __init__(self, q, capacity):
            self.q = q
            self.capacity = capacity
        def next(self):
            if self.capacity > 0:
                self.capacity -= 1
                return deref(self.q.get())
            raise StopIteration
            #raise Exception("no more elements", "idiot!!!")
        #def has_next(self): return self.capacity > 0
        def __next__(self): return self.next()
        def __iter__(self): return self
        def doall(self): return list(self)
        def dorun(self):
            for i in self:
                pass
    return ResultSet(q, argvs_len)

def _exec(f, argv):
    def worker(cf, argv):
        try:
            cf.send(f(*argv))
        finally:
            cf.close()

    pf, cf = Pipe()
    p = Process(target=worker, args=(cf, argv))
    p.start()
    return pf

def ppmap(f, *seqs):
    return [pf.recv() for pf in [_exec(f, argv) for argv in zip(*seqs)]]

def pp_map(f, *seqs, **kwargs):
    q = Queue.Queue(kwargs.get('pool_size', 4))
    argvs = list(zip(*seqs))
    def run():
        for argv in argvs:
            q.put(_exec(f, argv))
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
    class ResultSet(object):
        def __init__(self, q, capacity):
            self.q = q
            self.capacity = capacity
        def __iter__(self): return self
        def next(self):
            if self.capacity > 0:
                self.capacity -= 1
                return self.q.get().recv()
            raise StopIteration
    return ResultSet(q, len(argvs))

####################### Concurrence END ###################


####################### Observer ######################

### Atom is a Observable object, implements by use Closure

class Atom(object):
    def __init__(self, v):
        self.v = v
        self.watchers = []

    def add_watch(self, k, w):
        self.watchers.append((k, w))
    def remove_watch(self, k, w):
        self.watchers.remove((k, w))

    def _notify_watchers(self, ov, nv):
        for k, w in self.watchers:
            try:
                w(k, self, ov, nv)
            except e:
                print(e)

    def reset(self, nv):
        ov = self.v
        self.v = nv
        self._notify_watchers(ov, self.v)
        return nv

    def swap(self, fn, *args, **kwargs):
        ov = self.v
        self.v = fn(self.v, *args, **kwargs)
        self._notify_watchers(ov, self.v)
        return nv


def add_watch(g, k, w): g.add_watch(k, w)
def remove_watch(g, k, w): g.remove_watch(k, w)
def reset(g, no): g.reset(no)
def swap(g, fn, *args, **kwargs): g.swap(fn, *args, **kwargs)
####################### Observer END ######################


####################### stream handler ####################
def dostream(ret, *ls):
    for l in ls:
        if hasattr(l, '__call__'):
            ret = l(ret)
        elif type(l) in (tuple, list):
            ret = l[0](ret, *l[1:])
        else:
            raise Exception("bad arguments", l)
    return ret

def donestream(ret, *ls):
    for l in ls:
        if hasattr(l, '__call__'):
            ret = l(ret)
        elif type(l) in (tuple, list):
            ret = l[0](*(l[1:]+type(l)((ret,))))
        else:
            raise Exception("bad arguments", l)
    return ret
####################### stream handler END####################


############################# util fn ########################
def key(item): return item[0]
def val(item): return item[1]

#get = dict.__getitem__
def get(x): return x.get()

def nth(l, idx): return l[idx]
def first(l): return l[0]
def second(l): return l[1]
def last(l): return l[-1]
def identity(x): return x;

def partial(f, *args, **kwargs):
    def partialed(*pargs, **pkwargs):
        _args = args + pargs
        kwargs.update(pkwargs)
        return f(*_args, **kwargs)
    partialed.__name__ == f.__name__
    return partialed

def rpartial(f, *args, **kwargs):
    def partialed(*pargs, **pkwargs):
        _args = pargs + args
        pkwargs.update(kwargs)
        return f(*_args, **pkwargs)
    partialed.__name__ == f.__name__
    return partialed


def md5(s):
    return hashlib.md5(s).hexdigest()

def currentTimeMillis():
    return int(time.time() * 1000)

def take(n, xs):
    i = 0
    for x in xs:
        if i >= n:
            break
        i += 1
        yield x

def drop(n, xs):
    i = 0
    for x in xs:
        if i < n:
            i += 1
            continue
        yield x

def  inc(x): return x + 1
def  dec(x): return x - 1

def dorun(xs):
    for x in xs:
        pass

def doall(xs):
    return [x for x in xs]


def assoc(coll, k, v):
    coll[k] = v
    return coll

def frequencies(coll):
    return reduce(
        lambda counts, x: assoc(counts, x, counts.get(x, 0) + 1),
        coll,
        {}
    )

def comp(*fs):
    if not fs:
        return identity
    rfs = fs[-2::-1]
    def _comp(*args, **kw):
        ret = fs[-1](*args, **kw)
        for f in rfs:
            ret = f(ret)
        return ret

    return _comp

def not_empty(xs):
    if not xs:
        return
    return xs

############################# util fn END ########################


############################## test util #####################
def timing(f):
    def wrapper(*args, **kwargs):
        t = time.time()
        try:
            return f(*args, **kwargs)
        finally:
            print("Elapsed time:", 1000 * (time.time() - t), "msecs")
    return wrapper
########################### test util END #####################


########################## multiple methods ###################
def defmulti(switcher_fn):
    def dispatcher(*args, **kwargs):
        key = switcher_fn(*args, **kwargs)
        func = dispatcher.dispatch_map.get(key)
        if func:
            return func(*args, **kwargs)
        raise Exception("No function defined for dispatch value: %s" % key)
    dispatcher.dispatch_map = {}
    return dispatcher

def defmethod(multi_fn, key):
    def inner(wrapped):
        multi_fn.dispatch_map[key] = wrapped
        return multi_fn
    return inner

######################### IO util #############################
def slurp(file_name):
    with open(file_name, 'r') as f:
        return f.read()

def spit(file_name, string, encoding="utf-8"):
    with open(file_name, 'w') as f:
        f.write(string)


########################### memoize ############################
def memoize(fn):
    mem = {}
    def wrapped(*args):
        ret = mem.get(args)
        if not ret:
            ret = fn(*args)
            mem[args] = ret
        return ret
    return wrapped



def pre(validate):
    def wrap(fn):
        def wrapped(*args, **kwargs):
            assert validate(*args, **kwargs)
            return fn(*args, **kwargs)
        return wrapped
    return wrap

def post(validate):
    def wrap(fn):
        def wrapped(*args, **kwargs):
            ret = fn(*args, **kwargs)
            assert validate(ret)
            return ret
        return wrapped
    return wrap

class Fn(object):
    def __init__(self):
        object.__init__(self)

    def __add__(self, other):
        return lambda x, y: x + y
    def __mul__(self, other):
        return lambda x, y: x * y
    def __div__(self, other):
        return lambda x, y: x / y



_ = Fn()

def coroutine(f):
    def starter(*args, **kwargs):
        cr = f(*args, **kwargs)
        cr.next()
        return cr
    return starter

def async(f):
    return lambda *args, **kwargs: future(f, *args, **kwargs)

def once(f):
    mem = [False, None]
    def onced(*args, **kwargs):
        if mem[0]:
            return mem[1]
        mem[1] = f(*args, **kwargs)
        mem[0] = True
        return mem[1]
    @inject_to(onced)
    def re_assign(*args, **kwargs):
        mem[1] = f(*args, **kwargs)
        mem[0] = True
        return mem[1]
    return onced

def lock(l):
    if hasattr(l, "__call__"):
        return lock(threading.Lock())(l)
    def wrap_lock(f):
        def locked(*args, **kwargs):
            with l:
                return f(*args, **kwargs)
        return locked
    return wrap_lock

def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton

class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)

class Pool(Queue.Queue):
    def __init__(self, ctor, pool_size):
        Queue.Queue.__init__(self, pool_size)
        self.ctor = ctor
        self.pool_size = pool_size

    @lock
    def new_value(self):
        if self.pool_size > 0:
            self.pool_size -= 1
            return self.ctor()

    @contextmanager
    def __call__(self):
        val = None
        if self.pool_size > 0 and self.empty():
            val = self.new_value()
        else:
            val = self.get()

        if not val:
            val = self.get()

        try:
            yield val
        finally:
            self.put(val)

def pool(pool_size):
    """
    Decorator
    """
    def pooled(f):
        return Pool(f, pool_size=pool_size)
    return pooled

def pr_str(x):
    return repr(x).decode("unicode-escape")

def prn(*args):
    print(" ".join(map(pr_str, args)))

def pr(*args):
    print(" ".join(map(pr_str, args)), end="")

def parse_command_line(args):
    return {args[i].replace("--", ""): args[i+1] for i in range (0, len(args), 2)}
