from find_worker_config.utils import LogActivityModule

# CreateLog(
#     request=request, log_status=LogStatus.SUCCESS, action="OFFICE LOCATION UPDATE", user=self.request.user, user_type=UserDefault.PROVIDER,
#     entity=address, for_notify=False, metadata={"message": "Update Your Office Location"}
# )
def CreateLog(request, log_status, action, user=None, user_type=None, entity=None, for_notify=False, metadata={}):
    data = {
        "status": log_status,
        "action": action,
        "user": user,
        "user_type": user_type,
        "entity": entity,
        "for_notify": for_notify,
        "metadata": metadata,
        "request": request
    }
    log = LogActivityModule(data)
    log.create()

