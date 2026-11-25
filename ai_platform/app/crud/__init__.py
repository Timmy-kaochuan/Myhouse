"""CRUD 包：统一导出各资源的异步 CRUD 函数。

约定：函数第一个参数为 AsyncSession，内部自行 commit；
调用方（路由/Celery 任务/智能体）无需管理事务。
"""
from app.crud.agent_run import (
    create_agent_run,
    delete_agent_run,
    get_agent_run,
    list_agent_runs,
    update_agent_run,
)
from app.crud.cfd_task import (
    create_cfd_task,
    delete_cfd_task,
    get_cfd_task,
    list_cfd_tasks,
    update_cfd_task,
)
from app.crud.design_case import (
    create_design_case,
    delete_design_case,
    get_design_case,
    list_design_cases,
    update_design_case,
)
from app.crud.experiment_record import (
    create_experiment_record,
    delete_experiment_record,
    get_experiment_record,
    list_experiment_records,
    update_experiment_record,
)
from app.crud.proxy_model import (
    create_proxy_model,
    delete_proxy_model,
    get_proxy_model,
    list_proxy_models,
    update_proxy_model,
)
from app.crud.user import (
    create_user,
    delete_user,
    get_user,
    get_user_by_email,
    list_users,
    update_user,
)

__all__ = [
    # user
    "create_user", "get_user", "get_user_by_email", "list_users", "update_user", "delete_user",
    # design_case
    "create_design_case", "get_design_case", "list_design_cases", "update_design_case", "delete_design_case",
    # cfd_task
    "create_cfd_task", "get_cfd_task", "list_cfd_tasks", "update_cfd_task", "delete_cfd_task",
    # proxy_model
    "create_proxy_model", "get_proxy_model", "list_proxy_models", "update_proxy_model", "delete_proxy_model",
    # agent_run
    "create_agent_run", "get_agent_run", "list_agent_runs", "update_agent_run", "delete_agent_run",
    # experiment_record
    "create_experiment_record", "get_experiment_record", "list_experiment_records",
    "update_experiment_record", "delete_experiment_record",
]
