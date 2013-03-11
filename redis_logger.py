# -*- coding: utf-8 -*-
from datetime import datetime
from django.db.backends import BaseDatabaseWrapper

from debug_toolbar.panels import DebugPanel
from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.utils import ms_from_timedelta
from debug_toolbar.utils.tracking import replace_call

import types
import inspect
import redis
from redis import StrictRedis

# def replace_call(func):
#     def inner(callback):
#         def wrapped(*args,**kwargs):
#             print 'wrapped'
#             print 'callback',callback
#             print 'f',func
#             print 'args',args
#             print 'kwargs',kwargs
#             print '**************'
#             return callback(func,*args,**kwargs)
#         actual = getattr(func,'__wrapped__',func)
#         wrapped.__wrapped__ = actual
#         wrapped.__doc__ = getattr(actual,'__doc__',None)
#         wrapped.__name__ = actual.__name__
#         print 'actual',actual
#         print 'wrapped',wrapped
#         _replace_function(func,wrapped)
#         return wrapped
#     return inner
#
# def _replace_function(func,wrapped):
#     print 'replace'
#     print 'func',func
#     print dir(func)
#     if isinstance(func,types.FunctionType):
#         pass
#     elif getattr(func,'im_self',None):
#         pass
#     elif hasattr(func,'im_class'):
#         setattr(func.im_class,func.__name__,wrapped)
#     else:
#         raise
#     print '*******'

def _get_func_info():
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe,2)
    return calframe

@replace_call(redis.StrictRedis.execute_command)
def execute_command(func,self,*args,**options):

    command = args[0]
    start = datetime.now()
    result = func(self,*args,**options)

    stop = datetime.now()
    duration = ms_from_timedelta(stop - start)

    #TODO find more better way to get the calling func info
    calframe = _get_func_info()

    params = {
        'func':calframe[4][3],
        'func_path':"{}:{}".format(calframe[4][1],calframe[4][2]),
        'command':command,
        'result':result,
        'start_time':start,
        'stop_time':stop,
        'duration':duration,
        'is_slow':None,

    }

    #TODO more better way to loggging?
    djdt = DebugToolbarMiddleware.get_current()
    if not djdt:
        return result
    logger = djdt.get_panel(RedisDebugPanel)
    logger.record(**params)

    return result


class RedisDebugPanel(DebugPanel):
    name = 'Redis'
    template = 'debug_toolbar/panels/redis.html'
    has_content = True

    def __init__(self,*args,**kwargs):
        super(RedisDebugPanel, self).__init__(*args, **kwargs)
        self._keys = list()
        self._num_commands = 0
        self._total_time = 0

    def record(self,**kwargs):
        self._keys.append(kwargs)
        self._total_time += kwargs['duration']
        self._num_commands += 1

    def title(self):
        return 'REDIS LOGGER'

    def nav_title(self):
        return 'REDIS LOGGER'

    def url(self):
        return ''

    def process_response(self,request,response):

        if self._keys:
            self.record_stats({
            'keys':self._keys,
            'total_time':self._total_time,
            'commands_num':self._num_commands,
            })



