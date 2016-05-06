from celery import current_task

USE_CELERY = False

global TASK_STATE
global TASK_INFO

def get_state():

    global TASK_STATE
    if not TASK_STATE:
        TASK_STATE = ''

    global TASK_INFO
    if not TASK_INFO:
        TASK_INFO = ''

    return (TASK_STATE, TASK_INFO)

def set_state(state, info):

    global TASK_STATE
    TASK_STATE = state

    global TASK_INFO
    TASK_INFO = info

    return (TASK_STATE, TASK_INFO)

def task_state(t_state, t_msg):
    """
    either uses celery for messaging or
    updates the task state locally
    """

    global TASK_STATE
    TASK_STATE = t_state

    global TASK_INFO
    TASK_INFO = t_msg

    if USE_CELERY:
        # send message to the front end
        current_task.update_state(state=t_state, meta={'Status': t_msg})

def task_error(t_msg):
    """
    sets the task state to FAILURE
    """
    task_state('FAILURE', t_msg)
