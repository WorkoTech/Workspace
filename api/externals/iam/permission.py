import logging
logger = logging.getLogger(__name__)

from api.externals.http import Http
from api.externals.iam.abstract import AbstractExternalIAM
from api.models.workspace_permission import WorkspacePermission


class ExternalWorkspacePermission(AbstractExternalIAM):
    @staticmethod
    def __get_permission_url(workspace_id):
        return f"{ExternalWorkspacePermission.IAM_BASE_URL}/permission/workspace/{workspace_id}"

    @staticmethod
    def get(token, workspace_id):
        logger.info("Fetching workspace user permissions")
        try:
            response = Http.get(
                ExternalWorkspacePermission.__get_permission_url(workspace_id),
                token=token
            )
        except Exception as e:
            logger.warning("Unable to fetch workspace user permissions")
            return None

        if response.status_code == 200:
            return WorkspacePermission(response.json()['accessLevel'])
        return None

    @staticmethod
    def set(token, workspace_id, permission):
        logger.info("Setting workspace user permissions")
        body = { 'accessLevel': permission.name }

        try:
            response = Http.post(
                ExternalWorkspacePermission.__get_permission_url(workspace_id),
                token=token,
                body=body
            )
        except Exception as e:
            logger.error("Unable to set user workspace permissions", e)
            return False

        if response.status_code == 201:
            logger.info("User workspace permissions successfully set")
            return True
        return False
