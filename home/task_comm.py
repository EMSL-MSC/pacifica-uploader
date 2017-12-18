"""
provides a generic way to communicate from the background task
without the task knowing if celery is running
"""

import traceback

from celery import current_task

import json


class TaskComm(object):
    """
    essentially static class that provides a single conduit from the backend
    to the front end whether celery is being used or not.
    """

    # make the default true so that if the tasks are run under celery and
    # aren't updated by the config file, it is in the right state
    USE_CELERY = True

    state = {'TASK_STATE': '', 'TASK_INFO': ''}

    @classmethod
    def get_state(cls):
        """
        sets the state of the currently running task to
        be read by the front end task
        """
        state = cls.state['TASK_STATE']
        info = cls.state['TASK_INFO']

        return (state, info)

    @classmethod
    def set_state(cls, t_state, t_msg):
        """
        updates the task state
        """
        cls.state['TASK_STATE'] = t_state
        cls.state['TASK_INFO'] = t_msg

        print str(t_state) + ': ' + str(t_msg)

        if cls.USE_CELERY:
            # send message to the front end
            current_task.update_state(state=t_state, meta={'result': t_msg})

            state = cls.state['TASK_STATE']
            info = cls.state['TASK_INFO']
            ret = {'state': state, 'info': info}
            current_task.info = json.dumps(ret)

        print '%s:  %s' % (t_state, t_msg)


def task_error(t_msg):
    """
    sets the task state to FAILURE
    also log the error here
    """
    print 'ERROR: ' + t_msg + ':  ' + traceback.format_exc()
    TaskComm.set_state('ERROR', t_msg + ':  ' + traceback.format_exc())
