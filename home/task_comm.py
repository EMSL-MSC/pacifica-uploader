from celery import current_task

USE_CELERY = False

TASK_STATE = ''
TASK_INFO = ''

def task_state(t_state, t_msg):
    """
    either uses celery for messaging or
    updates the task state locally
    """

    TASK_STATE = t_state
    TASK_INFO = t_msg

    if USE_CELERY:
        # send message to the front end
        current_task.update_state(state=t_state, meta={'Status': t_msg})

def task_error(t_msg):
    """
    sets the task state to FAILURE
    """
    task_state('FAILURE', t_msg)
