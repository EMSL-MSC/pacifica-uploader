"""
provides a generic way to communicate from the background task
without the task knowing if celery is running
"""
from celery import current_task

USE_CELERY = True

class TaskComm(object):
    """
    essentially static class that provides a single conduit from the backend
    to the front end whether celery is being used or not.
    """

    state = {'TASK_STATE':'', 'TASK_INFO':''}

    @classmethod
    def set_state(cls, state, info):
        """
        sets the state of the currently running task to
        be read by the front end task, whether celery is being used or not.
        """
        cls.state['TASK_STATE'] = state
        cls.state['TASK_INFO'] = info

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
    def task_state(cls, t_state, t_msg):
        """
        either uses celery for messaging or
        updates the task state locally
        """
        cls.set_state(t_state, t_msg)

        if USE_CELERY:
            # send message to the front end
            current_task.update_state(state=t_state, meta={'Status': t_msg})


def task_error(t_msg):
    """
    sets the task state to FAILURE
    also log the error here
    """
    TaskComm.task_state('FAILURE', t_msg)
